"""ServiceContainer — 轻量级服务定位器。

在 AppContext 构建完成后，提供统一的服务访问接口。
与 AppContext 不同，ServiceContainer 允许延迟初始化和服务替换（主要用于测试）。
"""

from __future__ import annotations

from typing import Any


class ServiceContainer:
    """轻量服务容器。

    在 AppBuilder 完成装配后，所有服务统一注册到此容器。
    UI 层和 Worker 层通过容器获取依赖，而不是直接 import 全局单例。
    """

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """注册一个服务实例。"""
        self._services[name] = service

    def get(self, name: str) -> Any:
        """获取已注册的服务实例。

        Raises:
            KeyError: 服务未注册时抛出。
        """
        if name not in self._services:
            raise KeyError(f"服务 '{name}' 未注册")
        return self._services[name]

    def get_optional(self, name: str) -> Any:
        """获取服务实例，不存在时返回 None。"""
        return self._services.get(name)

    def has(self, name: str) -> bool:
        """检查服务是否已注册。"""
        return name in self._services

    def unregister(self, name: str) -> None:
        """移除一个服务注册。"""
        self._services.pop(name, None)

    def clear(self) -> None:
        """清空所有服务注册。"""
        self._services.clear()
