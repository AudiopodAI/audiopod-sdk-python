"""
Unit tests for score-first music (AudioMusic v3) on ``MusicService`` (PLAT-3823).

The transport is mocked at the service's ``client`` boundary: a fake client
records ``(method, path, kwargs)`` and returns canned responses in order, so no
network is involved. Sleeps are patched out so polling tests run instantly.
"""

import asyncio

import pytest

from audiopod.exceptions import AudioPodError, ValidationError
from audiopod.services import music as music_module
from audiopod.services.music import MusicService

V3 = "/api/v1/music/v3"


class _Client:
    """Sync fake: records calls, returns queued responses (last one repeats)."""

    def __init__(self, *responses):
        self.responses = list(responses) or [{}]
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


class _AsyncClient(_Client):
    async def request(self, method, endpoint, **kwargs):  # type: ignore[override]
        return _Client.request(self, method, endpoint, **kwargs)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(music_module.time, "sleep", lambda _s: None)

    async def _fast_sleep(_s):
        return None

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)


def _svc(*responses, async_mode=False):
    client = (_AsyncClient if async_mode else _Client)(*responses)
    return MusicService(client, async_mode=async_mode), client


# --------------------------------------------------------------------------
# Request paths and bodies
# --------------------------------------------------------------------------


def test_availability_path():
    svc, client = _svc({"available": True})
    assert svc.v3_availability() == {"available": True}
    assert client.calls == [("GET", f"{V3}/availability", {})]


def test_compose_posts_plan_with_only_given_fields():
    svc, client = _svc({"job_id": 7, "status": "PENDING"})
    job = svc.compose(style="lofi piano", lyrics="[Verse]\nhello", cot="melody", seed=3)
    assert job["job_id"] == 7
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", f"{V3}/plan")
    assert kwargs["json_data"] == {
        "style": "lofi piano",
        "lyrics": "[Verse]\nhello",
        "cot": "melody",
        "seed": 3,
    }


def test_compose_sends_coming_soon_fields_when_given():
    svc, client = _svc({"job_id": 1, "status": "PENDING"})
    svc.compose(
        style="folk", lyrics="", description="a song about rain", target_seconds=90, language="en"
    )
    assert client.calls[0][2]["json_data"] == {
        "style": "folk",
        "description": "a song about rain",
        "target_seconds": 90,
        "language": "en",
    }


def test_compose_rejects_lyrics_and_description_together():
    svc, client = _svc()
    with pytest.raises(ValidationError):
        svc.compose(style="x", lyrics="la la", description="rain")
    assert client.calls == []


def test_revise_score_body():
    svc, client = _svc({"job_id": 9, "status": "PENDING"})
    svc.revise_score(
        source_job_id=5,
        instruction="make the chorus soar",
        section="Chorus",
        bars={"start": 9, "end": 16},
        allow_tempo_change=False,
    )
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", f"{V3}/revise")
    assert kwargs["json_data"] == {
        "source_job_id": 5,
        "instruction": "make the chorus soar",
        "section": "Chorus",
        "bars": {"start": 9, "end": 16},
        "allow_tempo_change": False,
    }


def test_revise_score_minimal_body():
    svc, client = _svc({"job_id": 9, "status": "PENDING"})
    svc.revise_score(5, "brighter")
    assert client.calls[0][2]["json_data"] == {"source_job_id": 5, "instruction": "brighter"}


def test_revise_instruction_limit():
    svc, client = _svc({"job_id": 9, "status": "PENDING"})
    svc.revise_score(5, "x" * 500)  # boundary is accepted
    with pytest.raises(ValidationError):
        svc.revise_score(5, "x" * 501)
    with pytest.raises(ValidationError):
        svc.revise_score(5, "   ")
    assert len(client.calls) == 1


@pytest.mark.parametrize(
    "bars",
    [{"start": 5}, {"start": 8, "end": 2}, {"start": "1", "end": 2}, {"start": True, "end": 2}],
)
def test_revise_rejects_bad_bars(bars):
    svc, client = _svc()
    with pytest.raises(ValidationError):
        svc.revise_score(5, "tighten", bars=bars)
    assert client.calls == []


