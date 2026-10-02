"""Reviewed localization; quotes and required user decisions never start work."""
import asyncio
import time
from typing import Dict, List, Optional
from urllib.parse import quote

from .base import BaseService
from .. import workflow_contracts as C
from ..exceptions import APIError
from ..workflow_utils import canonical_uuid as uuid, uuid_fields

BASE = "/api/v1/dubbing"


def resource(kind, identifier, tail=""):
    return BASE + "/" + kind + "/" + uuid(identifier) + tail


def token_path(token, tail=""):
    return BASE + "/reviews/" + quote(token, safe="") + tail


class DubbingService(BaseService):
    def _call(self, method, path, **kwargs):
        return self.client.request(method, path, **kwargs)

    def capabilities(self) -> C.DubbingCapabilities:
        return self._call("GET", BASE + "/capabilities")

    def adopt_source(self, upload_session_id: str) -> C.DubbingSource:
        return self._call("POST", BASE + "/sources", json_data={"upload_session_id":uuid(upload_session_id)})

    def get_source(self, source_id: str) -> C.DubbingSource:
        return self._call("GET", resource("sources",source_id))

    def source_media(self, source_id: str) -> bytes:
        return self.client.request_bytes(resource("sources",source_id,"/media"))

    def create_project(self, body: C.CreateDubbingProject) -> C.DubbingProject:
        return self._call("POST",BASE+"/projects",json_data=uuid_fields(body))

    def list_projects(self, *, folder_id=None, unfiled=False, review=None, completion=None) -> Dict[str,List[C.DubbingProject]]:
        params = {"unfiled":unfiled}
        if folder_id is not None: params["folder_id"] = uuid(folder_id)
        if review is not None: params["review"] = review
        if completion is not None: params["completion"] = completion
        return self._call("GET",BASE+"/projects",params=params)

    def get_project(self, project_id: str) -> C.DubbingProject:
        return self._call("GET",resource("projects",project_id))

    def delete_project(self, project_id: str) -> C.DubbingProjectDeleted:
        return self._call("DELETE",resource("projects",project_id))

    def project_voices(self, project_id: str) -> Dict:
        return self._call("GET",resource("projects",project_id,"/voices"))

    def create_edition(self, project_id: str, body: C.CreateDubbingEdition) -> C.DubbingEdition:
        return self._call("POST",resource("projects",project_id,"/editions"),json_data=body)

    def get_edition(self, edition_id: str) -> C.DubbingEdition:
        return self._call("GET",resource("editions",edition_id))

    def save_edition(self, edition_id: str, body: C.SaveDubbingEdition) -> C.DubbingEdition:
        return self._call("PUT",resource("editions",edition_id),json_data=body)

    def quote(self, edition_id: str, *, retranslate=False) -> C.DubbingQuote:
        return self._call("GET",resource("editions",edition_id,"/quote"),params={"retranslate":str(retranslate).lower()})

    def analyze(self, project_id: str, body: C.AnalyzeDubbing) -> Dict[str,List[C.DubbingJob]]:
        if body.get("confirm") is not True: raise ValueError("Explicit confirmation is required")
        payload = {**body,"confirmations":[uuid_fields(item) for item in body["confirmations"]]}
        return self._call("POST",resource("projects",project_id,"/analyze"),json_data=payload)

    def get_job(self, job_id: str) -> C.DubbingJob:
        return self._call("GET",resource("jobs",job_id))

    def generate(self, job_id: str, body: C.GenerateDubbing) -> C.DubbingJob:
        if body.get("confirm") is not True: raise ValueError("Explicit confirmation is required")
        return self._call("POST",resource("jobs",job_id,"/generate"),json_data=body)

    def retranslate(self, job_id: str, body: C.GenerateDubbing) -> C.DubbingJob:
        if body.get("confirm") is not True: raise ValueError("Explicit confirmation is required")
        return self._call("POST",resource("jobs",job_id,"/retranslate"),json_data=body)

    def cancel(self, job_id: str) -> C.DubbingJob:
        return self._call("POST",resource("jobs",job_id,"/cancel"))

    def retry_exports(self, job_id: str) -> C.DubbingJob:
        return self._call("POST",resource("jobs",job_id,"/retry-exports"))

    def events(self, job_id: str, after: int = 0) -> Dict[str,List[C.DubbingEvent]]:
        return self._call("GET",resource("jobs",job_id,"/events"),params={"after":after})

    def artifact(self, job_id: str, kind: C.DubbingOutput) -> bytes:
        return self.client.request_bytes(resource("jobs",job_id,"/artifacts/"+quote(kind,safe="")))

    def review_complete(self, edition_id: str, expected_revision: int) -> C.DubbingEdition:
        return self._call("POST",resource("editions",edition_id,"/review-complete"),json_data={"expected_revision":expected_revision})

    def list_folders(self) -> Dict[str,List[C.DubbingFolder]]:
        return self._call("GET",BASE+"/folders")

    def create_folder(self, label: str, kind: str = "client") -> C.DubbingFolder:
        return self._call("POST",BASE+"/folders",json_data={"label":label,"kind":kind})

    def rename_folder(self, folder_id: str, label: str, kind: str = "client") -> C.DubbingFolder:
        return self._call("PUT",resource("folders",folder_id),json_data={"label":label,"kind":kind})

    def delete_folder(self, folder_id: str) -> Dict:
        return self._call("DELETE",resource("folders",folder_id))

    def move_project(self, project_id: str, folder_id: Optional[str]) -> C.DubbingProject:
        return self._call("PUT",resource("projects",project_id,"/folder"),json_data={"folder_id":uuid(folder_id) if folder_id else None})

    @staticmethod
    def _glossary_scope(language, project_id):
        return {"language":language,**({"project_id":uuid(project_id)} if project_id is not None else {})}

    def get_glossary(self, language: str, project_id: Optional[str] = None) -> C.DubbingGlossary:
        return self._call("GET",BASE+"/glossary",params=self._glossary_scope(language,project_id))

    def set_glossary(self, language: str, body: C.GlossaryWrite, project_id: Optional[str] = None) -> C.DubbingGlossary:
        return self._call("PUT",BASE+"/glossary",params=self._glossary_scope(language,project_id),json_data=body)

    def reset_glossary(self, language: str, expected_version: int, project_id: Optional[str] = None) -> C.DubbingGlossary:
        return self._call("DELETE",BASE+"/glossary",params={**self._glossary_scope(language,project_id),"expected_version":expected_version})

    def list_templates(self) -> Dict[str,List[C.DubbingTemplate]]:
        return self._call("GET",BASE+"/templates")

    def save_template(self, job_id: str, label: str) -> C.DubbingTemplate:
        return self._call("POST",BASE+"/templates/from-job",json_data={"job_id":uuid(job_id),"label":label})

    def from_template(self, body: C.ProjectFromTemplate) -> C.DubbingProject:
        return self._call("POST",BASE+"/projects/from-template",json_data=uuid_fields(body))

    def invite_reviewer(self, edition_id: str, recipient_email: str) -> C.DubbingReviewGrant:
        return self._call("POST",resource("editions",edition_id,"/review-grants"),json_data={"recipient_email":recipient_email})

    def list_review_grants(self, edition_id: str) -> Dict[str,List[C.DubbingReviewGrant]]:
        return self._call("GET",resource("editions",edition_id,"/review-grants"))

    def revoke_review_grant(self, grant_id: str) -> Dict:
        return self._call("DELETE",resource("review-grants",grant_id))

    def get_review(self, token: str) -> C.DubbingReview:
        return self._call("GET",token_path(token))

    def add_comment(self, token: str, body: C.WriteDubbingComment) -> C.DubbingComment:
        return self._call("POST",token_path(token,"/comments"),json_data=body)

    def approve_review(self, token: str, expected_revision: int) -> Dict:
        return self._call("POST",token_path(token,"/approve"),json_data={"expected_revision":expected_revision})

    def list_review_comments(self, edition_id: str) -> Dict[str,List[C.DubbingComment]]:
        return self._call("GET",resource("editions",edition_id,"/review-comments"))

    def review_media(self, grant_id: str, kind: C.DubbingOutput) -> bytes:
        return self.client.request_bytes(BASE+"/reviews/media/"+uuid(grant_id)+"/"+quote(kind,safe=""))

    @staticmethod
    def _wait_result(job):
        if job["status"] in ("completed","review_required","export_partial"): return True
        if job["status"] in ("failed","cancelled","expired"):
            raise APIError(job.get("error_code") or "Dubbing "+job["status"], detail={"code":job.get("error_code"),"job":job})
        return False

    def wait_for_job(self, job_id: str, timeout: float = 300, poll_interval: float = 2) -> C.DubbingJob:
        if self.async_mode: return self._async_wait(job_id,timeout,poll_interval)
        started = time.monotonic()
        while True:
            job = self.get_job(job_id)
            if self._wait_result(job): return job
            if time.monotonic()-started >= timeout:
                raise APIError("Timed out waiting for dubbing job "+job_id,
                    detail={"code":"wait_timeout","action":"poll_job","job":job})
            time.sleep(poll_interval)

    async def _async_wait(self, job_id, timeout, poll_interval):
        started = time.monotonic()
        while True:
            job = await self.get_job(job_id)
            if self._wait_result(job): return job
            if time.monotonic()-started >= timeout:
                raise APIError("Timed out waiting for dubbing job "+job_id,
                    detail={"code":"wait_timeout","action":"poll_job","job":job})
            await asyncio.sleep(poll_interval)
