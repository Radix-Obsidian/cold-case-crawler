"""Script-related Pydantic models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Type definitions for speakers and emotion tags
Speaker = Literal["dr_aris_thorne", "maya_vance"]

EmotionTag = Literal[
    "scoffs",
    "clears_throat",
    "dramatic_pause",
    "sighs",
    "excited",
    "whispers",
    "interrupting",
    "gasps",
    "neutral",
]


class DialogueLine(BaseModel):
    """A single line of dialogue in the podcast script."""

    speaker: Speaker
    text: str = Field(min_length=1)
    emotion_tag: EmotionTag = "neutral"

    @field_validator("text")
    @classmethod
    def text_not_whitespace(cls, v: str) -> str:
        """Validate that text is not only whitespace."""
        if not v.strip():
            raise ValueError("text cannot be only whitespace")
        return v

    def to_elevenlabs_format(self) -> str:
        """Format text with emotion tag for ElevenLabs v3."""
        if self.emotion_tag == "neutral":
            return self.text
        return f"[{self.emotion_tag}] {self.text}"


class PodcastScript(BaseModel):
    """Complete podcast episode script."""

    script_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    episode_title: str = Field(min_length=1)
    chapters: list[DialogueLine] = Field(min_length=1)
    social_hooks: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("episode_title")
    @classmethod
    def episode_title_not_whitespace(cls, v: str) -> str:
        """Validate that episode_title is not only whitespace."""
        if not v.strip():
            raise ValueError("episode_title cannot be only whitespace")
        return v
