from __future__ import annotations

from typing import Any, Callable

from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class ToolConfirmationPanel(QWidget):
    """待确认工具动作的按钮面板。"""

    def __init__(
        self,
        on_confirm: Callable[[], None],
        on_cancel: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.confirm_button = QPushButton("执行", self)
        self.confirm_button.setObjectName("confirmActionButton")
        self.confirm_button.setFixedHeight(38)
        self.confirm_button.clicked.connect(on_confirm)

        self.cancel_button = QPushButton("取消", self)
        self.cancel_button.setObjectName("cancelActionButton")
        self.cancel_button.setFixedHeight(38)
        self.cancel_button.clicked.connect(on_cancel)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.confirm_button)
        layout.addWidget(self.cancel_button)
        self.setLayout(layout)
        self.setVisible(False)

    def set_action(self, action: Any | None) -> None:
        has_action = action is not None
        self.setVisible(has_action)
        self.confirm_button.setVisible(has_action)
        self.cancel_button.setVisible(has_action)

    def set_busy(self, busy: bool) -> None:
        self.confirm_button.setEnabled(not busy)
        self.cancel_button.setEnabled(not busy)

    def state_snapshot(self) -> dict[str, bool]:
        return {
            "confirm_visible": self.confirm_button.isVisible(),
            "cancel_visible": self.cancel_button.isVisible(),
            "confirm_enabled": self.confirm_button.isEnabled(),
            "cancel_enabled": self.cancel_button.isEnabled(),
        }
