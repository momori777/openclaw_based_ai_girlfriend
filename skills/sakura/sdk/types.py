"""SDK 共享类型定义。

本模块是第三方插件作者应依赖的公开类型入口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolContribution:
    """插件提供的 Agent 工具贡献。"""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any] | None = None
    group: str = "default"
    risk: str = "low"
    requires_confirmation: bool = False
    capability: str | None = None


@dataclass(frozen=True)
class ToolsTabContribution:
    """插件贡献到设置窗口的工具页。"""

    tab_id: str
    title: str
    build: Callable[[Any], Any]
    order: float = 100.0


@dataclass(frozen=True)
class SettingsPanelContribution:
    """插件贡献的设置面板。"""

    section_id: str
    title: str
    build: Callable[[Any], Any]
    order: float = 100.0


@dataclass(frozen=True)
class ChatUIWidgetContribution:
    """插件贡献的聊天UI组件。"""

    widget_id: str
    build: Callable[[Any], Any]
    order: float = 100.0


@dataclass(frozen=True)
class PromptPatchContribution:
    """插件贡献的提示词补丁。"""

    patch_id: str
    system_prompt_append: str = ""
    reply_protocol_append: str = ""


@dataclass(frozen=True)
class PluginManifestView:
    """暴露给插件的清单视图。"""

    plugin_id: str
    name: str
    version: str
    description: str = ""
    api_version: int = 1
    priority: int = 100
    enabled: bool = True
    required: bool = False
