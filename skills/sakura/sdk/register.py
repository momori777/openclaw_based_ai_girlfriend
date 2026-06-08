"""SDK 能力注册表 — 已升级为 Sakura 原生插件系统的新接口。

旧的 register_tools_tab 接口保留兼容。
新增 register_tool / register_settings_panel / register_chat_ui_widget / register_prompt_patch。
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, get_args, get_origin

from sdk.types import (
    ChatUIWidgetContribution,
    PromptPatchContribution,
    SettingsPanelContribution,
    ToolContribution as SDKToolContribution,
    ToolsTabContribution,
)


@dataclass
class PluginCapabilityRegistry:
    """收集插件贡献的能力注册表。"""

    tools: list[SDKToolContribution] = field(default_factory=list)
    settings_panels: list[SettingsPanelContribution] = field(default_factory=list)
    tools_tabs: list[ToolsTabContribution] = field(default_factory=list)
    chat_ui_widgets: list[ChatUIWidgetContribution] = field(default_factory=list)
    prompt_patches: list[PromptPatchContribution] = field(default_factory=list)

    def register_tool(self, contribution: SDKToolContribution) -> None:
        self.tools.append(contribution)

    def register_settings_panel(self, contribution: SettingsPanelContribution) -> None:
        self.settings_panels.append(contribution)

    def register_tools_tab(self, contribution: ToolsTabContribution) -> None:
        self.tools_tabs.append(contribution)

    def register_chat_ui_widget(self, contribution: ChatUIWidgetContribution) -> None:
        self.chat_ui_widgets.append(contribution)

    def register_prompt_patch(self, contribution: PromptPatchContribution) -> None:
        self.prompt_patches.append(contribution)

    def tool(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
        group: str = "default",
        risk: str = "low",
        requires_confirmation: bool = False,
        capability: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """以装饰器形式注册工具，避免旧全局注册表的残留状态。"""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.register_tool(
                SDKToolContribution(
                    name=name,
                    description=description,
                    parameters=parameters or _schema_from_signature(func),
                    handler=_handler_from_callable(func),
                    group=group,
                    risk=risk,
                    requires_confirmation=requires_confirmation,
                    capability=capability,
                )
            )
            return func

        return decorator


def _handler_from_callable(func: Callable[..., Any]) -> Callable[[dict[str, Any]], Any]:
    """把普通 Python 函数包装成 ToolRegistry 需要的 dict 参数处理器。"""
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())
    if len(parameters) == 1:
        parameter = parameters[0]
        annotation = parameter.annotation
        if (
            parameter.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }
            and (
                parameter.name in {"args", "arguments"}
                or annotation in {dict, dict[str, Any]}
            )
        ):
            return lambda arguments: func(arguments)

    def handler(arguments: dict[str, Any]) -> Any:
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
        return func(**kwargs)

    return handler


def _schema_from_signature(func: Callable[..., Any]) -> dict[str, Any]:
    signature = inspect.signature(func)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in signature.parameters.values():
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue
        if parameter.name in {"self", "cls"}:
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
