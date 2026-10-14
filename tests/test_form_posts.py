"""
PLAT-3976: form posts without a file must reach the server as a form.

Several endpoints take FastAPI ``Form(...)`` fields (TTS generate, denoise,
stem / MIDI / speaker jobs by URL). The client's default ``Content-Type`` is
``application/json``; sending a urlencoded body under that header makes the
server ignore every field (a TTS call failed with 422 "input_text missing", a
URL denoise arrived with no URL). These tests put the request on a real local
HTTP server and read back what the server parsed.
"""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from audiopod import AsyncClient, Client


class _Echo(BaseHTTPRequestHandler):
    """Answers every POST with the Content-Type and form fields it received."""

    def do_POST(self):  # noqa: N802 (http.server API)
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode()
        ctype = self.headers.get("Content-Type", "")
        fields = (
            {k: v if len(v) > 1 else v[0] for k, v in parse_qs(body).items()}
            if ctype.startswith("application/x-www-form-urlencoded")
            else {}
        )
        query = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
        payload = json.dumps(
            {"id": 1, "job_id": 1, "ctype": ctype, "fields": fields, "query": query}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_args):
        pass


@pytest.fixture
def base_url():
    server = HTTPServer(("127.0.0.1", 0), _Echo)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_sync_tts_sends_a_form(base_url):
    client = Client(api_key="ap_test", base_url=base_url, max_retries=0)
    echo = client.voice.generate_speech(voice_id=368, text="hello")
    assert echo["ctype"].startswith("application/x-www-form-urlencoded")
    assert echo["fields"]["input_text"] == "hello"


def test_sync_denoise_by_url_sends_url_and_quality_mode(base_url):
    client = Client(api_key="ap_test", base_url=base_url, max_retries=0)
    echo = client.denoiser.denoise(
        url="https://example.com/a.mp3", mode="ultra", wait_for_completion=False
    )
    assert echo["fields"] == {"url": "https://example.com/a.mp3", "quality_mode": "ultra"}


def test_sync_denoise_without_mode_leaves_server_default(base_url):
    client = Client(api_key="ap_test", base_url=base_url, max_retries=0)
    echo = client.denoiser.denoise(url="https://example.com/a.mp3", wait_for_completion=False)
    assert "quality_mode" not in echo["fields"]
    assert "mode" not in echo["fields"]


def test_sync_json_posts_stay_json(base_url):
    client = Client(api_key="ap_test", base_url=base_url, max_retries=0)
    echo = client.request("POST", "/x", json_data={"a": 1})
    assert echo["ctype"] == "application/json"


def test_async_tts_sends_a_form(base_url):
    async def run():
        async with AsyncClient(api_key="ap_test", base_url=base_url) as client:
            return await client.voice.generate_speech(voice_id=368, text="hello")

    echo = asyncio.run(run())
    assert echo["ctype"].startswith("application/x-www-form-urlencoded")
    assert echo["fields"]["input_text"] == "hello"


def test_async_form_repeats_list_values_and_drops_none(base_url):
    async def run():
        async with AsyncClient(api_key="ap_test", base_url=base_url) as client:
            return await client.request("POST", "/x", data={"k": ["a", "b"], "n": None, "b": True})

    echo = asyncio.run(run())
    assert echo["fields"] == {"k": ["a", "b"], "b": "True"}


def test_sync_diarize_sends_num_speakers_as_query_and_url_as_form(base_url):
    client = Client(api_key="ap_test", base_url=base_url, max_retries=0)
    echo = client.speaker.diarize(url="https://example.com/a.mp3", num_speakers=2)
    assert echo["fields"] == {"url": "https://example.com/a.mp3"}
    assert echo["query"] == {"num_speakers": "2"}


def test_async_diarize_sends_num_speakers_as_query(base_url):
    async def run():
        async with AsyncClient(api_key="ap_test", base_url=base_url) as client:
            return await client.speaker.diarize(url="https://example.com/a.mp3", num_speakers=3)

    echo = asyncio.run(run())
    assert echo["fields"] == {"url": "https://example.com/a.mp3"}
    assert echo["query"] == {"num_speakers": "3"}
