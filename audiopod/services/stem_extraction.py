"""
Stem Extraction Service - Audio stem separation
"""

from typing import List, Optional, Dict, Any
from .base import BaseService
from ..exceptions import ValidationError


class StemExtractionService(BaseService):
    """
    Service for audio stem separation.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Extract all stems
        job = client.stem_extraction.extract_stems(
            audio_file="song.mp3",
            stem_types=["vocals", "drums", "bass", "other"],
            wait_for_completion=True
        )

        # Download stems
        for stem_name, url in job["download_urls"].items():
            print(f"{stem_name}: {url}")
        ```
    """

    def extract_stems(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        stem_types: Optional[List[str]] = None,
        model_name: str = "htdemucs",
        two_stems_mode: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Extract stems from audio.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file (alternative to audio_file)
            stem_types: Stems to extract (e.g., ["vocals", "drums", "bass", "other"])
            model_name: Model to use ("htdemucs" or "htdemucs_6s")
            two_stems_mode: Two-stem mode ("vocals", "drums", or "bass")
            wait_for_completion: Wait for job to complete
            timeout: Max wait time in seconds

        Returns:
            Job dict with id, status, download_urls (when completed)
        """
        if not audio_file and not url:
            raise ValidationError("Provide audio_file or url")

        if audio_file and url:
            raise ValidationError("Provide audio_file or url, not both")

        if stem_types is None:
            stem_types = (
                ["vocals", "drums", "bass", "other", "piano", "guitar"]
                if model_name == "htdemucs_6s"
                else ["vocals", "drums", "bass", "other"]
            )

        data = {"stem_types": str(stem_types), "model_name": model_name}

        if url:
            data["url"] = url

        if two_stems_mode:
            data["two_stems_mode"] = two_stems_mode

        files = self._prepare_file_upload(audio_file, "file") if audio_file else None

        if self.async_mode:
            return self._async_extract_stems(data, files, wait_for_completion, timeout)

        response = self.client.request(
            "POST", "/api/v1/stem-extraction/extract", data=data, files=files
        )

        if wait_for_completion:
            return self._wait_for_stem_job(response["id"], timeout)

        return response

    async def _async_extract_stems(
        self,
        data: Dict[str, Any],
        files: Optional[Dict[str, Any]],
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/stem-extraction/extract", data=data, files=files
        )
        if wait_for_completion:
            return await self._async_wait_for_stem_job(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get stem extraction job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/stem-extraction/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/stem-extraction/status/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List stem extraction jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/stem-extraction/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/stem-extraction/jobs", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a stem extraction job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/stem-extraction/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/stem-extraction/jobs/{job_id}")

    def _wait_for_stem_job(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Wait for stem job completion."""
        import time

        start = time.time()
        while time.time() - start < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()
            if status == "COMPLETED":
                return job
            elif status in ["FAILED", "ERROR"]:
                raise Exception(f"Job failed: {job.get('error_message', 'Unknown')}")
            time.sleep(5)
        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")

    async def _async_wait_for_stem_job(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Async wait for stem job completion."""
        import asyncio
        import time

        start = time.time()
        while time.time() - start < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()
            if status == "COMPLETED":
                return job
            elif status in ["FAILED", "ERROR"]:
                raise Exception(f"Job failed: {job.get('error_message', 'Unknown')}")
            await asyncio.sleep(5)
        raise TimeoutError(f"Job {job_id} timed out after {timeout}s")

