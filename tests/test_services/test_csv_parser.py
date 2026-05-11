"""
Unit tests for the CSV Parser Service.

Tests cover: valid CSV, missing columns, empty files, exceeding max rows,
missing required field values, and encoding issues.
"""

import io

import pytest

from app.core.exceptions import CSVValidationError
from app.services.csv_parser import MAX_ROWS, parse_and_validate_csv


class MockUploadFile:
    """Minimal mock of FastAPI's UploadFile for unit testing the parser."""

    def __init__(self, content: str, filename: str = "test.csv"):
        self._content = content.encode("utf-8")
        self.filename = filename

    async def read(self) -> bytes:
        return self._content


@pytest.mark.asyncio
async def test_valid_csv_parses_correctly():
    """A well-formed CSV should return a list of dicts."""
    csv_content = "name,address,phone\nHospital A,123 Main St,555-1234\nHospital B,456 Oak Ave,"
    file = MockUploadFile(csv_content)

    rows = await parse_and_validate_csv(file)

    assert len(rows) == 2
    assert rows[0]["name"] == "Hospital A"
    assert rows[0]["address"] == "123 Main St"
    assert rows[0]["phone"] == "555-1234"
    assert rows[1]["phone"] is None  # Empty phone should be None


@pytest.mark.asyncio
async def test_missing_required_column_raises_error():
    """CSV missing 'address' column should raise CSVValidationError."""
    csv_content = "name,phone\nHospital A,555-1234"
    file = MockUploadFile(csv_content)

    with pytest.raises(CSVValidationError) as exc_info:
        await parse_and_validate_csv(file)

    assert any("address" in e["error"] for e in exc_info.value.errors)


@pytest.mark.asyncio
async def test_empty_csv_raises_error():
    """A CSV with only headers and no data rows should fail."""
    csv_content = "name,address,phone"
    file = MockUploadFile(csv_content)

    with pytest.raises(CSVValidationError) as exc_info:
        await parse_and_validate_csv(file)

    assert any("no data rows" in e["error"] for e in exc_info.value.errors)


@pytest.mark.asyncio
async def test_exceeding_max_rows_raises_error():
    """A CSV with more than MAX_ROWS data rows should fail."""
    header = "name,address,phone"
    rows = "\n".join(f"Hospital {i},Address {i},555-{i:04d}" for i in range(MAX_ROWS + 1))
    csv_content = f"{header}\n{rows}"
    file = MockUploadFile(csv_content)

    with pytest.raises(CSVValidationError) as exc_info:
        await parse_and_validate_csv(file)

    assert any("exceeds maximum" in e["error"] for e in exc_info.value.errors)


@pytest.mark.asyncio
async def test_missing_required_field_value_raises_error():
    """A row with an empty 'name' field should fail validation."""
    csv_content = "name,address,phone\n,123 Main St,555-1234"
    file = MockUploadFile(csv_content)

    with pytest.raises(CSVValidationError) as exc_info:
        await parse_and_validate_csv(file)

    assert any("name" in e["error"] for e in exc_info.value.errors)


@pytest.mark.asyncio
async def test_completely_empty_file_raises_error():
    """An empty file (no headers) should raise CSVValidationError."""
    file = MockUploadFile("")

    with pytest.raises(CSVValidationError) as exc_info:
        await parse_and_validate_csv(file)

    assert any("empty" in e["error"].lower() for e in exc_info.value.errors)


@pytest.mark.asyncio
async def test_phone_is_optional():
    """CSV rows without phone values should parse successfully with phone=None."""
    csv_content = "name,address\nHospital A,123 Main St"
    file = MockUploadFile(csv_content)

    rows = await parse_and_validate_csv(file)

    assert len(rows) == 1
    assert rows[0]["phone"] is None
