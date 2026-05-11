"""
CSV Parser Service.

DRY validation logic shared by both the /bulk upload and /bulk/validate
endpoints. Decodes raw file bytes, validates structure and content,
and returns a list of parsed row dictionaries.
"""

import csv
import io

from fastapi import UploadFile

from app.core.exceptions import CSVValidationError

# Configuration for CSV processing
MAX_ROWS = 20
REQUIRED_COLUMNS = {"name", "address"}
ALLOWED_COLUMNS = {"name", "address", "phone"}


async def parse_and_validate_csv(file: UploadFile) -> list[dict]:
    """
    Parse and validate an uploaded CSV file.

    Returns a list of dicts, one per row, with keys: name, address, phone.
    Raises CSVValidationError if any structural or content issues are found.
    """
    errors: list[dict] = []

    # --- Step 1: Read and decode file bytes ---
    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise CSVValidationError([{"row": 0, "error": "File is not valid UTF-8 encoded text"}])

    # --- Step 2: Parse CSV ---
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CSVValidationError([{"row": 0, "error": "CSV file is empty or has no header row"}])

    # --- Step 3: Validate column headers ---
    headers = {h.strip().lower() for h in reader.fieldnames}
    missing_columns = REQUIRED_COLUMNS - headers
    if missing_columns:
        raise CSVValidationError(
            [{"row": 0, "error": f"Missing required column(s): {', '.join(sorted(missing_columns))}"}]
        )

    # --- Step 4: Parse and validate rows ---
    rows: list[dict] = []
    for i, raw_row in enumerate(reader, start=1):
        # Normalize keys to lowercase and strip whitespace
        row = {k.strip().lower(): v.strip() if v else "" for k, v in raw_row.items()}

        # Validate required fields are not empty
        if not row.get("name"):
            errors.append({"row": i, "error": "Missing required 'name' field"})
        if not row.get("address"):
            errors.append({"row": i, "error": "Missing required 'address' field"})

        rows.append({
            "name": row.get("name", ""),
            "address": row.get("address", ""),
            "phone": row.get("phone") or None,
        })

    # --- Step 5: Validate row count ---
    if len(rows) == 0:
        errors.append({"row": 0, "error": "CSV file contains no data rows"})

    if len(rows) > MAX_ROWS:
        errors.append({"row": 0, "error": f"CSV exceeds maximum of {MAX_ROWS} rows (found {len(rows)})"})

    # --- Step 6: Raise or return ---
    if errors:
        raise CSVValidationError(errors)

    return rows
