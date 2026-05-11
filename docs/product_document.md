# Product Requirements Document (PRD)
**Project**: Hospital Bulk Processing System
**Client/Company**: Paribus

## 1. Overview
The Hospital Bulk Processing System is a standalone microservice designed to handle bulk uploads of hospital records via CSV files. It integrates directly with the existing Paribus Hospital Directory API to streamline the data entry process, which would otherwise require tedious individual manual entries.

## 2. Target Audience
- **Operations & Data Entry Teams**: Users who need to quickly onboard multiple hospitals simultaneously.
- **System Administrators**: Users monitoring the health, success rates, and performance of bulk operations.

## 3. Core Workflows
1. **Upload & Validate**: A user uploads a CSV file containing hospital data (Name, Address, Phone). The system validates the data format and ensures it respects the maximum limit of 20 rows.
2. **Batch Generation**: The system generates a unique UUID (Batch ID) to logically group the incoming records.
3. **Concurrent Processing**: The system seamlessly dispatches the validated records to the upstream Hospital Directory API.
4. **Batch Activation**: Upon successful creation of the records, the system triggers an activation sequence to mark all hospitals in the batch as "active."
5. **Reporting**: The system provides a comprehensive summary detailing successes, failures, and processing time.

## 4. Functional Requirements

### 4.1 Bulk CSV Upload Endpoint
- **Endpoint**: `POST /hospitals/bulk`
- **Input**: `multipart/form-data` with a `.csv` file attachment.
- **CSV Schema**: `name` (required), `address` (required), `phone` (optional).
- **Validation**:
  - Maximum 20 rows per file.
  - Strict column header validation.
  - Row-level data validation (missing required fields).
- **Processing Logic**:
  - Automatically create a unique Batch ID (UUID).
  - Submit individual records to `POST /hospitals/` on the external API.
  - If records are processed without catastrophic system failure, execute `PATCH /hospitals/batch/{batch_id}/activate`.
- **Output**: A JSON payload containing:
  - `batch_id`
  - `total_hospitals`, `processed_hospitals`, `failed_hospitals`
  - `processing_time_seconds`
  - `batch_activated` (boolean)
  - `hospitals` (array of objects detailing the status of each row).

### 4.2 Error Handling & Resilience
- Graceful degradation if the upstream API times out or returns a 500.
- Detailed row-level error reporting in the response payload.

## 5. Non-Functional Requirements

### 5.1 Performance & Scalability
- **Asynchronous I/O**: The system will use asynchronous HTTP clients to process the CSV rows concurrently, ensuring minimal wait times for the end user.
- **Statelessness**: The API will remain stateless to ensure easy horizontal scaling if required in the future.

### 5.2 Modularity & Code Quality
- Inspired by the `core-be` modular architecture, code will be separated into:
  - `api/` (Routing and HTTP transport)
  - `services/` (Business logic, CSV parsing, Upstream API communication)
  - `core/` (Configuration, constants, and utilities)
  - `models/` (Pydantic data models)
- Fully typed Python code to ensure readability and maintainability.

### 5.3 Deployment & Operations
- **Containerization**: Fully Dockerized using best practices (similar to the `core-be` Dockerfile approach).
- **Environment Management**: Robust environment variable handling for upstream URLs and configuration.

## 6. Out of Scope (For MVP)
- **User Authentication/Authorization**: The API will be open for the purpose of the assignment unless explicitly required.
- **Database Persistence**: The system acts as a pure pass-through and orchestrator; it will not store hospital data locally (in-memory state is sufficient for request lifecycle).
- **Real-Time WebSockets**: Given the strict 20-row limit, processing will be near-instantaneous. A synchronous HTTP response is more appropriate than WebSockets.
