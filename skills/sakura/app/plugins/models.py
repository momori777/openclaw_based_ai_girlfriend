"""app/plugins/models.py — 插件数据模型。

定义插件清单(manifest)、发现规格(spec)、贡献点(contribution)的统一模型。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sdk.types import (
    ChatUIWidgetContribution,
    PromptPatchContribution,
    SettingsPanelContribution,
    ToolContribution,
    ToolsTabContribution,
)


@dataclass(frozen=True)
class PluginManifest:
    """插件的完整清单信息。

    可从 plugin.yaml 或 PluginBase 属性中解析。
    """

    plugin_id: str
    name: str = ""
    description: str = ""
    version: str = "0.0.0"
    api_version: int = 1
    priority: int = 100
    enabled: bool = True
    required: bool = False
    entry: str = ""
    plugin_root: Path | None = None


@dataclass(frozen=True)
class PluginSpec:
    """插件发现规格。

    从 plugins.yaml 配置文件解析。
    """

    entry: str
    enabled: bool = True
    priority: int = 100
    plugin_id: str = ""
    name: str = ""
    description: str = ""
    version: str = "0.0.0"
    api_version: int = 1
    required: bool = False
    plugin_root: Path | None = None
    source: str = "config"
    priority_override: bool = False
