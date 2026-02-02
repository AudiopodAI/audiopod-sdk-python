"""
Stem Extraction Service - Audio stem separation
"""

from typing import List, Optional, Dict, Any, Literal
from .base import BaseService
from ..exceptions import ValidationError


# Valid separation modes for the new API
StemMode = Literal["single", "two", "four", "six", "producer", "studio", "mastering"]
SingleStem = Literal["vocals", "drums", "bass", "guitar", "piano", "other", "instrumental"]


class StemExtractionService(BaseService):
    """
    Service for audio stem separation.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Simple mode-based extraction (recommended)
        result = client.stem_extraction.separate(
            url="https://youtube.com/watch?v=VIDEO_ID",
            mode="six"
        )
        for stem, url in result["download_urls"].items():
            print(f"{stem}: {url}")

        # Or extract only vocals
        result = client.stem_extraction.separate(
            file="song.mp3",
            mode="single",
            stem="vocals"
        )
        ```
    """

    def separate(
        self,
        file: Optional[str] = None,
        url: Optional[str] = None,
        mode: StemMode = "four",
        stem: Optional[SingleStem] = None,
        wait_for_completion: bool = True,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Separate audio into stems using simple mode selection.

        Args:
            file: Path to local audio file
            url: URL of audio/video (YouTube, SoundCloud, direct link)
            mode: Separation mode:
                - "single": Extract one stem (specify stem param)
                - "two": Vocals + Instrumental
                - "four": Vocals, Drums, Bass, Other (default)
                - "six": Vocals, Drums, Bass, Guitar, Piano, Other
                - "producer": 8 stems with kick, snare, hihat
                - "studio": 12 stems for professional mixing
                - "mastering": 16 stems maximum detail
            stem: For mode="single", which stem to extract
            wait_for_completion: Wait for job to complete (default: True)
            timeout: Max wait time in seconds

        Returns:
            Job dict with id, status, download_urls (when completed)
        """
        if not file and not url:
            raise ValidationError("Provide file or url")

        if file and url:
            raise ValidationError("Provide file or url, not both")

        if mode == "single" and not stem:
            raise ValidationError(
                "stem parameter required for mode='single'. "
                "Options: vocals, drums, bass, guitar, piano, other, instrumental"
            )

        data = {"mode": mode}
        if stem:
            data["stem"] = stem
        if url:
            data["url"] = url

        files = self._prepare_file_upload(file, "file") if file else None

        if self.async_mode:
            return self._async_separate(data, files, wait_for_completion, timeout)

        response = self.client.request(
            "POST", "/api/v1/stem-extraction/api/extract", data=data, files=files
        )

        if wait_for_completion:
            return self._wait_for_stem_job(response["id"], timeout)

        return response

    async def _async_separate(
        self,
        data: Dict[str, Any],
        files: Optional[Dict[str, Any]],
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/stem-extraction/api/extract", data=data, files=files
        )
        if wait_for_completion:
            return await self._async_wait_for_stem_job(response["id"], timeout)
        return response

    def extract(
        self,
        file: Optional[str] = None,
        url: Optional[str] = None,
        mode: StemMode = "four",
        stem: Optional[SingleStem] = None,
    ) -> Dict[str, Any]:
        """
        Submit stem extraction job (returns immediately without waiting).

        Use wait_for_completion() to poll for results.
        """
        return self.separate(file=file, url=url, mode=mode, stem=stem, wait_for_completion=False)

    def wait_for_completion(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Wait for stem extraction job to complete."""
        return self._wait_for_stem_job(job_id, timeout)

    def status(self, job_id: int) -> Dict[str, Any]:
        """Get stem extraction job status (alias for get_job)."""
        return self.get_job(job_id)

    def modes(self) -> Dict[str, Any]:
        """Get available separation modes."""
        if self.async_mode:
            return self._async_modes()
        return self.client.request("GET", "/api/v1/stem-extraction/modes")

    async def _async_modes(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/stem-extraction/modes")

    # Legacy method - kept for backward compatibility
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
        Extract stems from audio (legacy method).

        For new code, use separate() instead which uses the simpler mode-based API.

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

