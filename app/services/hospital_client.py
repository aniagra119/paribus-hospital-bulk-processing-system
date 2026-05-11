"""
Hospital Client — HTTPX wrapper for the upstream Hospital Directory API.

Uses tenacity for automatic retries on transient failures (502, 503,
timeouts). A single httpx.AsyncClient instance is injected via the
FastAPI lifespan to benefit from connection pooling.
"""

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.exceptions import UpstreamAPIError

logger = logging.getLogger(__name__)


class HospitalClient:
    """Async HTTP client for the Hospital Directory API."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True,
    )
    async def create_hospital(self, payload: dict) -> dict:
        """
        Create a single hospital via POST /hospitals/.

        Returns the upstream response dict on success.
        Raises UpstreamAPIError on non-retryable failures.
        """
        try:
            response = await self._client.post("/hospitals/", json=payload)

            if response.status_code in (502, 503):
                # Force tenacity retry by raising a retriable exception
                raise httpx.ConnectError(
                    f"Upstream returned {response.status_code}"
                )

            if response.status_code >= 400:
                raise UpstreamAPIError(
                    detail=f"Upstream API error: {response.status_code} — {response.text}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.TimeoutException:
            raise  # Let tenacity handle the retry
        except httpx.ConnectError:
            raise  # Let tenacity handle the retry
        except UpstreamAPIError:
            raise  # Don't retry client errors (4xx)
        except Exception as exc:
            raise UpstreamAPIError(detail=f"Unexpected error: {exc}") from exc

    async def activate_batch(self, batch_id: str) -> bool:
        """
        Activate all hospitals in a batch via PATCH /hospitals/batch/{batch_id}/activate.

        Returns True on success, raises UpstreamAPIError on failure.
        """
        try:
            response = await self._client.patch(
                f"/hospitals/batch/{batch_id}/activate"
            )
            if response.status_code >= 400:
                raise UpstreamAPIError(
                    detail=f"Failed to activate batch: {response.status_code} — {response.text}",
                    status_code=response.status_code,
                )
            return True

        except httpx.TimeoutException as exc:
            raise UpstreamAPIError(
                detail=f"Timeout while activating batch: {exc}"
            ) from exc
        except UpstreamAPIError:
            raise
        except Exception as exc:
            raise UpstreamAPIError(
                detail=f"Unexpected error activating batch: {exc}"
            ) from exc
