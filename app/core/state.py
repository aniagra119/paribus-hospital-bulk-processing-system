"""
In-memory Batch State Manager.

A lightweight singleton that tracks the state of all active bulk upload
jobs. Enables WebSocket progress streaming and the Resume Capability
without requiring an external database.

Note: State is lost on server restart. This is acceptable for the
current system requirements.
"""

import uuid

from app.core.exceptions import BatchNotFoundError
from app.models.domain import BatchState, HospitalRowStatus


class BatchStateManager:
    """Manages batch lifecycle state in a Python dictionary."""

    def __init__(self) -> None:
        self._batches: dict[str, BatchState] = {}

    def create_batch(self, rows: list[dict]) -> BatchState:
        """Initialize a new batch with all rows set to 'pending'."""
        batch_id = str(uuid.uuid4())
        row_statuses = [
            HospitalRowStatus(row_number=i + 1, payload=row)
            for i, row in enumerate(rows)
        ]
        batch = BatchState(
            batch_id=batch_id,
            total_rows=len(rows),
            rows=row_statuses,
        )
        self._batches[batch_id] = batch
        return batch

    def get_batch(self, batch_id: str) -> BatchState:
        """Retrieve batch state by ID. Raises BatchNotFoundError if missing."""
        batch = self._batches.get(batch_id)
        if batch is None:
            raise BatchNotFoundError(batch_id)
        return batch

    def update_row_status(
        self,
        batch_id: str,
        row_number: int,
        status: str,
        hospital_id: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update the status of a specific row within a batch."""
        batch = self.get_batch(batch_id)
        for row in batch.rows:
            if row.row_number == row_number:
                row.status = status
                row.hospital_id = hospital_id
                row.error = error
                break

        # Recalculate aggregate counts
        batch.processed_count = sum(1 for r in batch.rows if r.status == "success")
        batch.failed_count = sum(1 for r in batch.rows if r.status == "failed")

    def mark_batch_completed(
        self, batch_id: str, activated: bool, elapsed: float = 0.0
    ) -> None:
        """Finalize batch status after all rows have been processed."""
        batch = self.get_batch(batch_id)
        batch.batch_activated = activated
        batch.processing_time_seconds = elapsed
        if batch.failed_count == 0:
            batch.status = "completed"
        elif batch.processed_count == 0:
            batch.status = "failed"
        else:
            batch.status = "partially_failed"

    def get_failed_rows(self, batch_id: str) -> list[HospitalRowStatus]:
        """Return all rows marked as 'failed' for a given batch (used by Resume)."""
        batch = self.get_batch(batch_id)
        return [row for row in batch.rows if row.status == "failed"]

    def reset_failed_rows(self, batch_id: str) -> None:
        """Reset failed rows back to 'pending' so they can be retried."""
        batch = self.get_batch(batch_id)
        for row in batch.rows:
            if row.status == "failed":
                row.status = "pending"
                row.error = None
        batch.status = "processing"
        batch.batch_activated = False


# Module-level singleton instance
batch_state_manager = BatchStateManager()
