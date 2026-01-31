"""
Transcription Service - Speech-to-text

API Routes:
- POST /api/v1/transcription/transcribe        - Transcribe from URL
- POST /api/v1/transcription/transcribe-upload - Transcribe from file upload
- GET  /api/v1/transcription/jobs/{id}         - Get job details
- GET  /api/v1/transcription/jobs              - List jobs
- DELETE /api/v1/transcription/jobs/{id}       - Delete job
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class TranscriptionService(BaseService):
    """Service for speech-to-text transcription."""

    def transcribe(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        language: Optional[str] = None,
        speaker_diarization: bool = False,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Transcribe audio to text.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file (or list of URLs)
            language: Language code (auto-detected if not provided)
            speaker_diarization: Enable speaker separation
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with transcript when completed
        """
        if audio_file:
            # File upload endpoint
            data = {
                "enable_speaker_diarization": speaker_diarization,
            }
            if language:
                data["language"] = language

            files = self._prepare_file_upload(audio_file, "files")

            if self.async_mode:
                return self._async_transcribe_upload(data, files, wait_for_completion, timeout)

            response = self.client.request(
                "POST", "/api/v1/transcription/transcribe-upload", data=data, files=files
            )
        else:
            # URL-based endpoint
            data = {
                "source_urls": [url] if isinstance(url, str) else url,
                "enable_speaker_diarization": speaker_diarization,
            }
            if language:
                data["language"] = language

            if self.async_mode:
                return self._async_transcribe(data, wait_for_completion, timeout)

            response = self.client.request(
                "POST", "/api/v1/transcription/transcribe", json_data=data
            )

        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_transcription(job_id, timeout)
        return response

    async def _async_transcribe(
        self, data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/transcription/transcribe", json_data=data
        )
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_transcription(job_id, timeout)
        return response

    async def _async_transcribe_upload(
        self, data: Dict, files: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/transcription/transcribe-upload", data=data, files=files
        )
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_transcription(job_id, timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get transcription job details and status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/transcription/jobs/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/transcription/jobs/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List transcription jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/transcription/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/transcription/jobs", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a transcription job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/transcription/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/transcription/jobs/{job_id}")

    def get_transcript(self, job_id: int, format: str = "json") -> Any:
        """
        Get transcript content.
        
        Args:
            job_id: Job ID
            format: Output format - 'json', 'txt', 'srt', 'vtt'
        """
        if self.async_mode:
            return self._async_get_transcript(job_id, format)
        return self.client.request(
            "GET", f"/api/v1/transcription/jobs/{job_id}/transcript", params={"format": format}
        )

    async def _async_get_transcript(self, job_id: int, format: str) -> Any:
        return await self.client.request(
            "GET", f"/api/v1/transcription/jobs/{job_id}/transcript", params={"format": format}
        )

    def _wait_for_transcription(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Wait for transcription job completion."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR", "CANCELLED"):
                raise Exception(f"Transcription failed: {job.get('error_message', 'Unknown error')}")

            time.sleep(3)

        raise TimeoutError(f"Transcription {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_transcription(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async wait for transcription job completion."""
        import asyncio
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR", "CANCELLED"):
                raise Exception(f"Transcription failed: {job.get('error_message', 'Unknown error')}")

            await asyncio.sleep(3)

        raise TimeoutError(f"Transcription {job_id} did not complete within {timeout} seconds")

