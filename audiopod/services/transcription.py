"""
Transcription Service - Speech-to-text
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
            url: URL of audio file
            language: Language code (auto-detected if not provided)
            speaker_diarization: Enable speaker separation
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with transcript when completed
        """
        data = {"speaker_diarization": speaker_diarization}
        if language:
            data["language"] = language
        if url:
            data["url"] = url

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_transcribe(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/transcribe", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_transcribe(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/transcribe", data=data, files=files)
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get transcription job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/transcribe/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/transcribe/status/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List transcription jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/transcribe/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/transcribe/jobs", params={"skip": skip, "limit": limit}
        )

