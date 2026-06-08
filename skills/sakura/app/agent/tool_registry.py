"""兼容层 — 所有导入自动路由到 app/agent/tools/registry.py。

新代码应直接使用:
    from app.agent.tools import Tool, ToolRegistry, ToolExecutionResult, ToolPermissionPolicy
"""

from __future__ import annotations

# 重新导出所有旧接口，保持向后兼容
from app.agent.tools.registry import (
    Tool,
    ToolExecutionResult,
    ToolHandler,
    ToolMetadata,
    ToolRegistry,
)

# 向后兼容的 _requires_confirmation_despite_free_access — 委托给 ToolPermissionPolicy
from app.agent.tools.permission_policy import ToolPermissionPolicy

__all__ = [
    "Tool",
    "ToolExecutionResult",
    "ToolHandler",
    "ToolMetadata",
    "ToolPermissionPolicy",
    "ToolRegistry",
]
