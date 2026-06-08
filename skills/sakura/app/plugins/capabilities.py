"""app/plugins/capabilities.py — 插件能力收集注册表。

分离 PluginCapabilityRegistry 与 PluginDiscovery，让插件贡献收集集中管理。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from app.plugins.models import (
    ChatUIWidgetContribution,
    PromptPatchContribution,
    SettingsPanelContribution,
    ToolContribution,
    ToolsTabContribution,
)
from sdk.register import PluginCapabilityRegistry as SDKPluginCapabilityRegistry


@dataclass
class PluginCapabilities:
    """单个插件加载后收集的所有贡献。"""

    plugin_id: str
    tools: list[ToolContribution] = field(default_factory=list)
    settings_panels: list[SettingsPanelContribution] = field(default_factory=list)
    tools_tabs: list[ToolsTabContribution] = field(default_factory=list)
    chat_ui_widgets: list[ChatUIWidgetContribution] = field(default_factory=list)
    prompt_patches: list[PromptPatchContribution] = field(default_factory=list)


@dataclass
class PluginCapabilityRegistry:
    """收集所有插件的贡献，供 host 统一应用。

    由插件在 initialize() 中调用注册方法填充。
    最终由 PluginManager 收集所有注册项并返回。
    """

    tools: list[ToolContribution] = field(default_factory=list)
    settings_panels: list[SettingsPanelContribution] = field(default_factory=list)
    tools_tabs: list[ToolsTabContribution] = field(default_factory=list)
    chat_ui_widgets: list[ChatUIWidgetContribution] = field(default_factory=list)
    prompt_patches: list[PromptPatchContribution] = field(default_factory=list)

    def register_tool(self, contribution: ToolContribution) -> None:
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
        """公开 SDK 的无全局状态工具装饰器兼容入口。"""
        return SDKPluginCapabilityRegistry.tool(
            self,
            name=name,
            description=description,
            parameters=parameters,
            group=group,
            risk=risk,
            requires_confirmation=requires_confirmation,
            capability=capability,
        )

    # 向后兼容: 保持与旧 SDK register_tools_tab 的兼容
    # 旧的 PluginCapabilityRegistry (sdk/register.py) 通过此方法兼容
