"""
Audiobook Service - Turn a manuscript into a finished, ACX-compliant audiobook.

The full pipeline, end to end: create a project, add a manuscript (upload a
PDF/EPUB, paste text, or generate from a prompt), narrate it, export an
ACX-compliant package, and download it. Use :meth:`AudiobookService.produce`
for the whole flow in one call, or drive each step yourself.
"""

import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

from ..exceptions import APIError
from .base import BaseService

_BASE = "/api/v1/audiobook"

# Project statuses that mean "the manuscript is not parsed yet". `draft` is a
# project that has never been given a manuscript; `parsing` is a parse in flight
# (a re-parse re-enters `parsing` with an old `parsing_completed_at` still set,
# so status wins over the timestamp).
_PARSE_PENDING_STATUSES = frozenset({"draft", "parsing", "pending", "queued"})
# Statuses that mean the parse will never finish.
_PARSE_FAILED_STATUSES = frozenset({"failed", "error", "canceled", "cancelled"})


class AudiobookService(BaseService):
    """
    Service for automated audiobook production.

    Example:
        ```python
        from audiopod import Client

        client = Client()

        # One-call production: manuscript in, ACX package out
        result = client.audiobook.produce(
            title="The Lighthouse Keeper",
            author="A. P. Tester",
            file="book.epub",
            voice_id=387,
        )
        print(result["download_url"])

        # Or drive each step
        project = client.audiobook.create_project(title="My Book", author="Me")
        up = client.audiobook.upload_manuscript(project["id"], file="book.epub")
        client.audiobook.parse_manuscript(project["id"], up["file_key"], "book.epub")
        client.audiobook.narrate(project["id"], voice_id=387)      # waits by default
        export = client.audiobook.export(project["id"])            # waits by default
        dl = client.audiobook.download(project["id"], export["job_id"])
        ```
    """

    # ------------------------------------------------------------------ projects
    def create_project(
        self,
        title: str,
        author: Optional[str] = None,
        description: Optional[str] = None,
        isbn: Optional[str] = None,
        genre: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create an audiobook project. ``title`` is required."""
        body = {"title": title}
        for k, v in {"author": author, "description": description, "isbn": isbn, "genre": genre}.items():
            if v is not None:
                body[k] = v
        body.update(kwargs)
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects", json_data=body)
        return self.client.request("POST", f"{_BASE}/projects", json_data=body)

    def list_projects(
        self,
        page: int = 1,
        per_page: int = 20,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List your audiobook projects (paginated).

        ``page`` is 1-based; ``per_page`` is capped at 100 by the API.

        ``skip``/``limit`` are **deprecated** — the API has always spoken
        ``page``/``per_page``, so the old arguments were silently dropped and
        every caller got page 1. When supplied they are translated
        (``page = skip // per_page + 1``) and a ``DeprecationWarning`` is raised.
        """
        page, per_page = self._page_params(page, per_page, skip, limit)
        params = {"page": page, "per_page": per_page}
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects", params=params)
        return self.client.request("GET", f"{_BASE}/projects", params=params)

    def get_project(self, project_id: str, include_chapters: bool = False) -> Dict[str, Any]:
        """
        Get a single project.

        Pass ``include_chapters=True`` to get the project's chapters inline (a
        ``chapters`` array) instead of a second call to :meth:`list_chapters`.
        """
        # Sent as a string: aiohttp rejects bool query values outright, and
        # FastAPI parses "true" to True on the other end.
        params = {"include_chapters": "true"} if include_chapters else None
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}", params=params)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}", params=params)

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project."""
        if self.async_mode:
            return self._async_request("DELETE", f"{_BASE}/projects/{project_id}")
        return self.client.request("DELETE", f"{_BASE}/projects/{project_id}")

    # --------------------------------------------------------------- manuscript
    def upload_manuscript(self, project_id: str, file: str) -> Dict[str, Any]:
        """Upload a manuscript file (PDF, EPUB, DOCX, or TXT). Returns a ``file_key``."""
        files = self._prepare_file_upload(file, field_name="file")
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/manuscript/upload", files=files)
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/manuscript/upload", files=files)

    def parse_manuscript(self, project_id: str, file_key: str, filename: str) -> Dict[str, Any]:
        """Parse an uploaded manuscript into chapters (async; returns a parse ``job_id``)."""
        # The endpoint takes form fields (not JSON); send them as multipart
        # fields via (None, value) tuples so the client emits multipart/form-data.
        files = {"file_key": (None, file_key), "filename": (None, filename)}
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/manuscript/parse", files=files)
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/manuscript/parse", files=files)

    def paste_text(self, project_id: str, text: str) -> Dict[str, Any]:
        """Add a manuscript by pasting raw text."""
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/manuscript/paste", json_data={"text": text})
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/manuscript/paste", json_data={"text": text})

    def generate_book(
        self,
        project_id: str,
        prompt: str,
        title: Optional[str] = None,
        audience: Optional[str] = None,
        tone: str = "warm",
        chapter_count: int = 3,
        words_per_chapter: int = 600,
    ) -> Dict[str, Any]:
        """Draft an original manuscript from a prompt, then chapter it."""
        body: Dict[str, Any] = {"prompt": prompt, "tone": tone,
                                "chapter_count": chapter_count, "words_per_chapter": words_per_chapter}
        if title is not None:
            body["title"] = title
        if audience is not None:
            body["audience"] = audience
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/manuscript/generate", json_data=body)
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/manuscript/generate", json_data=body)

    # ----------------------------------------------------------------- chapters
    def list_chapters(
        self,
        project_id: str,
        page: int = 1,
        per_page: int = 50,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List chapters in a project (paginated).

        ``page`` is 1-based; ``per_page`` is capped at 500 by the API.
        ``skip``/``limit`` are **deprecated** — see :meth:`list_projects`.
        """
        page, per_page = self._page_params(page, per_page, skip, limit)
        params = {"page": page, "per_page": per_page}
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/chapters", params=params)
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/chapters", params=params)

    def get_chapter(self, project_id: str, chapter_id: str) -> Dict[str, Any]:
        """Get a single chapter."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}")

    def update_chapter(self, project_id: str, chapter_id: str, **fields: Any) -> Dict[str, Any]:
        """Edit a chapter (``title``, ``content``, ``skip_narration``, ``voice_id``, ``narration_notes``)."""
        if self.async_mode:
            return self._async_request("PUT", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}", json_data=fields)
        return self.client.request("PUT", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}", json_data=fields)

    def regenerate_chapter(self, project_id: str, chapter_id: str) -> Dict[str, Any]:
        """Re-render a single chapter's audio (e.g. after an edit)."""
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}/regenerate")
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/chapters/{chapter_id}/regenerate")

    # --------------------------------------------------------------- paragraphs
    def list_paragraphs(
        self,
        project_id: str,
        chapter_id: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List a chapter's paragraphs, ordered by position.

        Pagination is optional: with ``page``/``per_page`` omitted the API
        returns every paragraph in the chapter.
        """
        params: Dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        path = f"{_BASE}/projects/{project_id}/chapters/{chapter_id}/paragraphs"
        if self.async_mode:
            return self._async_request("GET", path, params=params or None)
        return self.client.request("GET", path, params=params or None)

    def narrate_paragraph(self, project_id: str, paragraph_id: str, **options: Any) -> Dict[str, Any]:
        """
        Generate (or regenerate) audio for a single paragraph; records a take.

        Options: ``voice_id``, ``text_override``, ``narration_speed``,
        ``narration_style``, ``emotion``, ``character_name``, ``direction``.
        Returns the queued ``task_id`` plus a ``billing`` breakdown (first take
        billed, first regen free). Raises on 402 when credits are short and on
        409 when the paragraph is locked.
        """
        body = {k: v for k, v in options.items() if v is not None}
        path = f"{_BASE}/projects/{project_id}/paragraphs/{paragraph_id}/narrate"
        if self.async_mode:
            return self._async_request("POST", path, json_data=body)
        return self.client.request("POST", path, json_data=body)

    def batch_narrate(
        self,
        project_id: str,
        voice_id: Optional[int] = None,
        chapter_ids: Optional[List[str]] = None,
        paragraph_ids: Optional[List[str]] = None,
        include_completed: bool = False,
        include_locked: bool = False,
        include_skipped: bool = False,
        narration_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Queue one job that narrates the selected paragraphs sequentially.

        With both ``chapter_ids`` and ``paragraph_ids`` omitted the whole
        project is narrated. Already-completed, locked and skip-flagged
        paragraphs are excluded unless the matching ``include_*`` flag is set.
        Returns ``job_id``, ``total_paragraphs`` and ``skipped_paragraphs``.
        """
        body: Dict[str, Any] = {
            "include_completed": include_completed,
            "include_locked": include_locked,
            "include_skipped": include_skipped,
            "narration_settings": narration_settings or {},
        }
        if voice_id is not None:
            body["voice_id"] = voice_id
        if chapter_ids is not None:
            body["chapter_ids"] = chapter_ids
        if paragraph_ids is not None:
            body["paragraph_ids"] = paragraph_ids
        path = f"{_BASE}/projects/{project_id}/narration/batch"
        if self.async_mode:
            return self._async_request("POST", path, json_data=body)
        return self.client.request("POST", path, json_data=body)

    # ------------------------------------------------------------------- voices
    def list_voices(self) -> Dict[str, Any]:
        """List narration voices (``available_voices``, ``recommended_voices``, ``user_custom_voices``)."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/voices/available")
        return self.client.request("GET", f"{_BASE}/voices/available")

    def list_languages(self) -> Dict[str, Any]:
        """List supported narration languages."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/voices/languages")
        return self.client.request("GET", f"{_BASE}/voices/languages")

    def cost_estimate(self, project_id: str) -> Dict[str, Any]:
        """Per-paragraph cost breakdown for a project before narrating."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/cost-estimate")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/cost-estimate")

    # ----------------------------------------------------------------- narration
    def start_narration(
        self,
        project_id: str,
        voice_id: int,
        chapter_ids: Optional[List[str]] = None,
        narration_speed: float = 1.0,
        narration_style: str = "narrative",
    ) -> Dict[str, Any]:
        """Queue narration for all chapters (or ``chapter_ids``) without waiting.

        Posts to ``/narration/batch``. The older ``/narration/start`` route was
        retired (PLAT-2087) because it bypassed metering entirely, and now
        returns 410 Gone unconditionally — so every call through this method,
        including :meth:`produce`, used to fail outright.

        ``batch`` narrates the whole project when no ``chapter_ids`` are given,
        which is what this method has always meant.
        """
        body: Dict[str, Any] = {
            "voice_id": voice_id,
            # The batch worker reads speed/style out of narration_settings under
            # the SHORT keys "speed"/"style" — passing narration_speed /
            # narration_style here would be accepted and then silently dropped.
            "narration_settings": {
                "speed": narration_speed,
                "style": narration_style,
            },
        }
        if chapter_ids is not None:
            body["chapter_ids"] = chapter_ids
        path = f"{_BASE}/projects/{project_id}/narration/batch"
        if self.async_mode:
            return self._async_request("POST", path, json_data=body)
        return self.client.request("POST", path, json_data=body)

    def narration_progress(self, project_id: str) -> Dict[str, Any]:
        """Current narration progress (``total_chapters``, ``completed_chapters``, ``failed_chapters``)."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/narration/progress")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/narration/progress")

    def narrate(
        self,
        project_id: str,
        voice_id: int,
        chapter_ids: Optional[List[str]] = None,
        narration_speed: float = 1.0,
        narration_style: str = "narrative",
        wait_for_completion: bool = True,
        timeout: int = 1800,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Narrate the project. Waits for all chapters by default."""
        started = self.start_narration(project_id, voice_id, chapter_ids, narration_speed, narration_style)
        if not wait_for_completion:
            return started
        return self.wait_for_narration(project_id, timeout=timeout, poll_interval=poll_interval)

    def wait_for_narration(self, project_id: str, timeout: int = 1800, poll_interval: int = 5) -> Dict[str, Any]:
        """Block until narration finishes (``completed + failed >= total``)."""
        start = time.time()
        while time.time() - start < timeout:
            p = self.client.request("GET", f"{_BASE}/projects/{project_id}/narration/progress")
            total = p.get("total_chapters", 0)
            if total and p.get("completed_chapters", 0) + p.get("failed_chapters", 0) >= total:
                return p
            time.sleep(poll_interval)
        raise TimeoutError(f"Narration for {project_id} did not finish within {timeout}s")

    # -------------------------------------------------------------------- export
    def start_export(self, project_id: str, include_chapters: Optional[List[str]] = None) -> Dict[str, Any]:
        """Start an ACX export (runs a compliance check). Returns a ``job_id`` + ``compliance_check``."""
        body: Dict[str, Any] = {}
        if include_chapters is not None:
            body["include_chapters"] = include_chapters
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/export", json_data=body)
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/export", json_data=body)

    def export_status(self, project_id: str, job_id: int) -> Dict[str, Any]:
        """Status of an export job."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/export/{job_id}/status")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/export/{job_id}/status")

    def export(
        self,
        project_id: str,
        include_chapters: Optional[List[str]] = None,
        wait_for_completion: bool = True,
        timeout: int = 600,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """Export an ACX package. Waits for completion by default; returns the export job (with ``job_id``)."""
        started = self.start_export(project_id, include_chapters)
        job_id = started.get("job_id")
        if not wait_for_completion or job_id is None:
            return started
        self.wait_for_export(project_id, job_id, timeout=timeout, poll_interval=poll_interval)
        return started

    def wait_for_export(self, project_id: str, job_id: int, timeout: int = 600, poll_interval: int = 5) -> Dict[str, Any]:
        """Block until an export job reaches ``COMPLETED`` (raises on failure)."""
        start = time.time()
        while time.time() - start < timeout:
            s = self.client.request("GET", f"{_BASE}/projects/{project_id}/export/{job_id}/status")
            status = str(s.get("status", "")).upper()
            if status in ("COMPLETED", "SUCCESS", "DONE"):
                return s
            if status in ("FAILED", "ERROR"):
                raise Exception(f"Export {job_id} failed: {s.get('error') or s}")
            time.sleep(poll_interval)
        raise TimeoutError(f"Export {job_id} did not finish within {timeout}s")

    def download(self, project_id: str, job_id: int) -> Dict[str, Any]:
        """Get the ACX package manifest, including a presigned ``download_url`` to the ZIP."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/export/{job_id}/download")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/export/{job_id}/download")

    # ----------------------------------------------------------------- one-call
    def produce(
        self,
        title: str,
        voice_id: int,
        file: Optional[str] = None,
        text: Optional[str] = None,
        author: Optional[str] = None,
        narration_speed: float = 1.0,
        narration_style: str = "narrative",
        timeout: int = 1800,
        poll_interval: int = 5,
    ) -> Dict[str, Any]:
        """
        Run the whole pipeline and return the ACX package manifest.

        Provide a manuscript via ``file`` (PDF/EPUB/DOCX/TXT) or ``text``.
        Creates a project, ingests + parses the manuscript, narrates with
        ``voice_id``, exports an ACX package, and returns its ``download_url``.
        """
        if not file and not text:
            raise ValueError("Provide either file= or text=")

        project = self.create_project(title=title, author=author)
        pid = project["id"]

        if file:
            up = self.upload_manuscript(pid, file=file)
            filename = file.split("/")[-1]
            self.parse_manuscript(pid, up["file_key"], filename)
            self._wait_for_chapters(pid, timeout=timeout, poll_interval=poll_interval)
        else:
            self.paste_text(pid, text=text)
            self._wait_for_chapters(pid, timeout=timeout, poll_interval=poll_interval)

        self.narrate(pid, voice_id=voice_id, narration_speed=narration_speed,
                     narration_style=narration_style, wait_for_completion=True,
                     timeout=timeout, poll_interval=poll_interval)
        export = self.export(pid, wait_for_completion=True, timeout=timeout, poll_interval=poll_interval)
        manifest = self.download(pid, export["job_id"])
        return {"project_id": pid, "export_job_id": export["job_id"],
                "compliance_check": export.get("compliance_check"), **manifest}

    # -------------------------------------------------------------- parse status
    def wait_for_parse(self, project_id: str, timeout: int = 600, poll_interval: int = 3) -> Dict[str, Any]:
        """
        Block until the project's manuscript has finished parsing; returns the project.

        ``/manuscript/parse`` is asynchronous and has no status endpoint of its
        own — the project row carries the state (``status``,
        ``parsing_completed_at``, ``error_message``). Raises
        :class:`~audiopod.exceptions.APIError` as soon as the parse fails
        (instead of polling on until timeout), and ``TimeoutError`` — naming the
        last state seen — if it never settles.
        """
        if self.async_mode:
            return self._async_wait_for_parse(project_id, timeout, poll_interval)

        start = time.time()
        project: Dict[str, Any] = {}
        while time.time() - start < timeout:
            project = self.client.request("GET", f"{_BASE}/projects/{project_id}")
            if self._parse_finished(project_id, project):
                return project
            time.sleep(poll_interval)
        raise TimeoutError(self._parse_timeout_message(project_id, project, timeout))

    async def _async_wait_for_parse(self, project_id: str, timeout: int, poll_interval: int) -> Dict[str, Any]:
        import asyncio

        start = time.time()
        project: Dict[str, Any] = {}
        while time.time() - start < timeout:
            project = await self.client.request("GET", f"{_BASE}/projects/{project_id}")
            if self._parse_finished(project_id, project):
                return project
            await asyncio.sleep(poll_interval)
        raise TimeoutError(self._parse_timeout_message(project_id, project, timeout))

    @staticmethod
    def _parse_finished(project_id: str, project: Dict[str, Any]) -> bool:
        """True once parsing has completed. Raises ``APIError`` if it failed."""
        status = str(project.get("status") or "").lower()
        error = project.get("error_message")
        if error:
            raise APIError(f"Manuscript parsing failed for project {project_id}: {error}")
        if status in _PARSE_FAILED_STATUSES:
            raise APIError(
                f"Manuscript parsing failed for project {project_id} (status={status or 'unknown'})"
            )
        if status in _PARSE_PENDING_STATUSES:
            return False
        return project.get("parsing_completed_at") is not None

    @staticmethod
    def _parse_timeout_message(project_id: str, project: Dict[str, Any], timeout: int) -> str:
        return (
            f"Manuscript for {project_id} did not finish parsing within {timeout}s "
            f"(last seen status={project.get('status') or 'unknown'}, "
            f"parsing_completed_at={project.get('parsing_completed_at')})"
        )

    def _wait_for_chapters(self, project_id: str, timeout: int = 600, poll_interval: int = 3) -> List[Dict[str, Any]]:
        """Wait for parsing to finish, then return the project's chapters.

        Kept for backwards compatibility; :meth:`wait_for_parse` is the public
        entry point and does the actual waiting (it fails fast on a parse error
        instead of spinning until timeout).
        """
        self.wait_for_parse(project_id, timeout=timeout, poll_interval=poll_interval)
        data = self.client.request(
            "GET", f"{_BASE}/projects/{project_id}/chapters", params={"page": 1, "per_page": 50}
        )
        chapters = data.get("chapters") or data.get("items") or (data if isinstance(data, list) else [])
        if not chapters:
            raise APIError(f"Manuscript for {project_id} parsed but produced no chapters")
        return chapters

    # ------------------------------------------------------------------- helpers
    @staticmethod
    def _page_params(
        page: int, per_page: int, skip: Optional[int], limit: Optional[int]
    ) -> Tuple[int, int]:
        """Normalize the deprecated ``skip``/``limit`` pair onto ``page``/``per_page``."""
        if limit is not None:
            warnings.warn(
                "limit= is deprecated and was never honoured by the API; use per_page=",
                DeprecationWarning,
                stacklevel=3,
            )
            per_page = limit
        if skip is not None:
            warnings.warn(
                "skip= is deprecated and was never honoured by the API; use page= "
                "(1-based). Translating skip -> page.",
                DeprecationWarning,
                stacklevel=3,
            )
            page = (skip // per_page) + 1 if per_page else 1
        return page, per_page

    def _async_request(self, method: str, path: str, **kwargs: Any):
        """Async passthrough mirroring the sync ``client.request`` (await the result)."""
        return self.client.request(method, path, **kwargs)
