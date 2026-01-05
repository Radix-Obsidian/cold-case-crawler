"""Pytest fixtures for Murder Index tests."""

import pytest


@pytest.fixture
def sample_case_data() -> dict:
    """Sample case data for testing."""
    return {
        "case_id": "case-001",
        "title": "The Minnesota Mystery",
        "location": "Minnesota",
        "date_occurred": "1987-12-14",
        "raw_content": "A quiet suburb in Minnesota...",
        "evidence_list": [],
        "source_urls": ["https://example.com/case"],
    }


@pytest.fixture
def sample_dialogue_data() -> dict:
    """Sample dialogue line data for testing."""
    return {
        "speaker": "maya_vance",
        "text": "This is compelling evidence.",
        "emotion_tag": "excited",
    }
