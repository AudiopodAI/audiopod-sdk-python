"""
Denoiser Service - Audio noise reduction
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

        response = self.client.request("POST", "/api/v1/denoise", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_denoise(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/denoise", data=data, files=files)
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get denoise job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/denoise/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/denoise/status/{job_id}")

