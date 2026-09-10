"""
Unit tests for ``AudiobookService.regenerate_chapter`` (PLAT-3116).

``POST /audiobook/projects/{id}/chapters/{chapter_id}/regenerate`` rendered an
entire chapter's TTS synchronously inside the FastAPI request and charged
nothing — no credit reservation, no billing-auth context, no rate pacer, no
export lock. It was retired in PLAT-3056 and now returns 410 Gone
unconditionally, which meant every call through this SDK method failed outright.

Same transport-boundary fake as ``test_audiobook_cancel.py``: no network. Both
the sync branch and the ``async_mode`` branch are covered, because the two build
the request separately and a fix applied to one has silently missed the other
before.
"""

import asyncio

from audiopod.services.audiobook import AudiobookService

_BATCH_RESPONSE = {
    "job_id": 8801,
    "total_paragraphs": 42,
    "skipped_paragraphs": 0,
    "estimated_completion_time": None,
}

_PATH = "/api/v1/audiobook/projects/proj_abc/narration/batch"


class _RecordingClient:
    """Sync fake: records calls, returns a canned dict."""

    def __init__(self, response=None):
        self.response = response
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        return self.response


class _AsyncRecordingClient:
    """Async fake: ``request`` is a coroutine, mirroring ``AsyncClient``."""

    def __init__(self, response=None):
        self.response = response
        self.calls = []

    async def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        return self.response


def test_sync_posts_to_batch_not_the_retired_regenerate_route():
    client = _RecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    result = service.regenerate_chapter("proj_abc", "chap_7")

    assert result == _BATCH_RESPONSE
    method, endpoint, _ = client.calls[0]
    assert method == "POST"
    assert endpoint == _PATH
    assert "/regenerate" not in endpoint, (
        "still calling the retired route — every request would 410"
    )


def test_async_posts_to_batch_not_the_retired_regenerate_route():
    client = _AsyncRecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=True)

    result = asyncio.run(service.regenerate_chapter("proj_abc", "chap_7"))

    assert result == _BATCH_RESPONSE
    method, endpoint, _ = client.calls[0]
    assert method == "POST"
    assert endpoint == _PATH
    assert "/regenerate" not in endpoint


def test_scopes_to_the_one_chapter():
    """A missing ``chapter_ids`` would re-narrate — and re-bill — the whole book."""
    client = _RecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    service.regenerate_chapter("proj_abc", "chap_7")

    body = client.calls[0][2]["json_data"]
    assert body["chapter_ids"] == ["chap_7"]


def test_forces_include_completed():
    """Without it the call is a silent no-op that 400s.

    A chapter being RE-rendered already has audio, so every one of its
    paragraphs is filtered out as already-complete and the API answers
    "No eligible paragraphs to narrate".
    """
    client = _RecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    service.regenerate_chapter("proj_abc", "chap_7")

    assert client.calls[0][2]["json_data"]["include_completed"] is True


def test_voice_override_is_passed_through_when_given():
    client = _RecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    service.regenerate_chapter("proj_abc", "chap_7", voice_id=55)

    assert client.calls[0][2]["json_data"]["voice_id"] == 55


def test_voice_key_is_omitted_when_not_given():
    """Sending ``voice_id: None`` is not the same as not sending it.

    The batch endpoint treats an explicit null as "override every paragraph's
    voice with nothing" rather than "leave each paragraph's voice alone".
    """
    client = _RecordingClient(response=_BATCH_RESPONSE)
    service = AudiobookService(client, async_mode=False)

    service.regenerate_chapter("proj_abc", "chap_7")

    assert "voice_id" not in client.calls[0][2]["json_data"]
