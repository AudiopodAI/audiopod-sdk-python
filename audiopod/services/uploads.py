"""Single-PUT upload sessions; server admission owns measured duration."""
import aiohttp
import requests
from .base import BaseService
from ..workflow_contracts import PresignUpload, PresignedUpload, UploadLimits


def _no_auth(request):
    return request


def _storage_headers(upload):
    return {key: value for key, value in upload["headers"].items()
            if key.lower() not in {"authorization", "x-api-key"}}


class UploadsService(BaseService):
    def limits(self, service: str = "dubbing") -> UploadLimits:
        return self.client.request("GET","/api/v1/uploads/limits",params={"service":service})

    def presign(self, body: PresignUpload) -> PresignedUpload:
        return self.client.request("POST","/api/v1/uploads/presign",json_data=body)

    def put(self, upload: PresignedUpload, file_path: str):
        if upload["method"] != "PUT": raise ValueError("Unsupported presigned upload method")
        if self.async_mode: return self._async_put(upload,file_path)
        # A fresh transport has no API Authorization/X-API-Key and no redirects.
        with open(file_path,"rb") as stream:
            response = requests.put(upload["url"],data=stream,headers=_storage_headers(upload),auth=_no_auth,allow_redirects=False,
                timeout=self.client.config.timeout,verify=self.client.config.verify_ssl)
            response.raise_for_status()
            if not 200 <= response.status_code < 300: raise RuntimeError("Upload was redirected")
            return {"upload_session_id":upload["upload_id"],"etag":response.headers.get("ETag")}

    async def _async_put(self, upload, file_path):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.client.config.timeout)) as session:
            with open(file_path,"rb") as stream:
                async with session.put(upload["url"],data=stream,headers=_storage_headers(upload),allow_redirects=False,
                    ssl=self.client.config.verify_ssl) as response:
                    response.raise_for_status()
                    if not 200 <= response.status < 300: raise RuntimeError("Upload was redirected")
                    return {"upload_session_id":upload["upload_id"],"etag":response.headers.get("ETag")}
