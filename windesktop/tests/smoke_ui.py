"""界面冒烟测试：离屏渲染主窗口与 PDF 页面，输出截图到 tests/_out/。

用法：python tests/smoke_ui.py
"""

from __future__ import annotations

import os
import shutil
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.main import create_app  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from make_sample_image import make_image  # noqa: E402
from make_sample_pdf import make_pdf  # noqa: E402

OUT = ROOT / "tests" / "_out"


def shoot(window: MainWindow, app: QApplication, name: str, delay: int = 0) -> None:
    for _ in range(3):
        app.processEvents()
    if delay:
        from PySide6.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        QTimer.singleShot(delay, loop.quit)
        loop.exec()
        app.processEvents()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    ok = window.grab().save(str(path))
    print(f"{'ok  ' if ok else 'FAIL'} {path}")


def main() -> int:
    app = create_app([])
    window = MainWindow()
    window.resize(1140, 780)
    window.show()
    app.processEvents()

    shoot(window, app, "01_home.png")

    window.open_tool("pdf2img")
    app.processEvents()
    shoot(window, app, "02_pdf_page_empty.png")

    page = window._pages["pdf2img"]
    sample_dir = OUT / "sample"
    if sample_dir.exists():
        shutil.rmtree(sample_dir)
    pdfs = [make_pdf(sample_dir / f"项目报告_{i}.pdf", pages=2 + i) for i in range(1, 4)]
    page.add_paths([str(sample_dir)])
    app.processEvents()
    shoot(window, app, "03_pdf_files.png")

    page.fmt_combo.setCurrentIndex(1)
    page.dpi_spin.setValue(150)
    app.processEvents()
    shoot(window, app, "04_pdf_jpg_options.png")

    # ---- 图片加水印 ----
    window.show_home()
    app.processEvents()
    window.open_tool("imgwatermark")
    app.processEvents()
    shoot(window, app, "05_watermark_empty.png")

    wm_page = window._pages["imgwatermark"]
    photos = OUT / "photos"
    if photos.exists():
        shutil.rmtree(photos)
    for index in range(1, 4):
        make_image(photos / f"样张_{index}.jpg", (1400 + index * 120, 900), f"PHOTO {index}")
    wm_page.add_paths([str(photos)])
    wm_page.text_edit.setPlainText("© 我的照片 2026")
    wm_page.refresh_preview()
    app.processEvents()
    shoot(window, app, "06_watermark_ready.png")

    wm_page.text_edit.setPlainText("仅限内部使用 · 请勿外传")
    wm_page.opacity_spin.setValue(45)
    wm_page.size_spin.setValue(34)
    wm_page.spacing_spin.setValue(90)
    wm_page.angle_spin.setValue(30)
    wm_page.refresh_preview()
    app.processEvents()
    shoot(window, app, "07_watermark_options.png")

    print(f"样本文件：{[p.name for p in pdfs]}")
    print(f"待转换列表：{page.file_list.count()} 项")
    print(f"页数汇总：{page.count_label.text()}")
    print(f"水印列表：{wm_page.file_list.count()} 张 / {wm_page.count_label.text()}")
    return 0


if __name__ == "__main__":
    # 直接用 _exit 跳过解释器退出阶段：PySide6 在进程收尾时偶尔会 abort（测试专用写法）
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
