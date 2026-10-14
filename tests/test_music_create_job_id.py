"""
PLAT-3976: the v2 music create endpoints answer ``{"job": {"id": N}, "message": ...}``.

``generate(..., wait_for_completion=True)`` read only a flat ``id`` / ``job_id``,
so it polled ``/api/v1/music/jobs/None/status``. It must poll the nested job id.
"""

import asyncio

from audiopod.services.music import MusicService


class _Client:
    def __init__(self):
        self.calls = []

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint))
        if method == "POST":
            return {"job": {"id": 9, "status": "PENDING"}, "message": "started"}
        return {"id": 9, "status": "COMPLETED", "output_url": "https://x/9.flac"}


class _AsyncClient(_Client):
    async def request(self, method, endpoint, **kwargs):  # type: ignore[override]
        return _Client.request(self, method, endpoint, **kwargs)


def test_generate_waits_on_the_nested_job_id():
    client = _Client()
    track = MusicService(client).generate(prompt="lo-fi", duration=30, wait_for_completion=True)
    assert track["output_url"] == "https://x/9.flac"
    assert ("GET", "/api/v1/music/jobs/9/status") in client.calls


def test_async_generate_waits_on_the_nested_job_id():
    client = _AsyncClient()
    svc = MusicService(client, async_mode=True)
    track = asyncio.run(svc.generate(prompt="lo-fi", duration=30, wait_for_completion=True))
    assert track["output_url"] == "https://x/9.flac"
    assert ("GET", "/api/v1/music/jobs/9/status") in client.calls
