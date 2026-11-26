"""工具子页面的公共外壳：返回按钮 + 标题。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.registry import ToolSpec


class ToolPage(QWidget):
    """所有工具页面继承它，内容放进 self.body。"""

    back_requested = Signal()

    def __init__(self, spec: ToolSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.setObjectName("pageRoot")

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 20, 26, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(12)

        self.back_button = QPushButton("←  返回", self)
        self.back_button.setObjectName("ghost")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.clicked.connect(self.back_requested.emit)
        header.addWidget(self.back_button, 0, Qt.AlignmentFlag.AlignVCenter)

        text_box = QVBoxLayout()
        text_box.setSpacing(2)
        title = QLabel(spec.title, self)
        title.setObjectName("pageHeaderTitle")
        desc = QLabel(spec.summary, self)
        desc.setObjectName("hintText")
        text_box.addWidget(title)
        text_box.addWidget(desc)
        header.addLayout(text_box, 1)
        root.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(12)
        root.addLayout(self.body, 1)

    def on_shown(self) -> None:
        """页面被切换到前台时调用，子类可覆盖。"""
