"""Debate engine service for generating podcast scripts using PydanticAI agents."""

import logging
from typing import Any, List, Optional
from uuid import uuid4

from src.agents.maya import create_maya_agent
from src.agents.thorne import create_thorne_agent
from src.models.case import CaseFile
from src.models.script import DialogueLine, PodcastScript
from src.utils.errors import AgentResponseError, DebateEngineError

logger = logging.getLogger(__name__)


class DebateEngine:
    """Service for generating debate-style podcast scripts between two AI hosts."""

    def __init__(
        self,
        supabase_client: Optional[Any] = None,
    ) -> None:
        """
        Initialize the DebateEngine.

        Args:
            supabase_client: Supabase client for persistence (optional)
        """
        self.thorne = create_thorne_agent()
        self.maya = create_maya_agent()
        self.supabase = supabase_client

    async def generate_debate(
        self,
        case: CaseFile,
        num_exchanges: int = 10,
    ) -> PodcastScript:
        """
        Generate alternating dialogue between hosts about the case.

        Args:
            case: The CaseFile to debate
            num_exchanges: Number of back-and-forth exchanges (default 10)

        Returns:
            PodcastScript containing the complete debate

        Raises:
            DebateEngineError: If debate generation fails
            AgentResponseError: If an agent fails to generate valid response
        """
        dialogue_lines: List[DialogueLine] = []

        try:
            for exchange_num in range(num_exchanges):
                # Maya speaks first in each exchange
                maya_prompt = self._build_prompt(case, dialogue_lines, "maya")
                maya_result = await self.maya.run(maya_prompt, deps=case)

                if not maya_result or not maya_result.output:
                    raise AgentResponseError(
                        f"Maya agent failed to generate response at exchange {exchange_num + 1}"
                    )

                # Ensure Maya's line has correct speaker
                maya_line = DialogueLine(
                    speaker="maya_vance",
                    text=maya_result.output.text,
                    emotion_tag=maya_result.output.emotion_tag,
                )
                dialogue_lines.append(maya_line)

                # Thorne responds
                thorne_prompt = self._build_prompt(case, dialogue_lines, "thorne")
                thorne_result = await self.thorne.run(thorne_prompt, deps=case)

                if not thorne_result or not thorne_result.output:
                    raise AgentResponseError(
                        f"Thorne agent failed to generate response at exchange {exchange_num + 1}"
                    )

                # Ensure Thorne's line has correct speaker
                thorne_line = DialogueLine(
                    speaker="dr_aris_thorne",
                    text=thorne_result.output.text,
                    emotion_tag=thorne_result.output.emotion_tag,
                )
                dialogue_lines.append(thorne_line)

                logger.debug(f"Completed exchange {exchange_num + 1}/{num_exchanges}")

        except AgentResponseError:
            raise
        except Exception as e:
            raise DebateEngineError(f"Debate generation failed: {e}")

        # Compile the script
        return self.compile_script(case, dialogue_lines)

    def _build_prompt(
        self,
        case: CaseFile,
        context: List[DialogueLine],
        speaker: str,
    ) -> str:
        """
        Construct context-aware prompts for agents.

        Args:
            case: The CaseFile being discussed
            context: Previous dialogue lines in the conversation
            speaker: Which speaker is being prompted ("maya" or "thorne")

        Returns:
            Formatted prompt string for the agent
        """
        # Build case context
        case_context = f"""
CASE INFORMATION:
Title: {case.title}
Location: {case.location}
Date: {case.date_occurred or "Unknown"}

CASE DETAILS:
{case.raw_content[:2000]}  # Limit to avoid token overflow
"""

        # Add evidence summary if available
        if case.evidence_list:
            evidence_summary = "\n".join(
                f"- {ev.evidence_type}: {ev.description[:100]}"
                for ev in case.evidence_list[:5]  # Limit to top 5
            )
            case_context += f"\nKEY EVIDENCE:\n{evidence_summary}"

        # Build conversation context
        conversation_context = ""
        if context:
            recent_lines = context[-6:]  # Last 3 exchanges
            conversation_context = "\nRECENT CONVERSATION:\n"
            for line in recent_lines:
                speaker_name = "Maya" if line.speaker == "maya_vance" else "Dr. Thorne"
                conversation_context += f"{speaker_name}: {line.text}\n"

        # Build the prompt based on speaker
        if speaker == "maya":
            if not context:
                instruction = """
You are OPENING this episode of Dead Air. This is the INTRO.
- Welcome listeners to Dead Air
- Introduce yourself and mention Dr. Thorne
- Briefly tease this week's case to hook listeners
- Set the tone for the investigation ahead
Generate your opening dialogue line as Maya Vance.
"""
            elif len(context) >= 28:  # Near the end (for 15 exchanges)
                instruction = """
You are CLOSING this episode of Dead Air. This is the OUTRO.
- Summarize the key theories discussed
- Thank listeners for joining
- Remind them to subscribe and follow Dead Air for next week's case
- Sign off with warmth
Generate your closing dialogue line as Maya Vance.
"""
            else:
                instruction = """
Continue the discussion as Maya Vance.
Respond to Dr. Thorne's points while advancing your narrative perspective.
Generate your next dialogue line.
"""
        else:  # thorne
            if len(context) == 1:  # First response after Maya's intro
                instruction = """
Maya just opened the show. Respond as Dr. Thorne with your intro.
- Greet listeners with your characteristic dry wit
- Acknowledge Maya's enthusiasm
- Set expectations for evidence-based analysis
Generate your opening dialogue line as Dr. Thorne.
"""
            elif len(context) >= 29:  # Near the end
                instruction = """
You are helping CLOSE this episode of Dead Air.
- Summarize what the evidence actually supports
- Acknowledge what remains unknown about this case
- Encourage listeners to think critically
- Sign off professionally
Generate your closing dialogue line as Dr. Thorne.
"""
            else:
                instruction = """
Respond to Maya's points as Dr. Aris Thorne.
Challenge her theories with evidence-based analysis.
Generate your next dialogue line.
"""

        return f"{case_context}\n{conversation_context}\n{instruction}"

    def generate_social_hooks(self, script: PodcastScript) -> List[str]:
        """
        Extract compelling social media hooks from the script.

        Args:
            script: The PodcastScript to extract hooks from

        Returns:
            List of social media hook strings
        """
        hooks: List[str] = []

        for line in script.chapters:
            text = line.text

            # Look for dramatic or intriguing statements
            hook_indicators = [
                "wait",
                "but here's the thing",
                "the evidence",
                "nobody knew",
                "the truth",
                "what if",
                "think about it",
                "full body chills",
                "the timeline",
                "the alibi",
            ]

            text_lower = text.lower()
            if any(indicator in text_lower for indicator in hook_indicators):
                # Clean up the text for social media
                hook = text.strip()
                if len(hook) > 20 and len(hook) < 280:  # Twitter-friendly length
                    hooks.append(hook)

        # Limit to top 5 hooks
        return hooks[:5]

    def compile_script(
        self,
        case: CaseFile,
        dialogue_lines: List[DialogueLine],
    ) -> PodcastScript:
        """
        Assemble DialogueLines into a PodcastScript.

        Args:
            case: The CaseFile the script is about
            dialogue_lines: List of DialogueLine objects to compile

        Returns:
            Complete PodcastScript with all dialogue lines preserved in order
        """
        script_id = f"script-{uuid4().hex[:12]}"
        episode_title = f"The {case.location} Mystery: {case.title}"

        # Create the script first without hooks
        script = PodcastScript(
            script_id=script_id,
            case_id=case.case_id,
            episode_title=episode_title,
            chapters=dialogue_lines,
            social_hooks=[],
        )

        # Generate social hooks from the compiled script
        social_hooks = self.generate_social_hooks(script)

        # Return script with hooks
        return PodcastScript(
            script_id=script_id,
            case_id=case.case_id,
            episode_title=episode_title,
            chapters=dialogue_lines,
            social_hooks=social_hooks,
        )

    async def persist_script(self, script: PodcastScript) -> str:
        """
        Store script in Supabase.

        Args:
            script: PodcastScript to persist

        Returns:
            The script_id of the persisted script

        Raises:
            DebateEngineError: If persistence fails
        """
        if not self.supabase:
            raise DebateEngineError("Supabase client not configured")

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
            }

            result = self.supabase.table("scripts").insert(script_data).execute()

            if not result.data:
                raise DebateEngineError("Failed to insert script into database")

            logger.info(
                f"Persisted script {script.script_id} with {len(script.chapters)} dialogue lines"
            )
            return script.script_id

        except Exception as e:
            raise DebateEngineError(f"Failed to persist script: {e}")


def create_debate_engine(supabase_client: Optional[Any] = None) -> DebateEngine:
    """
    Create a DebateEngine instance.

    Args:
        supabase_client: Optional Supabase client for persistence

    Returns:
        Configured DebateEngine instance
    """
    return DebateEngine(supabase_client=supabase_client)
