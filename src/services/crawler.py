"""Crawler service for scraping cold case data using Firecrawl."""

import hashlib
import logging
import re
from typing import Any, List, Optional
from uuid import uuid4

from firecrawl import AsyncFirecrawlApp

from src.models.case import CaseFile, Evidence
from src.utils.errors import CrawlerError, FirecrawlAPIError

logger = logging.getLogger(__name__)


class CrawlerService:
    """Service for crawling and scraping cold case data from web sources."""

    def __init__(
        self,
        firecrawl_api_key: str,
        supabase_client: Optional[Any] = None,
    ) -> None:
        """
        Initialize the CrawlerService.

        Args:
            firecrawl_api_key: API key for Firecrawl service
            supabase_client: Supabase client for persistence (optional)
        """
        self.firecrawl = AsyncFirecrawlApp(api_key=firecrawl_api_key)
        self.supabase = supabase_client

    async def search_cold_cases(
        self,
        query: str,
        limit: int = 10,
    ) -> List[CaseFile]:
        """
        Search for cold cases using Firecrawl's search endpoint.

        Args:
            query: Search query for cold cases
            limit: Maximum number of results to return

        Returns:
            List of CaseFile objects extracted from search results

        Raises:
            FirecrawlAPIError: If Firecrawl API returns an error
            CrawlerError: If parsing fails
        """
        try:
            response = await self.firecrawl.search(
                query=query,
                params={
                    "limit": limit,
                    "scrapeOptions": {
                        "formats": ["markdown"],
                    },
                },
            )

            if not response:
                return []

            # Handle SearchData response format from Firecrawl v2
            # Response has 'web' attribute with list of SearchResultWeb objects
            urls_to_scrape: List[str] = []
            
            if hasattr(response, 'web') and response.web:
                # Extract URLs from SearchResultWeb objects
                for result in response.web:
                    if hasattr(result, 'url') and result.url:
                        urls_to_scrape.append(result.url)
            elif isinstance(response, dict):
                # Fallback for dict response format
                results = response.get("data", []) or response.get("web", [])
                for result in results:
                    if isinstance(result, dict) and result.get("url"):
                        urls_to_scrape.append(result["url"])

            # Scrape each URL to get full content
            case_files: List[CaseFile] = []
            for url in urls_to_scrape[:limit]:
                try:
                    case_file = await self.scrape_case_url(url)
                    if case_file:
                        case_files.append(case_file)
                except Exception as e:
                    # Log error and continue processing remaining sources (Req 1.4)
                    logger.warning(f"Failed to scrape URL {url}: {e}")
                    continue

            return case_files

        except Exception as e:
            if "status" in str(e).lower() or "error" in str(e).lower():
                raise FirecrawlAPIError(500, str(e))
            raise CrawlerError(f"Search failed: {e}")

    async def scrape_case_url(self, url: str) -> Optional[CaseFile]:
        """
        Scrape a specific URL and extract case information.

        Args:
            url: URL to scrape for cold case data

        Returns:
            CaseFile if successfully scraped, None otherwise

        Raises:
            FirecrawlAPIError: If Firecrawl API returns an error
        """
        try:
            response = await self.firecrawl.scrape(
                url=url,
                params={
                    "formats": ["markdown"],
                },
            )

            if not response:
                logger.warning(f"Empty response from URL: {url}")
                return None

            # Handle ScrapeResponse object from Firecrawl v2
            response_dict: dict[str, Any] = {"url": url}
            
            if hasattr(response, 'markdown'):
                response_dict["markdown"] = response.markdown
            if hasattr(response, 'metadata'):
                response_dict["metadata"] = response.metadata if isinstance(response.metadata, dict) else {}
            elif isinstance(response, dict):
                response_dict = response
                response_dict["url"] = url

            return self._parse_case_from_response(response_dict)

        except Exception as e:
            logger.error(f"Failed to scrape URL {url}: {e}")
            raise FirecrawlAPIError(500, str(e))

    def _parse_case_from_response(
        self,
        response: dict[str, Any],
    ) -> Optional[CaseFile]:
        """
        Transform Firecrawl response to CaseFile Pydantic model.

        Args:
            response: Firecrawl API response containing markdown and metadata

        Returns:
            CaseFile if parsing succeeds, None otherwise
        """
        if not response:
            return None

        # Extract markdown content
        markdown = response.get("markdown", "")
        if not markdown or not markdown.strip():
            return None

        # Extract metadata
        metadata = response.get("metadata", {}) or {}
        url = response.get("url", "")

        # Generate case_id from URL or content hash
        case_id = self._generate_case_id(url, markdown)

        # Extract title from metadata or markdown
        title = self._extract_title(metadata, markdown)
        if not title:
            return None

        # Extract location from content
        location = self._extract_location(markdown)

        # Extract date if available
        date_occurred = self._extract_date(markdown)

        # Extract evidence items
        evidence_list = self._extract_evidence(markdown)

        # Build source URLs list
        source_urls = [url] if url else []

        try:
            return CaseFile(
                case_id=case_id,
                title=title,
                location=location,
                date_occurred=date_occurred,
                raw_content=markdown,
                evidence_list=evidence_list,
                source_urls=source_urls,
            )
        except Exception as e:
            logger.warning(f"Failed to create CaseFile: {e}")
            return None

    def _extract_evidence(self, markdown: str) -> List[Evidence]:
        """
        Parse evidence items from markdown content.

        Ensures all evidence items have unique evidence_id values (Req 1.3).

        Args:
            markdown: Markdown content to parse

        Returns:
            List of distinct Evidence items
        """
        evidence_list: List[Evidence] = []
        seen_ids: set[str] = set()

        # Pattern to find evidence-related content
        # Look for bullet points, numbered lists, or sections mentioning evidence
        evidence_patterns = [
            r"(?:evidence|clue|finding|discovery):\s*(.+?)(?:\n|$)",
            r"[-*]\s*(.+?(?:found|discovered|evidence|witness|testimony).+?)(?:\n|$)",
            r"(?:physical evidence|forensic|dna|fingerprint|weapon):\s*(.+?)(?:\n|$)",
        ]

        for pattern in evidence_patterns:
            matches = re.findall(pattern, markdown, re.IGNORECASE)
            for match in matches:
                description = match.strip()
                if not description or len(description) < 10:
                    continue

                # Determine evidence type
                evidence_type = self._classify_evidence_type(description)

                # Generate unique evidence_id
                evidence_id = self._generate_evidence_id(description)

                # Ensure uniqueness
                if evidence_id in seen_ids:
                    continue
                seen_ids.add(evidence_id)

                try:
                    evidence = Evidence(
                        evidence_id=evidence_id,
                        description=description[:500],  # Limit length
                        evidence_type=evidence_type,
                    )
                    evidence_list.append(evidence)
                except Exception:
                    continue

        return evidence_list

    def _classify_evidence_type(self, description: str) -> str:
        """Classify evidence type based on description content."""
        description_lower = description.lower()

        if any(
            term in description_lower
            for term in ["dna", "fingerprint", "blood", "weapon", "forensic", "physical"]
        ):
            return "physical"
        elif any(
            term in description_lower
            for term in ["witness", "testimony", "saw", "heard", "statement"]
        ):
            return "testimonial"
        elif any(
            term in description_lower
            for term in ["document", "record", "letter", "email", "phone"]
        ):
            return "documentary"
        else:
            return "circumstantial"

    def _generate_case_id(self, url: str, content: str) -> str:
        """Generate a unique case ID as a valid UUID."""
        if url:
            # Use URL hash to generate deterministic UUID
            hash_bytes = hashlib.md5(url.encode()).digest()
        else:
            # Fall back to content hash
            hash_bytes = hashlib.md5(content.encode()).digest()
        
        # Convert to UUID format
        import uuid
        return str(uuid.UUID(bytes=hash_bytes))

    def _generate_evidence_id(self, description: str) -> str:
        """Generate a unique evidence ID as a valid UUID."""
        import uuid
        hash_bytes = hashlib.md5(description.encode()).digest()
        return str(uuid.UUID(bytes=hash_bytes))

    def _extract_title(
        self,
        metadata: dict[str, Any],
        markdown: str,
    ) -> str:
        """Extract case title from metadata or markdown content."""
        # Try metadata title first
        if metadata.get("title"):
            return str(metadata["title"]).strip()

        # Try to find H1 heading in markdown
        h1_match = re.search(r"^#\s+(.+?)$", markdown, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()

        # Try to find any heading
        heading_match = re.search(r"^#{1,3}\s+(.+?)$", markdown, re.MULTILINE)
        if heading_match:
            return heading_match.group(1).strip()

        # Fall back to first line
        first_line = markdown.strip().split("\n")[0]
        if first_line:
            return first_line[:100].strip()

        return "Unknown Case"

    def _extract_location(self, markdown: str) -> str:
        """Extract location from markdown content."""
        # Common location patterns
        location_patterns = [
            r"(?:location|place|city|town|county|state):\s*(.+?)(?:\n|$)",
            r"(?:in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z]{2})",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*[A-Z][a-z]+)",
        ]

        for pattern in location_patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location and len(location) > 2:
                    return location[:100]

        return "Unknown Location"

    def _extract_date(self, markdown: str) -> Optional[str]:
        """Extract date from markdown content."""
        # Common date patterns
        date_patterns = [
            r"(?:date|occurred|happened|on):\s*(.+?)(?:\n|$)",
            r"(\d{1,2}/\d{1,2}/\d{2,4})",
            r"(\w+\s+\d{1,2},?\s+\d{4})",
            r"(\d{4}-\d{2}-\d{2})",
        ]

        for pattern in date_patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:50]

        return None

    async def persist_case(self, case: CaseFile) -> str:
        """
        Store case in Supabase.

        Args:
            case: CaseFile to persist

        Returns:
            The case_id of the persisted case

        Raises:
            CrawlerError: If persistence fails
        """
        if not self.supabase:
            raise CrawlerError("Supabase client not configured")

        try:
            # Prepare case data for insertion
            case_data = {
                "case_id": case.case_id,
                "title": case.title,
                "location": case.location,
                "date_occurred": case.date_occurred,
                "raw_content": case.raw_content,
                "source_urls": case.source_urls,
            }

            # Insert case into cases table
            result = self.supabase.table("cases").insert(case_data).execute()

            if not result.data:
                raise CrawlerError("Failed to insert case into database")

            # Insert evidence items
            for evidence in case.evidence_list:
                evidence_data = {
                    "evidence_id": evidence.evidence_id,
                    "case_id": case.case_id,
                    "description": evidence.description,
                    "evidence_type": evidence.evidence_type,
                    "source_url": evidence.source_url,
                }
                self.supabase.table("evidence").insert(evidence_data).execute()

            logger.info(f"Persisted case {case.case_id} with {len(case.evidence_list)} evidence items")
            return case.case_id

        except Exception as e:
            raise CrawlerError(f"Failed to persist case: {e}")


# Factory function for creating CrawlerService with settings
def create_crawler_service(supabase_client: Optional[Any] = None) -> CrawlerService:
    """
    Create a CrawlerService instance using application settings.

    Args:
        supabase_client: Optional Supabase client for persistence

    Returns:
        Configured CrawlerService instance
    """
    from src.config import get_settings

    settings = get_settings()
    return CrawlerService(
        firecrawl_api_key=settings.firecrawl_api_key,
        supabase_client=supabase_client,
    )
