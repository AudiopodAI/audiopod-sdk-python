"""
Voice Service - Voice cloning and text-to-speech
"""

from typing import Optional, Dict, Any, List
from .base import BaseService


class VoiceService(BaseService):
    """Service for voice cloning and text-to-speech."""

    def list_voices(self) -> List[Dict[str, Any]]:
        """List available voices."""
        if self.async_mode:
            return self._async_list_voices()
        return self.client.request("GET", "/api/v1/voices")

    async def _async_list_voices(self) -> List[Dict[str, Any]]:
        return await self.client.request("GET", "/api/v1/voices")

    def get_voice(self, voice_id: int) -> Dict[str, Any]:
        """Get voice details."""
        if self.async_mode:
            return self._async_get_voice(voice_id)
        return self.client.request("GET", f"/api/v1/voices/{voice_id}")

    async def _async_get_voice(self, voice_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/voices/{voice_id}")

    def create_voice(
        self,
        name: str,
        audio_file: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new voice clone."""
        files = self._prepare_file_upload(audio_file, "audio_file")
        data = {"name": name}
        if description:
            data["description"] = description

        if self.async_mode:
            return self._async_create_voice(data, files)
        return self.client.request("POST", "/api/v1/voices", data=data, files=files)

    async def _async_create_voice(self, data: Dict, files: Dict) -> Dict[str, Any]:
        return await self.client.request("POST", "/api/v1/voices", data=data, files=files)

    def delete_voice(self, voice_id: int) -> Dict[str, str]:
        """Delete a voice."""
        if self.async_mode:
            return self._async_delete_voice(voice_id)
        return self.client.request("DELETE", f"/api/v1/voices/{voice_id}")

    async def _async_delete_voice(self, voice_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/voices/{voice_id}")

    def generate_speech(
        self,
        text: str,
        voice_id: int,
        speed: float = 1.0,
        wait_for_completion: bool = False,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Generate speech from text."""
        data = {"text": text, "voice_id": voice_id, "speed": speed}

        if self.async_mode:
            return self._async_generate_speech(data, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/tts/generate", json_data=data)

        if wait_for_completion:
            return self._wait_for_completion(response["id"], timeout)
        return response

    async def _async_generate_speech(
        self, data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", "/api/v1/tts/generate", json_data=data)
        if wait_for_completion:
            return await self._async_wait_for_completion(response["id"], timeout)
        return response

