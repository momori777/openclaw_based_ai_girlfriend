"""插件管理兼容层。

真实实现位于 app.plugins.manager；本模块保留旧导入路径。
"""

from __future__ import annotations

from app.plugins.discovery import load_plugin_specs
from app.plugins.manager import PluginLoadResult, PluginManager
from app.plugins.models import PluginSpec


class SakuraPluginManager(PluginManager):
    """旧启动链路使用的名称，行为委托给原生 PluginManager。"""


__all__ = [
    "PluginLoadResult",
    "PluginSpec",
    "SakuraPluginManager",
    "load_plugin_specs",
]
