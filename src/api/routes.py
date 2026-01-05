"""FastAPI routes for Murder Index API."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from src.models.job import JobStatus
from src.services.database import DatabaseService, create_database_service
from src.utils.errors import (
    AudioServiceError,
    ColdCaseCrawlerError,
    CrawlerError,
    DebateEngineError,
    VideoServiceError,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# ==================== Error Response Model ====================


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str
    error_type: str
    errors: Optional[List[Dict[str, Any]]] = None


# ==================== Exception Handlers ====================


async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "error_type": "ValidationError",
            "errors": exc.errors(),
        },
    )


async def cold_case_crawler_exception_handler(
    request: Request, exc: ColdCaseCrawlerError
) -> JSONResponse:
    """Handle application-specific errors."""
    # Determine appropriate status code based on error type
    status_code = 500

    if isinstance(exc, CrawlerError):
        status_code = 502  # Bad Gateway for external API errors
    elif isinstance(exc, DebateEngineError):
        status_code = 500
    elif isinstance(exc, AudioServiceError):
        status_code = 502
    elif isinstance(exc, VideoServiceError):
        status_code = 502

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": str(exc),
            "error_type": type(exc).__name__,
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_type": "HTTPException",
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": "InternalError",
        },
    )


# ==================== Request/Response Models ====================


class CrawlRequest(BaseModel):
    """Request model for crawl endpoint."""

    query: str = Field(min_length=1, description="Search query for cold cases")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results to return")


class CrawlResponse(BaseModel):
    """Response model for crawl endpoint."""

    job_id: str
    status: str
    message: str


class DebateResponse(BaseModel):
    """Response model for debate endpoint."""

    job_id: str
    status: str
    script_id: Optional[str] = None
    message: str


class AudioResponse(BaseModel):
    """Response model for audio endpoint."""

    job_id: str
    status: str
    audio_url: Optional[str] = None
    message: str


class StatusResponse(BaseModel):
    """Response model for status endpoint."""

    job_id: str
    job_type: str
    status: str
    result_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WebhookPayload(BaseModel):
    """Request model for webhook endpoint."""

    script_id: str = Field(min_length=1, description="ID of the created script")
    case_id: str = Field(min_length=1, description="ID of the associated case")
    episode_title: str = Field(min_length=1, description="Title of the episode")
    event_type: str = Field(default="script.created", description="Type of webhook event")


class WebhookResponse(BaseModel):
    """Response model for webhook endpoint."""

    success: bool
    job_id: Optional[str] = None
    message: str


# ==================== Dependencies ====================


def get_database_service() -> DatabaseService:
    """Dependency for database service."""
    return create_database_service()


# ==================== Endpoints ====================


@router.post("/crawl", response_model=CrawlResponse)
async def crawl_cases(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: DatabaseService = Depends(get_database_service),
) -> CrawlResponse:
    """
    Initiate cold case search and scraping.

    Creates a background job to search for cold cases using the provided query.
    Returns immediately with a job_id that can be used to check status.
    """
    job_id = f"job-{uuid4().hex[:12]}"

    # Create job record
    job = JobStatus(
        job_id=job_id,
        job_type="crawl",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        await db.create_job(job)
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create crawl job")

    # Add background task for crawling
    background_tasks.add_task(
        _execute_crawl_job,
        job_id=job_id,
        query=request.query,
        limit=request.limit,
    )

    return CrawlResponse(
        job_id=job_id,
        status="pending",
        message=f"Crawl job started for query: {request.query}",
    )


@router.post("/debate/{case_id}", response_model=DebateResponse)
async def generate_debate(
    case_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseService = Depends(get_database_service),
) -> DebateResponse:
    """
    Generate podcast script for a case.

    Creates a background job to generate a debate-style podcast script
    for the specified case. Returns immediately with a job_id.
    """
    # Verify case exists
    case = await db.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")

    job_id = f"job-{uuid4().hex[:12]}"

    # Create job record
    job = JobStatus(
        job_id=job_id,
        job_type="debate",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        await db.create_job(job)
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create debate job")

    # Add background task for debate generation
    background_tasks.add_task(
        _execute_debate_job,
        job_id=job_id,
        case_id=case_id,
    )

    return DebateResponse(
        job_id=job_id,
        status="pending",
        message=f"Debate generation started for case: {case_id}",
    )


@router.post("/audio/{script_id}", response_model=AudioResponse)
async def generate_audio(
    script_id: str,
    background_tasks: BackgroundTasks,
    db: DatabaseService = Depends(get_database_service),
) -> AudioResponse:
    """
    Trigger audio generation for a script.

    Creates a background job to synthesize audio for the specified script.
    Returns immediately with a job_id.
    """
    # Verify script exists
    script = await db.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script not found: {script_id}")

    job_id = f"job-{uuid4().hex[:12]}"

    # Create job record
    job = JobStatus(
        job_id=job_id,
        job_type="audio",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        await db.create_job(job)
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail="Failed to create audio job")

    # Add background task for audio generation
    background_tasks.add_task(
        _execute_audio_job,
        job_id=job_id,
        script_id=script_id,
    )

    return AudioResponse(
        job_id=job_id,
        status="pending",
        message=f"Audio generation started for script: {script_id}",
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(
    job_id: str,
    db: DatabaseService = Depends(get_database_service),
) -> StatusResponse:
    """
    Get processing status for any job.

    Returns the current status of the specified job including
    result_id if completed or error_message if failed.
    """
    job = await db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return StatusResponse(
        job_id=job.job_id,
        job_type=job.job_type,
        status=job.status,
        result_id=job.result_id,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ==================== Webhook Endpoints ====================


@router.post("/webhooks/script-created", response_model=WebhookResponse)
async def handle_script_created_webhook(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    request: Request,
    db: DatabaseService = Depends(get_database_service),
) -> WebhookResponse:
    """
    Webhook handler for automatic audio generation when a script is saved.

    This endpoint is triggered by Supabase when a new PodcastScript is inserted
    into the scripts table. It automatically starts audio generation for the script.

    Requirements: 6.1, 6.2, 6.3
    """
    logger.info(f"Received webhook for script: {payload.script_id}, event: {payload.event_type}")

    # Validate event type
    if payload.event_type != "script.created":
        return WebhookResponse(
            success=False,
            message=f"Unsupported event type: {payload.event_type}",
        )

    # Verify script exists
    script = await db.get_script(payload.script_id)
    if not script:
        logger.warning(f"Webhook received for non-existent script: {payload.script_id}")
        return WebhookResponse(
            success=False,
            message=f"Script not found: {payload.script_id}",
        )

    # Create audio generation job
    job_id = f"job-{uuid4().hex[:12]}"

    job = JobStatus(
        job_id=job_id,
        job_type="audio",
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    try:
        await db.create_job(job)
    except Exception as e:
        logger.error(f"Failed to create audio job from webhook: {e}")
        return WebhookResponse(
            success=False,
            message=f"Failed to create audio job: {str(e)}",
        )

    # Add background task for audio generation
    background_tasks.add_task(
        _execute_audio_job,
        job_id=job_id,
        script_id=payload.script_id,
    )

    logger.info(f"Audio generation triggered for script {payload.script_id}, job: {job_id}")

    return WebhookResponse(
        success=True,
        job_id=job_id,
        message=f"Audio generation started for script: {payload.script_id}",
    )


# ==================== Background Tasks ====================


async def _execute_crawl_job(job_id: str, query: str, limit: int) -> None:
    """Execute crawl job in background."""
    from src.services.crawler import create_crawler_service

    db = create_database_service()

    try:
        # Update job status to processing
        await db.update_job_status(job_id, "processing")

        # Create crawler service with database
        crawler = create_crawler_service(supabase_client=db.supabase)

        # Execute search
        cases = await crawler.search_cold_cases(query, limit)

        # Persist cases
        case_ids: List[str] = []
        for case in cases:
            try:
                case_id = await crawler.persist_case(case)
                case_ids.append(case_id)
            except Exception as e:
                logger.warning(f"Failed to persist case: {e}")
                continue

        # Update job as completed
        result_id = case_ids[0] if case_ids else None
        await db.update_job_status(job_id, "completed", result_id=result_id)

        logger.info(f"Crawl job {job_id} completed: {len(case_ids)} cases found")

    except Exception as e:
        logger.error(f"Crawl job {job_id} failed: {e}")
        await db.update_job_status(job_id, "failed", error_message=str(e))


async def _execute_debate_job(job_id: str, case_id: str) -> None:
    """Execute debate job in background."""
    from src.services.debate import create_debate_engine

    db = create_database_service()

    try:
        # Update job status to processing
        await db.update_job_status(job_id, "processing")

        # Get the case
        case = await db.get_case(case_id)
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Create debate engine with database
        engine = create_debate_engine(supabase_client=db.supabase)

        # Generate debate
        script = await engine.generate_debate(case)

        # Persist script
        script_id = await engine.persist_script(script)

        # Update job as completed
        await db.update_job_status(job_id, "completed", result_id=script_id)

        logger.info(f"Debate job {job_id} completed: script {script_id}")

    except Exception as e:
        logger.error(f"Debate job {job_id} failed: {e}")
        await db.update_job_status(job_id, "failed", error_message=str(e))


async def _execute_audio_job(job_id: str, script_id: str) -> None:
    """Execute audio job in background."""
    from src.services.audio import create_audio_service

    db = create_database_service()

    try:
        # Update job status to processing
        await db.update_job_status(job_id, "processing")

        # Get the script
        script = await db.get_script(script_id)
        if not script:
            raise ValueError(f"Script not found: {script_id}")

        # Create audio service with database
        audio_service = create_audio_service(supabase_client=db.supabase)

        # Generate episode audio
        audio_url = await audio_service.generate_episode(script)

        # Create media record
        media_id = await db.create_media(
            script_id=script_id,
            media_type="audio",
            storage_path=f"episodes/{script_id}/episode.mp3",
            public_url=audio_url,
        )

        # Update job as completed
        await db.update_job_status(job_id, "completed", result_id=media_id)

        logger.info(f"Audio job {job_id} completed: media {media_id}")

    except Exception as e:
        logger.error(f"Audio job {job_id} failed: {e}")
        await db.update_job_status(job_id, "failed", error_message=str(e))
