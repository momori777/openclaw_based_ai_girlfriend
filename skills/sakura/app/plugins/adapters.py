"""app/plugins/adapters.py — SDK 兼容适配层。

将旧的 Shinsekai SDK 风格转换为新的 Sakura 原生插件接口。
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

from app.agent.tools.registry import Tool
from app.plugins.models import ToolContribution


def sdk_tool_to_contribution(name: str, description: str, parameters: dict,
                              handler, group: str = "default",
                              risk: str = "low", requires_confirmation: bool = False,
                              capability: str | None = None) -> ToolContribution:
    """将 SDK 风格工具参数转换为统一贡献。"""
    return ToolContribution(
        name=name,
        description=description,
        parameters=parameters,
        handler=handler,
        group=group,
        risk=risk,
        requires_confirmation=requires_confirmation,
        capability=capability,
    )


def contribution_to_app_tool(contribution: ToolContribution) -> Tool:
    """将工具贡献转换为 app 可用的 Tool 实例。"""
    return Tool(
        name=contribution.name,
        description=contribution.description,
        parameters=contribution.parameters,
        handler=_normalize_tool_handler(contribution.handler),
        requires_confirmation=contribution.requires_confirmation,
        group=contribution.group,
        risk=contribution.risk,
        capability=contribution.capability,
        source="plugin",
    )


def _normalize_tool_handler(handler: Callable[..., Any] | None) -> Callable[[dict[str, Any]], Any] | None:
    """兼容 handler(args) 与 handler(**kwargs) 两种插件写法。"""
    if handler is None:
        return None
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return lambda arguments: handler(arguments)
    parameters = list(signature.parameters.values())
    if not parameters:
        return lambda _arguments: handler()
    if len(parameters) == 1:
        parameter = parameters[0]
        if (
            parameter.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and parameter.name in {"args", "arguments"}
        ):
            return lambda arguments: handler(arguments)

    def wrapped(arguments: dict[str, Any]) -> Any:
        if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters):
            return handler(**arguments)
        kwargs = {
            parameter.name: arguments[parameter.name]
            for parameter in parameters
            if parameter.kind
            in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and parameter.name in arguments
        }
        return handler(**kwargs)

    return wrapped
