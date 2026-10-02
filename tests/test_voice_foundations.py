"""No-network contract and transport checks for caller-scoped voice workflows."""
import asyncio
import re
from pathlib import Path
from unittest.mock import Mock

import pytest

from audiopod import Client, __version__
from audiopod.config import ClientConfig
from audiopod.exceptions import APIError
from audiopod.services.voice import VoiceService


class RecordingClient:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if self.error:
            raise self.error
        return {"readiness": {"state": "unknown"}, "quote_identity": "q1"}


class AsyncRecordingClient(RecordingClient):
    async def request(self, method, path, **kwargs):
        return super().request(method, path, **kwargs)


@pytest.mark.parametrize("async_mode", [False, True])
def test_unknown_readiness_is_not_promoted_and_scope_cas_preserved(async_mode):
    client = AsyncRecordingClient() if async_mode else RecordingClient()
    voice = VoiceService(client, async_mode=async_mode)
    run = asyncio.run if async_mode else lambda result: result
    result = run(voice.capabilities("uuid1", "audition"))
    assert result["readiness"]["state"] == "unknown"
    run(voice.set_pronunciation("hi", 0, project_kind="podcast", project_id="p1",
                              entries=[{"source": "राकेश", "alias": "राकेश जी"}]))
    run(voice.reset_pronunciation("hi", 4, project_kind="podcast", project_id="p1"))
    assert client.calls[0][2]["params"] == {"operation": "audition"}
    assert client.calls[1][2]["json_data"]["expected_version"] == 0
    assert client.calls[1][2]["params"]["project_id"] == "p1"
    assert client.calls[2][0] == "DELETE"
    assert client.calls[2][2]["params"]["expected_version"] == 4


@pytest.mark.parametrize("async_mode", [False, True])
def test_quote_does_not_accept_and_confirmation_preserves_context(async_mode):
    client = AsyncRecordingClient() if async_mode else RecordingClient()
    voice = VoiceService(client, async_mode=async_mode)
    run = asyncio.run if async_mode else lambda result: result
    context = {"text": "नमस्ते राकेश", "language": "hi", "project_kind": "tts", "project_id": "p1"}
    run(voice.quote_audition(5, **context))
    assert len(client.calls) == 1
    assert client.calls[0][1].endswith("/5/quote")
    assert "confirm" not in client.calls[0][2]["json_data"]
    run(voice.audition(5, quote_identity="q1", idempotency_key="2fd18aeb-a0c7-477e-a1a3-d5c7c3f44154", confirm=True, **context))
    assert client.calls[1][2]["json_data"] == {**context, "quote_identity": "q1", "idempotency_key": "2fd18aeb-a0c7-477e-a1a3-d5c7c3f44154", "confirm": True}


@pytest.mark.parametrize("async_mode", [False, True])
def test_stale_quote_error_is_not_requoted_or_retried(async_mode):
    error = APIError("audition_quote_changed", status_code=409)
    client = AsyncRecordingClient(error) if async_mode else RecordingClient(error)
    voice = VoiceService(client, async_mode=async_mode)
    with pytest.raises(APIError) as exc:
        result = voice.audition(5, text="hello", language="en", quote_identity="old", idempotency_key="2fd18aeb-a0c7-477e-a1a3-d5c7c3f44154", confirm=True)
        if async_mode:
            asyncio.run(result)
    assert exc.value is error
    assert len(client.calls) == 1


@pytest.mark.parametrize("async_mode", [False, True])
def test_reference_crop_file_is_closed_after_request(tmp_path, async_mode):
    sample = tmp_path / "reference.wav"
    sample.write_bytes(b"fixture")
    client = AsyncRecordingClient() if async_mode else RecordingClient()
    voice = VoiceService(client, async_mode=async_mode)
    result = voice.reference_diagnostics(str(sample), 2.25, 7.5)
    if async_mode:
        asyncio.run(result)
    method, path, args = client.calls[0]
    assert (method, path) == ("POST", "/api/v1/voice/reference/diagnostics")
    assert args["data"] == {"crop_start_seconds": 2.25, "crop_end_seconds": 7.5}
    assert args["files"]["file"][1].closed


def test_generation_pins_expected_pronunciation_identity():
    client = RecordingClient()
    voice = VoiceService(client)
    voice.generate_speech(5, "hello", pronunciation_project_kind="tts",
                          pronunciation_project_id="p1", pronunciation_identity="rules1")
    assert client.calls[0][2]["data"]["pronunciation_identity"] == "rules1"


def test_form_content_type_and_no_automatic_charged_post_retry():
    client = Client(api_key="ap_fixture_not_a_secret", base_url="https://fixture.invalid")
    adapter = client.session.get_adapter("https://")
    assert "POST" not in adapter.max_retries.allowed_methods
    client.session.request = Mock()
    client._handle_response = lambda response: {}
    client.request("POST", "/api/v1/voice/voices/5/generate", data={"input_text": "hello"})
    args = client.session.request.call_args.kwargs
    assert args["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    client.request("POST", "/fixture", json_data={"value": 1})
    assert client.session.request.call_args.kwargs["headers"]["Content-Type"] == "application/json"
    client.close()


def test_runtime_transport_and_published_versions_match():
    metadata = (Path(__file__).parents[1] / "pyproject.toml").read_text()
    published = re.search(r'^version = "([^"]+)"', metadata, re.M).group(1)
    assert __version__ == ClientConfig().version == published
