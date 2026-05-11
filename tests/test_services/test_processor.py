"""
Unit tests for the Batch Processor service.

Tests cover: successful batch processing, partial failures,
full failures, and batch activation logic.
"""

import pytest

from app.core.exceptions import UpstreamAPIError
from app.core.state import batch_state_manager
from app.services.hospital_client import HospitalClient
from app.services.processor import process_batch
from unittest.mock import AsyncMock, MagicMock

import httpx


@pytest.fixture(autouse=True)
def _clear_state():
    batch_state_manager._batches.clear()
    yield
    batch_state_manager._batches.clear()


def _make_mock_client(
    create_side_effect=None,
    activate_side_effect=None,
):
    """Build a HospitalClient with mocked methods."""
    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    client = HospitalClient(client=mock_httpx)

    if create_side_effect is None:
        # Default: successful creation returning incrementing IDs
        call_count = {"n": 0}

        async def _create(payload):
            call_count["n"] += 1
            return {"id": call_count["n"], "name": payload["name"]}

        client.create_hospital = _create
    else:
        client.create_hospital = create_side_effect

    if activate_side_effect is None:
        client.activate_batch = AsyncMock(return_value=True)
    else:
        client.activate_batch = activate_side_effect

    return client


@pytest.mark.asyncio
async def test_successful_batch_processing():
    """All rows succeed — batch should be 'completed' and activated."""
    rows = [
        {"name": "Hospital A", "address": "Addr A", "phone": "111"},
        {"name": "Hospital B", "address": "Addr B", "phone": "222"},
    ]
    batch = batch_state_manager.create_batch(rows)
    client = _make_mock_client()

    await process_batch(client, batch.batch_id)

    result = batch_state_manager.get_batch(batch.batch_id)
    assert result.status == "completed"
    assert result.processed_count == 2
    assert result.failed_count == 0
    assert result.batch_activated is True


@pytest.mark.asyncio
async def test_partial_failure_batch():
    """One row fails — batch should be 'partially_failed' but still activated."""
    rows = [
        {"name": "Hospital A", "address": "Addr A", "phone": "111"},
        {"name": "Hospital B", "address": "Addr B", "phone": "222"},
    ]
    batch = batch_state_manager.create_batch(rows)

    call_count = {"n": 0}

    async def _flaky_create(payload):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise UpstreamAPIError("Simulated failure")
        return {"id": call_count["n"], "name": payload["name"]}

    client = _make_mock_client(create_side_effect=_flaky_create)

    await process_batch(client, batch.batch_id)

    result = batch_state_manager.get_batch(batch.batch_id)
    assert result.status == "partially_failed"
    assert result.processed_count == 1
    assert result.failed_count == 1
    assert result.batch_activated is True  # At least 1 succeeded


@pytest.mark.asyncio
async def test_all_rows_fail():
    """All rows fail — batch should be 'failed' and NOT activated."""
    rows = [{"name": "Hospital A", "address": "Addr A", "phone": None}]
    batch = batch_state_manager.create_batch(rows)

    async def _always_fail(payload):
        raise UpstreamAPIError("Always fails")

    client = _make_mock_client(create_side_effect=_always_fail)

    await process_batch(client, batch.batch_id)

    result = batch_state_manager.get_batch(batch.batch_id)
    assert result.status == "failed"
    assert result.processed_count == 0
    assert result.failed_count == 1
    assert result.batch_activated is False


@pytest.mark.asyncio
async def test_activation_failure_still_completes():
    """Activation fails but rows succeeded — batch should still reflect success counts."""
    rows = [{"name": "Hospital A", "address": "Addr A", "phone": None}]
    batch = batch_state_manager.create_batch(rows)

    async def _activate_fail(batch_id):
        raise UpstreamAPIError("Activation timeout")

    client = _make_mock_client(activate_side_effect=_activate_fail)

    await process_batch(client, batch.batch_id)

    result = batch_state_manager.get_batch(batch.batch_id)
    assert result.processed_count == 1
    assert result.batch_activated is False  # Activation failed
