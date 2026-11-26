"""生成测试用 PDF（借用 Qt 的 QPdfWriter，不引入额外依赖）。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPageSize, QPainter, QPdfWriter, QPen


def make_pdf(path: Path, pages: int = 3, title: str = "WinTools Sample") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(72)
    writer.setTitle(title)

    painter = QPainter()
    if not painter.begin(writer):
        raise RuntimeError("无法初始化 QPainter")
    try:
        for index in range(1, pages + 1):
            if index > 1:
                writer.newPage()
            rect = painter.viewport()
            painter.fillRect(rect, QColor("#FFFFFF"))
            painter.setPen(QPen(QColor("#BFDBFE"), 3))
            painter.drawRect(rect.adjusted(40, 40, -40, -40))

            font = QFont("Segoe UI", 34)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#1D4ED8"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"Sample Page {index}")

            small = QFont("Segoe UI", 14)
            painter.setFont(small)
            painter.setPen(QColor("#6B7280"))
            painter.drawText(
                rect.adjusted(0, 220, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                f"{title} · page {index}/{pages}",
            )
    finally:
        painter.end()
    return path


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/_out/sample.pdf")
    print(make_pdf(target))
