"""Property-based tests for data model validation.

Feature: cold-case-crawler
Properties 14, 15, 16, 17: Data Model Validation
Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
"""

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from src.models.case import CaseFile, Evidence
from src.models.script import DialogueLine, PodcastScript

# Strategies for valid values
valid_speakers = st.sampled_from(["dr_aris_thorne", "maya_vance"])
valid_emotion_tags = st.sampled_from([
    "scoffs", "clears_throat", "dramatic_pause", "sighs",
    "excited", "whispers", "interrupting", "gasps", "neutral"
])
non_empty_text = st.text(min_size=1, max_size=500).filter(lambda x: x.strip())

# Strategies for invalid values
empty_or_whitespace = st.sampled_from(["", " ", "  ", "\t", "\n", "   \t\n  "])
invalid_speakers = st.text(min_size=1, max_size=50).filter(
    lambda x: x not in ["dr_aris_thorne", "maya_vance"]
)
invalid_emotion_tags = st.text(min_size=1, max_size=50).filter(
    lambda x: x not in [
        "scoffs", "clears_throat", "dramatic_pause", "sighs",
        "excited", "whispers", "interrupting", "gasps", "neutral"
    ]
)


class TestProperty14RequiredNonEmptyFields:
    """Property 14: Required Non-Empty Fields Validation.
    
    *For any* attempt to create a CaseFile, PodcastScript, or DialogueLine 
    with an empty string or whitespace-only value for required fields 
    (case_id, location, episode_title, text), Pydantic SHALL raise a ValidationError.
    
    **Validates: Requirements 8.1, 8.2, 8.3**
    """

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_casefile_case_id_rejects_empty(self, empty_value: str) -> None:
        """CaseFile rejects empty/whitespace case_id."""
        with pytest.raises(ValidationError):
            CaseFile(
                case_id=empty_value,
                title="Valid Title",
                location="Minnesota",
                raw_content="Valid content",
            )

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_casefile_location_rejects_empty(self, empty_value: str) -> None:
        """CaseFile rejects empty/whitespace location."""
        with pytest.raises(ValidationError):
            CaseFile(
                case_id="case-001",
                title="Valid Title",
                location=empty_value,
                raw_content="Valid content",
            )

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_podcastscript_episode_title_rejects_empty(self, empty_value: str) -> None:
        """PodcastScript rejects empty/whitespace episode_title."""
        valid_line = DialogueLine(speaker="maya_vance", text="Valid text")
        with pytest.raises(ValidationError):
            PodcastScript(
                script_id="script-001",
                case_id="case-001",
                episode_title=empty_value,
                chapters=[valid_line],
            )

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_dialogueline_text_rejects_empty(self, empty_value: str) -> None:
        """DialogueLine rejects empty/whitespace text."""
        with pytest.raises(ValidationError):
            DialogueLine(speaker="maya_vance", text=empty_value)


