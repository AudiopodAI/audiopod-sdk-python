"""
Voice Service - Voice cloning and text-to-speech

API Routes:
- GET  /api/v1/voice/voice-profiles           - List all voices
- GET  /api/v1/voice/voices/{id}/status       - Get voice details
- POST /api/v1/voice/voice-profiles           - Create voice clone
- DELETE /api/v1/voice/voices/{id}            - Delete voice
- POST /api/v1/voice/voices/{id}/generate     - Generate TTS
- GET  /api/v1/voice/tts-jobs/{id}/status     - Get TTS job status
- POST /api/v1/voice/design                   - Design a voice from a text prompt
- POST /api/v1/voice/design/publish           - Publish a designed voice preview
"""

import json
from typing import Optional, Dict, Any, List, Union
from urllib.parse import quote
from .base import BaseService
from .. import workflow_contracts as C
from ..workflow_utils import canonical_uuid, uuid_fields


class VoiceService(BaseService):
    """Service for voice cloning and text-to-speech."""

    def capabilities(self, voice_id: Union[int, str], operation: str = "tts") -> C.VoiceCapabilities:
        """Effective caller/operation capabilities; unknown is not ready."""
        return self._foundation_request("GET", self._voice_path(voice_id, "capabilities"),
                                        params={"operation": operation})

    def reference_diagnostics(self, audio_file: str, crop_start_seconds: float = 0,
                              crop_end_seconds: Optional[float] = None) -> C.ReferenceDiagnostics:
        """Measure exact selected bytes without ASR, cloning or credit charges."""
        data = {"crop_start_seconds": crop_start_seconds}
        if crop_end_seconds is not None:
            data["crop_end_seconds"] = crop_end_seconds
        if self.async_mode:
            return self._async_reference_diagnostics(audio_file, data)
        with open(audio_file, "rb") as stream:
            return self.client.request("POST", "/api/v1/voice/reference/diagnostics", data=data,
                files={"file": (audio_file.rsplit("/", 1)[-1], stream, "application/octet-stream")})

    async def _async_reference_diagnostics(self, audio_file: str, data: Dict) -> Dict[str, Any]:
        with open(audio_file, "rb") as stream:
            return await self.client.request("POST", "/api/v1/voice/reference/diagnostics", data=data,
                files={"file": (audio_file.rsplit("/", 1)[-1], stream, "application/octet-stream")})

    def get_pronunciation(self, language: str, project_kind: str = "account",
                          project_id: Optional[str] = None) -> C.PronunciationPolicy:
        """Read caller-owned rules; a missing override inherits."""
        return self._foundation_request("GET", "/api/v1/voice/pronunciation",
            params=self._pronunciation_scope(language, project_kind, project_id))

    def set_pronunciation(self, language: str, expected_version: int, *,
                          entries: Optional[List[Dict[str, Any]]] = None, mode: str = "override",
                          project_kind: str = "account", project_id: Optional[str] = None) -> C.PronunciationPolicy:
        """Save against the observed version; concurrent edits return HTTP 409."""
        return self._foundation_request("PUT", "/api/v1/voice/pronunciation",
            params=self._pronunciation_scope(language, project_kind, project_id),
            json_data={"expected_version": expected_version, "mode": mode, "entries": entries or []})

    def reset_pronunciation(self, language: str, expected_version: int, *,
                            project_kind: str = "account", project_id: Optional[str] = None) -> C.PronunciationPolicy:
        """Reset to inheritance, preserving the server's revision tombstone."""
        scope = self._pronunciation_scope(language, project_kind, project_id)
        scope["expected_version"] = expected_version
        return self._foundation_request("DELETE", "/api/v1/voice/pronunciation", params=scope)

    def resolve_pronunciation(self, language: str, text: str = "", *, project_kind: str = "account",
                              project_id: Optional[str] = None) -> C.PronunciationResolution:
        """Resolve the exact snapshot and resulting spoken text without spending."""
        body = self._pronunciation_scope(language, project_kind, project_id)
        body["text"] = text
        return self._foundation_request("POST", "/api/v1/voice/pronunciation/resolve", json_data=body)

    def quote_audition(self, voice_id: Union[int, str], *, text: str, language: str,
                       **settings) -> C.ContextualAuditionQuote:
        """Quote the canonical paid speech lane for an excerpt of up to 500 characters."""
        path = "/api/v1/voice/auditions/" + quote(str(voice_id), safe="") + "/quote"
        return self._foundation_request("POST", path, json_data=uuid_fields({**settings, "text": text, "language": language}) if settings.get("project_kind") == "dubbing" else {**settings, "text": text, "language": language})

    def audition(self, voice_id: Union[int, str], *, text: str, language: str,
                 quote_identity: str, idempotency_key: str, confirm: bool, **settings) -> Dict[str, Any]:
        """Explicitly confirm a quoted excerpt. Stale quote errors require a new decision."""
        path = "/api/v1/voice/auditions/" + quote(str(voice_id), safe="")
        if confirm is not True:
            raise ValueError("Explicit confirmation is required")
        idempotency_key = canonical_uuid(idempotency_key)
        if settings.get("project_kind") == "dubbing": settings = uuid_fields(settings)
        return self._foundation_request("POST", path, json_data={**settings, "text": text, "language": language,
            "quote_identity": quote_identity, "idempotency_key": idempotency_key, "confirm": confirm})

    def create_consent(self, body: C.CreateVoiceConsent) -> C.VoiceConsent:
        return self._foundation_request("POST","/api/v1/voice/voice-consents",
            json_data=uuid_fields(body) if body.get("project_kind") == "dubbing" else body)

    def get_consent(self, consent_id: str) -> C.VoiceConsent:
        return self._foundation_request("GET","/api/v1/voice/voice-consents/"+canonical_uuid(consent_id))

    def preview_consent_invitation(self, token: str) -> C.VoiceConsent:
        return self._foundation_request("GET","/api/v1/voice/voice-consents/invitations/"+quote(token,safe=""))

    def accept_consent_invitation(self, token: str, consent_version: str, *, confirm: bool) -> C.VoiceConsent:
        return self._foundation_request("POST","/api/v1/voice/voice-consents/invitations/accept",
            json_data={"invitation_token":token,"consent_version":consent_version,"confirm":confirm})

    def revoke_consent(self, consent_id: str, expected_revision: int) -> C.VoiceConsent:
        return self._foundation_request("POST","/api/v1/voice/voice-consents/"+canonical_uuid(consent_id)+"/revoke",
            json_data={"expected_revision":expected_revision})

    def _reference_upload(self, path, audio_file, data):
        if self.async_mode: return self._async_reference_upload(path,audio_file,data)
        import os
        with open(audio_file,"rb") as stream:
            return self.client.request("POST",path,data=data,files={"file":(os.path.basename(audio_file),stream,"application/octet-stream")})

    async def _async_reference_upload(self, path, audio_file, data):
        import os
        with open(audio_file,"rb") as stream:
            return await self.client.request("POST",path,data=data,files={"file":(os.path.basename(audio_file),stream,"application/octet-stream")})

    def admit_reference(self, audio_file: str, *, consent_id: str, consent_revision: int, consent_version: str,
                        transcription: str, confirm_transcription: bool, replace_voice_id: Optional[int] = None,
                        reference_revision: int = 0) -> C.VoiceReferenceAdmission:
        data = {"consent_id":canonical_uuid(consent_id),"consent_revision":consent_revision,"consent_version":consent_version,
                "transcription":transcription,"confirm_transcription":str(confirm_transcription).lower(),"reference_revision":reference_revision}
        if replace_voice_id is not None: data["replace_voice_id"] = replace_voice_id
        return self._reference_upload("/api/v1/voice/reference/admissions",audio_file,data)

    def register_reference(self, audio_file: str, *, admission_token: str, idempotency_key: str, name: str,
                           language_code: Optional[str] = None) -> C.VoiceRegistration:
        data = {"admission_token":admission_token,"idempotency_key":canonical_uuid(idempotency_key),"name":name}
        if language_code is not None: data["language_code"] = language_code
        return self._reference_upload("/api/v1/voice/voice-profiles/register",audio_file,data)

    def registration_status(self, idempotency_key: str) -> C.VoiceRegistration:
        return self._foundation_request("GET","/api/v1/voice/voice-profiles/registrations/"+canonical_uuid(idempotency_key))

    def update_metadata(self, voice_id: Union[int,str], body: C.VoiceMetadata) -> Dict[str,Any]:
        return self._foundation_request("PATCH",self._voice_path(voice_id,"").rstrip("/"),json_data=body)

    @staticmethod
    def _voice_path(voice_id: Union[int, str], suffix: str) -> str:
        return "/api/v1/voice/voices/" + quote(str(voice_id), safe="") + "/" + suffix

    @staticmethod
    def _pronunciation_scope(language: str, project_kind: str, project_id: Optional[str]) -> Dict[str, Any]:
        scope = {"language": language, "project_kind": project_kind}
        if project_id is not None:
            scope["project_id"] = canonical_uuid(project_id) if project_kind == "dubbing" else project_id
        return scope

    def _foundation_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        if self.async_mode:
            return self._async_foundation_request(method, path, **kwargs)
        return self.client.request(method, path, **kwargs)

    async def _async_foundation_request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        return await self.client.request(method, path, **kwargs)

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
        """Deprecated: use create_consent, admit_reference and register_reference.

        Current servers reject this legacy request with consent_admission_required.
        """
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
        language: Optional[str] = "en",
        audio_format: str = "mp3",
        generation_params: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = False,
        timeout: int = 300,
        pronunciation_project_kind: Optional[str] = None,
        pronunciation_project_id: Optional[str] = None,
        pronunciation_identity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate speech from text using a voice.

        Args:
            voice_id: Voice ID (int) or UUID (str) to use for generation
            text: Text to convert to speech
            speed: Speech speed (0.25 to 4.0, default 1.0)
            language: Language code (default "en"). Pass None to auto-detect.
            audio_format: Output format - mp3, wav, ogg (default "mp3")
            generation_params: Optional voice-directing controls, sent as a JSON
                object. Recognized keys:
                - "delivery_mode": one of "stable", "balanced", "creative"
                - "timestamp_type": one of "word", "character"
                - "text_normalization": bool
            wait_for_completion: If True, poll until job completes
            timeout: Max seconds to wait for completion

        Returns:
            Job info dict with job_id, status, etc.
            If wait_for_completion=True, includes output_url when done.
        """
        data: Dict[str, Any] = {
            "input_text": text,
            "speed": speed,
            "audio_format": audio_format,
        }
        if language is not None:
            data["language"] = language
        if generation_params is not None:
            data["generation_params"] = json.dumps(generation_params)
        for key, value in {
            "pronunciation_project_kind": pronunciation_project_kind,
            "pronunciation_project_id": pronunciation_project_id,
            "pronunciation_identity": pronunciation_identity,
        }.items():
            if value is not None:
                data[key] = value

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

    # ------------------------------------------------------------- voice design
    def design(
        self,
        design_prompt: str,
        language: Optional[str] = None,
        preview_text: Optional[str] = None,
        num_samples: int = 3,
    ) -> Dict[str, Any]:
        """
        Design a brand-new voice from a text description.

        Returns a set of candidate previews; publish the one you like with
        :meth:`publish_design`.

        Args:
            design_prompt: Description of the voice to create (required).
            language: Optional language code for the previews.
            preview_text: Text spoken in the previews. If omitted, a default
                preview line is used.
            num_samples: How many candidate previews to generate. Default: 3

        Returns:
            Dict with ``previews`` (each has a ``preview_id``) and
            ``credits_charged``.
        """
        body: Dict[str, Any] = {"design_prompt": design_prompt, "num_samples": num_samples}
        if language is not None:
            body["language"] = language
        if preview_text is not None:
            body["preview_text"] = preview_text
        if self.async_mode:
            return self._async_design(body)
        return self.client.request("POST", "/api/v1/voice/design", json_data=body)

    async def _async_design(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", "/api/v1/voice/design", json_data=body)

    def publish_design(
        self,
        preview_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Publish a designed voice preview as a saved, reusable voice.

        Args:
            preview_id: The ``preview_id`` of the design preview to keep (required).
            name: Name for the new voice (required).
            description: Optional description for the voice.

        Returns:
            The published voice dict.
        """
        body: Dict[str, Any] = {"preview_id": preview_id, "name": name}
        if description is not None:
            body["description"] = description
        if self.async_mode:
            return self._async_publish_design(body)
        return self.client.request("POST", "/api/v1/voice/design/publish", json_data=body)

    async def _async_publish_design(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", "/api/v1/voice/design/publish", json_data=body)
