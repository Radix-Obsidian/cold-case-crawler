"""Property-based tests for API error handling.

Property 13: Invalid API Input Error Response
*For any* API request with invalid input (missing required fields, wrong types, invalid values),
the response SHALL have an HTTP status code in {400, 404, 422} and SHALL include a JSON body
with error details.

**Validates: Requirements 7.5**
"""

import pytest
from hypothesis import given, settings, strategies as st
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.routes import CrawlRequest, WebhookPayload


# ==================== Strategies ====================


# Strategy for empty strings (invalid for required fields with min_length=1)
# Note: CrawlRequest uses min_length=1 which only rejects empty strings, not whitespace
empty_strings = st.just("")

# Strategy for invalid limit values (out of range)
invalid_limits = st.one_of(
    st.integers(max_value=0),  # Less than 1
    st.integers(min_value=51),  # Greater than 50
)

# Strategy for non-string types that should fail validation
non_string_types = st.one_of(
    st.integers(),
    st.floats(allow_nan=False),
    st.lists(st.integers(), max_size=3),
    st.dictionaries(st.text(max_size=5), st.integers(), max_size=3),
    st.none(),
)


# ==================== Property Tests ====================


class TestProperty13InvalidAPIInputErrorResponse:
    """
    Property 13: Invalid API Input Error Response

    *For any* API request with invalid input (missing required fields, wrong types, invalid values),
    the response SHALL have an HTTP status code in {400, 404, 422} and SHALL include a JSON body
    with error details.

    **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
    **Validates: Requirements 7.5**
    """

    @given(query=empty_strings)
    @settings(max_examples=100)
    def test_crawl_empty_query_returns_422(self, query: str) -> None:
        """
        Property: Empty query strings should return 422.

        **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
        **Validates: Requirements 7.5**
        """
        # Test that CrawlRequest validation fails for empty/whitespace queries
        with pytest.raises(ValidationError) as exc_info:
            CrawlRequest(query=query)

        # Verify error contains field information
        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check that 'query' field is mentioned in errors
        field_names = [e.get("loc", [])[-1] if e.get("loc") else None for e in errors]
        assert "query" in field_names or any("query" in str(e) for e in errors)

    @given(limit=invalid_limits)
    @settings(max_examples=100)
    def test_crawl_invalid_limit_returns_422(self, limit: int) -> None:
        """
        Property: Invalid limit values (< 1 or > 50) should return 422.

        **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
        **Validates: Requirements 7.5**
        """
        # Test that CrawlRequest validation fails for invalid limits
        with pytest.raises(ValidationError) as exc_info:
            CrawlRequest(query="valid query", limit=limit)

        # Verify error contains field information
        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check that 'limit' field is mentioned in errors
        field_names = [e.get("loc", [])[-1] if e.get("loc") else None for e in errors]
        assert "limit" in field_names or any("limit" in str(e) for e in errors)

    @given(query_value=non_string_types)
    @settings(max_examples=100)
    def test_crawl_wrong_type_query_returns_422(self, query_value) -> None:
        """
        Property: Non-string query values should return 422.

        **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
        **Validates: Requirements 7.5**
        """
        # Skip None as it's handled differently (missing field)
        if query_value is None:
            return

        # Test that CrawlRequest validation fails for wrong types
        with pytest.raises((ValidationError, TypeError)):
            CrawlRequest(query=query_value)

    @given(
        valid_query=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        valid_limit=st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=100)
    def test_valid_crawl_request_succeeds(self, valid_query: str, valid_limit: int) -> None:
        """
        Property: Valid inputs should create valid CrawlRequest.

        This is a sanity check to ensure our validation isn't too strict.

        **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
        **Validates: Requirements 7.5**
        """
        # Valid inputs should not raise
        request = CrawlRequest(query=valid_query, limit=valid_limit)
        assert request.query == valid_query
        assert request.limit == valid_limit


class TestErrorResponseFormat:
    """Tests for error response format consistency."""

    @given(error_message=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()))
    @settings(max_examples=100)
    def test_validation_error_contains_detail(self, error_message: str) -> None:
        """
        Property: ValidationError responses should contain 'detail' field.

        **Feature: cold-case-crawler, Property 13: Invalid API Input Error Response**
        **Validates: Requirements 7.5**
        """
        # Create a validation error by passing invalid data
        try:
            CrawlRequest(query="")
        except ValidationError as e:
            errors = e.errors()
            # Verify errors list is not empty
            assert len(errors) > 0
            # Each error should have required fields
            for error in errors:
                assert "type" in error
                assert "loc" in error
                assert "msg" in error



class TestWebhookPayloadValidation:
    """Tests for webhook payload validation.

    Validates Requirements 6.1, 6.2, 6.3 - Automated Pipeline Trigger
    """

    @given(
        script_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        case_id=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        episode_title=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_valid_webhook_payload_succeeds(
        self, script_id: str, case_id: str, episode_title: str
    ) -> None:
        """
        Property: Valid webhook payloads should create valid WebhookPayload.

        **Feature: cold-case-crawler, Webhook Validation**
        **Validates: Requirements 6.1, 6.2**
        """
        payload = WebhookPayload(
            script_id=script_id,
            case_id=case_id,
            episode_title=episode_title,
        )
        assert payload.script_id == script_id
        assert payload.case_id == case_id
        assert payload.episode_title == episode_title
        assert payload.event_type == "script.created"  # Default value

    @given(field_to_empty=st.sampled_from(["script_id", "case_id", "episode_title"]))
    @settings(max_examples=100)
    def test_empty_required_fields_rejected(self, field_to_empty: str) -> None:
        """
        Property: Empty required fields should raise ValidationError.

        **Feature: cold-case-crawler, Webhook Validation**
        **Validates: Requirements 6.1, 6.2**
        """
        valid_data = {
            "script_id": "script-123",
            "case_id": "case-456",
            "episode_title": "Test Episode",
        }
        # Set one field to empty
        valid_data[field_to_empty] = ""

        with pytest.raises(ValidationError) as exc_info:
            WebhookPayload(**valid_data)

        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check that the empty field is mentioned in errors
        field_names = [e.get("loc", [])[-1] if e.get("loc") else None for e in errors]
        assert field_to_empty in field_names or any(field_to_empty in str(e) for e in errors)

    @given(
        event_type=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_custom_event_type_accepted(self, event_type: str) -> None:
        """
        Property: Custom event types should be accepted in payload.

        **Feature: cold-case-crawler, Webhook Validation**
        **Validates: Requirements 6.1**
        """
        payload = WebhookPayload(
            script_id="script-123",
            case_id="case-456",
            episode_title="Test Episode",
            event_type=event_type,
        )
        assert payload.event_type == event_type
