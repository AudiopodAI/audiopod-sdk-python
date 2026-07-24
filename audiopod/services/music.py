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
"""

from typing import Optional, Dict, Any, List, Literal
from .base import BaseService


MusicTask = Literal[
    "text2music", "prompt2instrumental", "lyric2vocals", "text2rap", "text2samples",
    "cover", "repaint", "extract", "complete", "simple", "retake", "extend", "edit",
]

MusicQuality = Literal["standard", "premium"]


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
            quality: Generation quality tier - "standard" or "premium"
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
                thinking (bool): Enable 4B LM Chain-of-Thought. Default: True
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
        The 4B Language Model auto-generates caption, lyrics, BPM, key, time signature, and duration.

        Args:
            query: Natural language description (e.g. "a soft Bengali love song for a quiet evening")
            instrumental: Generate instrumental only. Default: False
            vocal_language: Vocal language code ("en", "zh", etc.). Default: "unknown" (auto-detect)
            display_name: Custom name for the track
            duration: Duration in seconds (-1 for auto). Default: -1
            format: Output format. Default: "flac"
            quality: Generation quality tier - "standard" or "premium"
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
            quality: Generation quality tier - "standard" or "premium"
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
            quality: Generation quality tier - "standard" or "premium"
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
        Analyze audio to extract metadata using AudioMusic V2's 4B Language Model.

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
