from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class PromptContext:
    """提示词场景渲染所需的上下文。"""

    character_prompt: str = ""
    reply_tones: list[str] | None = None
    reply_portraits: list[str] | None = None
    memory_summary: str = ""
    current_time: str = ""
    step_index: int = 0
    remaining_steps: int = 0
    max_tool_calls_per_step: int = 0
    max_tool_calls_per_turn: int = 0
    extra_instructions: str = ""
    allow_screen_observation: bool = False
    event_type: str = "reminder_due"


@dataclass(frozen=True)
class PromptBlock:
    """可复用提示词块。"""

    title: str | None
    body: str


@dataclass(frozen=True)
class PromptRecipe:
    """由多个提示词块组成的场景配方。"""

    name: str
    blocks: Sequence[PromptBlock]

