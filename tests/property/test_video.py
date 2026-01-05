"""Property-based tests for video service.

Feature: cold-case-crawler
Property 10: Social Hooks Extraction Completeness
Validates: Requirements 4.1
"""

from unittest.mock import AsyncMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from src.models.script import DialogueLine, PodcastScript
from src.services.video import VideoService


# Strategies for generating valid DialogueLines
valid_speakers = st.sampled_from(["dr_aris_thorne", "maya_vance"])
valid_emotion_tags = st.sampled_from([
    "scoffs", "clears_throat", "dramatic_pause", "sighs",
    "excited", "whispers", "interrupting", "gasps", "neutral"
])
non_empty_text = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())


def dialogue_line_strategy() -> st.SearchStrategy[DialogueLine]:
    """Strategy for generating valid DialogueLine objects."""
    return st.builds(
        DialogueLine,
        speaker=valid_speakers,
        text=non_empty_text,
        emotion_tag=valid_emotion_tags,
    )


# Strategy for generating social hooks (non-empty strings)
social_hook_strategy = st.text(min_size=1, max_size=200).filter(lambda x: x.strip())


def podcast_script_with_hooks_strategy(
    min_hooks: int = 1, max_hooks: int = 10
) -> st.SearchStrategy[PodcastScript]:
    """Strategy for generating PodcastScript with social hooks."""
    return st.builds(
        PodcastScript,
        script_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()).map(lambda x: f"script-{x}"),
        case_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()).map(lambda x: f"case-{x}"),
        episode_title=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        chapters=st.lists(dialogue_line_strategy(), min_size=1, max_size=5),
        social_hooks=st.lists(social_hook_strategy, min_size=min_hooks, max_size=max_hooks),
    )


class TestProperty10SocialHooksExtractionCompleteness:
    """Property 10: Social Hooks Extraction Completeness.
    
    *For any* PodcastScript with a non-empty social_hooks list, the Video_Service 
    SHALL extract all hooks for video generation (output count equals input count).
    
    **Validates: Requirements 4.1**
    """

    @settings(max_examples=100)
    @given(script=podcast_script_with_hooks_strategy(min_hooks=1, max_hooks=10))
    @pytest.mark.asyncio
    async def test_all_social_hooks_processed(
        self, script: PodcastScript
    ) -> None:
        """All social hooks in a script are processed for video generation."""
        video_service = VideoService(
            creatomate_api_key="test-key",
            template_id="test-template",
        )
        
        # Track which hooks would be processed
        processed_hooks: list[str] = []
        
        # Mock generate_clip to track calls without making real API requests
        async def mock_generate_clip(hook: str, audio_url: str) -> str:
            processed_hooks.append(hook)
            return f"https://example.com/video/{len(processed_hooks)}.mp4"
        
        with patch.object(video_service, "generate_clip", side_effect=mock_generate_clip):
            audio_url = "https://example.com/audio.mp3"
            video_urls = await video_service.generate_all_clips(script, audio_url)
        
        # Verify all hooks were processed
        assert len(processed_hooks) == len(script.social_hooks), (
            f"Expected {len(script.social_hooks)} hooks to be processed, "
            f"got {len(processed_hooks)}"
        )
        
        # Verify output count equals input count
        assert len(video_urls) == len(script.social_hooks), (
            f"Expected {len(script.social_hooks)} video URLs, got {len(video_urls)}"
        )
        
        # Verify all original hooks were processed (content check)
        for hook in script.social_hooks:
            assert hook in processed_hooks, (
                f"Hook '{hook}' was not processed"
            )

    @settings(max_examples=100)
    @given(hooks=st.lists(social_hook_strategy, min_size=1, max_size=15))
    @pytest.mark.asyncio
    async def test_hook_count_equals_video_count(
        self, hooks: list[str]
    ) -> None:
        """Number of generated videos equals number of social hooks."""
        script = PodcastScript(
            script_id="test-script-001",
            case_id="test-case-001",
            episode_title="Test Episode",
            chapters=[
                DialogueLine(speaker="maya_vance", text="Test dialogue")
            ],
            social_hooks=hooks,
        )
        
        video_service = VideoService(
            creatomate_api_key="test-key",
            template_id="test-template",
        )
        
        # Mock generate_clip to return a URL for each hook
        call_count = 0
        
        async def mock_generate_clip(hook: str, audio_url: str) -> str:
            nonlocal call_count
            call_count += 1
            return f"https://example.com/video/{call_count}.mp4"
        
        with patch.object(video_service, "generate_clip", side_effect=mock_generate_clip):
            audio_url = "https://example.com/audio.mp3"
            video_urls = await video_service.generate_all_clips(script, audio_url)
        
        # Property: output count equals input count
        assert len(video_urls) == len(hooks), (
            f"Expected {len(hooks)} videos, got {len(video_urls)}"
        )
        
        # Verify generate_clip was called for each hook
        assert call_count == len(hooks), (
            f"Expected {len(hooks)} generate_clip calls, got {call_count}"
        )

    @settings(max_examples=100)
    @given(script=podcast_script_with_hooks_strategy(min_hooks=1, max_hooks=10))
    @pytest.mark.asyncio
    async def test_hooks_processed_in_order(
        self, script: PodcastScript
    ) -> None:
        """Social hooks are processed in their original order."""
        video_service = VideoService(
            creatomate_api_key="test-key",
            template_id="test-template",
        )
        
        # Track order of hook processing
        processing_order: list[str] = []
        
        async def mock_generate_clip(hook: str, audio_url: str) -> str:
            processing_order.append(hook)
            return f"https://example.com/video/{len(processing_order)}.mp4"
        
        with patch.object(video_service, "generate_clip", side_effect=mock_generate_clip):
            audio_url = "https://example.com/audio.mp3"
            await video_service.generate_all_clips(script, audio_url)
        
        # Verify hooks were processed in original order
        assert processing_order == script.social_hooks, (
            "Hooks should be processed in their original order"
        )

    @pytest.mark.asyncio
    async def test_empty_hooks_returns_empty_list(self) -> None:
        """Script with no social hooks returns empty video list."""
        script = PodcastScript(
            script_id="test-script-001",
            case_id="test-case-001",
            episode_title="Test Episode",
            chapters=[
                DialogueLine(speaker="maya_vance", text="Test dialogue")
            ],
            social_hooks=[],  # Empty hooks
        )
        
        video_service = VideoService(
            creatomate_api_key="test-key",
            template_id="test-template",
        )
        
        audio_url = "https://example.com/audio.mp3"
        video_urls = await video_service.generate_all_clips(script, audio_url)
        
        assert video_urls == [], (
            "Empty social hooks should return empty video list"
        )
