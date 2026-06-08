from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.agent.memory_curator import MemoryCurator
from app.storage.chat_history import ChatHistoryEntry


class MemoryCurationWorker(QObject):
    """在后台线程执行记忆整理，避免阻塞桌宠 UI。"""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        curator: MemoryCurator,
        entries: list[ChatHistoryEntry],
    ) -> None:
        super().__init__()
        self.curator = curator
        self.entries = entries

    @Slot()
    def run(self) -> None:
        try:
            result = self.curator.curate_entries(self.entries)
        except Exception as exc:  # 后台整理失败不能影响主聊天。
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)
