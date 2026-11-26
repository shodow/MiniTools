"""各工具页面共用的小部件与格式化函数。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def human_size(num: int) -> str:
    size = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


class DropZone(QFrame):
    """可拖拽 + 可点击的文件接收区。"""

    paths_dropped = Signal(list)
    clicked = Signal()

    def __init__(
        self,
        title: str,
        hint: str,
        parent: QWidget | None = None,
        height: int = 96,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(height)
        self.setProperty("dragActive", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        title_label = QLabel(title, self)
        title_label.setObjectName("dropTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label = QLabel(hint, self)
        hint_label.setObjectName("hintText")
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for child in (title_label, hint_label):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(title_label)
        layout.addWidget(hint_label)

    def _set_active(self, active: bool) -> None:
        if bool(self.property("dragActive")) == active:
            return
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._set_active(False)
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self.paths_dropped.emit(paths)
        else:
            event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)


def filesize_of(path: Path) -> str:
    try:
        return human_size(path.stat().st_size)
    except OSError:
        return "未知大小"
