"""
Music Service - AudioMusic V2 AI Music Generation

API Routes:
- POST /api/v1/music/text2music         - Generate music with vocals
- POST /api/v1/music/prompt2instrumental - Generate instrumental music
- POST /api/v1/music/lyric2vocals       - Generate vocals from lyrics
- POST /api/v1/music/text2rap           - Generate rap music
- POST /api/v1/music/text2samples       - Generate audio samples
- POST /api/v1/music/simple             - Simple mode (natural language query)
- POST /api/v1/music/cover              - Cover/style transfer
- POST /api/v1/music/reference          - Reference audio generation
- POST /api/v1/music/analyze            - Audio analysis
- POST /api/v1/music/extract-stem       - Stem extraction
- GET  /api/v1/music/jobs/{id}/status   - Get job status
- GET  /api/v1/music/jobs               - List jobs
- DELETE /api/v1/music/jobs/{id}        - Delete job
- GET  /api/v1/music/presets            - Get genre presets

Score-first music (AudioMusic v3) - the song is written as an editable score
(ABC notation) first, and the audio is rendered from that score:
- GET  /api/v1/music/v3/availability      - Is AudioMusic v3 offered here?
- POST /api/v1/music/v3/plan              - Write a score only (no audio)
- POST /api/v1/music/v3/revise            - Revise a score from an instruction
- POST /api/v1/music/v3/edit              - Record (render) a complete score
- POST /api/v1/music/v3/generate          - Score + audio in one call
- GET  /api/v1/music/v3/jobs              - List v3 jobs
- GET  /api/v1/music/v3/jobs/{id}         - Get one v3 job
- GET  /api/v1/music/v3/jobs/{id}/score   - Get a job's score
"""

import time
from typing import Optional, Dict, Any, List, Literal
from .base import BaseService
from ..exceptions import AudioPodError, ValidationError


MusicTask = Literal[
    "text2music", "prompt2instrumental", "lyric2vocals", "text2rap", "text2samples",
    "cover", "repaint", "extract", "complete", "simple", "retake", "extend", "edit",
]

#: Deprecated. Every plan now gets the highest-quality music model at the
#: standard rate, so there is nothing to choose. Kept so existing code that
#: passes ``quality=`` keeps type-checking and running.
MusicQuality = Literal["standard", "premium"]

#: How much of the song AudioMusic v3 writes as a score first: ``"full"``
#: (melody and harmony) or ``"melody"`` (the tune alone).
MusicV3Cot = Literal["full", "melody"]

#: Which v3 entry point produced a job (filter for :meth:`MusicService.list_v3_jobs`).
MusicV3Workflow = Literal["generate", "plan", "edit", "revise"]

V3_PREFIX = "/api/v1/music/v3"

#: Longest ``instruction`` :meth:`MusicService.revise_score` accepts.
MAX_REVISE_INSTRUCTION_CHARS = 500

_V3_DONE = "COMPLETED"
_V3_FAILED = ("FAILED", "ERROR", "CANCELLED", "CANCELED")


def _drop_none(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if v is not None}


