"""
Shared Pytest fixtures for the Hospital Bulk Processing System tests.
"""

import io

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.state import BatchStateManager, batch_state_manager
from app.main import app


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset the in-memory batch state before each test to avoid leakage."""
    batch_state_manager._batches.clear()
    yield
    batch_state_manager._batches.clear()


@pytest.fixture
def test_client():
    """
    Provide a TestClient with a mocked httpx.AsyncClient so that
    tests never make real HTTP requests to the upstream API.
    """
    # Create a mock transport that returns predictable responses
    mock_transport = httpx.MockTransport(_mock_upstream_handler)
    mock_client = httpx.AsyncClient(
        transport=mock_transport,
        base_url="https://hospital-directory.onrender.com",
    )
    app.state.http_client = mock_client
    with TestClient(app) as client:
        yield client


def _mock_upstream_handler(request: httpx.Request) -> httpx.Response:
    """
    Mock handler simulating the upstream Paribus Hospital Directory API.
    Returns predictable responses for POST /hospitals/ and PATCH activate.
    """
    if request.method == "POST" and str(request.url.path) == "/hospitals/":
        import json
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": 1,
                "name": body.get("name", ""),
                "address": body.get("address", ""),
                "phone": body.get("phone"),
                "creation_batch_id": body.get("creation_batch_id"),
                "active": False,
                "created_at": "2025-09-19T10:30:00Z",
            },
        )

    if request.method == "PATCH" and "activate" in str(request.url.path):
        return httpx.Response(200, json={})

    return httpx.Response(404, json={"detail": "Not found"})


def make_csv_file(content: str, filename: str = "test.csv") -> io.BytesIO:
    """Helper to create an in-memory CSV file for upload tests."""
    file = io.BytesIO(content.encode("utf-8"))
    file.name = filename
    return file
