"""
Podcast Service - AI podcast studio: projects, sources, outline, transcript, audio.

The full pipeline, end to end: create a project with speakers, attach one or
more sources (text/URL/file), generate an outline, generate a transcript, then
generate the multi-speaker audio. You can also drive each step yourself and edit
the outline / transcript / speakers in between. Reusable speaker and episode
profiles let you template recurring shows.

API Routes (all under ``/api/v1/podcast``):
- GET    /dashboard                                  - Dashboard stats
- GET    /episode-profiles                           - List episode profiles
- POST   /episode-profiles                           - Create episode profile
- PUT    /episode-profiles/{profile_id}              - Update episode profile
- DELETE /episode-profiles/{profile_id}              - Delete episode profile
- POST   /feed                                       - Enable the public RSS feed
- POST   /projects                                   - Create project
- GET    /projects                                   - List projects
- GET    /projects/{project_id}                      - Get project
- PUT    /projects/{project_id}                      - Update project
- DELETE /projects/{project_id}                      - Delete project
- GET    /projects/{id}/audio/estimate               - Estimate audio credits
- POST   /projects/{id}/audio/generate               - Generate audio (job)
- POST   /projects/{id}/dialogue/regenerate          - Regenerate one dialogue line
- PUT    /projects/{id}/outline                      - Replace the outline
- POST   /projects/{id}/outline/generate             - Generate the outline
- GET    /projects/{id}/progress                     - Generation progress
- POST   /projects/{id}/sources                      - Add a source (multipart)
- GET    /projects/{id}/sources                      - List sources
- DELETE /projects/{id}/sources/{source_id}          - Delete a source
- PUT    /projects/{id}/speakers/{speaker_id}        - Update a speaker
- PUT    /projects/{id}/transcript                   - Replace the transcript
- POST   /projects/{id}/transcript/generate          - Generate the transcript
- GET    /speaker-profiles                           - List speaker profiles
- POST   /speaker-profiles                           - Create speaker profile
- PUT    /speaker-profiles/{profile_id}              - Update speaker profile
- DELETE /speaker-profiles/{profile_id}              - Delete speaker profile
- GET    /voices/presets                             - List preset podcast voices
"""

import time
from typing import Any, Dict, List, Optional

from .base import BaseService

_BASE = "/api/v1/podcast"

# Progress statuses that mean the audio pipeline finished successfully.
_AUDIO_DONE_STATUSES = frozenset({"audio_ready", "completed"})
# Progress statuses that mean generation will never finish.
_FAILED_STATUSES = frozenset({"failed", "error", "canceled", "cancelled"})


