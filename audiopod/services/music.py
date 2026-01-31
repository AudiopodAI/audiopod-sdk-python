"""
Music Service - Music generation

API Routes:
- POST /api/v1/music/text2music         - Generate music with vocals
- POST /api/v1/music/prompt2instrumental - Generate instrumental music
- POST /api/v1/music/lyric2vocals       - Generate vocals from lyrics
- POST /api/v1/music/text2rap           - Generate rap music
- GET  /api/v1/music/jobs/{id}/status   - Get job status
- GET  /api/v1/music/jobs               - List jobs
- DELETE /api/v1/music/jobs/{id}        - Delete job
- GET  /api/v1/music/presets            - Get genre presets
"""

from typing import Optional, Dict, Any, List, Literal
from .base import BaseService


MusicTask = Literal["text2music", "prompt2instrumental", "lyric2vocals", "text2rap", "text2samples"]


class MusicService(BaseService):
    """Service for AI music generation."""

    def generate(
        self,
        prompt: str,
        task: MusicTask = "prompt2instrumental",
        duration: int = 30,
        lyrics: Optional[str] = None,
        genre_preset: Optional[str] = None,
        display_name: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Generate music from text prompt.

        Args:
            prompt: Text description of desired music
            task: Generation task type:
                - "prompt2instrumental": Instrumental music (no vocals)
                - "text2music": Music with vocals (requires lyrics)
                - "text2rap": Rap music (requires lyrics)
                - "lyric2vocals": Generate vocals from lyrics
            duration: Duration in seconds (default 30, max varies by task)
            lyrics: Lyrics for vocal tasks
            genre_preset: Genre preset name
            display_name: Custom name for the job
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with audio URL when completed
        """
        data = {
            "prompt": prompt,
            "audio_duration": duration,
        }
        
        if lyrics:
            data["lyrics"] = lyrics
        if genre_preset:
            data["genre_preset"] = genre_preset
        if display_name:
            data["display_name"] = display_name

        endpoint = f"/api/v1/music/{task}"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)

        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    async def _async_generate(
        self, endpoint: str, data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_music(job_id, timeout)
        return response

    def instrumental(
        self,
        prompt: str,
        duration: int = 30,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """Generate instrumental music (no vocals)."""
        return self.generate(
            prompt=prompt,
            task="prompt2instrumental",
            duration=duration,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
        )

    def song(
        self,
        prompt: str,
        lyrics: str,
        duration: int = 60,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """Generate a song with vocals."""
        return self.generate(
            prompt=prompt,
            task="text2music",
            lyrics=lyrics,
            duration=duration,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
        )

    def rap(
        self,
        prompt: str,
        lyrics: str,
        duration: int = 60,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """Generate rap music."""
        return self.generate(
            prompt=prompt,
            task="text2rap",
            lyrics=lyrics,
            duration=duration,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
        )

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get music generation job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/music/jobs/{job_id}/status")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/music/jobs/{job_id}/status")

    def list_jobs(self, skip: int = 0, limit: int = 50, task: Optional[str] = None) -> List[Dict[str, Any]]:
        """List music generation jobs."""
        params = {"skip": skip, "limit": limit}
        if task:
            params["task"] = task
            
        if self.async_mode:
            return self._async_list_jobs(params)
        return self.client.request("GET", "/api/v1/music/jobs", params=params)

    async def _async_list_jobs(self, params: Dict) -> List[Dict[str, Any]]:
        return await self.client.request("GET", "/api/v1/music/jobs", params=params)

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a music generation job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/music/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/music/jobs/{job_id}")

    def get_presets(self) -> Dict[str, Any]:
        """Get available genre presets."""
        if self.async_mode:
            return self._async_get_presets()
        return self.client.request("GET", "/api/v1/music/presets")

    async def _async_get_presets(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/music/presets")

    def _wait_for_music(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Wait for music generation job completion."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Music generation failed: {job.get('error_message', 'Unknown error')}")

            time.sleep(5)

        raise TimeoutError(f"Music generation {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_music(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async wait for music generation job completion."""
        import asyncio
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Music generation failed: {job.get('error_message', 'Unknown error')}")

            await asyncio.sleep(5)

        raise TimeoutError(f"Music generation {job_id} did not complete within {timeout} seconds")

