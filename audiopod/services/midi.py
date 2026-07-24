"""
Audio-to-MIDI Service - Convert audio (or existing stems) to MIDI
"""

import json
from typing import List, Optional, Dict, Any
from .base import BaseService
from ..exceptions import ValidationError


class MidiService(BaseService):
    """
    Service for converting audio into MIDI, either standalone (we split the
    mix into stems first) or as an add-on to an existing stem-separation job.

    AudioPod's audio-to-MIDI engine transcribes pitched stems (vocals, bass,
    guitar, piano, other) into note-level MIDI. It's a starting-point
    transcription — expect to tidy timing/note lengths by ear, dynamics are
    approximate, and it works best on clean recordings. Drums are accepted as
    a requested stem but aren't transcribed yet; they come back in
    `skipped_stems`.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Standalone: split + transcribe in one call
        job = client.midi.convert(file="song.mp3", stems=["vocals", "bass", "piano"])
        print(job["merged_midi_url"])
        for stem, url in (job["midi_urls"] or {}).items():
            print(f"{stem}: {url}")

        # Add-on: transcribe stems you already separated
        job = client.midi.convert_from_stem_job(stem_job_id=1234)
        ```
    """

    def convert(
        self,
        file: Optional[str] = None,
        url: Optional[str] = None,
        stems: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Standalone audio-to-MIDI: split an audio file/URL into stems and
        transcribe each pitched stem into MIDI.

        Args:
            file: Path to local audio file
            url: URL of audio/video to convert (alternative to file)
            stems: Stems to transcribe, e.g. ["vocals", "bass", "guitar", "piano", "other"].
                Defaults to all pitched stems server-side. "drums" is accepted
                but reported back in `skipped_stems` — not transcribed yet.
            options: Tunables forwarded to the audio-to-MIDI engine
                (onset_threshold, frame_threshold, min_note_len_ms,
                use_piano_model, tempo_bpm).
            wait_for_completion: Wait for job to complete (default: True)
            timeout: Max wait time in seconds

        Returns:
            Job dict with id, status, midi_urls (per stem), merged_midi_url,
            stem_urls (separated stem audio), detected_tempo_bpm, etc.
        """
        if not file and not url:
            raise ValidationError("Provide file or url")

        if file and url:
            raise ValidationError("Provide file or url, not both")

        data: Dict[str, Any] = {}
        if url:
            data["url"] = url
        if stems:
            data["stems"] = str(stems)
        if options:
            data["options"] = json.dumps(options)

        files = self._prepare_file_upload(file, "file") if file else None

        if self.async_mode:
            return self._async_convert(data, files, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v1/midi/convert", data=data, files=files)

        if wait_for_completion:
            return self._wait_for_midi_job(response["id"], timeout)

        return response

    async def _async_convert(
        self,
        data: Dict[str, Any],
        files: Optional[Dict[str, Any]],
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", "/api/v1/midi/convert", data=data, files=files
        )
        if wait_for_completion:
            return await self._async_wait_for_midi_job(response["id"], timeout)
        return response

    def convert_from_stem_job(
        self,
        stem_job_id: int,
        stems: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Add-on: transcribe the stems of an already-completed stem-separation
        job into MIDI (no re-split — bills the add-on rate only).

        Args:
            stem_job_id: ID of a completed `client.stem_extraction` job
            stems: Subset of the source job's stems to transcribe. Defaults to
                all stems the source job produced.
            options: Tunables forwarded to the audio-to-MIDI engine.
            wait_for_completion: Wait for job to complete (default: True)
            timeout: Max wait time in seconds

        Returns:
            Job dict, same shape as `convert()`.
        """
        json_data: Dict[str, Any] = {"stems": stems, "options": options}

        if self.async_mode:
            return self._async_convert_from_stem_job(
                stem_job_id, json_data, wait_for_completion, timeout
            )

        response = self.client.request(
            "POST", f"/api/v1/midi/convert/from-stems/{stem_job_id}", json_data=json_data
        )

        if wait_for_completion:
            return self._wait_for_midi_job(response["id"], timeout)

        return response

    async def _async_convert_from_stem_job(
        self,
        stem_job_id: int,
        json_data: Dict[str, Any],
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", f"/api/v1/midi/convert/from-stems/{stem_job_id}", json_data=json_data
        )
        if wait_for_completion:
            return await self._async_wait_for_midi_job(response["id"], timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get audio-to-MIDI job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/midi/status/{job_id}")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/midi/status/{job_id}")

    def list_jobs(self, skip: int = 0, limit: int = 50) -> List[Dict[str, Any]]:
        """List audio-to-MIDI jobs."""
        if self.async_mode:
            return self._async_list_jobs(skip, limit)
        return self.client.request(
            "GET", "/api/v1/midi/jobs", params={"skip": skip, "limit": limit}
        )

    async def _async_list_jobs(self, skip: int, limit: int) -> List[Dict[str, Any]]:
        return await self.client.request(
            "GET", "/api/v1/midi/jobs", params={"skip": skip, "limit": limit}
        )

    def delete_job(self, job_id: int) -> Dict[str, Any]:
        """Delete an audio-to-MIDI job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/midi/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"/api/v1/midi/jobs/{job_id}")

    def wait_for_completion(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Wait for an audio-to-MIDI job to complete."""
        return self._wait_for_midi_job(job_id, timeout)

    def _wait_for_midi_job(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Poll (sync) until the job is COMPLETED or FAILED."""
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

    async def _async_wait_for_midi_job(self, job_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Poll (async) until the job is COMPLETED or FAILED."""
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
