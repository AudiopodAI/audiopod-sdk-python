"""
Speaker Service - Speaker diarization and extraction
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class SpeakerService(BaseService):
    """Service for speaker diarization and extraction."""

    def diarize(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        num_speakers: Optional[int] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Identify and separate speakers in audio.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            num_speakers: Expected number of speakers (auto-detected if not provided)
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with speaker segments when completed
        """
        data = {}
        if num_speakers:
            data["num_speakers"] = num_speakers
        if url:
            data["url"] = url

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_diarize(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/speaker/diarize", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_diarize(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/speaker/diarize", data=data, files=files
        )
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def extract(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Extract individual speaker audio tracks.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with speaker audio URLs when completed
        """
        data = {}
        if url:
            data["url"] = url

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_extract(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/speaker/extract", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_extract(
        self, data: Dict, files: Optional[Dict], wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/speaker/extract", data=data, files=files
        )
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get speaker job details and status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/speaker/jobs/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/speaker/jobs/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List speaker jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/speaker/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/speaker/jobs", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a speaker job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/speaker/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/speaker/jobs/{job_id}")

