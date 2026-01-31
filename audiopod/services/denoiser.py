"""
Denoiser Service - Audio noise reduction

API Routes:
- POST /api/v1/denoiser/denoise      - Denoise audio
- GET  /api/v1/denoiser/jobs/{id}    - Get job details
- GET  /api/v1/denoiser/jobs         - List jobs
- DELETE /api/v1/denoiser/jobs/{id}  - Delete job
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class DenoiserService(BaseService):
    """Service for audio noise reduction."""

    def denoise(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        mode: str = "balanced",
        wait_for_completion: bool = False,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Remove noise from audio.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            mode: Denoise mode ("balanced", "studio", or "ultra")
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with denoised audio URL when completed
        """
        data = {"mode": mode}
        if url:
            data["url"] = url

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_denoise(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/denoiser/denoise", data=data, files=files)

        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_denoise(job_id, timeout)
        return response

    async def _async_denoise(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/denoiser/denoise", data=data, files=files)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_denoise(job_id, timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get denoise job details and status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/denoiser/jobs/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/denoiser/jobs/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List denoiser jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/denoiser/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/denoiser/jobs", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a denoiser job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/denoiser/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/denoiser/jobs/{job_id}")

    def _wait_for_denoise(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Wait for denoise job completion."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Denoising failed: {job.get('error_message', 'Unknown error')}")

            time.sleep(3)

        raise TimeoutError(f"Denoising {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_denoise(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async wait for denoise job completion."""
        import asyncio
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Denoising failed: {job.get('error_message', 'Unknown error')}")

            await asyncio.sleep(3)

        raise TimeoutError(f"Denoising {job_id} did not complete within {timeout} seconds")

