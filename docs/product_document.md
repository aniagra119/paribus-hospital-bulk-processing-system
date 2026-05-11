# Product Documentation
**Project**: Hospital Bulk Processing System
**Client/Company**: Paribus

## 1. Overview
The Hospital Bulk Processing System is a standalone microservice designed to handle bulk uploads of hospital records via CSV files. It integrates directly with the existing Paribus Hospital Directory API to streamline the data entry process, which would otherwise require tedious individual manual entries.

## 2. Target Audience
- **Operations & Data Entry Teams**: Users who need to quickly onboard multiple hospitals simultaneously.
- **System Administrators**: Users monitoring the health, success rates, and performance of bulk operations.

## 3. Core Workflows
1. **Upload & Validate**: A user uploads a CSV file containing hospital data (Name, Address, Phone). The system validates the data format and ensures it respects the maximum limit of 20 rows.
2. **Synchronous Processing**: The system generates a unique UUID (Batch ID), and immediately begins processing the CSV payload synchronously, dispatching valid records to the upstream API concurrently.
3. **Concurrent API Dispatch**: The system seamlessly dispatches the validated records to the upstream Hospital Directory API.
4. **Batch Activation**: Upon processing all records, the system triggers an activation sequence to mark the successful hospitals in the batch as "active."
5. **Comprehensive Response**: The system returns the complete results of the operation, including total processing time and individual hospital statuses.
6. **Real-time Tracking**: The user can monitor the live progress of long-running operations via a WebSocket connection using their Batch ID.

> **Note on Processing Model**: We opted for a synchronous "Upload & Wait" model for the primary flow to provide immediate data integrity feedback. Given the 20-row limit, this provides a better user experience than asynchronous background tasks which require the user to poll for completion.

## 4. Functional Requirements

### 4.1 Bulk CSV Upload Endpoint
- **Endpoint**: `POST /hospitals/bulk?background=false`
- **Parameters**: `background` (optional, default=false) — Set to `true` to process in background.
- **Input**: `multipart/form-data` with a `.csv` file attachment.
- **CSV Schema**: `name` (required), `address` (required), `phone` (optional).
- **Validation**:
  - Maximum 20 rows per file.
  - Strict column header validation.
  - Row-level data validation (missing required fields).
- **Processing Logic**:
  - Automatically create a unique Batch ID (UUID).
  - Dispatch concurrent requests to the upstream API and await their completion.
- **Output**: A `200 OK` JSON payload containing the comprehensive `batch_id`, total processing time, and the exact success/failure status of every single row.

### 4.2 Progress Tracking
- **Endpoint**: `WebSocket /ws/hospitals/progress/{batch_id}`
- **Functionality**: Clients can connect to this WebSocket to receive real-time updates on the processing status of their batch as the background task runs.
- **Updates Include**: Number of processed hospitals, failed hospitals, and final completion status. This demonstrates asynchronous job tracking capabilities.

### 4.3 Resume Capability
- **Endpoint**: `POST /hospitals/bulk/{batch_id}/resume?background=false`
- **Parameters**: `background` (optional, default=false) — Set to `true` to process in background.
- **Functionality**: If a bulk operation fails partially (e.g., due to an upstream API timeout or rate limit), the user can invoke this endpoint to retry only the failed records.
- **Processing Logic**: The system will fetch the state of the batch from memory, identify which records failed, and re-attempt to push them to the upstream API synchronously, returning the updated batch result.

### 4.4 Standalone CSV Validation
- **Endpoint**: `POST /hospitals/bulk/validate`
- **Input**: `multipart/form-data` with a `.csv` file attachment.
- **Functionality**: Allows the user to pre-validate a CSV format and contents without actually triggering any downstream API calls or creating a batch.
- **Output**: Detailed validation report highlighting errors (e.g., missing columns, empty rows, exceeding 20 rows).

### 4.5 Error Handling & Resilience
- **Automatic Retries**: The system utilizes the `tenacity` library to automatically retry upstream API calls if a transient network error or `502 Bad Gateway` occurs, ensuring maximum reliability.
- Graceful degradation if the upstream API ultimately times out after retries.

## 5. Non-Functional Requirements

### 5.1 Performance & Scalability
- **Asynchronous I/O**: The system will use native FastAPI features and `httpx` with `asyncio.gather` to process the CSV rows concurrently, ensuring the synchronous HTTP upload endpoint finishes in a matter of seconds.
- **Statelessness**: The API routes remain stateless, interacting with a centralized in-memory state manager.

### 5.2 Modularity & Code Quality
- Following a clean, modular architecture, code is separated into:
  - `api/` (Routing and HTTP transport)
  - `services/` (Business logic, CSV parsing, Upstream API communication)
  - `core/` (Configuration, state management, constants, and utilities)
  - `models/` (Pydantic data models)
- Fully typed Python code to ensure readability and maintainability.

### 5.3 Deployment & Operations
- **Containerization**: Fully Dockerized using best practices.
- **Environment Management**: Robust environment variable handling for upstream URLs.

## 6. Out of Scope (For MVP)
- **User Authentication/Authorization**: Currently handled at the load balancer or infrastructure level.
- **Persistent Database Infrastructure**: The system acts as a pure pass-through orchestrator. It uses an in-memory storage for job lifecycle tracking. Future iterations may include a persistent layer like Redis for high-availability deployments.
