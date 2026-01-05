"""PydanticAI agent configurations for podcast hosts."""

from src.agents.maya import MAYA_VANCE_SYSTEM_PROMPT, create_maya_agent
from src.agents.thorne import DR_THORNE_SYSTEM_PROMPT, create_thorne_agent

__all__ = [
    "create_thorne_agent",
    "create_maya_agent",
    "DR_THORNE_SYSTEM_PROMPT",
    "MAYA_VANCE_SYSTEM_PROMPT",
]
