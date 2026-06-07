# app/core/contracts/ — 共享数据协议
#
# 本包定义跨模块使用的共享类型和数据结构，包括：
# - messages.py: 聊天消息模型
# - replies.py: 回复结构 (ChatReply / ChatSegment)
# - actions.py: Agent 动作/结果/待确认数据结构
# - events.py: Agent 事件模型
#
# 当前这些类型定义在 app/agent/actions.py 和 app/llm/chat_reply.py 中，
# 后续阶段 (阶段2: 拆分AgentRuntime) 将逐步迁移到此包。
