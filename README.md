# Hospital Bulk Processing System

A production-grade microservice for bulk-uploading hospital records via CSV files.

## Features

- **Bulk CSV Upload** — Upload a CSV of up to 20 hospitals. Records are processed concurrently and pushed to the upstream Hospital Directory API.
- **Real-Time WebSocket Tracking** — Monitor processing progress live via a WebSocket connection.
- **Resume Failed Batches** — Retry only the failed rows from a partial batch failure without re-uploading the entire CSV.
- **Standalone CSV Validation** — Pre-validate your CSV structure and content before uploading.
- **Automatic Retries** — Transient upstream API failures (502, timeouts) are automatically retried via `tenacity`.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| HTTP Client | httpx (async) |
| Fault Tolerance | tenacity |
| Validation | Pydantic v2 |
| Testing | Pytest, pytest-asyncio |
| Containerization | Docker |

## Quick Start

### Local Development

```bash
# 1. Clone the repository
git clone <repo-url>
cd paribus-hospital-bulk-processing-system

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 4. Copy environment variables
cp .env.example .env

# 5. Run the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Docker

```bash
# Build and run
docker compose up --build

# Or build manually
docker build -t hospital-bulk-api .
docker run -p 8000:8000 hospital-bulk-api
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
coverage run -m pytest tests/ -v
coverage report -m
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/hospitals/bulk` | Upload CSV for bulk processing (supports `?background=true`) |
| `GET` | `/api/v1/hospitals/bulk/{batch_id}` | Retrieve processing results |
| `POST` | `/api/v1/hospitals/bulk/validate` | Validate CSV without processing |
| `POST` | `/api/v1/hospitals/bulk/{batch_id}/resume` | Retry failed rows (supports `?background=true`) |
| `WS` | `/api/v1/hospitals/progress/{batch_id}` | WebSocket for real-time progress |
| `GET` | `/health` | Health check |

### Example: Upload a CSV

```bash
curl -X POST http://localhost:8000/api/v1/hospitals/bulk \
  -F "file=@hospitals.csv"
```

### CSV Format

```csv
name,address,phone
General Hospital,123 Main St,555-1234
City Medical Center,456 Oak Ave,
```

- `name` — Required
- `address` — Required
- `phone` — Optional
- Maximum 20 rows per file

## Project Structure

```
app/
├── main.py              # App entrypoint, middleware, exception handlers
├── api/
│   ├── dependencies.py  # Dependency injection
│   └── v1/
│       └── hospitals.py # API endpoints
├── core/
│   ├── config.py        # App configuration
│   ├── exceptions.py    # Custom exception classes
│   └── state.py         # Batch state manager
├── models/
│   ├── domain.py        # Internal models
│   └── schemas.py       # API schemas
└── services/
    ├── csv_parser.py    # CSV processing
    ├── hospital_client.py # External API client
    └── processor.py     # Processing logic
```

## Documentation

Detailed documentation is available in the `docs/` directory:
- [Product Document](docs/product_document.md) — Requirements and scope
- [Design Document](docs/design_document.md) — Architecture and technical decisions
- [Upstream API Reference](docs/upstream_api_reference.md) — API specifications
