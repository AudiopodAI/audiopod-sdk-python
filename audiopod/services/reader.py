"""
Audio Reader Service - Turn a URL or pasted text into a listenable audio article.

Submit a URL or raw content, get back a narrated audio article with an embeddable
player. Use :meth:`ReaderService.estimate` to preview the credit cost first.

API Routes (all under ``/api/v1/reader``):
- GET    /                        - List reader jobs (paginated)
- POST   /estimate                - Estimate credits for a piece of content
- POST   /generate                - Create a reader job
- GET    /{job_id}                - Get a reader job
- DELETE /{job_id}                - Delete a reader job
- GET    /public/{job_id}         - Get the public view of a completed job
"""

import time
from typing import Any, Dict, Optional

from .base import BaseService

_BASE = "/api/v1/reader"

# Terminal statuses (compared case-insensitively).
_DONE_STATUSES = frozenset({"completed"})
_FAILED_STATUSES = frozenset({"failed", "error", "cancelled", "canceled"})


class ReaderService(BaseService):
    """
    Service for the Audio Reader.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Preview cost, then generate and wait for the audio
        est = client.reader.estimate(url="https://example.com/article")
        print(est["estimated_credits"], "credits")

        job = client.reader.generate(
            url="https://example.com/article",
            wait_for_completion=True,
        )
        print(job["audio_url"], job["embed_url"])
        ```
    """

    def list_jobs(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """List reader jobs (paginated)."""
        params = {"page": page, "page_size": page_size}
        if self.async_mode:
            return self._async_list_jobs(params)
        return self.client.request("GET", f"{_BASE}/", params=params)

    async def _async_list_jobs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/", params=params)

    def estimate(
        self,
        url: Optional[str] = None,
        content: Optional[str] = None,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Estimate credits for a reader job.

        Provide either ``url`` or ``content``.

        Args:
            url: URL of the article to read.
            content: Raw text to read (alternative to ``url``).
            voice: Voice to narrate with. If omitted, the service default is used.
        """
        body: Dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if content is not None:
            body["content"] = content
        if voice is not None:
            body["voice"] = voice
        if self.async_mode:
            return self._async_estimate(body)
        return self.client.request("POST", f"{_BASE}/estimate", json_data=body)

    async def _async_estimate(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", f"{_BASE}/estimate", json_data=body)

    def generate(
        self,
        url: Optional[str] = None,
        content: Optional[str] = None,
        title: Optional[str] = None,
        voice: Optional[str] = None,
        webhook_url: Optional[str] = None,
        show_branding: bool = True,
        wait_for_completion: bool = False,
        timeout: int = 600,
        poll_interval: int = 3,
    ) -> Dict[str, Any]:
        """
        Create a reader job that narrates a URL or pasted text.

        Provide either ``url`` or ``content``.

        Args:
            url: URL of the article to read.
            content: Raw text to read (alternative to ``url``).
            title: Optional title for the audio article.
            voice: Voice to narrate with. If omitted, the service default is used.
            webhook_url: URL notified when the job finishes.
            show_branding: Whether the embedded player shows AudioPod branding.
            wait_for_completion: Poll until the job completes.
            timeout: Max seconds to wait when ``wait_for_completion`` is True.
            poll_interval: Seconds between status polls.

        Returns:
            The reader job dict (includes ``id``, ``status``, and, when done,
            ``audio_url`` / ``embed_url``).
        """
        body: Dict[str, Any] = {"show_branding": show_branding}
        for k, v in {
            "url": url,
            "content": content,
            "title": title,
            "voice": voice,
            "webhook_url": webhook_url,
        }.items():
            if v is not None:
                body[k] = v
        if self.async_mode:
            return self._async_generate(body, wait_for_completion, timeout, poll_interval)
        response = self.client.request("POST", f"{_BASE}/generate", json_data=body)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_reader(job_id, timeout, poll_interval)
        return response

    async def _async_generate(
        self, body: Dict[str, Any], wait_for_completion: bool, timeout: int, poll_interval: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", f"{_BASE}/generate", json_data=body)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_reader(job_id, timeout, poll_interval)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get a reader job by ID."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"{_BASE}/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/{job_id}")

    def delete_job(self, job_id: int) -> Dict[str, Any]:
        """Delete a reader job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"{_BASE}/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"{_BASE}/{job_id}")

    def get_public(self, job_id: int) -> Dict[str, Any]:
        """Get the public view of a completed reader job."""
        if self.async_mode:
            return self._async_get_public(job_id)
        return self.client.request("GET", f"{_BASE}/public/{job_id}")

    async def _async_get_public(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/public/{job_id}")

    def _wait_for_reader(self, job_id: int, timeout: int, poll_interval: int) -> Dict[str, Any]:
        """Poll a reader job until it completes (or fails)."""
        start = time.time()
        while time.time() - start < timeout:
            job = self.get_job(job_id)
            status = str(job.get("status", "")).lower()
            if status in _DONE_STATUSES:
                return job
            if status in _FAILED_STATUSES:
                raise Exception(f"Reader job failed: {job.get('error', 'Unknown error')}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Reader job {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_reader(self, job_id: int, timeout: int, poll_interval: int) -> Dict[str, Any]:
        """Async poll a reader job until it completes (or fails)."""
        import asyncio

        start = time.time()
        while time.time() - start < timeout:
            job = await self.get_job(job_id)
            status = str(job.get("status", "")).lower()
            if status in _DONE_STATUSES:
                return job
            if status in _FAILED_STATUSES:
                raise Exception(f"Reader job failed: {job.get('error', 'Unknown error')}")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Reader job {job_id} did not complete within {timeout} seconds")