class MusicService(BaseService):
    """Service for AI music generation using AudioMusic V2."""

    def generate(
        self,
        prompt: str,
        task: MusicTask = "prompt2instrumental",
        duration: int = -1,
        lyrics: Optional[str] = None,
        genre_preset: Optional[str] = None,
        display_name: Optional[str] = None,
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate music from text prompt using AudioMusic V2.

        Args:
            prompt: Text description / caption of desired music
            task: Generation task type:
                - "prompt2instrumental": Instrumental music (no vocals)
                - "text2music": Music with vocals (requires lyrics)
                - "text2rap": Rap music (requires lyrics)
                - "lyric2vocals": Generate vocals from lyrics
                - "text2samples": Audio samples/loops
            duration: Duration in seconds (-1 for auto, max 600)
            lyrics: Lyrics for vocal tasks (with [verse], [chorus] tags)
            genre_preset: Genre preset name
            display_name: Custom name for the job
            quality: Deprecated and no longer needed. Every plan now gets the
                highest-quality music model at the standard rate. Still accepted
                for compatibility; only sent when you pass it explicitly.
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds
            **kwargs: AudioMusic V2 advanced parameters:
                caption (str): Alias for prompt
                instrumental (bool): Generate instrumental only
                format (str): Output format ("wav", "mp3", "flac", "ogg"). Default: "flac"
                model_version (str): "audiomusic-v2" (default) or "audiomusic-v1.5"
                inference_steps (int): Diffusion steps (32-100). Default: 64
                guidance_scale (float): CFG scale (1.0-15.0). Default: 7.0
                shift (float): Timestep shift (1.0-5.0). Default: 3.0
                infer_method (str): "ode" or "sde". Default: "ode"
                thinking (bool): Enable Chain-of-Thought planning. Default: True
                lm_temperature (float): LM temperature (0.0-2.0). Default: 0.85
                lm_cfg_scale (float): LM CFG (0.0-10.0). Default: 2.0
                bpm (int): Beats per minute (30-300, None for auto)
                keyscale (str): Musical key (None for auto)
                timesignature (str): Time signature (None for auto)
                vocal_language (str): Language code (None for auto)
                batch_size (int): Number of variations (1-8). Default: 1
                seed (int): Random seed (-1 for random)
                generate_lrc (bool): Generate LRC timestamps
                thumbnail_url (str): Track thumbnail URL

        Returns:
            Job dict with audio URL when completed
        """
        data = {
            "prompt": prompt,
            "audio_duration": duration,
        }

        if lyrics:
            data["lyrics"] = lyrics
        if genre_preset:
            data["genre_preset"] = genre_preset
        if display_name:
            data["display_name"] = display_name
        if quality is not None:
            data["quality"] = quality

        # Pass through AudioMusic V2 advanced parameters
        v2_params = [
            "caption", "instrumental", "format", "model_version",
            "inference_steps", "guidance_scale", "shift", "infer_method",
            "thinking", "lm_temperature", "lm_cfg_scale", "lm_top_k", "lm_top_p",
            "use_cot_metas", "use_cot_caption", "use_cot_lyrics", "use_cot_language",
            "bpm", "keyscale", "timesignature", "vocal_language",
            "batch_size", "seed", "generate_lrc", "thumbnail_url",
            "use_adg", "cfg_interval_start", "cfg_interval_end",
        ]
        for param in v2_params:
            if param in kwargs and kwargs[param] is not None:
                data[param] = kwargs[param]

        endpoint = f"/api/v1/music/{task}"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)

        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    async def _async_generate(
        self, endpoint: str, data: Dict, wait_for_completion: bool, timeout: int
    ) -> Dict[str, Any]:
        response = await self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return await self._async_wait_for_music(job_id, timeout)
        return response

    def instrumental(
        self,
        prompt: str,
        duration: int = 30,
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate instrumental music (no vocals)."""
        return self.generate(
            prompt=prompt,
            task="prompt2instrumental",
            duration=duration,
            quality=quality,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
            **kwargs,
        )

    def song(
        self,
        prompt: str,
        lyrics: str,
        duration: int = 60,
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate a song with vocals."""
        return self.generate(
            prompt=prompt,
            task="text2music",
            lyrics=lyrics,
            duration=duration,
            quality=quality,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
            **kwargs,
        )

    def rap(
        self,
        prompt: str,
        lyrics: str,
        duration: int = 60,
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate rap music."""
        return self.generate(
            prompt=prompt,
            task="text2rap",
            lyrics=lyrics,
            duration=duration,
            quality=quality,
            wait_for_completion=wait_for_completion,
            timeout=timeout,
            **kwargs,
        )

    def simple(
        self,
        query: str,
        instrumental: bool = False,
        vocal_language: str = "unknown",
        display_name: Optional[str] = None,
        duration: int = -1,
        format: str = "flac",
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Generate music from a simple natural language query using AudioMusic V2's Simple Mode.
        AudioMusic auto-generates caption, lyrics, BPM, key, time signature, and duration.

        Args:
            query: Natural language description (e.g. "a soft Bengali love song for a quiet evening")
            instrumental: Generate instrumental only. Default: False
            vocal_language: Vocal language code ("en", "zh", etc.). Default: "unknown" (auto-detect)
            display_name: Custom name for the track
            duration: Duration in seconds (-1 for auto). Default: -1
            format: Output format. Default: "flac"
            quality: Deprecated and no longer needed. Every plan now gets the
                highest-quality music model at the standard rate. Still accepted
                for compatibility; only sent when you pass it explicitly.
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with audio URL when completed
        """
        data = {
            "query": query,
            "instrumental": instrumental,
            "vocal_language": vocal_language,
            "audio_duration": duration,
            "format": format,
        }
        if display_name:
            data["display_name"] = display_name
        if quality is not None:
            data["quality"] = quality

        endpoint = "/api/v1/music/simple"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    def cover(
        self,
        src_audio_url: str,
        caption: str,
        lyrics: Optional[str] = None,
        audio_cover_strength: float = 0.7,
        display_name: Optional[str] = None,
        duration: int = -1,
        format: str = "flac",
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Generate a cover/style transfer of existing audio using AudioMusic V2.
        Transforms audio while maintaining structure but changing style/timbre.

        Args:
            src_audio_url: URL of the source audio to transform (required)
            caption: Style description for the cover (required)
            lyrics: New lyrics for the cover
            audio_cover_strength: Transformation strength (0.0-1.0). Default: 0.7
            display_name: Custom name for the track
            duration: Duration in seconds (-1 for auto). Default: -1
            format: Output format. Default: "flac"
            quality: Deprecated and no longer needed. Every plan now gets the
                highest-quality music model at the standard rate. Still accepted
                for compatibility; only sent when you pass it explicitly.
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with audio URL when completed
        """
        data = {
            "src_audio_url": src_audio_url,
            "caption": caption,
            "audio_cover_strength": audio_cover_strength,
            "audio_duration": duration,
            "format": format,
        }
        if lyrics:
            data["lyrics"] = lyrics
        if display_name:
            data["display_name"] = display_name
        if quality is not None:
            data["quality"] = quality

        endpoint = "/api/v1/music/cover"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    def reference(
        self,
        reference_audio_url: str,
        caption: str,
        lyrics: Optional[str] = None,
        instrumental: bool = False,
        display_name: Optional[str] = None,
        duration: int = -1,
        format: str = "flac",
        quality: Optional[MusicQuality] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Generate music with reference audio for style guidance.
        The reference audio provides global acoustic feature control (timbre, mixing style, atmosphere).

        Args:
            reference_audio_url: URL of reference audio for style guidance (required)
            caption: Text description / caption (required)
            lyrics: Song lyrics
            instrumental: Generate instrumental only. Default: False
            display_name: Custom name for the track
            duration: Duration in seconds (-1 for auto). Default: -1
            format: Output format. Default: "flac"
            quality: Deprecated and no longer needed. Every plan now gets the
                highest-quality music model at the standard rate. Still accepted
                for compatibility; only sent when you pass it explicitly.
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with audio URL when completed
        """
        data = {
            "reference_audio_url": reference_audio_url,
            "caption": caption,
            "instrumental": instrumental,
            "audio_duration": duration,
            "format": format,
        }
        if lyrics:
            data["lyrics"] = lyrics
        if display_name:
            data["display_name"] = display_name
        if quality is not None:
            data["quality"] = quality

        endpoint = "/api/v1/music/reference"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    def analyze(
        self,
        audio_url: str,
        temperature: float = 0.85,
    ) -> Dict[str, Any]:
        """
        Analyze audio to extract metadata using AudioMusic V2.

        Extracts: caption, lyrics, BPM, key/scale, time signature, duration, language.

        Args:
            audio_url: URL of audio to analyze (required)
            temperature: LM temperature (0.0-2.0). Default: 0.85

        Returns:
            Dict with: success, caption, lyrics, bpm, keyscale, timesignature, duration, language, audio_codes, error
        """
        data = {
            "audio_url": audio_url,
            "temperature": temperature,
        }

        if self.async_mode:
            return self._async_analyze(data)

        return self.client.request("POST", "/api/v1/music/analyze", json_data=data)

    async def _async_analyze(self, data: Dict) -> Dict[str, Any]:
        return await self.client.request("POST", "/api/v1/music/analyze", json_data=data)

    def extract_stem(
        self,
        src_audio_url: str,
        track_name: str,
        display_name: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Extract a specific stem/track from audio.

        Available tracks: vocals, drums, bass, guitar, keyboard, strings, synth,
        percussion, brass, woodwinds, backing_vocals, fx.

        Args:
            src_audio_url: URL of audio to extract stem from (required)
            track_name: Name of the track/instrument to extract (required)
            display_name: Custom name for the job
            wait_for_completion: Wait for completion
            timeout: Max wait time in seconds

        Returns:
            Job dict with extracted stem audio URL when completed
        """
        data = {
            "src_audio_url": src_audio_url,
            "track_name": track_name,
        }
        if display_name:
            data["display_name"] = display_name

        endpoint = "/api/v1/music/extract-stem"

        if self.async_mode:
            return self._async_generate(endpoint, data, wait_for_completion, timeout)

        response = self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            job_id = response.get("id") or response.get("job_id")
            return self._wait_for_music(job_id, timeout)
        return response

    def get_job(self, job_id: int) -> Dict[str, Any]:
        """Get music generation job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v1/music/jobs/{job_id}/status")

    async def _async_get_job(self, job_id: int) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v1/music/jobs/{job_id}/status")

    def list_jobs(self, skip: int = 0, limit: int = 50, task: Optional[str] = None) -> List[Dict[str, Any]]:
        """List music generation jobs."""
        params = {"skip": skip, "limit": limit}
        if task:
            params["task"] = task

        if self.async_mode:
            return self._async_list_jobs(params)
        return self.client.request("GET", "/api/v1/music/jobs", params=params)

    async def _async_list_jobs(self, params: Dict) -> List[Dict[str, Any]]:
        return await self.client.request("GET", "/api/v1/music/jobs", params=params)

    def delete_job(self, job_id: int) -> Dict[str, str]:
        """Delete a music generation job."""
        if self.async_mode:
            return self._async_delete_job(job_id)
        return self.client.request("DELETE", f"/api/v1/music/jobs/{job_id}")

    async def _async_delete_job(self, job_id: int) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v1/music/jobs/{job_id}")

    def get_presets(self) -> Dict[str, Any]:
        """Get available genre presets."""
        if self.async_mode:
            return self._async_get_presets()
        return self.client.request("GET", "/api/v1/music/presets")

    async def _async_get_presets(self) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v1/music/presets")

    # ------------------------------------------------------------------
    # Score-first music (AudioMusic v3)
    #
    # Every v3 track starts as an editable score in ABC notation. The usual
    # loop is: compose (score only) -> revise_score / hand-edit -> record_score
    # (render audio from the score). ``generate_v3`` does score + audio in one
    # call. There is no ``duration``: length follows the lyrics / score.
    #
    # In async mode (``AsyncClient``) every method returns an awaitable.
    # ------------------------------------------------------------------

    def v3_availability(self) -> Dict[str, Any]:
        """Whether score-first music (AudioMusic v3) is offered.

        Always answers, even where v3 is switched off. Hide your v3 surface when
        ``available`` is false rather than discovering it through 404s.

        Returns:
            ``{"available": bool}``
        """
        return self.client.request("GET", f"{V3_PREFIX}/availability")

    def compose(
        self,
        style: str,
        lyrics: Optional[str] = None,
        description: Optional[str] = None,
        cot: Optional[MusicV3Cot] = None,
        seed: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        display_name: Optional[str] = None,
        target_seconds: Optional[float] = None,
        language: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Write a score only, no audio (``POST /music/v3/plan``).

        Review or revise the score, then render it with :meth:`record_score`.
        Charges a small fixed amount for writing the score; nothing for audio.

        Args:
            style: Genre, instrumentation, mood, tempo feel, vocal character
                (1-2000 chars).
            lyrics: Lyrics, optionally with ``[Verse]``/``[Chorus]`` tags. Empty
                or omitted for an instrumental. Mutually exclusive with
                ``description``.
            description: COMING SOON - a plain-language brief to write the song
                from instead of lyrics. Mutually exclusive with ``lyrics``. Until
                the server supports it, sending it is rejected (422).
            cot: ``"full"`` (melody + harmony, the default) or ``"melody"``.
            seed: Reuse a seed to get closer to a previous result (0..2**31-1).
            cfg_scale: How literally to follow ``style`` (1.0-10.0, server
                default 3.0).
            display_name: Your own name for the track (max 200 chars).
            target_seconds: COMING SOON - an approximate target length.
                Rejected (422) until the server supports it.
            language: COMING SOON - lyric/vocal language code. Rejected (422)
                until the server supports it.
            wait_for_completion: Poll until the score is ready.
            timeout: Max seconds to wait when ``wait_for_completion``.
            poll_interval: Seconds between polls.

        Returns:
            The v3 job (``job_id``, ``status``, ``score`` once complete, ...).
        """
        if lyrics and description:
            raise ValidationError("Pass either lyrics or description, not both.")
        if description is not None and not lyrics:
            lyrics = None  # an empty lyrics string must not ride along with a description
        data = _drop_none(
            {
                "style": style,
                "lyrics": lyrics,
                "description": description,
                "cot": cot,
                "seed": seed,
                "cfg_scale": cfg_scale,
                "display_name": display_name,
                "target_seconds": target_seconds,
                "language": language,
            }
        )
        return self._v3_submit("/plan", data, wait_for_completion, timeout, poll_interval)

    def revise_score(
        self,
        source_job_id: int,
        instruction: str,
        section: Optional[str] = None,
        bars: Optional[Dict[str, int]] = None,
        allow_tempo_change: Optional[bool] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Revise a job's score from a plain-language instruction (``POST /music/v3/revise``).

        COMING SOON: the server side of this endpoint is still rolling out;
        until it does, this call answers 404.

        Produces a new score-only job (no audio). Its ``score_comparison`` says
        what changed, including ``changed_bars``. Render it with
        :meth:`record_score` when you are happy with it.

        Args:
            source_job_id: The v3 job whose score you want revised.
            instruction: What to change, e.g. "make the chorus build more"
                (1-500 chars).
            section: Limit the revision to one section, e.g. ``"Chorus"``.
            bars: Limit the revision to a bar range, ``{"start": 9, "end": 16}``.
            allow_tempo_change: Permit the revision to change the tempo.
            wait_for_completion: Poll until the revised score is ready.
            timeout: Max seconds to wait when ``wait_for_completion``.
            poll_interval: Seconds between polls.

        Returns:
            The new v3 job.
        """
        if not instruction or not instruction.strip():
            raise ValidationError("instruction must not be empty.")
        if len(instruction) > MAX_REVISE_INSTRUCTION_CHARS:
            raise ValidationError(
                f"instruction must be at most {MAX_REVISE_INSTRUCTION_CHARS} characters "
                f"(got {len(instruction)})."
            )
        if bars is not None:
            start, end = bars.get("start"), bars.get("end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or isinstance(start, bool)
                or isinstance(end, bool)
                or start > end
            ):
                raise ValidationError('bars must be {"start": int, "end": int} with start <= end.')
            bars = {"start": start, "end": end}
        data = _drop_none(
            {
                "source_job_id": source_job_id,
                "instruction": instruction,
                "section": section,
                "bars": bars,
                "allow_tempo_change": allow_tempo_change,
            }
        )
        return self._v3_submit("/revise", data, wait_for_completion, timeout, poll_interval)

    def record_score(
        self,
        source_job_id: int,
        abc: str,
        style: Optional[str] = None,
        lyrics: Optional[str] = None,
        cot: Optional[MusicV3Cot] = None,
        seed: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        display_name: Optional[str] = None,
        allow_tempo_change: Optional[bool] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Render audio from a complete score (``POST /music/v3/edit``).

        This records a new take from the score you send: sections you did not
        change are still performed afresh. An identical request for the same
        source that is still in progress is refused with 409
        (``SCORE_ALREADY_RECORDING``); poll the ``job_id`` in that error instead.

        Args:
            source_job_id: The job the score came from.
            abc: The COMPLETE score in ABC notation (not a fragment).
            style: Replacement style text; omit to reuse the source's.
            lyrics: Replacement lyrics; omit to reuse the source's.
            cot: ``"melody"`` (server default) lets the arrangement follow the
                tune freely; ``"full"`` holds it to the written harmony.
            seed: Optional seed.
            cfg_scale: How literally to follow ``style`` (1.0-10.0).
            display_name: Your own name for the track.
            allow_tempo_change: Permit the score to change the source's tempo
                (off by default on the server).
            wait_for_completion: Poll until the recording is ready.
            timeout: Max seconds to wait when ``wait_for_completion``.
            poll_interval: Seconds between polls.

        Returns:
            The new v3 job; once complete it carries ``audio_url``.
        """
        if not abc or not abc.strip():
            raise ValidationError("abc must be a complete, non-empty score.")
        data = _drop_none(
            {
                "source_job_id": source_job_id,
                "abc": abc,
                "style": style,
                "lyrics": lyrics,
                "cot": cot,
                "seed": seed,
                "cfg_scale": cfg_scale,
                "display_name": display_name,
                "allow_tempo_change": allow_tempo_change,
            }
        )
        return self._v3_submit("/edit", data, wait_for_completion, timeout, poll_interval)

    def generate_v3(
        self,
        style: str,
        lyrics: Optional[str] = None,
        abc: Optional[str] = None,
        cot: Optional[MusicV3Cot] = None,
        seed: Optional[int] = None,
        cfg_scale: Optional[float] = None,
        display_name: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Write a score AND render the song in one call (``POST /music/v3/generate``).

        There is no ``duration``: length follows how much lyric text you send.
        Billed as a small score charge plus the music priced from the score
        (see ``billing`` on the job).

        Args:
            style: Genre, instrumentation, mood, tempo feel, vocal character.
            lyrics: Lyrics; empty or omitted for an instrumental.
            abc: An existing complete score to render instead of writing one.
            cot: ``"full"`` (default) or ``"melody"``.
            seed: Optional seed.
            cfg_scale: How literally to follow ``style`` (1.0-10.0).
            display_name: Your own name for the track.
            wait_for_completion: Poll until the song is ready.
            timeout: Max seconds to wait when ``wait_for_completion``.
            poll_interval: Seconds between polls.

        Returns:
            The v3 job.
        """
        data = _drop_none(
            {
                "style": style,
                "lyrics": lyrics,
                "abc": abc,
                "cot": cot,
                "seed": seed,
                "cfg_scale": cfg_scale,
                "display_name": display_name,
            }
        )
        return self._v3_submit("/generate", data, wait_for_completion, timeout, poll_interval)

    def get_v3_job(self, job_id: int) -> Dict[str, Any]:
        """One v3 job: status, audio, score, diagnostics, billing."""
        return self.client.request("GET", f"{V3_PREFIX}/jobs/{int(job_id)}")

    def get_score(self, job_id: int) -> Dict[str, Any]:
        """Just a job's score (``abc``, ``abc_url``, ``midi_url``, ``editable``).

        Raises ``APIError`` (404, ``NO_SCORE``) when the job has no score yet.
        """
        return self.client.request("GET", f"{V3_PREFIX}/jobs/{int(job_id)}/score")

    def list_v3_jobs(
        self,
        skip: int = 0,
        limit: int = 50,
        workflow: Optional[MusicV3Workflow] = None,
        source_job_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Your v3 jobs, newest first.

        Args:
            skip: Offset.
            limit: Page size.
            workflow: Only jobs from one entry point (``"plan"``, ``"edit"``, ...).
            source_job_id: Only versions derived from this job (one lineage).
        """
        params = _drop_none(
            {"skip": skip, "limit": limit, "workflow": workflow, "source_job_id": source_job_id}
        )
        return self.client.request("GET", f"{V3_PREFIX}/jobs", params=params)

    def wait_for_v3_job(
        self, job_id: int, timeout: int = 900, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Poll a v3 job until it completes.

        Returns the completed job. Raises ``AudioPodError`` if the job fails or
        is cancelled, and ``TimeoutError`` after ``timeout`` seconds.
        """
        if self.async_mode:
            return self._async_wait_for_v3_job(job_id, timeout, poll_interval)
        deadline = time.monotonic() + timeout
        while True:
            job = self.get_v3_job(job_id)
            if _v3_finished(job):
                return job
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Music job {job_id} did not complete within {timeout} seconds")
            time.sleep(poll_interval)

    async def _async_wait_for_v3_job(
        self, job_id: int, timeout: int, poll_interval: int
    ) -> Dict[str, Any]:
        import asyncio

        deadline = time.monotonic() + timeout
        while True:
            job = await self.get_v3_job(job_id)
            if _v3_finished(job):
                return job
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Music job {job_id} did not complete within {timeout} seconds")
            await asyncio.sleep(poll_interval)

    def _v3_submit(
        self,
        path: str,
        data: Dict[str, Any],
        wait_for_completion: bool,
        timeout: int,
        poll_interval: int,
    ) -> Dict[str, Any]:
        endpoint = f"{V3_PREFIX}{path}"
        if self.async_mode:
            return self._async_v3_submit(
                endpoint, data, wait_for_completion, timeout, poll_interval
            )
        job = self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            return self.wait_for_v3_job(job["job_id"], timeout, poll_interval)
        return job

    async def _async_v3_submit(
        self,
        endpoint: str,
        data: Dict[str, Any],
        wait_for_completion: bool,
        timeout: int,
        poll_interval: int,
    ) -> Dict[str, Any]:
        job = await self.client.request("POST", endpoint, json_data=data)
        if wait_for_completion:
            return await self._async_wait_for_v3_job(job["job_id"], timeout, poll_interval)
        return job

    def _wait_for_music(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Wait for music generation job completion."""
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Music generation failed: {job.get('error_message', 'Unknown error')}")

            time.sleep(5)

        raise TimeoutError(f"Music generation {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_music(self, job_id: int, timeout: int) -> Dict[str, Any]:
        """Async wait for music generation job completion."""
        import asyncio
        import time
        start_time = time.time()

        while time.time() - start_time < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "").upper()

            if status == "COMPLETED":
                return job
            elif status in ("FAILED", "ERROR"):
                raise Exception(f"Music generation failed: {job.get('error_message', 'Unknown error')}")

            await asyncio.sleep(5)

        raise TimeoutError(f"Music generation {job_id} did not complete within {timeout} seconds")


def _v3_finished(job: Dict[str, Any]) -> bool:
    """True when the job completed; raises when it failed. False while running."""
    status = str(job.get("status") or "").upper()
    if status == _V3_DONE:
        return True
    if status in _V3_FAILED:
        raise AudioPodError(
            f"Music job {job.get('job_id')} {status.lower()}: "
            f"{job.get('error_message') or 'Unknown error'}"
        )
    return False
