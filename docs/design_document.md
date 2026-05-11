# Detailed Design Document
**Project**: Hospital Bulk Processing System
**Client/Company**: Paribus

## 1. System Architecture

The application will be built as a standalone API service using **FastAPI** to leverage asynchronous operations, ensuring that parallel network requests to the upstream API are handled efficiently.

### 1.1 Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Server**: Uvicorn
- **HTTP Client**: `httpx` (for async non-blocking external requests)
- **Validation & Serialization**: Pydantic
- **Data Parsing**: `csv` module (Python standard library) or `pandas`
- **Testing**: Pytest, pytest-asyncio, httpx
- **Containerization**: Docker

## 2. Component Diagram

```mermaid
graph TD
    A[Client] -->|POST /hospitals/bulk (CSV)| B[FastAPI Router]
    B --> C[CSV Validation Service]
    C -->|If Invalid| D[Return 400 Bad Request]
    C -->|If Valid| E[Batch Processor Service]
    
    E --> F[Generate UUID]
    E --> G[Async POST /hospitals/ (Parallel)]
    G <-->|httpx| H[Paribus Directory API]
    
    G --> I{All Requests Finished?}
    I -->|Yes, at least 1 success| J[PATCH /hospitals/batch/{uuid}/activate]
    J <-->|httpx| H
    I -->|All Failed| K[Skip Activation]
    
    J --> L[Aggregate Results]
    K --> L
    L --> M[Return JSON Response to Client]
```

## 3. Directory Structure

```text
paribus-hospital-bulk-processing-system/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app initialization & exception handlers
│   ├── api/                   # API Routers
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── hospitals.py   # Endpoint definitions
│   ├── core/                  # Configurations and app settings
│   │   ├── __init__.py
│   │   ├── config.py          # Environment variable definitions via Pydantic BaseSettings
│   │   └── exceptions.py      # Custom exception classes
│   ├── models/                # Pydantic Schemas for Requests and Responses
│   │   ├── __init__.py
│   │   └── hospital.py
│   └── services/              # Core business logic
│       ├── __init__.py
│       ├── csv_parser.py      # Logic for parsing and validating CSV
│       └── hospital_client.py # HTTPX client for Paribus API interactions
├── docs/                      # Product, Design, and Task documentation
├── tests/                     # Unit and Integration tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   └── test_services.py
├── .gitignore
├── Dockerfile                 # Multi-stage build
├── docker-compose.yml         # Simple setup for local running
├── requirements.txt           # App dependencies
└── requirements-dev.txt       # Testing dependencies
```

## 4. API Endpoints

### 4.1 `POST /api/v1/hospitals/bulk`
**Description**: Uploads a CSV, validates it, creates hospitals on the upstream API, and activates the batch.

**Request Form Data**:
- `file`: `UploadFile` (MIME: `text/csv`)

**Business Logic Flow**:
1. Check file size and type.
2. Decode bytes to string and parse CSV.
3. Validate columns (`name`, `address`, `phone`).
4. Validate row count (max 20).
5. Generate `batch_id` = `uuid.uuid4()`.
6. For each row, construct payload and add to `asyncio.gather` pool for `POST /hospitals/`.
7. Await all responses. Determine successes and failures.
8. If `processed_hospitals > 0`, call `PATCH /hospitals/batch/{batch_id}/activate`.
9. Construct final JSON response and return.

**Response (200 OK)**:
```json
{
  "batch_id": "uuid",
  "total_hospitals": 5,
  "processed_hospitals": 4,
  "failed_hospitals": 1,
  "processing_time_seconds": 1.25,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 101,
      "name": "General Hospital",
      "status": "created_and_activated"
    },
    {
      "row": 2,
      "name": "Invalid Hospital",
      "status": "failed",
      "error": "Upstream API timeout"
    }
  ]
}
```

## 5. Security & Error Handling
- **Invalid CSV format**: Return `400 Bad Request` with details before any API calls are made.
- **Upstream API Failure**: If the Paribus API is unreachable, return `502 Bad Gateway`.
- **Partial Failure**: If some records fail but others succeed, return `207 Multi-Status` or `200 OK` but explicitly detail failures in the response array (as requested in the assignment format).
