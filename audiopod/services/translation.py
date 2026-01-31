"""
Translation Service - Audio/speech translation

API Routes:
- POST /api/v1/translation/translate/speech   - Translate speech
- GET  /api/v1/translation/translations/{id}  - Get translation job
- GET  /api/v1/translation/translations       - List translations
- DELETE /api/v1/translation/translations/{id} - Delete translation
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

        response = self.client.request("POST", "/api/v1/translation/translate/speech", data=data, files=files)

        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_translation(job_id, timeout)
        return response

    async def _async_translate(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/translation/translate/speech", data=data, files=files)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_translation(job_id, timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get translation job details and status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/translation/translations/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/translation/translations/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List translation jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/translation/translations", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/translation/translations", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a translation job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/translation/translations/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/translation/translations/{job_id}")

    def _wait_for_translation(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Wait for translation job completion."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Translation failed: {job.get('error_message', 'Unknown error')}")

            time.sleep(5)

        raise TimeoutError(f"Translation {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_translation(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async wait for translation job completion."""
        import asyncio
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Translation failed: {job.get('error_message', 'Unknown error')}")

            await asyncio.sleep(5)

        raise TimeoutError(f"Translation {job_id} did not complete within {timeout} seconds")

