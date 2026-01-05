"""Application settings from environment variables."""

from functools import lru_cache
from dotenv import load_dotenv
import os

from pydantic_settings import BaseSettings

# Load environment variables
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment."""

    # API Keys
    firecrawl_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    elevenlabs_api_key: str = ""
    creatomate_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""

    # Configuration
    log_level: str = "INFO"
    max_retry_attempts: int = 3
    base_delay_seconds: float = 1.0

    # ElevenLabs
    elevenlabs_model: str = "eleven_v3"
    thorne_voice_id: str = ""
    maya_voice_id: str = ""
    maya_image_path: str = "frontend/maya_vance.png"
    thorne_image_path: str = "frontend/dr_aris_thorne.png"

    # Creatomate
    creatomate_template_id: str = ""

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
