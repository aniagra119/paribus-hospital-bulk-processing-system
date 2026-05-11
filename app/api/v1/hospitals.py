"""
Hospital Bulk Processing API endpoints.

This module defines all route handlers for the bulk processing system.
Routes are intentionally thin — they validate inputs, delegate to services,
and return structured responses. All business logic lives in services/.
"""

import asyncio
import logging

from typing import Union

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from app.api.dependencies import get_hospital_client
from app.core.exceptions import CSVValidationError
from app.core.state import batch_state_manager
from app.models.schemas import (
    BatchResultResponse,
    BulkUploadResponse,
    CSVValidationResponse,
    HospitalRowResult,
    ValidationErrorDetail,
    WebSocketProgressUpdate,
)
from app.services.csv_parser import parse_and_validate_csv
from app.services.hospital_client import HospitalClient
from app.services.processor import process_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hospitals", tags=["Hospitals"])


# ---------------------------------------------------------------------------
# POST /hospitals/bulk/validate  (Bonus: standalone CSV validation)
# NOTE: This route MUST be registered before /hospitals/bulk/{batch_id}/resume
#       to prevent FastAPI from interpreting "validate" as a batch_id.
# ---------------------------------------------------------------------------
@router.post("/bulk/validate", response_model=CSVValidationResponse)
async def validate_csv(file: UploadFile):
    """
    Validate a CSV file without triggering any upstream API calls.

    Returns a detailed report of any structural or content errors.
    """
    try:
        rows = await parse_and_validate_csv(file)
        return CSVValidationResponse(
            is_valid=True,
            total_rows=len(rows),
            errors=[],
        )
    except CSVValidationError as exc:
        # Don't re-raise — this endpoint returns validation results, not HTTP errors
        return CSVValidationResponse(
            is_valid=False,
            total_rows=0,
            errors=[
                ValidationErrorDetail(row=e["row"], error=e["error"])
                for e in exc.errors
            ],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _build_batch_result_response(batch_id: str) -> BatchResultResponse:
    """Helper to generate a full BatchResultResponse from a BatchState."""
    batch = batch_state_manager.get_batch(batch_id)

    row_results = []
    for row in batch.rows:
        status_str = "created_and_activated" if row.status == "success" else "failed"
        row_results.append(
            HospitalRowResult(
                row=row.row_number,
                hospital_id=row.hospital_id,
                name=row.payload.get("name", "Unknown"),
                status=status_str,
                error=row.error if row.status == "failed" else None,
            )
        )

    return BatchResultResponse(
        batch_id=batch.batch_id,
        total_hospitals=batch.total_rows,
        processed_hospitals=batch.processed_count,
        failed_hospitals=batch.failed_count,
        processing_time_seconds=batch.processing_time_seconds,
        batch_activated=batch.batch_activated,
        hospitals=row_results,
    )


# ---------------------------------------------------------------------------
# POST /hospitals/bulk  (Core endpoint)
# ---------------------------------------------------------------------------
@router.post(
    "/bulk",
    response_model=Union[BatchResultResponse, BulkUploadResponse],
)
async def bulk_upload(
    file: UploadFile,
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    client: HospitalClient = Depends(get_hospital_client),
):
    """
    Upload a CSV file and bulk-create hospitals.

    By default, processes synchronously and returns full results.
    If background=true, returns 202 Accepted and processes in the background.
    """
    rows = await parse_and_validate_csv(file)
    batch = batch_state_manager.create_batch(rows)

    if background:
        background_tasks.add_task(process_batch, client, batch.batch_id)
        return BulkUploadResponse(
            batch_id=batch.batch_id,
            status="processing_started",
            message="Processing in background. Track via WebSocket or GET /bulk/{batch_id}",
        )

    # Process synchronously
    await process_batch(client, batch.batch_id)
    return await _build_batch_result_response(batch.batch_id)


# ---------------------------------------------------------------------------
# GET /hospitals/bulk/{batch_id}  (Retrieve results)
# ---------------------------------------------------------------------------
@router.get("/bulk/{batch_id}", response_model=BatchResultResponse, response_model_exclude_none=True)
async def get_batch_report(batch_id: str):
    """
    Retrieve the current status and results of a specific bulk batch.
    """
    return await _build_batch_result_response(batch_id)


# ---------------------------------------------------------------------------
# POST /hospitals/bulk/{batch_id}/resume  (Bonus: retry failed rows)
# ---------------------------------------------------------------------------
@router.post(
    "/bulk/{batch_id}/resume",
    response_model=Union[BatchResultResponse, BulkUploadResponse],
)
async def resume_batch(
    batch_id: str,
    background: bool = False,
    background_tasks: BackgroundTasks = None,
    client: HospitalClient = Depends(get_hospital_client),
):
    """
    Resume a partially failed batch by retrying only the failed rows.

    By default, processes synchronously and returns updated full results.
    If background=true, returns 202 Accepted and processes in the background.
    """
    failed_rows = batch_state_manager.get_failed_rows(batch_id)

    if failed_rows:
        batch_state_manager.reset_failed_rows(batch_id)
        if background:
            background_tasks.add_task(process_batch, client, batch_id)
            return BulkUploadResponse(
                batch_id=batch_id,
                status="resume_started",
                message=f"Retrying {len(failed_rows)} failed rows in background.",
            )
        else:
            await process_batch(client, batch_id)

    return await _build_batch_result_response(batch_id)


# ---------------------------------------------------------------------------
# WebSocket /hospitals/progress/{batch_id}  (Bonus: real-time tracking)
# ---------------------------------------------------------------------------
@router.websocket("/progress/{batch_id}")
async def progress_websocket(websocket: WebSocket, batch_id: str):
    """
    Stream real-time progress updates for a batch.

    Sends JSON updates every 0.5s until the batch reaches a terminal state.
    """
    await websocket.accept()

    try:
        while True:
            batch = batch_state_manager.get_batch(batch_id)
            
            # If terminal state reached, send the FULL result as the last message
            if batch.status in ("completed", "failed", "partially_failed"):
                rows = []
                for row in batch.rows:
                    status_str = "created_and_activated" if row.status == "success" else "failed"
                    rows.append(HospitalRowResult(
                        row=row.row_number,
                        hospital_id=row.hospital_id,
                        name=row.payload.get("name", "Unknown"),
                        status=status_str,
                        error=row.error if row.status == "failed" else None
                    ))
                
                final_result = BatchResultResponse(
                    batch_id=batch.batch_id,
                    total_hospitals=batch.total_rows,
                    processed_hospitals=batch.processed_count,
                    failed_hospitals=batch.failed_count,
                    processing_time_seconds=0.0, # Time tracking is bonus, but we'll leave it 0 or calc
                    batch_activated=batch.batch_activated,
                    hospitals=rows
                )
                await websocket.send_json({
                    "type": "final_result",
                    "data": final_result.model_dump(exclude_none=True)
                })
                break
            
            # Otherwise, send a simple progress update
            update = WebSocketProgressUpdate(
                status=batch.status,
                processed=batch.processed_count,
                failed=batch.failed_count,
                total=batch.total_rows,
            )
            await websocket.send_json({
                "type": "progress_update",
                "data": update.model_dump(exclude_none=True)
            })

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for batch %s", batch_id)
    except Exception as exc:
        logger.error("WebSocket error for batch %s: %s", batch_id, exc)
        await websocket.close(code=1011)
