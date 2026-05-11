"""
Pydantic schemas for API request validation and response serialization.

These schemas define the contract between our API and external consumers.
They are separate from domain models to maintain a clean boundary between
internal state and public-facing data structures.
"""

from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Upstream API Schemas
# ---------------------------------------------------------------------------
class HospitalCreate(BaseModel):
    """Payload sent to the upstream API to create a hospital."""

    name: str
    address: str
    phone: str | None = None
    creation_batch_id: str | None = None


class Hospital(BaseModel):
    """Response received from the upstream API after hospital creation."""

    id: int
    name: str
    address: str
    phone: str | None = None
    creation_batch_id: str | None = None
    active: bool = True
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Our API Response Schemas
# ---------------------------------------------------------------------------
class BulkUploadResponse(BaseModel):
    """Response for POST /hospitals/bulk — returned immediately as 202."""

    batch_id: str
    status: str
    message: str


class HospitalRowResult(BaseModel):
    """Status of a single hospital row in the batch result."""

    row: int
    hospital_id: int | None = None
    name: str
    status: str  # "created_and_activated" | "failed"
    error: str | None = None


class BatchResultResponse(BaseModel):
    """Full processing results for a hospital batch."""

    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: list[HospitalRowResult]


class ValidationErrorDetail(BaseModel):
    """A single validation error for a CSV row."""

    row: int
    error: str


class CSVValidationResponse(BaseModel):
    """Response for POST /hospitals/bulk/validate."""

    is_valid: bool
    total_rows: int
    errors: list[ValidationErrorDetail]


class WebSocketProgressUpdate(BaseModel):
    """Schema for real-time progress streamed over WebSocket."""

    status: str
    processed: int
    failed: int
    total: int
