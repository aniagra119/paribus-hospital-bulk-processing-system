"""
Internal domain models for batch state tracking.

These models define the in-memory data structures used by the
BatchStateManager. They are NOT exposed directly in API responses;
instead, the schemas in models/schemas.py handle serialization.
"""

from pydantic import BaseModel


class HospitalRowStatus(BaseModel):
    """Tracks the processing status of a single hospital row from the CSV."""

    row_number: int
    payload: dict  # The raw parsed hospital data (name, address, phone)
    status: str = "pending"  # "pending" | "success" | "failed"
    hospital_id: int | None = None  # Populated on successful upstream creation
    error: str | None = None  # Populated on failure


class BatchState(BaseModel):
    """Represents the full state of a bulk upload batch job."""

    batch_id: str
    status: str = "processing"  # "processing" | "completed" | "partially_failed" | "failed"
    total_rows: int
    processed_count: int = 0
    failed_count: int = 0
    batch_activated: bool = False
    processing_time_seconds: float = 0.0
    rows: list[HospitalRowStatus] = []
