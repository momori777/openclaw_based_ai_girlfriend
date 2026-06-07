from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PluginContext:
    """插件初始化时可读取的 Sakura 宿主上下文。

    这里刻意只暴露非敏感信息；API Key、完整设置对象等仍由宿主管理。
    """

    base_dir: Path
    plugin_root: Path
    data_dir: Path
    manifest: Any

    def log(self, message: str, data: dict[str, Any] | None = None) -> None:
        """写入 Sakura 调试日志。"""
        try:
            from app.core.debug_log import debug_log
        except Exception:
            print(f"[Plugin:{self.manifest.plugin_id}] {message}")
            return
        debug_log(
            f"Plugin:{self.manifest.plugin_id}",
            message,
            data or {},
        )


@dataclass(frozen=True)
class PluginHostContext:
    """旧版插件初始化上下文，仅保留 base_dir 兼容。"""

    base_dir: Path
