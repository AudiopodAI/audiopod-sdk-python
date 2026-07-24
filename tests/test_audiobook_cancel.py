"""
Unit tests for ``AudiobookService.cancel_narration`` (PLAT-2591).

The transport is mocked at the service's ``client`` boundary — a fake client
records the request ``(method, path, kwargs)`` and returns a canned response, so
no network is involved. Both the sync branch and the ``async_mode`` branch are
covered, plus the idempotent 404 (``no_narration_running``).
"""

import asyncio

import pytest

from audiopod.exceptions import APIError
from audiopod.services.audiobook import AudiobookService

_CANCEL_RESPONSE = {
    "job_id": 4242,
    "status": "cancelled",
    "paragraphs_kept": 12,
    "paragraphs_reset": 8,
    "billing_released": 640,
    "project_status": "narration_cancelled",
}


class _RecordingClient:
    """Sync fake: records calls, returns a canned dict (or raises)."""

    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response


class _AsyncRecordingClient:
    """Async fake: ``request`` is a coroutine, mirroring ``AsyncClient``."""

    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    async def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.response


def test_cancel_narration_sync_posts_no_body_and_returns_dict():
    client = _RecordingClient(response=_CANCEL_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    result = service.cancel_narration("proj_abc")

    assert result == _CANCEL_RESPONSE
    assert len(client.calls) == 1
    method, endpoint, kwargs = client.calls[0]
    assert method == "POST"
    assert endpoint == "/api/v1/audiobook/projects/proj_abc/narration/cancel"
    # No request body — matches ``delete_project`` (no json_data/data/files).
    assert kwargs == {}


def test_cancel_narration_async_posts_no_body_and_returns_dict():
    client = _AsyncRecordingClient(response=_CANCEL_RESPONSE)
    service = AudiobookService(client, async_mode=True)

    # In async_mode the method returns an awaitable (the client coroutine).
    result = asyncio.run(service.cancel_narration("proj_abc"))

    assert result == _CANCEL_RESPONSE
    assert len(client.calls) == 1
    method, endpoint, kwargs = client.calls[0]
    assert method == "POST"
    assert endpoint == "/api/v1/audiobook/projects/proj_abc/narration/cancel"
    assert kwargs == {}


def test_cancel_narration_idempotent_404_raises_apierror():
    client = _RecordingClient(exc=APIError("no narration running", status_code=404))
    service = AudiobookService(client, async_mode=False)

    with pytest.raises(APIError) as exc_info:
        service.cancel_narration("proj_abc")

    assert exc_info.value.status_code == 404
