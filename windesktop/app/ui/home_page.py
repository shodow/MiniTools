"""首页：标题 + 搜索框 + 卡片网格。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app import APP_DISPLAY_NAME, __version__
from app.core import registry
from app.ui.card_widget import ToolCard
from app.ui.flow_layout import FlowLayout


class HomePage(QWidget):
    open_tool = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self._cards: list[ToolCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 18)
        root.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(12)
        titles = QVBoxLayout()
        titles.setSpacing(3)
        title = QLabel(APP_DISPLAY_NAME, self)
        title.setObjectName("homeTitle")
        subtitle = QLabel("选一张卡片，开始使用对应的小工具", self)
        subtitle.setObjectName("homeSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        top.addLayout(titles, 1)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("搜索工具…")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(232)
        self.search.textChanged.connect(self._apply_filter)
        top.addWidget(self.search, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(top)
        root.addSpacing(8)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        host.setObjectName("scrollHost")
        self.flow = FlowLayout(host, margin=2, spacing=16)
        host.setLayout(self.flow)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        self.empty_hint = QLabel("没有匹配的工具", self)
        self.empty_hint.setObjectName("hintText")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.hide()
        root.addWidget(self.empty_hint)

        footer = QLabel(f"WinTools v{__version__}  ·  本地运行，不联网", self)
        footer.setObjectName("hintText")
        root.addWidget(footer, 0, Qt.AlignmentFlag.AlignRight)

        self._populate()

    def _populate(self) -> None:
        for card in self._cards:
            self.flow.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        for spec in registry.all_tools():
            card = ToolCard(spec, self)
            card.clicked.connect(self.open_tool.emit)
            self.flow.addWidget(card)
            self._cards.append(card)

        if not self._cards:
            self.empty_hint.setText("还没有注册任何工具")
            self.empty_hint.show()
        self.flow.invalidate()

    def _apply_filter(self, text: str) -> None:
        allowed = {spec.id for spec in registry.search(text)}
        visible = 0
        for card in self._cards:
            show = card.spec.id in allowed
            card.setVisible(show)
            visible += int(show)
        if self._cards:
            self.empty_hint.setVisible(visible == 0)
            self.empty_hint.setText("没有匹配的工具")
        self.flow.invalidate()

    def refresh(self) -> None:
        self._populate()
        self._apply_filter(self.search.text())
