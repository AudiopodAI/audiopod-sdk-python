"""Optional public metadata and actual sync/async JSON compatibility."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Literal, Optional, get_type_hints

import pytest

from audiopod import Client, AsyncClient, PodcastDialogue, PodcastProject, PodcastTakeTiming


TIMING = {"dialogue_id": "line", "take_identity": None, "audio_sha256": "a" * 64,
    "format": "wav", "start_frame": 11025, "end_frame": 22050, "sample_rate": 44100}
PAYLOADS = [
    {"id": "project", "dialogues": [{"speaker": "Host", "text": "Legacy"}], "future_response_field": "kept"},
    {"id": "project", "dialogues": [{"id": "line", "speaker": "Host", "text": "Legacy", "take_identity": None}], "combined_timing": None},
    {"id": "project", "dialogues": [{"id": "line", "speaker": "Host", "text": "Hello", "take_identity": "b" * 64}], "combined_timing": [TIMING]},
]


def test_public_metadata_projection_types_are_optional_nullable_and_use_integer_frames():
    assert "take_identity" in PodcastDialogue.__optional_keys__
    assert get_type_hints(PodcastDialogue)["take_identity"] == Optional[str]
    assert "combined_timing" in PodcastProject.__optional_keys__
    assert get_type_hints(PodcastProject)["combined_timing"] == Optional[List[PodcastTakeTiming]]
    assert get_type_hints(PodcastTakeTiming)["take_identity"] == Optional[str]
    assert get_type_hints(PodcastTakeTiming)["format"] == Literal["wav"]
    for field in ("start_frame", "end_frame", "sample_rate"):
        assert get_type_hints(PodcastTakeTiming)[field] is int


@pytest.mark.parametrize("payload", PAYLOADS, ids=["legacy", "nullable", "measured"])
@pytest.mark.parametrize("async_mode", [False, True], ids=["sync", "async"])
@pytest.mark.asyncio
async def test_actual_json_reads_preserve_metadata_and_existing_transcript_ids(payload, async_mode):
    writes = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.reply()

        def do_PUT(self):
            writes.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.reply()

        def reply(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payload).encode("utf-8"))

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    params = {"api_key": "ap_isolated", "base_url": "http://127.0.0.1:{}".format(server.server_port), "max_retries": 0}
    try:
        if async_mode:
            async with AsyncClient(**params) as client:
                project = await client.podcast.get_project("project")
                await client.podcast.update_transcript("project", project["dialogues"])
        else:
            with Client(**params) as client:
                project = client.podcast.get_project("project")
                client.podcast.update_transcript("project", project["dialogues"])
        assert project == payload
        assert writes == [{"dialogues": payload["dialogues"]}]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
