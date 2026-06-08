"""Sakura 插件公开 SDK。

注意：sdk/tool_registry.py 的全局变量设计已废弃。
新插件请使用 PluginCapabilityRegistry 直接注册贡献。
"""

from sdk.plugin import PluginBase
from sdk.plugin_host_context import PluginContext, PluginHostContext
from sdk.register import PluginCapabilityRegistry

__all__ = [
    "PluginBase",
    "PluginCapabilityRegistry",
    "PluginContext",
    "PluginHostContext",
]