class TestProperty15ListMinimumLength:
    """Property 15: List Minimum Length Validation.
    
    *For any* attempt to create a PodcastScript with an empty chapters list, 
    Pydantic SHALL raise a ValidationError indicating the minimum length constraint.
    
    **Validates: Requirements 8.4**
    """

    @settings(max_examples=100)
    @given(
        script_id=non_empty_text,
        case_id=non_empty_text,
        episode_title=non_empty_text,
    )
    def test_podcastscript_empty_chapters_rejected(
        self, script_id: str, case_id: str, episode_title: str
    ) -> None:
        """PodcastScript rejects empty chapters list."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastScript(
                script_id=script_id,
                case_id=case_id,
                episode_title=episode_title,
                chapters=[],
            )
        # Verify the error mentions the minimum length constraint
        errors = exc_info.value.errors()
        assert any("chapters" in str(e.get("loc", "")) for e in errors)


class TestProperty16LiteralEnumValidation:
    """Property 16: Literal/Enum Field Validation.
    
    *For any* attempt to create a DialogueLine with a speaker value not in 
    {'dr_aris_thorne', 'maya_vance'} or an emotion_tag not in the allowed set, 
    Pydantic SHALL raise a ValidationError.
    
    **Validates: Requirements 8.5, 8.6**
    """

    @settings(max_examples=100)
    @given(invalid_speaker=invalid_speakers, text=non_empty_text)
    def test_dialogueline_invalid_speaker_rejected(
        self, invalid_speaker: str, text: str
    ) -> None:
        """DialogueLine rejects invalid speaker values."""
        with pytest.raises(ValidationError):
            DialogueLine(speaker=invalid_speaker, text=text)  # type: ignore

    @settings(max_examples=100)
    @given(
        speaker=valid_speakers,
        text=non_empty_text,
        invalid_tag=invalid_emotion_tags,
    )
    def test_dialogueline_invalid_emotion_tag_rejected(
        self, speaker: str, text: str, invalid_tag: str
    ) -> None:
        """DialogueLine rejects invalid emotion_tag values."""
        with pytest.raises(ValidationError):
            DialogueLine(speaker=speaker, text=text, emotion_tag=invalid_tag)  # type: ignore

    @settings(max_examples=100)
    @given(speaker=valid_speakers, text=non_empty_text, tag=valid_emotion_tags)
    def test_dialogueline_valid_values_accepted(
        self, speaker: str, text: str, tag: str
    ) -> None:
        """DialogueLine accepts valid speaker and emotion_tag values."""
        line = DialogueLine(speaker=speaker, text=text, emotion_tag=tag)  # type: ignore
        assert line.speaker == speaker
        assert line.text == text
        assert line.emotion_tag == tag


class TestProperty17ValidationErrorFieldIdentification:
    """Property 17: Validation Error Field Identification.
    
    *For any* Pydantic ValidationError raised during model creation, 
    the error SHALL include the field name(s) that failed validation in the error details.
    
    **Validates: Requirements 8.7**
    """

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_validation_error_identifies_case_id_field(self, empty_value: str) -> None:
        """ValidationError identifies case_id field."""
        with pytest.raises(ValidationError) as exc_info:
            CaseFile(
                case_id=empty_value,
                title="Valid Title",
                location="Minnesota",
                raw_content="Valid content",
            )
        errors = exc_info.value.errors()
        field_names = [str(e.get("loc", ())) for e in errors]
        assert any("case_id" in name for name in field_names)

    @settings(max_examples=100)
    @given(empty_value=empty_or_whitespace)
    def test_validation_error_identifies_text_field(self, empty_value: str) -> None:
        """ValidationError identifies text field."""
        with pytest.raises(ValidationError) as exc_info:
            DialogueLine(speaker="maya_vance", text=empty_value)
        errors = exc_info.value.errors()
        field_names = [str(e.get("loc", ())) for e in errors]
        assert any("text" in name for name in field_names)

    @settings(max_examples=100)
    @given(invalid_speaker=invalid_speakers)
    def test_validation_error_identifies_speaker_field(self, invalid_speaker: str) -> None:
        """ValidationError identifies speaker field."""
        with pytest.raises(ValidationError) as exc_info:
            DialogueLine(speaker=invalid_speaker, text="Valid text")  # type: ignore
        errors = exc_info.value.errors()
        field_names = [str(e.get("loc", ())) for e in errors]
        assert any("speaker" in name for name in field_names)

    @settings(max_examples=100)
    @given(
        script_id=non_empty_text,
        case_id=non_empty_text,
        episode_title=non_empty_text,
    )
    def test_validation_error_identifies_chapters_field(
        self, script_id: str, case_id: str, episode_title: str
    ) -> None:
        """ValidationError identifies chapters field."""
        with pytest.raises(ValidationError) as exc_info:
            PodcastScript(
                script_id=script_id,
                case_id=case_id,
                episode_title=episode_title,
                chapters=[],
            )
        errors = exc_info.value.errors()
        field_names = [str(e.get("loc", ())) for e in errors]
        assert any("chapters" in name for name in field_names)