def test_record_score_posts_edit():
    svc, client = _svc({"job_id": 11, "status": "PENDING"})
    svc.record_score(source_job_id=5, abc="X:1\nK:C\nCDEF|", allow_tempo_change=True)
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", f"{V3}/edit")
    assert kwargs["json_data"] == {
        "source_job_id": 5,
        "abc": "X:1\nK:C\nCDEF|",
        "allow_tempo_change": True,
    }


def test_record_score_requires_abc():
    svc, client = _svc()
    with pytest.raises(ValidationError):
        svc.record_score(source_job_id=5, abc="  ")
    assert client.calls == []


def test_generate_v3_posts_generate():
    svc, client = _svc({"job_id": 12, "status": "PENDING"})
    svc.generate_v3(style="synthwave", lyrics="", cfg_scale=4.0)
    method, path, kwargs = client.calls[0]
    assert (method, path) == ("POST", f"{V3}/generate")
    assert kwargs["json_data"] == {"style": "synthwave", "lyrics": "", "cfg_scale": 4.0}


def test_read_paths():
    svc, client = _svc([])
    svc.get_v3_job(3)
    svc.get_score(3)
    svc.list_v3_jobs(workflow="plan", source_job_id=3)
    assert client.calls == [
        ("GET", f"{V3}/jobs/3", {}),
        ("GET", f"{V3}/jobs/3/score", {}),
        (
            "GET",
            f"{V3}/jobs",
            {"params": {"skip": 0, "limit": 50, "workflow": "plan", "source_job_id": 3}},
        ),
    ]


# --------------------------------------------------------------------------
# Polling
# --------------------------------------------------------------------------


def test_compose_wait_polls_until_completed():
    svc, client = _svc(
        {"job_id": 7, "status": "PENDING"},
        {"job_id": 7, "status": "PROCESSING"},
        {"job_id": 7, "status": "COMPLETED", "score": {"abc": "X:1"}},
    )
    job = svc.compose(style="x", wait_for_completion=True)
    assert job["status"] == "COMPLETED"
    assert [c[1] for c in client.calls] == [f"{V3}/plan", f"{V3}/jobs/7", f"{V3}/jobs/7"]


def test_wait_raises_on_failure():
    svc, _ = _svc({"job_id": 7, "status": "FAILED", "error_message": "boom"})
    with pytest.raises(AudioPodError, match="boom"):
        svc.wait_for_v3_job(7)


def test_wait_times_out():
    svc, _ = _svc({"job_id": 7, "status": "PROCESSING"})
    with pytest.raises(TimeoutError):
        svc.wait_for_v3_job(7, timeout=0)


def test_async_record_and_wait():
    svc, client = _svc(
        {"job_id": 11, "status": "PENDING"},
        {"job_id": 11, "status": "completed", "audio_url": "https://x/a.flac"},
        async_mode=True,
    )
    job = asyncio.run(svc.record_score(5, "X:1\nK:C\nC|", wait_for_completion=True))
    assert job["audio_url"] == "https://x/a.flac"
    assert [c[1] for c in client.calls] == [f"{V3}/edit", f"{V3}/jobs/11"]


def test_async_simple_reads_return_awaitables():
    svc, client = _svc({"available": False}, async_mode=True)
    assert asyncio.run(svc.v3_availability()) == {"available": False}


# --------------------------------------------------------------------------
# v2 quality: accepted but not sent by default
# --------------------------------------------------------------------------


def test_v2_quality_not_sent_by_default():
    svc, client = _svc({"id": 1})
    svc.instrumental(prompt="ambient")
    assert "quality" not in client.calls[0][2]["json_data"]


def test_v2_quality_still_accepted():
    svc, client = _svc({"id": 1})
    svc.song(prompt="pop", lyrics="la", quality="premium")
    assert client.calls[0][2]["json_data"]["quality"] == "premium"
