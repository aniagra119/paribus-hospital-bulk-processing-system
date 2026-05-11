"""
Batch Processor — Orchestration logic for bulk hospital creation.

This module contains the background task functions that:
1. Dispatch concurrent HTTP requests to the upstream API.
2. Update the BatchStateManager with row-level results.
3. Trigger batch activation when at least one row succeeds.

Used by both the initial /bulk upload and the /bulk/{batch_id}/resume endpoint.
"""

import asyncio
import logging
import time

from app.core.exceptions import UpstreamAPIError
from app.core.state import batch_state_manager
from app.services.hospital_client import HospitalClient

logger = logging.getLogger(__name__)


async def _process_single_row(
    client: HospitalClient,
    batch_id: str,
    row_number: int,
    payload: dict,
) -> None:
    """Process a single hospital row — create it via the upstream API and update state."""
    try:
        result = await client.create_hospital(payload)
        hospital_id = result.get("id")
        batch_state_manager.update_row_status(
            batch_id=batch_id,
            row_number=row_number,
            status="success",
            hospital_id=hospital_id,
        )
    except Exception as exc:
        logger.warning("Row %d in batch %s failed: %s", row_number, batch_id, exc)
        batch_state_manager.update_row_status(
            batch_id=batch_id,
            row_number=row_number,
            status="failed",
            error=str(exc),
        )


async def process_batch(client: HospitalClient, batch_id: str) -> None:
    """
    Core processing logic: process all pending rows in a batch concurrently.

    After all rows are processed, attempts batch activation if at least
    one hospital was created successfully.
    """
    start_time = time.time()
    batch = batch_state_manager.get_batch(batch_id)

    # Only process rows that are still "pending"
    pending_rows = [row for row in batch.rows if row.status == "pending"]

    # Dispatch all pending rows concurrently
    tasks = [
        _process_single_row(
            client=client,
            batch_id=batch_id,
            row_number=row.row_number,
            payload={**row.payload, "creation_batch_id": batch_id},
        )
        for row in pending_rows
    ]
    await asyncio.gather(*tasks)

    # Attempt activation if at least one row succeeded
    batch = batch_state_manager.get_batch(batch_id)
    activated = False
    if batch.processed_count > 0:
        try:
            activated = await client.activate_batch(batch_id)
        except UpstreamAPIError as exc:
            logger.error("Batch activation failed for %s: %s", batch_id, exc)

    elapsed = round(time.time() - start_time, 2)
    batch_state_manager.mark_batch_completed(
        batch_id, activated=activated, elapsed=elapsed
    )

    elapsed = round(time.time() - start_time, 2)
    logger.info(
        "Batch %s completed in %.2fs — %d/%d succeeded, activated=%s",
        batch_id,
        elapsed,
        batch.processed_count,
        batch.total_rows,
        activated,
    )
