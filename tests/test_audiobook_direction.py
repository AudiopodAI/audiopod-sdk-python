"""
Unit tests for the audiobook direction surface (PLAT-2677).

These endpoints existed on the API for days before this SDK could reach them,
which is the gap this suite keeps closed. The transport is mocked at the
service's ``client`` boundary — a fake records ``(method, path, kwargs)`` and
returns a canned response, so no network is involved. Both the sync and the
``async_mode`` branch are covered.
"""

import asyncio

import pytest

from audiopod.services.audiobook import AudiobookService


class _RecordingClient:
    """Sync fake: records calls, replays a queue of canned responses."""

    def __init__(self, responses=None):
        self.responses = list(responses or [{}])
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


class _AsyncRecordingClient(_RecordingClient):
    async def request(self, method, endpoint, **kwargs):  # type: ignore[override]
        self.calls.append((method, endpoint, kwargs))
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


# ------------------------------------------------------------------ auto_direct


def test_auto_direct_posts_to_the_direction_path():
    client = _RecordingClient([{"job_id": "901", "total_chapters": 23}])
    service = AudiobookService(client, async_mode=False)

    result = service.auto_direct("proj_abc")

    method, endpoint, kwargs = client.calls[0]
    assert method == "POST"
    assert endpoint == "/api/v1/audiobook/projects/proj_abc/direction/auto"
    assert result["total_chapters"] == 23


def test_auto_direct_omits_chapter_ids_when_directing_the_whole_book():
    """The server reads a missing ``chapter_ids`` as "the whole book". Sending
    an empty list instead would scope the run to nothing and 400 with "No
    chapters found to direct"."""
    client = _RecordingClient([{"job_id": "1", "total_chapters": 1}])
    service = AudiobookService(client, async_mode=False)

    service.auto_direct("proj_abc")

    assert client.calls[0][2]["json_data"] == {}


def test_none_chapter_subset_means_the_whole_book():
    client = _RecordingClient([{"job_id": "1", "total_chapters": 1}])
    service = AudiobookService(client, async_mode=False)

    service.auto_direct("proj_abc", chapter_ids=None)

    assert "chapter_ids" not in client.calls[0][2]["json_data"]


def test_an_empty_chapter_subset_is_rejected_not_widened():
    """PLAT-3944: ``[]`` used to be dropped and re-direct the whole book."""
    client = _RecordingClient([{"job_id": "1", "total_chapters": 1}])
    service = AudiobookService(client, async_mode=False)

    with pytest.raises(ValueError, match="chapter_ids is empty"):
        service.auto_direct("proj_abc", chapter_ids=[])
    assert client.calls == []


def test_auto_direct_scopes_to_a_chapter_subset():
    client = _RecordingClient([{"job_id": "1", "total_chapters": 1}])
    service = AudiobookService(client, async_mode=False)

    service.auto_direct("proj_abc", chapter_ids=["ch1", "ch2"])

    assert client.calls[0][2]["json_data"] == {"chapter_ids": ["ch1", "ch2"]}


def test_auto_direct_async_branch_returns_an_awaitable():
    client = _AsyncRecordingClient([{"job_id": "901", "total_chapters": 2}])
    service = AudiobookService(client, async_mode=True)

    result = asyncio.run(service.auto_direct("proj_abc"))

    assert result["job_id"] == "901"


# ----------------------------------------------------------------------- status


def test_status_endpoints_hit_their_documented_paths():
    client = _RecordingClient([{"job_id": "901", "status": "COMPLETED"}])
    service = AudiobookService(client, async_mode=False)

    service.auto_direction_status("proj_abc", 901)
    service.latest_auto_direction("proj_abc")

    assert client.calls[0][1] == (
        "/api/v1/audiobook/projects/proj_abc/direction/auto/901/status"
    )
    assert client.calls[0][0] == "GET"
    assert client.calls[1][1] == (
        "/api/v1/audiobook/projects/proj_abc/direction/auto/latest"
    )


