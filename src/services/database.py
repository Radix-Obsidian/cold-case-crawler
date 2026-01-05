"""Database service for Supabase operations."""

import logging
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from src.models.case import CaseFile, Evidence
from src.models.job import JobStatus
from src.models.script import DialogueLine, PodcastScript
from src.utils.errors import ColdCaseCrawlerError

logger = logging.getLogger(__name__)


class DatabaseError(ColdCaseCrawlerError):
    """Base exception for database operations."""

    pass


class DatabaseService:
    """Service for Supabase database operations."""

    def __init__(self, supabase_client: Any) -> None:
        """
        Initialize the DatabaseService.

        Args:
            supabase_client: Supabase client instance
        """
        self.supabase = supabase_client

    # ==================== CASES CRUD ====================

    async def create_case(self, case: CaseFile) -> str:
        """
        Create a new case in the database.

        Args:
            case: CaseFile to persist

        Returns:
            The case_id of the created case

        Raises:
            DatabaseError: If creation fails
        """
        try:
            case_data = {
                "case_id": case.case_id,
                "title": case.title,
                "location": case.location,
                "date_occurred": case.date_occurred,
                "raw_content": case.raw_content,
                "source_urls": case.source_urls,
                "created_at": case.created_at.isoformat(),
            }

            result = self.supabase.table("cases").insert(case_data).execute()

            if not result.data:
                raise DatabaseError("Failed to insert case into database")

            # Insert evidence items
            for evidence in case.evidence_list:
                await self._create_evidence(case.case_id, evidence)

            logger.info(f"Created case {case.case_id}")
            return case.case_id

        except Exception as e:
            raise DatabaseError(f"Failed to create case: {e}")

    async def _create_evidence(self, case_id: str, evidence: Evidence) -> None:
        """Create evidence record linked to a case."""
        evidence_data = {
            "evidence_id": evidence.evidence_id,
            "case_id": case_id,
            "description": evidence.description,
            "evidence_type": evidence.evidence_type,
            "source_url": evidence.source_url,
        }
        self.supabase.table("evidence").insert(evidence_data).execute()

    async def get_case(self, case_id: str) -> Optional[CaseFile]:
        """
        Retrieve a case by ID.

        Args:
            case_id: The case ID to retrieve

        Returns:
            CaseFile if found, None otherwise
        """
        try:
            result = self.supabase.table("cases").select("*").eq("case_id", case_id).execute()

            if not result.data:
                return None

            case_data = result.data[0]

            # Fetch associated evidence
            evidence_result = (
                self.supabase.table("evidence").select("*").eq("case_id", case_id).execute()
            )

            evidence_list = []
            for ev in evidence_result.data or []:
                evidence_list.append(
                    Evidence(
                        evidence_id=ev["evidence_id"],
                        description=ev["description"],
                        evidence_type=ev["evidence_type"],
                        source_url=ev.get("source_url"),
                    )
                )

            return CaseFile(
                case_id=case_data["case_id"],
                title=case_data["title"],
                location=case_data["location"],
                date_occurred=case_data.get("date_occurred"),
                raw_content=case_data["raw_content"],
                evidence_list=evidence_list,
                source_urls=case_data.get("source_urls", []),
                created_at=datetime.fromisoformat(case_data["created_at"]),
            )

        except Exception as e:
            logger.error(f"Failed to get case {case_id}: {e}")
            return None

    async def get_cases_by_location(self, location: str) -> List[CaseFile]:
        """
        Retrieve cases filtered by location.

        Args:
            location: Location to filter by (exact match)

        Returns:
            List of CaseFiles matching the location
        """
        try:
            result = self.supabase.table("cases").select("*").eq("location", location).execute()

            cases = []
            for case_data in result.data or []:
                case = await self.get_case(case_data["case_id"])
                if case:
                    cases.append(case)

            return cases

        except Exception as e:
            logger.error(f"Failed to get cases by location {location}: {e}")
            return []

    async def update_case(self, case: CaseFile) -> bool:
        """
        Update an existing case.

        Args:
            case: CaseFile with updated data

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            case_data = {
                "title": case.title,
                "location": case.location,
                "date_occurred": case.date_occurred,
                "raw_content": case.raw_content,
                "source_urls": case.source_urls,
            }

            result = (
                self.supabase.table("cases")
                .update(case_data)
                .eq("case_id", case.case_id)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to update case {case.case_id}: {e}")
            return False

    async def delete_case(self, case_id: str) -> bool:
        """
        Delete a case and its associated evidence.

        Args:
            case_id: The case ID to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            # Delete evidence first (foreign key constraint)
            self.supabase.table("evidence").delete().eq("case_id", case_id).execute()

            # Delete the case
            result = self.supabase.table("cases").delete().eq("case_id", case_id).execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to delete case {case_id}: {e}")
            return False

    async def list_cases(self, limit: int = 100) -> List[CaseFile]:
        """
        List all cases.

        Args:
            limit: Maximum number of cases to return

        Returns:
            List of CaseFiles
        """
        try:
            result = self.supabase.table("cases").select("case_id").limit(limit).execute()

            cases = []
            for row in result.data or []:
                case = await self.get_case(row["case_id"])
                if case:
                    cases.append(case)

            return cases

        except Exception as e:
            logger.error(f"Failed to list cases: {e}")
            return []

    # ==================== SCRIPTS CRUD ====================

    async def create_script(self, script: PodcastScript) -> str:
        """
        Create a new script in the database.

        Args:
            script: PodcastScript to persist

        Returns:
            The script_id of the created script

        Raises:
            DatabaseError: If creation fails
        """
        try:
            # Convert chapters to JSON-serializable format
            chapters_json = [
                {
                    "speaker": line.speaker,
                    "text": line.text,
                    "emotion_tag": line.emotion_tag,
                }
                for line in script.chapters
            ]

            script_data = {
                "script_id": script.script_id,
                "case_id": script.case_id,
                "episode_title": script.episode_title,
                "chapters": chapters_json,
                "social_hooks": script.social_hooks,
                "created_at": script.created_at.isoformat(),
            }

            result = self.supabase.table("scripts").insert(script_data).execute()

            if not result.data:
                raise DatabaseError("Failed to insert script into database")

            logger.info(f"Created script {script.script_id}")
            return script.script_id

        except Exception as e:
            raise DatabaseError(f"Failed to create script: {e}")

    async def get_script(self, script_id: str) -> Optional[PodcastScript]:
        """
        Retrieve a script by ID.

        Args:
            script_id: The script ID to retrieve

        Returns:
            PodcastScript if found, None otherwise
        """
        try:
            result = (
                self.supabase.table("scripts").select("*").eq("script_id", script_id).execute()
            )

            if not result.data:
                return None

            script_data = result.data[0]

            # Convert chapters from JSON
            chapters = [
                DialogueLine(
                    speaker=ch["speaker"],
                    text=ch["text"],
                    emotion_tag=ch.get("emotion_tag", "neutral"),
                )
                for ch in script_data.get("chapters", [])
            ]

            return PodcastScript(
                script_id=script_data["script_id"],
                case_id=script_data["case_id"],
                episode_title=script_data["episode_title"],
                chapters=chapters,
                social_hooks=script_data.get("social_hooks", []),
                created_at=datetime.fromisoformat(script_data["created_at"]),
            )

        except Exception as e:
            logger.error(f"Failed to get script {script_id}: {e}")
            return None

    async def get_scripts_by_case_id(self, case_id: str) -> List[PodcastScript]:
        """
        Retrieve scripts filtered by case_id.

        Args:
            case_id: Case ID to filter by (exact match)

        Returns:
            List of PodcastScripts for the case
        """
        try:
            result = self.supabase.table("scripts").select("*").eq("case_id", case_id).execute()

            scripts = []
            for script_data in result.data or []:
                script = await self.get_script(script_data["script_id"])
                if script:
                    scripts.append(script)

            return scripts

        except Exception as e:
            logger.error(f"Failed to get scripts by case_id {case_id}: {e}")
            return []

    async def update_script(self, script: PodcastScript) -> bool:
        """
        Update an existing script.

        Args:
            script: PodcastScript with updated data

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            chapters_json = [
                {
                    "speaker": line.speaker,
                    "text": line.text,
                    "emotion_tag": line.emotion_tag,
                }
                for line in script.chapters
            ]

            script_data = {
                "episode_title": script.episode_title,
                "chapters": chapters_json,
                "social_hooks": script.social_hooks,
            }

            result = (
                self.supabase.table("scripts")
                .update(script_data)
                .eq("script_id", script.script_id)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to update script {script.script_id}: {e}")
            return False

    async def delete_script(self, script_id: str) -> bool:
        """
        Delete a script.

        Args:
            script_id: The script ID to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            # Delete associated media first
            self.supabase.table("media").delete().eq("script_id", script_id).execute()

            # Delete the script
            result = self.supabase.table("scripts").delete().eq("script_id", script_id).execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to delete script {script_id}: {e}")
            return False

    # ==================== MEDIA CRUD ====================

    async def create_media(
        self,
        script_id: str,
        media_type: str,
        storage_path: str,
        public_url: Optional[str] = None,
    ) -> str:
        """
        Create a new media record.

        Args:
            script_id: Associated script ID
            media_type: Type of media ('audio' or 'video')
            storage_path: Path in Supabase storage
            public_url: Public URL for the media

        Returns:
            The media_id of the created record

        Raises:
            DatabaseError: If creation fails
        """
        try:
            media_id = str(uuid4())

            media_data = {
                "media_id": media_id,
                "script_id": script_id,
                "media_type": media_type,
                "storage_path": storage_path,
                "public_url": public_url,
                "created_at": datetime.utcnow().isoformat(),
            }

            result = self.supabase.table("media").insert(media_data).execute()

            if not result.data:
                raise DatabaseError("Failed to insert media into database")

            logger.info(f"Created media {media_id} for script {script_id}")
            return media_id

        except Exception as e:
            raise DatabaseError(f"Failed to create media: {e}")

    async def get_media(self, media_id: str) -> Optional[dict[str, Any]]:
        """
        Retrieve a media record by ID.

        Args:
            media_id: The media ID to retrieve

        Returns:
            Media record dict if found, None otherwise
        """
        try:
            result = self.supabase.table("media").select("*").eq("media_id", media_id).execute()

            if not result.data:
                return None

            return result.data[0]

        except Exception as e:
            logger.error(f"Failed to get media {media_id}: {e}")
            return None

    async def get_media_by_script_id(self, script_id: str) -> List[dict[str, Any]]:
        """
        Retrieve media records filtered by script_id.

        Args:
            script_id: Script ID to filter by

        Returns:
            List of media records for the script
        """
        try:
            result = self.supabase.table("media").select("*").eq("script_id", script_id).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get media by script_id {script_id}: {e}")
            return []

    async def update_media(
        self,
        media_id: str,
        storage_path: Optional[str] = None,
        public_url: Optional[str] = None,
    ) -> bool:
        """
        Update a media record.

        Args:
            media_id: The media ID to update
            storage_path: New storage path (optional)
            public_url: New public URL (optional)

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            update_data: dict[str, Any] = {}
            if storage_path is not None:
                update_data["storage_path"] = storage_path
            if public_url is not None:
                update_data["public_url"] = public_url

            if not update_data:
                return True

            result = (
                self.supabase.table("media")
                .update(update_data)
                .eq("media_id", media_id)
                .execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to update media {media_id}: {e}")
            return False

    async def delete_media(self, media_id: str) -> bool:
        """
        Delete a media record.

        Args:
            media_id: The media ID to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            result = self.supabase.table("media").delete().eq("media_id", media_id).execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to delete media {media_id}: {e}")
            return False

    # ==================== JOBS CRUD ====================

    async def create_job(self, job: JobStatus) -> str:
        """
        Create a new job record.

        Args:
            job: JobStatus to persist

        Returns:
            The job_id of the created job

        Raises:
            DatabaseError: If creation fails
        """
        try:
            job_data = {
                "job_id": job.job_id,
                "job_type": job.job_type,
                "status": job.status,
                "result_id": job.result_id,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat(),
                "updated_at": job.updated_at.isoformat(),
            }

            result = self.supabase.table("jobs").insert(job_data).execute()

            if not result.data:
                raise DatabaseError("Failed to insert job into database")

            logger.info(f"Created job {job.job_id}")
            return job.job_id

        except Exception as e:
            raise DatabaseError(f"Failed to create job: {e}")

    async def get_job(self, job_id: str) -> Optional[JobStatus]:
        """
        Retrieve a job by ID.

        Args:
            job_id: The job ID to retrieve

        Returns:
            JobStatus if found, None otherwise
        """
        try:
            result = self.supabase.table("jobs").select("*").eq("job_id", job_id).execute()

            if not result.data:
                return None

            job_data = result.data[0]

            return JobStatus(
                job_id=job_data["job_id"],
                job_type=job_data["job_type"],
                status=job_data["status"],
                result_id=job_data.get("result_id"),
                error_message=job_data.get("error_message"),
                created_at=datetime.fromisoformat(job_data["created_at"]),
                updated_at=datetime.fromisoformat(job_data["updated_at"]),
            )

        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update a job's status.

        Args:
            job_id: The job ID to update
            status: New status value
            result_id: Result ID if completed (optional)
            error_message: Error message if failed (optional)

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            update_data: dict[str, Any] = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat(),
            }

            if result_id is not None:
                update_data["result_id"] = result_id
            if error_message is not None:
                update_data["error_message"] = error_message

            result = (
                self.supabase.table("jobs").update(update_data).eq("job_id", job_id).execute()
            )

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to update job {job_id}: {e}")
            return False

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job record.

        Args:
            job_id: The job ID to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        try:
            result = self.supabase.table("jobs").delete().eq("job_id", job_id).execute()

            return bool(result.data)

        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False

    async def get_jobs_by_status(self, status: str) -> List[JobStatus]:
        """
        Retrieve jobs filtered by status.

        Args:
            status: Status to filter by

        Returns:
            List of JobStatus records matching the status
        """
        try:
            result = self.supabase.table("jobs").select("*").eq("status", status).execute()

            jobs = []
            for job_data in result.data or []:
                jobs.append(
                    JobStatus(
                        job_id=job_data["job_id"],
                        job_type=job_data["job_type"],
                        status=job_data["status"],
                        result_id=job_data.get("result_id"),
                        error_message=job_data.get("error_message"),
                        created_at=datetime.fromisoformat(job_data["created_at"]),
                        updated_at=datetime.fromisoformat(job_data["updated_at"]),
                    )
                )

            return jobs

        except Exception as e:
            logger.error(f"Failed to get jobs by status {status}: {e}")
            return []

    # ==================== UTILITY METHODS ====================

    async def case_exists(self, case_id: str) -> bool:
        """Check if a case exists."""
        try:
            result = (
                self.supabase.table("cases").select("case_id").eq("case_id", case_id).execute()
            )
            return bool(result.data)
        except Exception:
            return False

    async def script_exists(self, script_id: str) -> bool:
        """Check if a script exists."""
        try:
            result = (
                self.supabase.table("scripts")
                .select("script_id")
                .eq("script_id", script_id)
                .execute()
            )
            return bool(result.data)
        except Exception:
            return False


# Factory function for creating DatabaseService with settings
def create_database_service() -> DatabaseService:
    """
    Create a DatabaseService instance using application settings.

    Returns:
        Configured DatabaseService instance
    """
    from supabase import create_client

    from src.config import get_settings

    settings = get_settings()
    supabase_client = create_client(settings.supabase_url, settings.supabase_key)
    return DatabaseService(supabase_client=supabase_client)
