"""首页上的功能卡片。"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.core.registry import ToolSpec
from app.ui.icons import badge_pixmap

CARD_WIDTH = 272
CARD_HEIGHT = 172


class ToolCard(QFrame):
    clicked = Signal(str)

    def __init__(self, spec: ToolSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.setObjectName("toolCard")
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip(f"{spec.title}\n{spec.summary}")

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(10)
        icon = QLabel(self)
        icon.setPixmap(badge_pixmap(spec.badge, spec.accent))
        icon.setFixedSize(54, 54)
        icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        head.addWidget(icon, 0, Qt.AlignmentFlag.AlignTop)
        head.addStretch(1)
        arrow = QLabel("→", self)
        arrow.setObjectName("cardArrow")
        arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        head.addWidget(arrow, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(head)

        self.title_label = QLabel(spec.title, self)
        self.title_label.setObjectName("cardTitle")
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self.title_label)

        self.summary_label = QLabel(spec.summary, self)
        self.summary_label.setObjectName("cardSummary")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self.summary_label, 1)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(18)
        self._shadow.setOffset(0, 4)
        self._shadow.setColor(QColor(15, 23, 42, 32))
        self.setGraphicsEffect(self._shadow)
        self._shadow_anim = QPropertyAnimation(self._shadow, b"blurRadius", self)
        self._shadow_anim.setDuration(140)
        self._shadow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- 交互 ----
    def _animate_shadow(self, blur: int, offset: float) -> None:
        self._shadow_anim.stop()
        self._shadow_anim.setStartValue(self._shadow.blurRadius())
        self._shadow_anim.setEndValue(blur)
        self._shadow_anim.start()
        self._shadow.setOffset(0, offset)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._animate_shadow(30, 6)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._animate_shadow(18, 4)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.spec.id)
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.spec.id)
            event.accept()
            return
        super().keyPressEvent(event)
