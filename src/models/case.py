"""Case-related Pydantic models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    """A piece of evidence from a cold case."""

    evidence_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_type: str  # e.g., "physical", "testimonial", "circumstantial"
    source_url: Optional[str] = None

    @field_validator("evidence_id", "description")
    @classmethod
    def not_whitespace(cls, v: str) -> str:
        """Validate that field is not only whitespace."""
        if not v.strip():
            raise ValueError("field cannot be only whitespace")
        return v


class CaseFile(BaseModel):
    """Structured cold case data extracted from web sources."""

    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    location: str = Field(min_length=1)
    date_occurred: Optional[str] = None
    raw_content: str = Field(min_length=1)
    evidence_list: list[Evidence] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("case_id", "title", "location", "raw_content")
    @classmethod
    def not_whitespace(cls, v: str) -> str:
        """Validate that field is not only whitespace."""
        if not v.strip():
            raise ValueError("field cannot be only whitespace")
        return v
