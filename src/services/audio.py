"""Audio service for synthesizing podcast audio using ElevenLabs."""

import logging
from typing import Any, List, Optional

from src.models.script import DialogueLine, PodcastScript
from src.utils.errors import AudioServiceError, ElevenLabsAPIError
from src.utils.retry import with_retry

logger = logging.getLogger(__name__)


class AudioService:
    """Service for converting podcast scripts to audio using ElevenLabs."""

    def __init__(
        self,
        elevenlabs_api_key: str,
        supabase_client: Optional[Any] = None,
        thorne_voice_id: str = "",
        maya_voice_id: str = "",
        model_id: str = "eleven_v3",
    ) -> None:
        """
        Initialize the AudioService.

        Args:
            elevenlabs_api_key: API key for ElevenLabs service
            supabase_client: Supabase client for storage (optional)
            thorne_voice_id: Voice ID for Dr. Thorne
            maya_voice_id: Voice ID for Maya Vance
            model_id: ElevenLabs model ID (default: eleven_v3)
        """
        self.api_key = elevenlabs_api_key
        self.supabase = supabase_client
        self.model_id = model_id
        self.voice_map = {
            "dr_aris_thorne": thorne_voice_id,
            "maya_vance": maya_voice_id,
        }
        self._client: Optional[Any] = None

    async def _get_client(self) -> Any:
        """Get or create the ElevenLabs async client."""
        if self._client is None:
            from elevenlabs import AsyncElevenLabs

            self._client = AsyncElevenLabs(api_key=self.api_key)
        return self._client

    def apply_directorial_pass(self, line: DialogueLine) -> DialogueLine:
        """
        Validate and enrich emotion tags for ElevenLabs processing.

        This method ensures emotion tags are properly formatted for ElevenLabs v3.
        The to_elevenlabs_format() method on DialogueLine handles the actual formatting.

        Args:
            line: DialogueLine to process

        Returns:
            DialogueLine with validated emotion tag (unchanged if already valid)
        """
        # The DialogueLine model already validates emotion_tag via Literal type
        # This method serves as a pass-through that could add additional processing
        # For now, we just return the line as-is since validation is handled by Pydantic
        return line

    @with_retry(max_attempts=3, base_delay=1.0, exceptions=(ElevenLabsAPIError, Exception))
    async def synthesize_dialogue(self, line: DialogueLine) -> bytes:
        """
        Convert a single dialogue line to audio using eleven_v3 model.

        Args:
            line: DialogueLine to synthesize

        Returns:
            Audio data as bytes

        Raises:
            ElevenLabsAPIError: If ElevenLabs API returns an error
            AudioServiceError: If synthesis fails
        """
        client = await self._get_client()

        # Get voice ID for speaker
        voice_id = self.voice_map.get(line.speaker)
        if not voice_id:
            raise AudioServiceError(f"No voice ID configured for speaker: {line.speaker}")

        # Apply directorial pass and get formatted text
        processed_line = self.apply_directorial_pass(line)
        text = processed_line.to_elevenlabs_format()

        try:
            # Use ElevenLabs text-to-speech API
            audio_generator = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=self.model_id,
            )

            # Collect audio bytes from generator
            audio_chunks: List[bytes] = []
            async for chunk in audio_generator:
                audio_chunks.append(chunk)

            return b"".join(audio_chunks)

        except Exception as e:
            error_msg = str(e)
            if "status" in error_msg.lower() or "error" in error_msg.lower():
                raise ElevenLabsAPIError(500, error_msg)
            raise AudioServiceError(f"Audio synthesis failed: {e}")

    def _concatenate_audio(self, segments: List[bytes]) -> bytes:
        """
        Merge audio segments into a single byte array.

        Args:
            segments: List of audio byte arrays to concatenate

        Returns:
            Single concatenated byte array
        """
        return b"".join(segments)

    async def generate_episode(self, script: PodcastScript) -> str:
        """
        Generate full episode audio from a PodcastScript.

        Processes all DialogueLines sequentially, concatenates audio,
        and uploads to Supabase storage.

        Args:
            script: PodcastScript to convert to audio

        Returns:
            URL of the uploaded audio file

        Raises:
            AudioServiceError: If episode generation fails
        """
        if not script.chapters:
            raise AudioServiceError("Script has no dialogue lines to process")

        audio_segments: List[bytes] = []

        # Process each dialogue line sequentially (Req 3.1)
        for idx, line in enumerate(script.chapters):
            try:
                logger.debug(f"Synthesizing line {idx + 1}/{len(script.chapters)}")
                audio_data = await self.synthesize_dialogue(line)
                audio_segments.append(audio_data)
            except Exception as e:
                logger.error(f"Failed to synthesize line {idx + 1}: {e}")
                raise AudioServiceError(f"Failed to synthesize dialogue line {idx + 1}: {e}")

        # Concatenate all audio segments
        full_audio = self._concatenate_audio(audio_segments)

        if not full_audio:
            raise AudioServiceError("No audio data generated")

        # Upload to storage
        audio_url = await self._upload_to_storage(script.script_id, full_audio)

        logger.info(
            f"Generated episode for script {script.script_id}: "
            f"{len(script.chapters)} lines, {len(full_audio)} bytes"
        )

        return audio_url

    async def _upload_to_storage(self, script_id: str, audio_data: bytes) -> str:
        """
        Store MP3 in Supabase storage.

        Args:
            script_id: ID of the script for file naming
            audio_data: Audio bytes to upload

        Returns:
            Public URL of the uploaded file

        Raises:
            AudioServiceError: If upload fails
        """
        if not self.supabase:
            raise AudioServiceError("Supabase client not configured")

        try:
            # Define storage path
            file_path = f"episodes/{script_id}/episode.mp3"

            # Upload to Supabase storage bucket
            result = self.supabase.storage.from_("podcasts").upload(
                path=file_path,
                file=audio_data,
                file_options={"content-type": "audio/mpeg"},
            )

            if not result:
                raise AudioServiceError("Upload returned empty result")

            # Get public URL
            public_url = self.supabase.storage.from_("podcasts").get_public_url(file_path)

            logger.info(f"Uploaded audio to {file_path}")
            return public_url

        except Exception as e:
            raise AudioServiceError(f"Failed to upload audio: {e}")


def create_audio_service(supabase_client: Optional[Any] = None) -> AudioService:
    """
    Create an AudioService instance using application settings.

    Args:
        supabase_client: Optional Supabase client for storage

    Returns:
        Configured AudioService instance
    """
    from src.config import get_settings

    settings = get_settings()
    return AudioService(
        elevenlabs_api_key=settings.elevenlabs_api_key,
        supabase_client=supabase_client,
        thorne_voice_id=settings.thorne_voice_id,
        maya_voice_id=settings.maya_voice_id,
        model_id=settings.elevenlabs_model,
    )
