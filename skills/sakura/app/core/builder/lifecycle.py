"""Lifecycle — 应用生命周期管理。

管理 Sakura 的启动（分阶段初始化）和优雅关闭流程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class AppPhase(Enum):
    """应用生命周期的各个阶段。"""
    INIT = auto()           # 初始状态
    STARTUP_LIGHT = auto()  # 轻量启动（立绘可见）
    STARTUP_DEFERRED = auto()  # 后台初始化中
    RUNNING = auto()        # 正常运行
    SHUTTING_DOWN = auto()  # 正在关闭
    TERMINATED = auto()     # 已终止


@dataclass
class LifecycleManager:
    """管理应用启动/运行/关闭的生命周期。

    负责：
    - 追踪当前阶段
    - 管理关闭时需清理的资源
    - 确保关闭顺序正确
    """

    phase: AppPhase = AppPhase.INIT
    _cleanup_handlers: list[callable] = field(default_factory=list)

    def transition_to(self, phase: AppPhase) -> None:
        """切换生命周期阶段。"""
        if self.phase == AppPhase.TERMINATED:
            raise RuntimeError("应用已终止，无法切换阶段")
        self.phase = phase

    @property
    def is_running(self) -> bool:
        """应用是否正在运行。"""
        return self.phase == AppPhase.RUNNING

    @property
    def is_shutting_down(self) -> bool:
        """应用是否正在关闭。"""
        return self.phase in {AppPhase.SHUTTING_DOWN, AppPhase.TERMINATED}

    def register_cleanup(self, handler: callable) -> None:
        """注册关闭时需调用的清理函数。

        清理函数按注册的逆序调用。
        """
        self._cleanup_handlers.append(handler)

    def shutdown(self) -> None:
        """执行关闭流程：逆序调用所有清理函数。"""
        self.transition_to(AppPhase.SHUTTING_DOWN)
        for handler in reversed(self._cleanup_handlers):
            try:
                handler()
            except Exception:
                pass  # 清理失败不应阻止后续清理
        self.transition_to(AppPhase.TERMINATED)
