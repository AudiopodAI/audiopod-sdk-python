"""
Audiobook Service - Turn a manuscript into a finished, ACX-compliant audiobook.

The full pipeline, end to end: create a project, add a manuscript (upload a
PDF/EPUB, paste text, or generate from a prompt), narrate it, export an
ACX-compliant package, and download it. Use :meth:`AudiobookService.produce`
for the whole flow in one call, or drive each step yourself.
"""

import time
from typing import Any, Dict, List, Optional

from .base import BaseService

_BASE = "/api/v1/audiobook"


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

    def list_projects(self, skip: int = 0, limit: int = 20) -> Dict[str, Any]:
        """List your audiobook projects (paginated)."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects", params={"skip": skip, "limit": limit})
        return self.client.request("GET", f"{_BASE}/projects", params={"skip": skip, "limit": limit})

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get a single project."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}")
        return self.client.request("GET", f"{_BASE}/projects/{project_id}")

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
    def list_chapters(self, project_id: str, skip: int = 0, limit: int = 50) -> Dict[str, Any]:
        """List chapters in a project."""
        if self.async_mode:
            return self._async_request("GET", f"{_BASE}/projects/{project_id}/chapters", params={"skip": skip, "limit": limit})
        return self.client.request("GET", f"{_BASE}/projects/{project_id}/chapters", params={"skip": skip, "limit": limit})

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
        """Queue narration for all chapters (or ``chapter_ids``) without waiting."""
        body: Dict[str, Any] = {"voice_id": voice_id, "narration_speed": narration_speed,
                                "narration_style": narration_style}
        if chapter_ids is not None:
            body["chapter_ids"] = chapter_ids
        if self.async_mode:
            return self._async_request("POST", f"{_BASE}/projects/{project_id}/narration/start", json_data=body)
        return self.client.request("POST", f"{_BASE}/projects/{project_id}/narration/start", json_data=body)

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

    def _wait_for_chapters(self, project_id: str, timeout: int = 600, poll_interval: int = 3) -> List[Dict[str, Any]]:
        start = time.time()
        while time.time() - start < timeout:
            data = self.client.request("GET", f"{_BASE}/projects/{project_id}/chapters", params={"skip": 0, "limit": 50})
            chapters = data.get("chapters") or data.get("items") or (data if isinstance(data, list) else [])
            if chapters:
                return chapters
            time.sleep(poll_interval)
        raise TimeoutError(f"Manuscript for {project_id} did not parse within {timeout}s")

    # ------------------------------------------------------------------- helpers
    def _async_request(self, method: str, path: str, **kwargs: Any):
        """Async passthrough mirroring the sync ``client.request`` (await the result)."""
        return self.client.request(method, path, **kwargs)
