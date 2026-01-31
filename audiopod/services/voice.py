"""
Voice Service - Voice cloning and text-to-speech

API Routes:
- GET  /api/v1/voice/voice-profiles           - List all voices
- GET  /api/v1/voice/voices/{id}/status       - Get voice details
- POST /api/v1/voice/voice-profiles           - Create voice clone
- DELETE /api/v1/voice/voices/{id}            - Delete voice
- POST /api/v1/voice/voices/{id}/generate     - Generate TTS
- GET  /api/v1/voice/tts-jobs/{id}/status     - Get TTS job status
"""

from typing import Optional, Dict, Any, List, Union
from .base import BaseService


class VoiceService(BaseService):
    """Service for voice cloning and text-to-speech."""

    def list_voices(
        self,
        skip: int = 0,
        limit: int = 100,
        include_public: bool = True,
    ) -> List[Dict[str, Any]]:
        """List available voices (both custom and public)."""
        params = {
            "skip": skip,
            "limit": limit,
            "include_public": str(include_public).lower(),
        }
        if self.async_mode:
            return self._async_list_voices(params)
        return self.client.request("GET", "/api/v1/voice/voice-profiles", params=params)

    async def _async_list_voices(self, params: Dict) -> List[Dict[str, Any]]:
        return await self.client.request("GET", "/api/v1/voice/voice-profiles", params=params)

    def get_voice(self, voice_id: Union[int, str]) -> Dict[str, Any]:
        """Get voice details by ID or UUID."""
        if self.async_mode:
            return self._async_get_voice(voice_id)
        return self.client.request("GET", f"/api/v1/voice/voices/{voice_id}/status")

    async def _async_get_voice(self, voice_id: Union[int, str]) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/voice/voices/{voice_id}/status")

    def create_voice(
        self,
        name: str,
        audio_file: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new voice clone from an audio file."""
        files = self._prepare_file_upload(audio_file, "file")
        data = {"name": name}
        if description:
            data["description"] = description

        if self.async_mode:
            return self._async_create_voice(data, files)
        return self.client.request("POST", "/api/v1/voice/voice-profiles", data=data, files=files)

    async def _async_create_voice(self, data: Dict, files: Dict) -> Dict[str, Any]:
        return await self.client.request("POST", "/api/v1/voice/voice-profiles", data=data, files=files)

    def delete_voice(self, voice_id: Union[int, str]) -> Dict[str, str]:
        """Delete a voice by ID or UUID."""
        if self.async_mode:
            return self._async_delete_voice(voice_id)
        return self.client.request("DELETE", f"/api/v1/voice/voices/{voice_id}")

    async def _async_delete_voice(self, voice_id: Union[int, str]) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/voice/voices/{voice_id}")

    def generate_speech(
        self,
        voice_id: Union[int, str],
        text: str,
        speed: float = 1.0,
        language: str = "en",
        audio_format: str = "mp3",
        wait_for_completion: bool = False,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Generate speech from text using a voice.
        
        Args:
            voice_id: Voice ID (int) or UUID (str) to use for generation
            text: Text to convert to speech
            speed: Speech speed (0.25 to 4.0, default 1.0)
            language: Language code (default "en")
            audio_format: Output format - mp3, wav, ogg (default "mp3")
            wait_for_completion: If True, poll until job completes
            timeout: Max seconds to wait for completion
            
        Returns:
            Job info dict with job_id, status, etc.
            If wait_for_completion=True, includes output_url when done.
        """
        data = {
            "input_text": text,
            "speed": speed,
            "language": language,
            "audio_format": audio_format,
        }

        if self.async_mode:
            return self._async_generate_speech(voice_id, data, wait_for_completion, timeout)

        response = self.client.request(
            "POST",
            f"/api/v1/voice/voices/{voice_id}/generate",
            data=data,
        )

        if wait_for_completion:
            job_id = response.get("job_id") or response.get("id")
            return self._wait_for_job_completion(job_id, timeout)
        return response

    async def _async_generate_speech(
        self, voice_id: Union[int, str], data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST",
            f"/api/v1/voice/voices/{voice_id}/generate",
            data=data,
        )
        if wait_for_completion:
            job_id = response.get("job_id") or response.get("id")
            return await self._async_wait_for_job_completion(job_id, timeout)
        return response

    def get_job_status(self, job_id: int) -> Dict[str, Any]:
        """
        Get TTS job status.
        
        Args:
            job_id: The job ID returned from generate_speech
            
        Returns:
            Job status dict with status, progress, output_url (when completed), etc.
        """
        if self.async_mode:
            return self._async_get_job_status(job_id)
        return self.client.request("GET", f"/api/v1/voice/tts-jobs/{job_id}/status")

    async def _async_get_job_status(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/voice/tts-jobs/{job_id}/status")

    def _wait_for_job_completion(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Poll job status until completion or timeout."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status.get("status") in ("completed", "COMPLETED"):
                return status
            elif status.get("status") in ("failed", "FAILED", "error", "ERROR"):
                raise Exception(f"Job failed: {status.get('error_message', 'Unknown error')}")
            
            time.sleep(2)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_job_completion(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async poll job status until completion or timeout."""
        import asyncio
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = await self.get_job_status(job_id)
            
            if status.get("status") in ("completed", "COMPLETED"):
                return status
            elif status.get("status") in ("failed", "FAILED", "error", "ERROR"):
                raise Exception(f"Job failed: {status.get('error_message', 'Unknown error')}")
            
            await asyncio.sleep(2)
        
        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

