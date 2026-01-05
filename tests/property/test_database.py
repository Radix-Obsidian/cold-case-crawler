"""Property-based tests for database operations.

Feature: cold-case-crawler
Properties 11, 12: Database Integrity and Query Filtering
Validates: Requirements 5.3, 5.4, 5.5
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from hypothesis import given, settings, strategies as st

from src.models.case import CaseFile, Evidence
from src.models.script import DialogueLine, PodcastScript
from src.services.database import DatabaseService


# ==================== Mock Supabase Client ====================


class MockSupabaseResponse:
    """Mock response from Supabase operations."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None) -> None:
        self.data = data or []


class MockSupabaseTable:
    """Mock Supabase table for testing database operations."""

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._table_name: str = ""
        self._filters: List[tuple[str, str, Any]] = []
        self._select_columns: str = "*"
        self._limit_value: Optional[int] = None

    def _reset_query(self) -> None:
        """Reset query state."""
        self._filters = []
        self._select_columns = "*"
        self._limit_value = None

    def select(self, columns: str = "*") -> "MockSupabaseTable":
        """Mock select operation."""
        self._select_columns = columns
        return self

    def insert(self, data: Dict[str, Any]) -> "MockSupabaseTable":
        """Mock insert operation."""
        # Determine primary key based on table
        pk_field = self._get_pk_field()
        pk_value = data.get(pk_field)
        if pk_value:
            self._data[pk_value] = data.copy()
        return self

    def update(self, data: Dict[str, Any]) -> "MockSupabaseTable":
        """Mock update operation - stores update data for later execution."""
        self._update_data = data
        return self

    def delete(self) -> "MockSupabaseTable":
        """Mock delete operation."""
        self._is_delete = True
        return self

    def eq(self, field: str, value: Any) -> "MockSupabaseTable":
        """Mock eq filter."""
        self._filters.append(("eq", field, value))
        return self

    def limit(self, count: int) -> "MockSupabaseTable":
        """Mock limit operation."""
        self._limit_value = count
        return self

    def execute(self) -> MockSupabaseResponse:
        """Execute the mock query."""
        # Handle delete
        if hasattr(self, "_is_delete") and self._is_delete:
            self._is_delete = False
            keys_to_delete = []
            for pk, record in self._data.items():
                if self._matches_filters(record):
                    keys_to_delete.append(pk)
            deleted = []
            for pk in keys_to_delete:
                deleted.append(self._data.pop(pk))
            self._reset_query()
            return MockSupabaseResponse(deleted)

        # Handle update
        if hasattr(self, "_update_data"):
            update_data = self._update_data
            del self._update_data
            updated = []
            for pk, record in self._data.items():
                if self._matches_filters(record):
                    record.update(update_data)
                    updated.append(record)
            self._reset_query()
            return MockSupabaseResponse(updated)

        # Handle select
        results = []
        for record in self._data.values():
            if self._matches_filters(record):
                results.append(record)

        if self._limit_value:
            results = results[: self._limit_value]

        self._reset_query()
        return MockSupabaseResponse(results)

    def _matches_filters(self, record: Dict[str, Any]) -> bool:
        """Check if record matches all filters."""
        for op, field, value in self._filters:
            if op == "eq":
                if record.get(field) != value:
                    return False
        return True

    def _get_pk_field(self) -> str:
        """Get primary key field for current table."""
        pk_map = {
            "cases": "case_id",
            "scripts": "script_id",
            "media": "media_id",
            "jobs": "job_id",
            "evidence": "evidence_id",
        }
        return pk_map.get(self._table_name, "id")


