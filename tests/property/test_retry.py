"""Property-based tests for retry behavior.

Feature: cold-case-crawler
Property 9: Exponential Backoff Retry Behavior
Validates: Requirements 3.6
"""

import asyncio
from typing import Optional, Tuple
from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

from src.utils.retry import with_retry


class TestProperty9ExponentialBackoffRetry:
    """Property 9: Exponential Backoff Retry Behavior.
    
    *For any* sequence of API failures up to the retry limit, the delay between 
    retries SHALL follow exponential backoff (delay_n = base_delay * 2^n), and 
    the total number of attempts SHALL not exceed max_attempts.
    
    **Validates: Requirements 3.6**
    """

    @settings(max_examples=100, deadline=None)
    @given(
        max_attempts=st.integers(min_value=1, max_value=5),
        num_failures=st.integers(min_value=0, max_value=10),
    )
    def test_retry_attempts_not_exceed_max(
        self, max_attempts: int, num_failures: int
    ) -> None:
        """Total retry attempts SHALL not exceed max_attempts."""
        call_count = 0
        recorded_delays: list = []

        async def mock_sleep(delay: float) -> None:
            recorded_delays.append(delay)

        @with_retry(max_attempts=max_attempts, base_delay=0.001)
        async def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count <= num_failures:
                raise ValueError("Simulated failure")
            return "success"

        async def run_test() -> None:
            nonlocal call_count, recorded_delays
            call_count = 0
            recorded_delays = []
            with patch("src.utils.retry.asyncio.sleep", mock_sleep):
                try:
                    await failing_func()
                except ValueError:
                    pass  # Expected if num_failures >= max_attempts

        asyncio.get_event_loop().run_until_complete(run_test())
        assert call_count <= max_attempts

    @settings(max_examples=100, deadline=None)
    @given(
        max_attempts=st.integers(min_value=2, max_value=5),
        base_delay=st.floats(min_value=0.001, max_value=0.05),
    )
    def test_exponential_backoff_delays(
        self, max_attempts: int, base_delay: float
    ) -> None:
        """Delays SHALL follow exponential backoff pattern."""
        recorded_delays: list = []

        async def mock_sleep(delay: float) -> None:
            recorded_delays.append(delay)

        @with_retry(max_attempts=max_attempts, base_delay=base_delay)
        async def always_fails() -> str:
            raise ValueError("Always fails")

        async def run_test() -> None:
            nonlocal recorded_delays
            recorded_delays = []
            with patch("src.utils.retry.asyncio.sleep", mock_sleep):
                try:
                    await always_fails()
                except ValueError:
                    pass

        asyncio.get_event_loop().run_until_complete(run_test())

        # Should have max_attempts - 1 delays (no delay after last attempt)
        expected_delay_count = max_attempts - 1
        assert len(recorded_delays) == expected_delay_count

        # Verify exponential backoff pattern
        for i, delay in enumerate(recorded_delays):
            expected_delay = base_delay * (2**i)
            assert abs(delay - expected_delay) < 0.0001, (
                f"Delay {i} was {delay}, expected {expected_delay}"
            )

    @settings(max_examples=100, deadline=None)
    @given(
        max_attempts=st.integers(min_value=1, max_value=5),
        success_on_attempt=st.integers(min_value=1, max_value=5),
    )
    def test_success_after_failures(
        self, max_attempts: int, success_on_attempt: int
    ) -> None:
        """Function succeeds if success happens within max_attempts."""
        call_count = 0

        async def mock_sleep(delay: float) -> None:
            pass

        @with_retry(max_attempts=max_attempts, base_delay=0.001)
        async def eventually_succeeds() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < success_on_attempt:
                raise ValueError("Not yet")
            return "success"

        async def run_test() -> Tuple[Optional[str], bool]:
            nonlocal call_count
            call_count = 0
            with patch("src.utils.retry.asyncio.sleep", mock_sleep):
                try:
                    result = await eventually_succeeds()
                    return result, True
                except ValueError:
                    return None, False

        result, succeeded = asyncio.get_event_loop().run_until_complete(run_test())

        if success_on_attempt <= max_attempts:
            assert succeeded
            assert result == "success"
            assert call_count == success_on_attempt
        else:
            assert not succeeded
            assert call_count == max_attempts

    @settings(max_examples=100, deadline=None)
    @given(max_attempts=st.integers(min_value=1, max_value=5))
    def test_raises_last_exception_on_exhaustion(self, max_attempts: int) -> None:
        """When all attempts fail, the last exception is raised."""
        call_count = 0

        async def mock_sleep(delay: float) -> None:
            pass

        @with_retry(max_attempts=max_attempts, base_delay=0.001)
        async def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Failure {call_count}")

        async def run_test() -> str:
            nonlocal call_count
            call_count = 0
            with patch("src.utils.retry.asyncio.sleep", mock_sleep):
                try:
                    await always_fails()
                    return ""
                except ValueError as e:
                    return str(e)

        error_msg = asyncio.get_event_loop().run_until_complete(run_test())
        assert error_msg == f"Failure {max_attempts}"
        assert call_count == max_attempts

    @settings(max_examples=100, deadline=None)
    @given(max_attempts=st.integers(min_value=1, max_value=5))
    def test_only_catches_specified_exceptions(self, max_attempts: int) -> None:
        """Retry only catches specified exception types."""
        call_count = 0

        async def mock_sleep(delay: float) -> None:
            pass

        @with_retry(
            max_attempts=max_attempts,
            base_delay=0.001,
            exceptions=(ValueError,),
        )
        async def raises_type_error() -> str:
            nonlocal call_count
            call_count += 1
            raise TypeError("Not caught")

        async def run_test() -> bool:
            nonlocal call_count
            call_count = 0
            with patch("src.utils.retry.asyncio.sleep", mock_sleep):
                try:
                    await raises_type_error()
                    return False
                except TypeError:
                    return True

        raised_immediately = asyncio.get_event_loop().run_until_complete(run_test())
        assert raised_immediately
        assert call_count == 1  # No retries for uncaught exception type
