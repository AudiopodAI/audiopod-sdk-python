"""
PLAT-3976: a new voice clone is PENDING until processed, and speech with it
fails until it is COMPLETED. ``create_voice(..., wait_for_ready=True)`` polls
``GET /api/v1/voice/voices/{id}/status`` until it is usable.

Also pins the actionable 401 / 402 messages. HTTP is mocked at the service's
``client`` boundary (voice) or the ``requests`` response (errors); sleeps are
patched out.
"""

import asyncio
import json

import pytest
import requests

from audiopod import Client
from audiopod.exceptions import AudioPodError, AuthenticationError, InsufficientBalanceError
from audiopod.services import voice as voice_module
from audiopod.services.voice import VoiceService

STATUS = "/api/v1/voice/voices/7/status"


class _Client:
    """Sync fake: records calls, returns queued responses (last one repeats)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint))
        if len(self.responses) > 1:
            return self.responses.pop(0)
        return self.responses[0]


class _AsyncClient(_Client):
    async def request(self, method, endpoint, **kwargs):  # type: ignore[override]
        return _Client.request(self, method, endpoint, **kwargs)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(voice_module.time, "sleep", lambda _s: None)

    async def _fast_sleep(_s):
        return None

    monkeypatch.setattr(asyncio, "sleep", _fast_sleep)


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "sample.wav"
    path.write_bytes(b"RIFF")
    return str(path)


def _svc(*responses, async_mode=False):
    client = (_AsyncClient if async_mode else _Client)(*responses)
    return VoiceService(client, async_mode=async_mode), client


PENDING = {"id": 7, "status": "PENDING"}
PROCESSING = {"id": 7, "status": "PROCESSING"}
DONE = {"id": 7, "status": "COMPLETED", "name": "Me"}


def test_create_without_wait_returns_immediately(sample):
    svc, client = _svc(PENDING)
    assert svc.create_voice("Me", sample) == PENDING
    assert [c[0] for c in client.calls] == ["POST"]


def test_create_wait_polls_status_until_completed(sample):
    svc, client = _svc(PENDING, PROCESSING, DONE)
    assert svc.create_voice("Me", sample, wait_for_ready=True) == DONE
    assert client.calls == [
        ("POST", "/api/v1/voice/voice-profiles"),
        ("GET", STATUS),
        ("GET", STATUS),
    ]


def test_create_wait_skips_polling_when_already_completed(sample):
    svc, client = _svc(DONE)
    assert svc.create_voice("Me", sample, wait_for_ready=True) == DONE
    assert len(client.calls) == 1


def test_lowercase_status_is_accepted():
    svc, _ = _svc({"id": 7, "status": "completed"})
    assert svc.wait_for_voice_ready(7)["status"] == "completed"


def test_failed_clone_raises_with_reason(sample):
    svc, _ = _svc(PENDING, {"id": 7, "status": "FAILED", "error_message": "too short"})
    with pytest.raises(AudioPodError, match="Voice 7 cloning failed: too short"):
        svc.create_voice("Me", sample, wait_for_ready=True)


def test_timeout_raises_timeout_error(sample):
    svc, _ = _svc(PENDING)
    with pytest.raises(TimeoutError, match="last status: PENDING"):
        svc.create_voice("Me", sample, wait_for_ready=True, timeout=0)


def test_wait_accepts_bare_id():
    svc, client = _svc(PROCESSING, DONE)
    assert svc.wait_for_voice_ready(7) == DONE
    assert client.calls == [("GET", STATUS), ("GET", STATUS)]


def test_response_without_id_is_a_clear_error():
    svc, _ = _svc({})
    with pytest.raises(AudioPodError, match="no numeric 'id'"):
        svc.wait_for_voice_ready({"status": "PENDING"})


def test_async_create_wait(sample):
    svc, client = _svc(PENDING, PROCESSING, DONE, async_mode=True)
    result = asyncio.run(svc.create_voice("Me", sample, wait_for_ready=True))
    assert result == DONE
    assert [c[0] for c in client.calls] == ["POST", "GET", "GET"]


def test_async_failed_clone_raises(sample):
    svc, _ = _svc(PENDING, {"id": 7, "status": "CANCELLED"}, async_mode=True)
    with pytest.raises(AudioPodError, match="cancelled"):
        asyncio.run(svc.create_voice("Me", sample, wait_for_ready=True))


# --------------------------------------------------------------------------
# Actionable errors
# --------------------------------------------------------------------------


def _response(status, body):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(body).encode()
    resp.url = "https://api.audiopod.ai/x"
    return resp


def test_missing_key_message_says_how_to_fix(monkeypatch):
    monkeypatch.delenv("AUDIOPOD_API_KEY", raising=False)
    with pytest.raises(AuthenticationError, match="AUDIOPOD_API_KEY.*dashboard/account/api-keys"):
        Client()


def test_401_message_says_how_to_fix():
    client = Client(api_key="ap_test")
    with pytest.raises(AuthenticationError) as err:
        client._handle_response(_response(401, {"detail": "Invalid API key"}))
    assert "Invalid API key" in str(err.value)
    assert "Set AUDIOPOD_API_KEY" in str(err.value)
    assert "https://audiopod.ai/dashboard/account/api-keys" in str(err.value)


def test_402_reads_nested_detail_and_points_at_top_up():
    client = Client(api_key="ap_test")
    body = {
        "detail": {
            "error": "insufficient_api_balance",
            "message": "Insufficient API wallet balance. Required: $0.50, Available: $0.10",
            "required_cents": 50,
            "available_cents": 10,
        }
    }
    with pytest.raises(InsufficientBalanceError) as err:
        client._handle_response(_response(402, body))
    assert err.value.required_cents == 50
    assert err.value.available_cents == 10
    assert "Required: $0.50" in str(err.value)
    assert "prepaid API wallet" in str(err.value)
    assert "plan or pay-as-you-go credits" in str(err.value)
    assert "https://audiopod.ai/pricing" in str(err.value)
    assert "create_topup_checkout" in str(err.value)
    assert "Available: $0.10. API-key requests" in str(err.value)


def test_402_with_plain_string_detail():
    client = Client(api_key="ap_test")
    with pytest.raises(InsufficientBalanceError, match="Not enough credits"):
        client._handle_response(_response(402, {"detail": "Not enough credits."}))


def test_402_has_no_double_period():
    client = Client(api_key="ap_test")
    with pytest.raises(InsufficientBalanceError) as err:
        client._handle_response(_response(402, {"detail": "Insufficient balance."}))
    assert str(err.value).startswith("Insufficient balance. API-key requests")


def test_cli_clone_uploads_the_reference_and_waits(monkeypatch, sample):
    """`audiopod clone` passed an unknown `files=` kwarg (TypeError) before."""
    from audiopod import cli

    seen = {}

    class _Voice:
        def create_voice(self, **kwargs):
            seen.update(kwargs)
            return DONE

    class _Fake:
        voice = _Voice()

    monkeypatch.setattr(cli, "_client", lambda _args: _Fake())
    args = cli.build_parser().parse_args(["clone", sample, "--name", "Me"])
    args.func(args)
    assert seen["audio_file"] == sample
    assert seen["wait_for_ready"] is True
    assert seen["timeout"] == 300


def test_cli_clone_timeout_exits_cleanly(monkeypatch, sample, capsys):
    """A still-PENDING voice past --timeout prints a one-line error, no traceback."""
    from audiopod import cli

    svc, _ = _svc(PENDING)

    class _Fake:
        voice = svc

    monkeypatch.setattr(cli, "_client", lambda _args: _Fake())
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["clone", sample, "--name", "Me", "--timeout", "0"])
    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert err.startswith("audiopod: Voice 7 was not ready after 0 seconds")
    assert "Traceback" not in err
