"""小图标生成：卡片图标与应用图标都用 QPainter 现画，免去资源文件依赖。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPixmap,
)


def badge_pixmap(
    text: str,
    color: str,
    size: int = 54,
    radius: int = 15,
    ratio: int = 2,
) -> QPixmap:
    """画一个圆角方块 + 白色粗体短文字，作为卡片图标。"""
    pixmap = QPixmap(size * ratio, size * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    base = QColor(color)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, base.lighter(118))
    gradient.setColorAt(1.0, base.darker(108))
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    font = QFont("Segoe UI", max(8, int(size * 0.31)))
    font.setBold(True)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.5)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return pixmap


def app_icon_pixmap(size: int = 64) -> QPixmap:
    """应用图标：圆角蓝底 + 白色扳手形状（用字符近似，避免矢量资源）。"""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#3B82F6"))
    gradient.setColorAt(1.0, QColor("#1D4ED8"))
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    radius = size * 0.24
    painter.drawRoundedRect(QRectF(0, 0, size, size), radius, radius)

    font = QFont("Segoe UI", int(size * 0.44))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "M")
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_icon_pixmap(size))
    return icon


def icon_size(value: int) -> QSize:
    return QSize(value, value)
