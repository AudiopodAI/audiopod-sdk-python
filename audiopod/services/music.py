"""
Music Service - Music generation
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class MusicService(BaseService):
    """Service for AI music generation."""

    def generate(
        self,
        prompt: str,
        duration: int = 30,
        model: str = "musicgen",
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Generate music from text prompt.

        Args:
            prompt: Text description of desired music
            duration: Duration in seconds (max 300)
            model: Model to use
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with audio URL when completed
        """
        data = {"prompt": prompt, "duration": duration, "model": model}

        if self.async_mode:
            return self._async_generate(data, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/music/generate", json_data=data)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_generate(
        self, data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/music/generate", json_data=data)
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get music generation job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/music/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/music/status/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List music generation jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/music/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/music/jobs", params={"skip": skip, "limit": limit}
        )

