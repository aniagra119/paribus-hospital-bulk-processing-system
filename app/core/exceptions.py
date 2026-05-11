"""
Custom exceptions for the Hospital Bulk Processing System.

These exceptions are caught by global exception handlers in main.py
to return consistent, structured error responses without cluttering
route handlers with try/except blocks.
"""


class CSVValidationError(Exception):
    """Raised when CSV file validation fails (bad format, missing columns, too many rows)."""

    def __init__(self, errors: list[dict]) -> None:
        self.errors = errors
        super().__init__(f"CSV validation failed with {len(errors)} error(s)")


class UpstreamAPIError(Exception):
    """Raised when the upstream Hospital Directory API is unreachable or returns a server error."""

    def __init__(self, detail: str, status_code: int | None = None) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class BatchNotFoundError(Exception):
    """Raised when a batch_id does not exist in the BatchStateManager."""

    def __init__(self, batch_id: str) -> None:
        self.batch_id = batch_id
        super().__init__(f"Batch '{batch_id}' not found")
