"""Video service for generating video clips using Creatomate REST API."""

import logging
from typing import Any, Optional

import httpx

from src.models.script import PodcastScript
from src.utils.errors import CreatomateAPIError, VideoServiceError
from src.utils.retry import with_retry

logger = logging.getLogger(__name__)

# Creatomate API endpoint
CREATOMATE_API_URL = "https://api.creatomate.com/v2/renders"


class VideoService:
    """Service for generating video clips using Creatomate REST API."""

    def __init__(
        self,
        creatomate_api_key: str,
        template_id: str,
        supabase_client: Optional[Any] = None,
    ) -> None:
        """
        Initialize the VideoService.

        Args:
            creatomate_api_key: API key for Creatomate service
            template_id: Creatomate template ID for video generation
            supabase_client: Supabase client for storage (optional)
        """
        self.api_key = creatomate_api_key
        self.template_id = template_id
        self.supabase = supabase_client
        self.api_url = CREATOMATE_API_URL

    def _build_render_payload(self, hook: str, audio_url: str) -> dict[str, Any]:
        """
        Construct API request payload for Creatomate.

        Args:
            hook: Social hook text for the video
            audio_url: URL of the audio file to include

        Returns:
            Dictionary payload for Creatomate API request
        """
        return {
            "template_id": self.template_id,
            "modifications": {
                "text": hook,
                "audio_url": audio_url,
            },
        }

    @with_retry(max_attempts=3, base_delay=1.0, exceptions=(CreatomateAPIError, Exception))
    async def generate_clip(self, hook: str, audio_url: str) -> str:
        """
        Generate a video clip for a social hook.

        Args:
            hook: Social hook text for the video
            audio_url: URL of the audio file to include

        Returns:
            URL of the generated video

        Raises:
            CreatomateAPIError: If Creatomate API returns an error
            VideoServiceError: If video generation fails
        """
        payload = self._build_render_payload(hook, audio_url)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60.0,
                )

                if response.status_code != 200 and response.status_code != 201:
                    raise CreatomateAPIError(
                        response.status_code,
                        response.text,
                    )

                result = response.json()

                # Creatomate returns a list of renders
                if isinstance(result, list) and len(result) > 0:
                    video_url = result[0].get("url", "")
                elif isinstance(result, dict):
                    video_url = result.get("url", "")
                else:
                    raise VideoServiceError("Unexpected response format from Creatomate")

                if not video_url:
                    raise VideoServiceError("No video URL in Creatomate response")

                logger.info(f"Generated video clip: {video_url}")
                return video_url

        except httpx.HTTPError as e:
            raise VideoServiceError(f"HTTP error during video generation: {e}")

    async def generate_all_clips(
        self, script: PodcastScript, audio_url: str
    ) -> list[str]:
        """
        Generate video clips for all social hooks in a script.

        Args:
            script: PodcastScript containing social hooks
            audio_url: URL of the audio file to include in videos

        Returns:
            List of video URLs for each social hook

        Raises:
            VideoServiceError: If video generation fails
        """
        if not script.social_hooks:
            logger.warning(f"Script {script.script_id} has no social hooks")
            return []

        video_urls: list[str] = []

        for idx, hook in enumerate(script.social_hooks):
            try:
                logger.debug(
                    f"Generating clip {idx + 1}/{len(script.social_hooks)} "
                    f"for script {script.script_id}"
                )
                video_url = await self.generate_clip(hook, audio_url)
                video_urls.append(video_url)
            except Exception as e:
                logger.error(f"Failed to generate clip for hook {idx + 1}: {e}")
                # Log error and mark as failed per Req 4.4
                # Continue processing remaining hooks

        logger.info(
            f"Generated {len(video_urls)}/{len(script.social_hooks)} clips "
            f"for script {script.script_id}"
        )

        return video_urls

    async def persist_video(
        self, script_id: str, video_url: str, hook_index: int
    ) -> str:
        """
        Store video URL in Supabase.

        Args:
            script_id: ID of the script this video belongs to
            video_url: URL of the generated video
            hook_index: Index of the social hook this video is for

        Returns:
            Media ID of the stored record

        Raises:
            VideoServiceError: If storage fails
        """
        if not self.supabase:
            raise VideoServiceError("Supabase client not configured")

        try:
            # Insert video record into media table
            result = (
                self.supabase.table("media")
                .insert(
                    {
                        "script_id": script_id,
                        "media_type": "video",
                        "storage_path": f"clips/{script_id}/hook_{hook_index}.mp4",
                        "public_url": video_url,
                    }
                )
                .execute()
            )

            if not result.data:
                raise VideoServiceError("Insert returned empty result")

            media_id = result.data[0].get("media_id", "")
            logger.info(f"Persisted video {media_id} for script {script_id}")
            return media_id

        except Exception as e:
            raise VideoServiceError(f"Failed to persist video: {e}")


def create_video_service(supabase_client: Optional[Any] = None) -> VideoService:
    """
    Create a VideoService instance using application settings.

    Args:
        supabase_client: Optional Supabase client for storage

    Returns:
        Configured VideoService instance
    """
    from src.config import get_settings

    settings = get_settings()
    return VideoService(
        creatomate_api_key=settings.creatomate_api_key,
        template_id=settings.creatomate_template_id,
        supabase_client=supabase_client,
    )
