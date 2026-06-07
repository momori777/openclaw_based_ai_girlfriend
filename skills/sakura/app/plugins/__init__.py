"""app/plugins/ — Sakura 原生插件系统。

本包提供完整的插件生命周期管理：

- models.py: 数据模型 (PluginManifest / PluginSpec / Contribution)
- discovery.py: 插件发现 (PluginDiscovery)
- capabilities.py: 能力收集注册表 (PluginCapabilityRegistry)
- manager.py: 插件管理器 (PluginManager)
- adapters.py: SDK 兼容适配层

与旧 SDK (sdk/) 的关系：
- sdk/ 保留作为 Shinsekai 兼容层
- app/plugins/ 是 Sakura 原生接口
- PluginManager 同时支持 SDK PluginBase 和新接口
"""

from app.plugins.capabilities import PluginCapabilities, PluginCapabilityRegistry
from app.plugins.discovery import PluginDiscovery, load_plugin_specs
from app.plugins.manager import PluginLoadResult, PluginManager
from app.plugins.models import (
    ChatUIWidgetContribution,
    PluginManifest,
    PluginSpec,
    PromptPatchContribution,
    SettingsPanelContribution,
    ToolContribution,
    ToolsTabContribution,
)

__all__ = [
    "ChatUIWidgetContribution",
    "PluginCapabilities",
    "PluginCapabilityRegistry",
    "PluginDiscovery",
    "PluginLoadResult",
    "PluginManager",
    "PluginManifest",
    "PluginSpec",
    "PromptPatchContribution",
    "SettingsPanelContribution",
    "ToolContribution",
    "ToolsTabContribution",
    "load_plugin_specs",
]
