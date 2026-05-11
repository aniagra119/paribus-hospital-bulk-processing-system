"""
Application entrypoint for the Hospital Bulk Processing System.

Initializes the FastAPI app, registers global exception handlers,
configures middleware, and wires up API routers.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.hospitals import router as hospitals_router
from app.core.config import settings
from app.core.exceptions import (
    BatchNotFoundError,
    CSVValidationError,
    UpstreamAPIError,
)


# ---------------------------------------------------------------------------
# Lifespan: manage the shared httpx.AsyncClient (singleton)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create a single httpx.AsyncClient on startup and close it on shutdown."""
    app.state.http_client = httpx.AsyncClient(
        base_url=settings.UPSTREAM_API_URL,
        timeout=httpx.Timeout(30.0),
    )
    yield
    await app.state.http_client.aclose()


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for processing hospital records in bulk from CSV uploads.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------
@app.exception_handler(CSVValidationError)
async def csv_validation_error_handler(
    _request: Request, exc: CSVValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": "CSV validation failed", "errors": exc.errors},
    )


@app.exception_handler(UpstreamAPIError)
async def upstream_api_error_handler(
    _request: Request, exc: UpstreamAPIError
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": exc.detail},
    )


@app.exception_handler(BatchNotFoundError)
async def batch_not_found_error_handler(
    _request: Request, exc: BatchNotFoundError
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={"detail": f"Batch '{exc.batch_id}' not found"},
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(hospitals_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check to verify the service is running."""
    return {"status": "ok"}


