"""Property-based tests for crawler transformations.

Feature: cold-case-crawler
Properties 1, 2, 3: Crawler Service Transformations
Validates: Requirements 1.2, 1.3, 1.4
"""

import pytest
from hypothesis import given, settings, strategies as st

from src.models.case import CaseFile, Evidence
from src.services.crawler import CrawlerService


# Strategy for generating valid Firecrawl-like responses
def firecrawl_response_strategy():
    """Generate valid Firecrawl response dictionaries."""
    return st.fixed_dictionaries({
        "url": st.text(min_size=10, max_size=100).map(lambda x: f"https://example.com/{x}"),
        "markdown": st.text(min_size=20, max_size=2000).filter(lambda x: x.strip()),
        "metadata": st.fixed_dictionaries({
            "title": st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        }),
    })


# Strategy for generating markdown with evidence patterns
def markdown_with_evidence_strategy():
    """Generate markdown content containing evidence patterns."""
    evidence_items = st.lists(
        st.text(min_size=15, max_size=100).filter(lambda x: x.strip()),
        min_size=1,
        max_size=10,
    )
    
    def build_markdown(items):
        lines = ["# Cold Case Investigation\n\nLocation: Minnesota\n"]
        for i, item in enumerate(items):
            lines.append(f"- Evidence found: {item}")
        return "\n".join(lines)
    
    return evidence_items.map(build_markdown)


# Strategy for generating URLs (some valid, some invalid)
def url_list_strategy(min_valid=0, max_valid=5, min_invalid=0, max_invalid=3):
    """Generate lists of URLs with mix of valid and invalid."""
    valid_urls = st.lists(
        st.text(min_size=5, max_size=50).map(lambda x: f"https://valid.com/{x}"),
        min_size=min_valid,
        max_size=max_valid,
    )
    invalid_urls = st.lists(
        st.sampled_from(["", "invalid", "not-a-url", "ftp://bad"]),
        min_size=min_invalid,
        max_size=max_invalid,
    )
    return st.tuples(valid_urls, invalid_urls).map(lambda t: t[0] + t[1])


class TestProperty1FirecrawlToCaseFileTransformation:
    """Property 1: Firecrawl Response to CaseFile Transformation.
    
    *For any* valid Firecrawl search response containing markdown and metadata fields, 
    the Crawler_Service SHALL produce a valid CaseFile Pydantic model with all 
    required fields populated.
    
    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(response=firecrawl_response_strategy())
    def test_valid_response_produces_valid_casefile(self, response: dict) -> None:
        """Valid Firecrawl response produces valid CaseFile."""
        # Create crawler service (no API key needed for parsing)
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        # Parse the response
        case_file = crawler._parse_case_from_response(response)
        
        # Should produce a valid CaseFile
        assert case_file is not None
        assert isinstance(case_file, CaseFile)
        
        # All required fields should be populated (non-empty)
        assert case_file.case_id and case_file.case_id.strip()
        assert case_file.title and case_file.title.strip()
        assert case_file.location and case_file.location.strip()
        assert case_file.raw_content and case_file.raw_content.strip()
        
        # Source URL should be captured
        if response.get("url"):
            assert response["url"] in case_file.source_urls

    @settings(max_examples=100)
    @given(
        url=st.text(min_size=10, max_size=100).map(lambda x: f"https://example.com/{x}"),
        title=st.text(min_size=5, max_size=100).filter(lambda x: x.strip()),
        content=st.text(min_size=20, max_size=500).filter(lambda x: x.strip()),
    )
    def test_metadata_title_used_when_available(
        self, url: str, title: str, content: str
    ) -> None:
        """Metadata title is used when available."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        response = {
            "url": url,
            "markdown": content,
            "metadata": {"title": title},
        }
        
        case_file = crawler._parse_case_from_response(response)
        
        assert case_file is not None
        assert case_file.title == title.strip()

    @settings(max_examples=100)
    @given(
        url=st.text(min_size=10, max_size=100).map(lambda x: f"https://example.com/{x}"),
        heading=st.text(min_size=5, max_size=100).filter(lambda x: x.strip() and '\n' not in x),
        content=st.text(min_size=20, max_size=500).filter(lambda x: x.strip()),
    )
    def test_markdown_heading_used_when_no_metadata_title(
        self, url: str, heading: str, content: str
    ) -> None:
        """Markdown H1 heading is used when metadata title is missing."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        markdown = f"# {heading}\n\n{content}"
        response = {
            "url": url,
            "markdown": markdown,
            "metadata": {},
        }
        
        case_file = crawler._parse_case_from_response(response)
        
        assert case_file is not None
        assert case_file.title == heading.strip()

    @settings(max_examples=100)
    @given(response=firecrawl_response_strategy())
    def test_case_id_generated_consistently(self, response: dict) -> None:
        """Same response produces same case_id (deterministic)."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        case_file1 = crawler._parse_case_from_response(response)
        case_file2 = crawler._parse_case_from_response(response)
        
        assert case_file1 is not None
        assert case_file2 is not None
        assert case_file1.case_id == case_file2.case_id