class MockSupabaseClient:
    """Mock Supabase client for testing."""

    def __init__(self) -> None:
        self._tables: Dict[str, MockSupabaseTable] = {}

    def table(self, name: str) -> MockSupabaseTable:
        """Get or create a mock table."""
        if name not in self._tables:
            self._tables[name] = MockSupabaseTable()
        table = self._tables[name]
        table._table_name = name
        return table

    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all records from a table (for testing)."""
        if table_name in self._tables:
            return list(self._tables[table_name]._data.values())
        return []


# ==================== Hypothesis Strategies ====================

# Strategy for valid non-empty text
non_empty_text = st.text(min_size=1, max_size=100).filter(lambda x: x.strip())

# Strategy for valid speakers
valid_speakers = st.sampled_from(["dr_aris_thorne", "maya_vance"])

# Strategy for valid emotion tags
valid_emotion_tags = st.sampled_from([
    "scoffs", "clears_throat", "dramatic_pause", "sighs",
    "excited", "whispers", "interrupting", "gasps", "neutral"
])

# Strategy for valid locations
valid_locations = st.sampled_from([
    "Minnesota", "California", "Texas", "New York", "Florida",
    "Ohio", "Illinois", "Pennsylvania", "Georgia", "Michigan"
])


@st.composite
def case_file_strategy(draw: st.DrawFn) -> CaseFile:
    """Generate valid CaseFile instances."""
    case_id = f"case-{draw(st.uuids())}"
    title = draw(non_empty_text)
    location = draw(valid_locations)
    raw_content = draw(non_empty_text)

    return CaseFile(
        case_id=case_id,
        title=title,
        location=location,
        raw_content=raw_content,
        evidence_list=[],
        source_urls=[],
    )


@st.composite
def dialogue_line_strategy(draw: st.DrawFn) -> DialogueLine:
    """Generate valid DialogueLine instances."""
    return DialogueLine(
        speaker=draw(valid_speakers),
        text=draw(non_empty_text),
        emotion_tag=draw(valid_emotion_tags),
    )


@st.composite
def podcast_script_strategy(draw: st.DrawFn, case_id: Optional[str] = None) -> PodcastScript:
    """Generate valid PodcastScript instances."""
    script_id = f"script-{draw(st.uuids())}"
    actual_case_id = case_id or f"case-{draw(st.uuids())}"
    episode_title = draw(non_empty_text)

    # Generate 1-5 dialogue lines
    num_lines = draw(st.integers(min_value=1, max_value=5))
    chapters = [draw(dialogue_line_strategy()) for _ in range(num_lines)]

    return PodcastScript(
        script_id=script_id,
        case_id=actual_case_id,
        episode_title=episode_title,
        chapters=chapters,
        social_hooks=[],
    )


# ==================== Property Tests ====================


class TestProperty11DatabaseIntegrity:
    """Property 11: Database Integrity - Unique IDs and Valid Foreign Keys.

    *For any* set of stored CaseFiles and PodcastScripts:
    - All case_id values SHALL be unique across CaseFiles
    - All script_id values SHALL be unique across PodcastScripts
    - Every PodcastScript.case_id SHALL reference an existing CaseFile.case_id

    **Validates: Requirements 5.3, 5.4**
    """

    @settings(max_examples=100)
    @given(cases=st.lists(case_file_strategy(), min_size=1, max_size=10))
    @pytest.mark.asyncio
    async def test_case_ids_are_unique(self, cases: List[CaseFile]) -> None:
        """All case_id values are unique across stored CaseFiles."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store all cases
        stored_ids = set()
        for case in cases:
            await db_service.create_case(case)
            stored_ids.add(case.case_id)

        # Verify all stored records have unique IDs
        all_records = mock_client.get_all_records("cases")
        stored_case_ids = [r["case_id"] for r in all_records]

        # Each ID should appear exactly once
        assert len(stored_case_ids) == len(set(stored_case_ids))

    @settings(max_examples=100)
    @given(
        case=case_file_strategy(),
        num_scripts=st.integers(min_value=1, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_script_ids_are_unique(
        self, case: CaseFile, num_scripts: int
    ) -> None:
        """All script_id values are unique across stored PodcastScripts."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store the case first
        await db_service.create_case(case)

        # Generate and store multiple scripts for the same case
        stored_script_ids = set()
        for i in range(num_scripts):
            script = PodcastScript(
                script_id=f"script-{uuid4()}",
                case_id=case.case_id,
                episode_title=f"Episode {i + 1}",
                chapters=[DialogueLine(speaker="maya_vance", text=f"Line {i}")],
            )
            await db_service.create_script(script)
            stored_script_ids.add(script.script_id)

        # Verify all stored scripts have unique IDs
        all_records = mock_client.get_all_records("scripts")
        stored_ids = [r["script_id"] for r in all_records]

        assert len(stored_ids) == len(set(stored_ids))

    @settings(max_examples=100)
    @given(case=case_file_strategy())
    @pytest.mark.asyncio
    async def test_script_references_existing_case(self, case: CaseFile) -> None:
        """Every PodcastScript.case_id references an existing CaseFile.case_id."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store the case
        await db_service.create_case(case)

        # Create a script referencing the case
        script = PodcastScript(
            script_id=f"script-{uuid4()}",
            case_id=case.case_id,
            episode_title="Test Episode",
            chapters=[DialogueLine(speaker="maya_vance", text="Test line")],
        )
        await db_service.create_script(script)

        # Verify the script's case_id exists in cases table
        case_exists = await db_service.case_exists(script.case_id)
        assert case_exists is True

    @settings(max_examples=100)
    @given(case=case_file_strategy())
    @pytest.mark.asyncio
    async def test_retrieved_case_matches_stored(self, case: CaseFile) -> None:
        """Retrieved case data matches what was stored."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store the case
        await db_service.create_case(case)

        # Retrieve and verify
        retrieved = await db_service.get_case(case.case_id)

        assert retrieved is not None
        assert retrieved.case_id == case.case_id
        assert retrieved.title == case.title
        assert retrieved.location == case.location
        assert retrieved.raw_content == case.raw_content


class TestProperty12QueryFilteringCorrectness:
    """Property 12: Query Filtering Correctness.

    *For any* query with case_id or location filter, the returned results
    SHALL only contain records where the filtered field exactly matches
    the filter value.

    **Validates: Requirements 5.5**
    """

    @settings(max_examples=100)
    @given(
        cases=st.lists(case_file_strategy(), min_size=2, max_size=10),
    )
    @pytest.mark.asyncio
    async def test_filter_by_case_id_returns_exact_match(
        self, cases: List[CaseFile]
    ) -> None:
        """Filtering by case_id returns only the exact matching case."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store all cases
        for case in cases:
            await db_service.create_case(case)

        # Query for a specific case
        target_case = cases[0]
        retrieved = await db_service.get_case(target_case.case_id)

        # Verify exact match
        assert retrieved is not None
        assert retrieved.case_id == target_case.case_id

    @settings(max_examples=100)
    @given(
        location=valid_locations,
        num_matching=st.integers(min_value=1, max_value=5),
        num_non_matching=st.integers(min_value=0, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_filter_by_location_returns_only_matching(
        self, location: str, num_matching: int, num_non_matching: int
    ) -> None:
        """Filtering by location returns only cases with exact location match."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Create cases with the target location
        matching_cases = []
        for i in range(num_matching):
            case = CaseFile(
                case_id=f"case-match-{uuid4()}",
                title=f"Matching Case {i}",
                location=location,
                raw_content=f"Content {i}",
            )
            await db_service.create_case(case)
            matching_cases.append(case)

        # Create cases with different locations
        other_locations = [loc for loc in [
            "Minnesota", "California", "Texas", "New York", "Florida"
        ] if loc != location]

        for i in range(num_non_matching):
            other_loc = other_locations[i % len(other_locations)]
            case = CaseFile(
                case_id=f"case-other-{uuid4()}",
                title=f"Other Case {i}",
                location=other_loc,
                raw_content=f"Other content {i}",
            )
            await db_service.create_case(case)

        # Query by location
        results = await db_service.get_cases_by_location(location)

        # Verify all results have the exact location
        for result in results:
            assert result.location == location

        # Verify we got the expected number of matching cases
        assert len(results) == num_matching

    @settings(max_examples=100)
    @given(case=case_file_strategy())
    @pytest.mark.asyncio
    async def test_filter_by_script_case_id_returns_only_matching(
        self, case: CaseFile
    ) -> None:
        """Filtering scripts by case_id returns only scripts for that case."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store the case
        await db_service.create_case(case)

        # Create scripts for this case
        scripts_for_case = []
        for i in range(3):
            script = PodcastScript(
                script_id=f"script-{uuid4()}",
                case_id=case.case_id,
                episode_title=f"Episode {i}",
                chapters=[DialogueLine(speaker="maya_vance", text=f"Line {i}")],
            )
            await db_service.create_script(script)
            scripts_for_case.append(script)

        # Create another case with its own scripts
        other_case = CaseFile(
            case_id=f"case-other-{uuid4()}",
            title="Other Case",
            location="California",
            raw_content="Other content",
        )
        await db_service.create_case(other_case)

        other_script = PodcastScript(
            script_id=f"script-other-{uuid4()}",
            case_id=other_case.case_id,
            episode_title="Other Episode",
            chapters=[DialogueLine(speaker="dr_aris_thorne", text="Other line")],
        )
        await db_service.create_script(other_script)

        # Query scripts by case_id
        results = await db_service.get_scripts_by_case_id(case.case_id)

        # Verify all results belong to the queried case
        for result in results:
            assert result.case_id == case.case_id

        # Verify we got the expected number
        assert len(results) == len(scripts_for_case)

    @settings(max_examples=100)
    @given(case=case_file_strategy())
    @pytest.mark.asyncio
    async def test_nonexistent_case_id_returns_none(self, case: CaseFile) -> None:
        """Querying for non-existent case_id returns None."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Store a case
        await db_service.create_case(case)

        # Query for a different case_id
        nonexistent_id = f"case-nonexistent-{uuid4()}"
        result = await db_service.get_case(nonexistent_id)

        assert result is None

    @settings(max_examples=100)
    @given(location=valid_locations)
    @pytest.mark.asyncio
    async def test_nonexistent_location_returns_empty(self, location: str) -> None:
        """Querying for non-existent location returns empty list."""
        mock_client = MockSupabaseClient()
        db_service = DatabaseService(mock_client)

        # Create cases with different locations
        other_locations = [loc for loc in [
            "Minnesota", "California", "Texas", "New York", "Florida"
        ] if loc != location]

        for i, loc in enumerate(other_locations[:2]):
            case = CaseFile(
                case_id=f"case-{uuid4()}",
                title=f"Case {i}",
                location=loc,
                raw_content=f"Content {i}",
            )
            await db_service.create_case(case)

        # Query for the location that wasn't used
        results = await db_service.get_cases_by_location(location)

        assert results == []
