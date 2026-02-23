"""
Video Service - Video generation

API Routes:
- POST /api/v2/video/karaoke      - Create karaoke video
- POST /api/v2/video/music-video  - Create AI music video
- POST /api/v2/video/lyric-video  - Create lyric video
- GET  /api/v2/video/{id}         - Get job status
- GET  /api/v2/video/{id}/download - Get download URLs
- DELETE /api/v2/video/{id}       - Delete job
"""

from typing import Optional, Dict, Any, List, Literal
from .base import BaseService


VideoType = Literal["karaoke", "music_video", "lyric_video"]
AspectRatio = Literal["16:9", "9:16", "1:1"]
SceneGeneration = Literal["flux", "veo3", "static"]
AnimationStyle = Literal["typewriter", "fade-word", "slide-up", "bounce", "wave", "zoom"]


class VideoService(BaseService):
    """Service for video generation."""

    def create_karaoke(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        aspect_ratio: AspectRatio = "16:9",
        scene_generation: SceneGeneration = "flux",
        key_shift: int = 0,
        style: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Create a karaoke video from audio.

        Args:
            audio_file: Path to local audio file
            url: URL of audio/video (YouTube, etc.)
            aspect_ratio: Video aspect ratio
            scene_generation: Background generation method
            key_shift: Pitch shift in semitones (-12 to 12)
            style: Style configuration (colors, font, etc.)
            webhook_url: URL for completion notification
            wait_for_completion: Wait for video to finish
            timeout: Max wait time in seconds

        Returns:
            Job dict with id, status, video_url (when completed)
        """
        if audio_file:
            return self._create_from_upload(
                "karaoke", audio_file, aspect_ratio, scene_generation,
                key_shift, webhook_url, wait_for_completion, timeout
            )
        
        data = {
            "audio_url": url,
            "aspect_ratio": aspect_ratio,
            "scene_generation": scene_generation,
            "key_shift": key_shift,
        }
        if style:
            data["style"] = style
        if webhook_url:
            data["webhook_url"] = webhook_url

        if self.async_mode:
            return self._async_create("karaoke", data, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v2/video/karaoke", json_data=data)
        
        if wait_for_completion:
            return self._wait_for_video(response["id"], timeout)
        return response

    def create_music_video(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        music_job_id: Optional[str] = None,
        aspect_ratio: AspectRatio = "16:9",
        scene_generation: SceneGeneration = "flux",
        scene_count: int = 10,
        include_lyrics: bool = True,
        style: Optional[Dict[str, Any]] = None,
        webhook_url: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 900,
    ) -> Dict[str, Any]:
        """
        Create an AI music video.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            music_job_id: AudioPod music generation job ID
            aspect_ratio: Video aspect ratio
            scene_generation: Scene generation method (flux or veo3)
            scene_count: Number of scenes to generate (5-20)
            include_lyrics: Overlay lyrics on video
            style: Style configuration
            webhook_url: URL for completion notification
            wait_for_completion: Wait for video to finish
            timeout: Max wait time in seconds

        Returns:
            Job dict with video_url when completed
        """
        data = {
            "aspect_ratio": aspect_ratio,
            "scene_generation": scene_generation,
            "scene_count": scene_count,
            "include_lyrics": include_lyrics,
        }
        if url:
            data["audio_url"] = url
        if music_job_id:
            data["music_job_id"] = music_job_id
        if style:
            data["style"] = style
        if webhook_url:
            data["webhook_url"] = webhook_url

        if self.async_mode:
            return self._async_create("music-video", data, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v2/video/music-video", json_data=data)
        
        if wait_for_completion:
            return self._wait_for_video(response["id"], timeout)
        return response

    def create_lyric_video(
        self,
        audio_file: Optional[str] = None,
        url: Optional[str] = None,
        lyrics: Optional[str] = None,
        aspect_ratio: AspectRatio = "16:9",
        animation_style: AnimationStyle = "fade-word",
        background_color: str = "#1a1a2e",
        accent_color: str = "#e94560",
        particles_enabled: bool = True,
        background_image_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        wait_for_completion: bool = False,
        timeout: int = 600,
    ) -> Dict[str, Any]:
        """
        Create a kinetic typography lyric video.

        Args:
            audio_file: Path to local audio file
            url: URL of audio file
            lyrics: Custom lyrics (auto-transcribed if not provided)
            aspect_ratio: Video aspect ratio
            animation_style: Text animation style
            background_color: Background color
            accent_color: Accent/highlight color
            particles_enabled: Enable particle effects
            background_image_url: Optional background image
            webhook_url: URL for completion notification
            wait_for_completion: Wait for video to finish
            timeout: Max wait time in seconds

        Returns:
            Job dict with video_url when completed
        """
        data = {
            "aspect_ratio": aspect_ratio,
            "style": {
                "animation_style": animation_style,
                "background_color": background_color,
                "accent_color": accent_color,
                "particles_enabled": particles_enabled,
            },
        }
        if url:
            data["audio_url"] = url
        if lyrics:
            data["lyrics"] = lyrics
        if background_image_url:
            data["background_image_url"] = background_image_url
        if webhook_url:
            data["webhook_url"] = webhook_url

        if self.async_mode:
            return self._async_create("lyric-video", data, wait_for_completion, timeout)

        response = self.client.request("POST", "/api/v2/video/lyric-video", json_data=data)
        
        if wait_for_completion:
            return self._wait_for_video(response["id"], timeout)
        return response

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get video job status."""
        if self.async_mode:
            return self._async_get_job(job_id)
        return self.client.request("GET", f"/api/v2/video/{job_id}")

    async def _async_get_job(self, job_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v2/video/{job_id}")

    def get_download_urls(self, job_id: str) -> Dict[str, Any]:
        """Get download URLs for completed video."""
        if self.async_mode:
            return self._async_get_download(job_id)
        return self.client.request("GET", f"/api/v2/video/{job_id}/download")

    async def _async_get_download(self, job_id: str) -> Dict[str, Any]:
        return await self.client.request("GET", f"/api/v2/video/{job_id}/download")

    def delete_job(self, job_id: str) -> Dict[str, str]:
        """Delete a video job."""
        if self.async_mode:
            return self._async_delete(job_id)
        return self.client.request("DELETE", f"/api/v2/video/{job_id}")

    async def _async_delete(self, job_id: str) -> Dict[str, str]:
        return await self.client.request("DELETE", f"/api/v2/video/{job_id}")

    def list_jobs(
        self,
        video_type: Optional[VideoType] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List video jobs."""
        params = {"limit": limit, "offset": offset}
        if video_type:
            params["type"] = video_type
        
        if self.async_mode:
            return self._async_list(params)
        return self.client.request("GET", "/api/v2/video/", params=params)

    async def _async_list(self, params: Dict) -> Dict[str, Any]:
        return await self.client.request("GET", "/api/v2/video/", params=params)

    def _create_from_upload(
        self,
        video_type: str,
        audio_file: str,
        aspect_ratio: str,
        scene_generation: str,
        key_shift: int,
        webhook_url: Optional[str],
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        """Create video from file upload."""
        data = {
            "aspect_ratio": aspect_ratio,
            "scene_generation": scene_generation,
            "key_shift": str(key_shift),
        }
        if webhook_url:
            data["webhook_url"] = webhook_url

        files = self._prepare_file_upload(audio_file, "file")
        
        response = self.client.request(
            "POST", f"/api/v2/video/{video_type}/upload", data=data, files=files
        )
        
        if wait_for_completion:
            return self._wait_for_video(response["id"], timeout)
        return response

    async def _async_create(
        self,
        endpoint: str,
        data: Dict,
        wait_for_completion: bool,
        timeout: int,
    ) -> Dict[str, Any]:
        response = await self.client.request(
            "POST", f"/api/v2/video/{endpoint}", json_data=data
        )
        if wait_for_completion:
            return await self._async_wait_for_video(response["id"], timeout)
        return response

    def _wait_for_video(self, job_id: str, timeout: int) -> Dict[str, Any]:
        """Wait for video job completion."""
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            job = self.get_job(job_id)
            status = job.get("status", "")
            
            if status == "completed":
                # Get download URLs
                download = self.get_download_urls(job_id)
                job.update(download)
                return job
            elif status == "failed":
                raise Exception(f"Video generation failed: {job.get('error', 'Unknown')}")
            
            time.sleep(5)
        
        raise TimeoutError(f"Video {job_id} timed out after {timeout}s")

    async def _async_wait_for_video(self, job_id: str, timeout: int) -> Dict[str, Any]:
        """Async wait for video job completion."""
        import asyncio
        import time
        start = time.time()
        
        while time.time() - start < timeout:
            job = await self.get_job(job_id)
            status = job.get("status", "")
            
            if status == "completed":
                download = await self.get_download_urls(job_id)
                job.update(download)
                return job
            elif status == "failed":
                raise Exception(f"Video generation failed: {job.get('error', 'Unknown')}")
            
            await asyncio.sleep(5)
        
        raise TimeoutError(f"Video {job_id} timed out after {timeout}s")