@pytest.mark.parametrize(
    "state,finished",
    [
        ("COMPLETED", True),
        ("FAILED", True),
        ("CANCELED", True),
        ("CANCELLED", True),
        ("completed", True),
        ("PROCESSING", False),
        ("PENDING", False),
        ("", False),
    ],
)
def test_terminal_state_detection(state, finished):
    assert AudiobookService._direction_finished({"status": state}) is finished


def test_auto_direct_and_wait_polls_until_terminal():
    client = _RecordingClient(
        [
            {"job_id": "901", "total_chapters": 2},
            {"job_id": "901", "status": "PENDING"},
            {"job_id": "901", "status": "PROCESSING"},
            {"job_id": "901", "status": "COMPLETED", "result": {"directed_count": 40}},
        ]
    )
    service = AudiobookService(client, async_mode=False)

    status = service.auto_direct_and_wait("proj_abc", poll_interval=0)

    assert status["status"] == "COMPLETED"
    assert status["result"]["directed_count"] == 40


def test_auto_direct_and_wait_returns_a_failed_run_rather_than_hanging():
    client = _RecordingClient(
        [
            {"job_id": "901", "total_chapters": 2},
            {"job_id": "901", "status": "FAILED", "error_message": "nope"},
        ]
    )
    service = AudiobookService(client, async_mode=False)

    status = service.auto_direct_and_wait("proj_abc", poll_interval=0)

    assert status["status"] == "FAILED"


def test_auto_direct_and_wait_times_out_with_the_last_state_named():
    client = _RecordingClient(
        [{"job_id": "901", "total_chapters": 2}, {"job_id": "901", "status": "PENDING"}]
    )
    service = AudiobookService(client, async_mode=False)

    with pytest.raises(TimeoutError) as excinfo:
        service.auto_direct_and_wait("proj_abc", timeout=0, poll_interval=0)
    assert "901" in str(excinfo.value)


# -------------------------------------------------------------- parse_manuscript


def test_parse_manuscript_sends_only_the_required_fields_by_default():
    """``auto_direction`` is tri-state on the wire: absent means "use the
    default for my auth method". Sending ``false`` by default would silently
    turn that into an explicit opt-out."""
    client = _RecordingClient([{"job_id": 5}])
    service = AudiobookService(client, async_mode=False)

    service.parse_manuscript("proj_abc", "key123", "book.epub")

    files = client.calls[0][2]["files"]
    assert set(files) == {"file_key", "filename"}


@pytest.mark.parametrize("value,wire", [(True, "true"), (False, "false")])
def test_parse_manuscript_forwards_an_explicit_auto_direction(value, wire):
    client = _RecordingClient([{"job_id": 5}])
    service = AudiobookService(client, async_mode=False)

    service.parse_manuscript("proj_abc", "key123", "book.epub", auto_direction=value)

    assert client.calls[0][2]["files"]["auto_direction"] == (None, wire)


def test_parse_manuscript_forwards_force():
    client = _RecordingClient([{"job_id": 5}])
    service = AudiobookService(client, async_mode=False)

    service.parse_manuscript("proj_abc", "key123", "book.epub", force=True)

    assert client.calls[0][2]["files"]["force"] == (None, "true")


# ---------------------------------------------------------------- batch_narrate


def test_batch_narrate_passes_delivery_mode_through_verbatim():
    client = _RecordingClient([{"job_id": 7, "total_paragraphs": 40}])
    service = AudiobookService(client, async_mode=False)

    service.batch_narrate(
        "proj_abc",
        chapter_ids=["ch8"],
        include_completed=True,
        narration_settings={"delivery_mode": "creative"},
    )

    body = client.calls[0][2]["json_data"]
    assert body["narration_settings"]["delivery_mode"] == "creative"
    assert body["include_completed"] is True
    assert body["chapter_ids"] == ["ch8"]
