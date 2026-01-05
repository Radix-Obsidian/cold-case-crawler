"""Job status Pydantic model."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class JobStatus(BaseModel):
    """Status tracking for async jobs."""

    job_id: str = Field(min_length=1)
    job_type: Literal["crawl", "debate", "audio", "video"]
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    result_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