class PodcastService(BaseService):
    """
    Service for the AI podcast studio.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # Create a two-speaker project
        project = client.podcast.create_project(
            title="Weekly Roundup",
            topic="This week in audio AI",
            speakers=[
                {"name": "Ava", "role": "Host"},
                {"name": "Ben", "role": "Expert"},
            ],
        )
        pid = project["id"]

        # Add a source, build the outline + transcript, then render audio
        client.podcast.add_source(pid, source_type="text", text="Show notes...")
        client.podcast.generate_outline(pid)
        client.podcast.generate_transcript(pid)
        result = client.podcast.generate_audio(pid, wait_for_completion=True)
        ```
    """

    # ---------------------------------------------------------------- dashboard
    def dashboard(self) -> Dict[str, Any]:
        """Get podcast dashboard statistics."""
        if self.async_mode:
            return self._async_dashboard()
        return self.client.request("GET", f"{_BASE}/dashboard")

    async def _async_dashboard(self) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/dashboard")

    # --------------------------------------------------------- episode profiles
    def list_episode_profiles(self) -> List[Dict[str, Any]]:
        """List reusable episode profiles."""
        if self.async_mode:
            return self._async_list_episode_profiles()
        return self.client.request("GET", f"{_BASE}/episode-profiles")

    async def _async_list_episode_profiles(self) -> List[Dict[str, Any]]:
        return await self.client.request("GET", f"{_BASE}/episode-profiles")

    def create_episode_profile(
        self,
        name: str,
        description: Optional[str] = None,
        default_briefing: Optional[str] = None,
        num_segments: int = 5,
        tone: Optional[str] = None,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a reusable episode profile."""
        body: Dict[str, Any] = {"name": name, "num_segments": num_segments}
        for k, v in {
            "description": description,
            "default_briefing": default_briefing,
            "tone": tone,
            "format": format,
        }.items():
            if v is not None:
                body[k] = v
        if self.async_mode:
            return self._async_create_episode_profile(body)
        return self.client.request("POST", f"{_BASE}/episode-profiles", json_data=body)

    async def _async_create_episode_profile(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", f"{_BASE}/episode-profiles", json_data=body)

    def update_episode_profile(self, profile_id: str, **fields: Any) -> Dict[str, Any]:
        """Update an episode profile. Pass any of: name, description,
        default_briefing, num_segments, tone, format."""
        body = {k: v for k, v in fields.items() if v is not None}
        if self.async_mode:
            return self._async_update_episode_profile(profile_id, body)
        return self.client.request("PUT", f"{_BASE}/episode-profiles/{profile_id}", json_data=body)

    async def _async_update_episode_profile(self, profile_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("PUT", f"{_BASE}/episode-profiles/{profile_id}", json_data=body)

    def delete_episode_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete an episode profile."""
        if self.async_mode:
            return self._async_delete_episode_profile(profile_id)
        return self.client.request("DELETE", f"{_BASE}/episode-profiles/{profile_id}")

    async def _async_delete_episode_profile(self, profile_id: str) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"{_BASE}/episode-profiles/{profile_id}")

    # ---------------------------------------------------------------- feed
    def feed(self) -> Dict[str, Any]:
        """Enable and return the user's public podcast RSS feed URL."""
        if self.async_mode:
            return self._async_feed()
        return self.client.request("POST", f"{_BASE}/feed")

    async def _async_feed(self) -> Dict[str, Any]:
        return await self.client.request("POST", f"{_BASE}/feed")

    # ---------------------------------------------------------------- projects
    def create_project(
        self,
        title: str,
        topic: str,
        speakers: List[Dict[str, Any]],
        briefing: str = "",
        key_points: Optional[List[str]] = None,
        language: str = "en",
        quality_preset: Optional[str] = None,
        target_duration_minutes: Optional[int] = None,
        episode_profile_id: Optional[str] = None,
        briefing_suffix: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a podcast project.

        Args:
            title: Project title (required)
            topic: What the episode is about (required)
            speakers: List of speaker dicts (required). Each speaker supports:
                ``name`` (required), ``role`` (one of "Host", "Expert", "Guest",
                "Narrator"), ``voice_type`` ("preset", "cloned", "standard"),
                ``voice_id``, ``voice_ref_id``, ``language`` (default "en"),
                ``use_turbo``, ``backstory``, ``personality``.
            briefing: Freeform briefing for the writers. Default: ""
            key_points: Bullet points the episode should hit.
            language: Language code. Default: "en"
            quality_preset: One of "quick", "standard", "premium".
            target_duration_minutes: Target episode length.
            episode_profile_id: Reuse an episode profile as the template.
            briefing_suffix: Text appended to the briefing.

        Returns:
            The created project dict (includes ``id``).
        """
        body: Dict[str, Any] = {
            "title": title,
            "topic": topic,
            "speakers": speakers,
            "briefing": briefing,
            "language": language,
            "key_points": key_points if key_points is not None else [],
        }
        for k, v in {
            "quality_preset": quality_preset,
            "target_duration_minutes": target_duration_minutes,
            "episode_profile_id": episode_profile_id,
            "briefing_suffix": briefing_suffix,
        }.items():
            if v is not None:
                body[k] = v
        if self.async_mode:
            return self._async_create_project(body)
        return self.client.request("POST", f"{_BASE}/projects", json_data=body)

    async def _async_create_project(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", f"{_BASE}/projects", json_data=body)

    def list_projects(
        self,
        page: int = 1,
        per_page: int = 20,
        status_filter: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List podcast projects (paginated)."""
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if status_filter is not None:
            params["status_filter"] = status_filter
        if search is not None:
            params["search"] = search
        if self.async_mode:
            return self._async_list_projects(params)
        return self.client.request("GET", f"{_BASE}/projects", params=params)

    async def _async_list_projects(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/projects", params=params)

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a single podcast project."""
        if self.async_mode:
            return self._async_get_project(project_id)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}")

    async def _async_get_project(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/projects/{project_id}")

    def update_project(self, project_id: str, **fields: Any) -> Dict[str, Any]:
        """Update a project. Pass any of: title, topic, briefing, key_points,
        language, quality_preset, target_duration_minutes."""
        body = {k: v for k, v in fields.items() if v is not None}
        if self.async_mode:
            return self._async_update_project(project_id, body)
        return self.client.request("PUT", f"{_BASE}/projects/{project_id}", json_data=body)

    async def _async_update_project(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("PUT", f"{_BASE}/projects/{project_id}", json_data=body)

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a podcast project."""
        if self.async_mode:
            return self._async_delete_project(project_id)
        return self.client.request("DELETE", f"{_BASE}/projects/{project_id}")

    async def _async_delete_project(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"{_BASE}/projects/{project_id}")

    # ---------------------------------------------------------------- sources
    def add_source(
        self,
        project_id: str,
        source_type: str,
        text: Optional[str] = None,
        url: Optional[str] = None,
        file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Add a source to a project. This endpoint is multipart/form-data.

        Args:
            project_id: Target project
            source_type: The kind of source (e.g. "text", "url", "file")
            text: Raw text (for text sources)
            url: A URL to ingest (for url sources)
            file: Path to a local file to upload (for file sources)
        """
        data: Dict[str, Any] = {"source_type": source_type}
        if text is not None:
            data["text"] = text
        if url is not None:
            data["url"] = url
        files = self._prepare_file_upload(file, "file") if file else None
        if self.async_mode:
            return self._async_add_source(project_id, data, files)
        return self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/sources", data=data, files=files
        )

    async def _async_add_source(
        self, project_id: str, data: Dict[str, Any], files: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        return await self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/sources", data=data, files=files
        )

    def list_sources(self, project_id: str) -> Dict[str, Any]:
        """List a project's sources."""
        if self.async_mode:
            return self._async_list_sources(project_id)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/sources")

    async def _async_list_sources(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/projects/{project_id}/sources")

    def delete_source(self, project_id: str, source_id: str) -> Dict[str, Any]:
        """Delete a source from a project."""
        if self.async_mode:
            return self._async_delete_source(project_id, source_id)
        return self.client.request("DELETE", f"{_BASE}/projects/{project_id}/sources/{source_id}")

    async def _async_delete_source(self, project_id: str, source_id: str) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"{_BASE}/projects/{project_id}/sources/{source_id}")

    # ---------------------------------------------------------------- outline
    def generate_outline(
        self,
        project_id: str,
        num_segments: int = 5,
        focus_areas: Optional[List[str]] = None,
        target_duration_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate the episode outline."""
        body: Dict[str, Any] = {
            "num_segments": num_segments,
            "focus_areas": focus_areas if focus_areas is not None else [],
        }
        if target_duration_minutes is not None:
            body["target_duration_minutes"] = target_duration_minutes
        if self.async_mode:
            return self._async_generate_outline(project_id, body)
        return self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/outline/generate", json_data=body
        )

    async def _async_generate_outline(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/outline/generate", json_data=body
        )

    def update_outline(self, project_id: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Replace the episode outline.

        Args:
            project_id: Target project
            segments: List of segment dicts. Each supports ``title`` (required),
                ``description``, and ``size`` (one of "short", "medium", "long").
        """
        body = {"segments": segments}
        if self.async_mode:
            return self._async_update_outline(project_id, body)
        return self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/outline", json_data=body
        )

    async def _async_update_outline(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/outline", json_data=body
        )

    # ---------------------------------------------------------------- transcript
    def generate_transcript(self, project_id: str) -> Dict[str, Any]:
        """Generate the full transcript from the outline."""
        if self.async_mode:
            return self._async_generate_transcript(project_id)
        return self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/transcript/generate", json_data={}
        )

    async def _async_generate_transcript(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/transcript/generate", json_data={}
        )

    def update_transcript(self, project_id: str, dialogues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Replace the transcript.

        Args:
            project_id: Target project
            dialogues: List of dialogue dicts. Each supports ``speaker``
                (required), ``text`` (required), and ``use_turbo``.
        """
        body = {"dialogues": dialogues}
        if self.async_mode:
            return self._async_update_transcript(project_id, body)
        return self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/transcript", json_data=body
        )

    async def _async_update_transcript(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/transcript", json_data=body
        )

    def regenerate_dialogue(
        self, project_id: str, dialogue_id: str, new_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate (and optionally rewrite) a single dialogue line."""
        body: Dict[str, Any] = {"dialogue_id": dialogue_id}
        if new_text is not None:
            body["new_text"] = new_text
        if self.async_mode:
            return self._async_regenerate_dialogue(project_id, body)
        return self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/dialogue/regenerate", json_data=body
        )

    async def _async_regenerate_dialogue(self, project_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/dialogue/regenerate", json_data=body
        )

    # ---------------------------------------------------------------- speakers
    def update_speaker(self, project_id: str, speaker_id: str, **fields: Any) -> Dict[str, Any]:
        """Update a project speaker. Pass any of: name, role, voice_ref_id,
        backstory, personality, language."""
        body = {k: v for k, v in fields.items() if v is not None}
        if self.async_mode:
            return self._async_update_speaker(project_id, speaker_id, body)
        return self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/speakers/{speaker_id}", json_data=body
        )

    async def _async_update_speaker(
        self, project_id: str, speaker_id: str, body: Dict[str, Any]
    ) -> Dict[str, Any]:
        return await self.client.request(
            "PUT", f"{_BASE}/projects/{project_id}/speakers/{speaker_id}", json_data=body
        )

    # ---------------------------------------------------------------- audio
    def estimate_audio(self, project_id: str) -> Dict[str, Any]:
        """Estimate the credit cost of generating the episode audio."""
        if self.async_mode:
            return self._async_estimate_audio(project_id)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/audio/estimate")

    async def _async_estimate_audio(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/projects/{project_id}/audio/estimate")

    def generate_audio(
        self,
        project_id: str,
        regenerate_all: bool = False,
        wait_for_completion: bool = False,
        timeout: int = 900,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Generate the multi-speaker episode audio.

        Args:
            project_id: Target project
            regenerate_all: Re-render every dialogue, not just the pending ones.
            wait_for_completion: Poll ``get_progress`` until the audio is ready.
            timeout: Max seconds to wait when ``wait_for_completion`` is True.
            poll_interval: Seconds between progress polls.

        Returns:
            The ``{job_id, dialogues_to_generate}`` response, or the final
            progress dict when ``wait_for_completion`` is True.
        """
        body = {"regenerate_all": regenerate_all}
        if self.async_mode:
            return self._async_generate_audio(project_id, body, wait_for_completion, timeout, poll_interval)
        response = self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/audio/generate", json_data=body
        )
        if wait_for_completion:
            return self._wait_for_audio(project_id, timeout, poll_interval)
        return response

    async def _async_generate_audio(
        self,
        project_id: str,
        body: Dict[str, Any],
        wait_for_completion: bool,
        timeout: int,
        poll_interval: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", f"{_BASE}/projects/{project_id}/audio/generate", json_data=body
        )
        if wait_for_completion:
            return await self._async_wait_for_audio(project_id, timeout, poll_interval)
        return response

    def get_progress(self, project_id: str) -> Dict[str, Any]:
        """Get real-time generation progress for a project."""
        if self.async_mode:
            return self._async_get_progress(project_id)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/progress")

    async def _async_get_progress(self, project_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/projects/{project_id}/progress")

    def _wait_for_audio(self, project_id: str, timeout: int, poll_interval: int) -> Dict[str, Any]:
        """Poll project progress until the audio is ready (or it fails)."""
        start = time.time()
        while time.time() - start < timeout:
            progress = self.get_progress(project_id)
            status = str(progress.get("status", "")).lower()
            if status in _AUDIO_DONE_STATUSES:
                return progress
            if status in _FAILED_STATUSES:
                raise Exception(
                    f"Podcast audio generation failed: {progress.get('error_message', 'Unknown error')}"
                )
            time.sleep(poll_interval)
        raise TimeoutError(f"Podcast {project_id} audio did not complete within {timeout} seconds")

    async def _async_wait_for_audio(self, project_id: str, timeout: int, poll_interval: int) -> Dict[str, Any]:
        """Async poll project progress until the audio is ready (or it fails)."""
        import asyncio

        start = time.time()
        while time.time() - start < timeout:
            progress = await self.get_progress(project_id)
            status = str(progress.get("status", "")).lower()
            if status in _AUDIO_DONE_STATUSES:
                return progress
            if status in _FAILED_STATUSES:
                raise Exception(
                    f"Podcast audio generation failed: {progress.get('error_message', 'Unknown error')}"
                )
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Podcast {project_id} audio did not complete within {timeout} seconds")

    # ---------------------------------------------------------- speaker profiles
    def list_speaker_profiles(self) -> List[Dict[str, Any]]:
        """List reusable speaker profiles."""
        if self.async_mode:
            return self._async_list_speaker_profiles()
        return self.client.request("GET", f"{_BASE}/speaker-profiles")

    async def _async_list_speaker_profiles(self) -> List[Dict[str, Any]]:
        return await self.client.request("GET", f"{_BASE}/speaker-profiles")

    def create_speaker_profile(
        self,
        name: str,
        speaker_name: str,
        voice_id: Optional[int] = None,
        backstory: Optional[str] = None,
        personality: Optional[str] = None,
        role: Optional[str] = None,
        language: str = "en",
    ) -> Dict[str, Any]:
        """
        Create a reusable speaker profile.

        Args:
            name: Profile name (required)
            speaker_name: The speaker's on-air name (required)
            voice_id: The voice to use for this speaker.
            backstory: Speaker backstory used to steer the writing.
            personality: Speaker personality used to steer the writing.
            role: One of "Host", "Expert", "Guest", "Narrator".
            language: Language code. Default: "en"
        """
        body: Dict[str, Any] = {"name": name, "speaker_name": speaker_name, "language": language}
        for k, v in {
            "voice_id": voice_id,
            "backstory": backstory,
            "personality": personality,
            "role": role,
        }.items():
            if v is not None:
                body[k] = v
        if self.async_mode:
            return self._async_create_speaker_profile(body)
        return self.client.request("POST", f"{_BASE}/speaker-profiles", json_data=body)

    async def _async_create_speaker_profile(self, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("POST", f"{_BASE}/speaker-profiles", json_data=body)

    def update_speaker_profile(self, profile_id: str, **fields: Any) -> Dict[str, Any]:
        """Update a speaker profile. Pass any of: name, speaker_name, voice_id,
        backstory, personality, role, language."""
        body = {k: v for k, v in fields.items() if v is not None}
        if self.async_mode:
            return self._async_update_speaker_profile(profile_id, body)
        return self.client.request("PUT", f"{_BASE}/speaker-profiles/{profile_id}", json_data=body)

    async def _async_update_speaker_profile(self, profile_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return await self.client.request("PUT", f"{_BASE}/speaker-profiles/{profile_id}", json_data=body)

    def delete_speaker_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a speaker profile."""
        if self.async_mode:
            return self._async_delete_speaker_profile(profile_id)
        return self.client.request("DELETE", f"{_BASE}/speaker-profiles/{profile_id}")

    async def _async_delete_speaker_profile(self, profile_id: str) -> Dict[str, Any]:
        return await self.client.request("DELETE", f"{_BASE}/speaker-profiles/{profile_id}")

    # ---------------------------------------------------------------- voices
    def voice_presets(self) -> Dict[str, Any]:
        """List the available preset podcast voices."""
        if self.async_mode:
            return self._async_voice_presets()
        return self.client.request("GET", f"{_BASE}/voices/presets")

    async def _async_voice_presets(self) -> Dict[str, Any]:
        return await self.client.request("GET", f"{_BASE}/voices/presets")