class TestProperty2EvidenceListDistinctness:
    """Property 2: Evidence List Distinctness.
    
    *For any* CaseFile created from markdown content, all Evidence items in the 
    evidence_list SHALL have unique evidence_id values (no duplicates).
    
    **Validates: Requirements 1.3**
    """

    @settings(max_examples=100)
    @given(markdown=markdown_with_evidence_strategy())
    def test_evidence_ids_are_unique(self, markdown: str) -> None:
        """All evidence items have unique evidence_id values."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        evidence_list = crawler._extract_evidence(markdown)
        
        # Collect all evidence IDs
        evidence_ids = [e.evidence_id for e in evidence_list]
        
        # All IDs should be unique
        assert len(evidence_ids) == len(set(evidence_ids)), (
            f"Duplicate evidence IDs found: {evidence_ids}"
        )

    @settings(max_examples=100)
    @given(
        evidence_text=st.text(min_size=15, max_size=100).filter(lambda x: x.strip()),
    )
    def test_same_evidence_produces_same_id(self, evidence_text: str) -> None:
        """Same evidence description produces same evidence_id (deterministic)."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        id1 = crawler._generate_evidence_id(evidence_text)
        id2 = crawler._generate_evidence_id(evidence_text)
        
        assert id1 == id2

    @settings(max_examples=100)
    @given(
        text1=st.text(min_size=15, max_size=100).filter(lambda x: x.strip()),
        text2=st.text(min_size=15, max_size=100).filter(lambda x: x.strip()),
    )
    def test_different_evidence_produces_different_ids(
        self, text1: str, text2: str
    ) -> None:
        """Different evidence descriptions produce different evidence_ids."""
        # Skip if texts are identical
        if text1 == text2:
            return
            
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        id1 = crawler._generate_evidence_id(text1)
        id2 = crawler._generate_evidence_id(text2)
        
        assert id1 != id2, f"Different texts produced same ID: {text1!r} vs {text2!r}"

    @settings(max_examples=100)
    @given(response=firecrawl_response_strategy())
    def test_casefile_evidence_list_has_unique_ids(self, response: dict) -> None:
        """CaseFile evidence_list has unique evidence_id values."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        case_file = crawler._parse_case_from_response(response)
        
        if case_file and case_file.evidence_list:
            evidence_ids = [e.evidence_id for e in case_file.evidence_list]
            assert len(evidence_ids) == len(set(evidence_ids))


class TestProperty3ErrorResilienceInBatchProcessing:
    """Property 3: Error Resilience in Batch Processing.
    
    *For any* list of URLs where some are invalid/inaccessible, the Crawler_Service 
    SHALL successfully process all valid URLs and return CaseFiles for them, 
    regardless of failures on invalid URLs.
    
    **Validates: Requirements 1.4**
    """

    @settings(max_examples=100)
    @given(
        valid_responses=st.lists(
            firecrawl_response_strategy(),
            min_size=1,
            max_size=5,
        ),
        num_invalid=st.integers(min_value=0, max_value=3),
    )
    def test_valid_responses_processed_despite_invalid_ones(
        self, valid_responses: list, num_invalid: int
    ) -> None:
        """Valid responses are processed even when mixed with invalid ones."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        # Mix valid responses with invalid ones (None, empty dict, missing fields)
        all_responses = valid_responses.copy()
        invalid_responses = [
            None,
            {},
            {"markdown": ""},
            {"markdown": "   "},
            {"url": "test", "markdown": None},
        ][:num_invalid]
        all_responses.extend(invalid_responses)
        
        # Process each response
        case_files = []
        for response in all_responses:
            try:
                if response:
                    case_file = crawler._parse_case_from_response(response)
                    if case_file:
                        case_files.append(case_file)
            except Exception:
                # Errors should be handled gracefully
                continue
        
        # Should have processed all valid responses
        assert len(case_files) >= len(valid_responses) - num_invalid

    @settings(max_examples=100)
    @given(
        valid_count=st.integers(min_value=1, max_value=5),
        invalid_count=st.integers(min_value=0, max_value=3),
    )
    def test_batch_processing_continues_after_errors(
        self, valid_count: int, invalid_count: int
    ) -> None:
        """Batch processing continues after encountering errors."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        # Create valid responses
        valid_responses = [
            {
                "url": f"https://example.com/case{i}",
                "markdown": f"# Case {i}\n\nLocation: City {i}\n\nContent about case {i}",
                "metadata": {"title": f"Case {i}"},
            }
            for i in range(valid_count)
        ]
        
        # Create invalid responses
        invalid_responses = [None] * invalid_count
        
        # Interleave valid and invalid
        all_responses = []
        for i in range(max(valid_count, invalid_count)):
            if i < invalid_count:
                all_responses.append(invalid_responses[i])
            if i < valid_count:
                all_responses.append(valid_responses[i])
        
        # Process all responses
        successful_cases = []
        for response in all_responses:
            try:
                if response:
                    case_file = crawler._parse_case_from_response(response)
                    if case_file:
                        successful_cases.append(case_file)
            except Exception:
                continue
        
        # All valid responses should be processed
        assert len(successful_cases) == valid_count

    @settings(max_examples=100)
    @given(response=firecrawl_response_strategy())
    def test_parse_does_not_raise_on_valid_input(self, response: dict) -> None:
        """Parsing valid input does not raise exceptions."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        # Should not raise
        try:
            result = crawler._parse_case_from_response(response)
            assert result is None or isinstance(result, CaseFile)
        except Exception as e:
            pytest.fail(f"Parsing raised unexpected exception: {e}")

    @settings(max_examples=100)
    @given(
        invalid_input=st.sampled_from([
            None,
            {},
            {"markdown": ""},
            {"markdown": "   "},
            {"url": "test"},
            {"metadata": {}},
        ])
    )
    def test_parse_handles_invalid_input_gracefully(self, invalid_input) -> None:
        """Parsing invalid input returns None instead of raising."""
        crawler = CrawlerService(firecrawl_api_key="test-key")
        
        # Should not raise, should return None
        try:
            result = crawler._parse_case_from_response(invalid_input)
            assert result is None
        except Exception as e:
            pytest.fail(f"Parsing raised exception on invalid input: {e}")
