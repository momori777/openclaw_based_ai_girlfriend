from __future__ import annotations

from pathlib import Path

from sdk.plugin_host_context import PluginContext, PluginHostContext
from sdk.register import PluginCapabilityRegistry


class PluginBase:
    """Sakura 插件基类。

    新插件推荐使用类属性声明 plugin_id / plugin_version，并实现
    initialize(register, context)。旧三参数 initialize 仍由宿主兼容。
    """

    plugin_id = ""
    plugin_version = "0.0.0"

    def initialize(
        self,
        register: PluginCapabilityRegistry,
        context: PluginContext,
    ) -> None:
        raise NotImplementedError

    def shutdown(self) -> None:
        return None


LegacyInitializeArgs = tuple[PluginCapabilityRegistry, Path, PluginHostContext]
