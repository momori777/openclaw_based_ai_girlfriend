"""SDK 工具装饰器 — 已废弃。

新插件请使用 app/plugins/models.py 中的 ToolContribution，
通过 PluginCapabilityRegistry.register_tool() 注册工具。
"""

from __future__ import annotations

import inspect
import warnings
from dataclasses import dataclass
from typing import Any, Callable, get_args, get_origin


warnings.warn(
    "sdk/tool_registry.py 已废弃，请使用 app.plugins.models.ToolContribution",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass(frozen=True)
class RegisteredTool:
    name: str
    description: str
    group: str
    risk: str
    requires_confirmation: bool
    func: Callable[..., Any]
    parameters: dict[str, Any]


# 保留全局变量以保持向后兼容 (但不推荐使用)
_REGISTERED_TOOLS: list[RegisteredTool] = []


def tool(*, name: str, description: str, group: str = "default",
         risk: str = "low", requires_confirmation: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """注册工具 (已废弃)。"""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        _REGISTERED_TOOLS.append(
            RegisteredTool(
                name=name, description=description, group=group,
                risk=risk, requires_confirmation=requires_confirmation,
                func=func, parameters=_schema_from_signature(func),
            )
        )
        return func
    return decorator


def registered_tools() -> list[RegisteredTool]:
    return list(_REGISTERED_TOOLS)


def clear_registered_tools() -> None:
    _REGISTERED_TOOLS.clear()


def _schema_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    signature = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue
        properties[parameter.name] = _schema_for_annotation(parameter.annotation)
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
    return {"type": "object", "properties": properties, "required": required}


def _schema_for_annotation(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    if origin is not None:
        args = get_args(annotation)
        if type(None) in args:
            non_null = [item for item in args if item is not type(None)]
            if non_null:
                schema = _schema_for_annotation(non_null[0])
                schema["nullable"] = True
                return schema
        if origin in {list, tuple, set}:
            item_schema = _schema_for_annotation(args[0]) if args else {}
            return {"type": "array", "items": item_schema}
        if origin is dict:
            return {"type": "object"}
    if annotation in {str, inspect.Parameter.empty}:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    return {"type": "string"}
