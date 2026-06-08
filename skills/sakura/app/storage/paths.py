"""app/storage/paths.py — 统一存储路径管理。

所有 data/ 下的路径由本模块统一生成，避免各处手写 base_dir / "data" / ...。
"""

from __future__ import annotations

from pathlib import Path


class StoragePaths:
    """统一生成 Sakura 的存储路径。"""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self._data = self.base_dir / "data"

    # ---- 配置 ----
    @property
    def config_dir(self) -> Path:
        return self._data / "config"

    def api_config(self) -> Path:
        return self.config_dir / "api.yaml"

    def system_config(self) -> Path:
        return self.config_dir / "system_config.yaml"

    def characters_config(self) -> Path:
        return self.config_dir / "characters.yaml"

    def mcp_config(self) -> Path:
        return self.config_dir / "mcp.yaml"

    def plugins_config(self) -> Path:
        return self.config_dir / "plugins.yaml"

    # ---- 聊天历史 ----
    @property
    def chat_history_dir(self) -> Path:
        return self._data / "chat_history"

    def chat_history_for(self, character_id: str) -> Path:
        return self.chat_history_dir / f"{character_id}.jsonl"

    def legacy_chat_history(self) -> Path:
        return self._data / "chat_history.jsonl"

    # ---- 视觉观察 ----
    @property
    def visual_observations_dir(self) -> Path:
        return self._data / "visual_observations"

    def visual_observations_for(self, character_id: str) -> Path:
        return self.visual_observations_dir / f"{character_id}.jsonl"

    # ---- 记忆 ----
    @property
    def memory_dir(self) -> Path:
        return self._data / "memory"

    def memory_store(self) -> Path:
        return self._data / "memory.json"

    def memory_curation_state(self) -> Path:
        return self._data / "memory_curation_state.json"

    # ---- 提醒 ----
    def reminders_store(self) -> Path:
        return self._data / "reminders.json"

    # ---- 待办 ----
    def tasks_store(self) -> Path:
        return self._data / "tasks.json"

    # ---- 笔记 ----
    @property
    def notes_dir(self) -> Path:
        return self._data / "notes"

    # ---- 辅助 ----
    def ensure_dirs(self) -> None:
        """确保所有存储目录存在。"""
        for d in [
            self.config_dir,
            self.chat_history_dir,
            self.visual_observations_dir,
            self.memory_dir,
            self.notes_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)
