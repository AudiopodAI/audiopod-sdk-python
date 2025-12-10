"""
Base Service Class
"""

import time
from typing import Any, Dict, Optional, Tuple, BinaryIO


class BaseService:
    """Base class for all services"""

    def __init__(self, client: Any, async_mode: bool = False):
        self.client = client
        self.async_mode = async_mode

    def _prepare_file_upload(
        self, file_path: str, field_name: str = "file"
    ) -> Dict[str, Tuple[str, BinaryIO, str]]:
        """Prepare file for upload."""
        import mimetypes

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        file_handle = open(file_path, "rb")
        filename = file_path.split("/")[-1]

        return {field_name: (filename, file_handle, mime_type)}

    def _wait_for_completion(
        self, job_id: int, timeout: int = 900, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Wait for job completion."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            response = self.client.request("GET", f"/api/v1/jobs/{job_id}")

            status = response.get("status", "").upper()
            if status == "COMPLETED":
                return response
            elif status in ["FAILED", "ERROR"]:
                raise Exception(f"Job failed: {response.get('error_message', 'Unknown error')}")

            time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

    async def _async_wait_for_completion(
        self, job_id: int, timeout: int = 900, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Async wait for job completion."""
        import asyncio

        start_time = time.time()

        while time.time() - start_time < timeout:
            response = await self.client.request("GET", f"/api/v1/jobs/{job_id}")

            status = response.get("status", "").upper()
            if status == "COMPLETED":
                return response
            elif status in ["FAILED", "ERROR"]:
                raise Exception(f"Job failed: {response.get('error_message', 'Unknown error')}")

            await asyncio.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

