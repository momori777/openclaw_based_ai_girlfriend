from __future__ import annotations

from typing import Any


MAX_MODEL_CONTEXT_MESSAGES = 24
MAX_MODEL_CONTEXT_CHARS = 40_000


def trim_messages_for_model(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """保留最近上下文，并用字符预算兜底限制入模历史体积。"""
    recent = list(messages[-MAX_MODEL_CONTEXT_MESSAGES:])
    while len(recent) > 1 and _estimate_messages_chars(recent) > MAX_MODEL_CONTEXT_CHARS:
        recent.pop(0)
    return recent


def _estimate_messages_chars(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", ""))) for message in messages)
