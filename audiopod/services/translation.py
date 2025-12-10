"""
Translation Service - Audio/speech translation
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class TranslationService(BaseService):
    """Service for audio translation."""

    def translate(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        target_language: str = "en",
        source_language: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Translate audio to another language.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            target_language: Target language code
            source_language: Source language (auto-detected if not provided)
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with translated audio URL when completed
        """
        data = {"target_language": target_language}
        if source_language:
            data["source_language"] = source_language
        if url:
            data["url"] = url

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_translate(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/translate", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_translate(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/translate", data=data, files=files)
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get translation job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/translate/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/translate/status/{job_id}")

