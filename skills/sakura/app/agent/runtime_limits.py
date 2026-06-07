"""Agent 运行时限制常量和类型。

将 MAX_* 常量从 runtime.py 中提取出来，
让这些限制值可以被独立测试和引用。
"""

from __future__ import annotations

from collections.abc import Callable

from app.agent.actions import AgentProgress

# 每轮对话最多允许的 Agent 决策步数
MAX_AGENT_STEPS_PER_TURN = 4

# 每步最多允许的工具调用数
MAX_TOOL_CALLS_PER_STEP = 3

# 整轮最多允许的工具调用总数
MAX_TOOL_CALLS_PER_TURN = 8

# 工具结果截断字符数
MAX_TOOL_RESULT_CHARS = 6000

# pending action 续跑时保留的消息数上限
MAX_PENDING_CONTEXT_MESSAGES = 12

# pending action 续跑时保留的文本字符上限
MAX_PENDING_CONTEXT_TEXT_CHARS = 4000

# 主动事件中保留的最近对话消息数上限
MAX_EVENT_RECENT_CONVERSATION_MESSAGES = 12

# 主动事件中保留的最近对话文本字符上限
MAX_EVENT_RECENT_CONVERSATION_CONTENT_CHARS = 800

# 进度回调类型
ProgressCallback = Callable[[AgentProgress], None]
