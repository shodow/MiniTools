"""单独复现“批量转换中途取消”的稳定性问题。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QElapsedTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.main import create_app  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from make_sample_pdf import make_pdf  # noqa: E402


def wait_until(app: QApplication, predicate, timeout_ms: int = 60000) -> bool:
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < timeout_ms:
        app.processEvents()
        if predicate():
            return True
    return False


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="minitools-cancel-"))
    app = create_app([])
    window = MainWindow()
    window.show()
    app.processEvents()
    try:
        pdf = make_pdf(tmp / "长文档.pdf", pages=30)
        window.open_tool("pdf2img")
        page = window._pages["pdf2img"]
        page.add_paths([str(pdf)])
        page.mode_combo.setCurrentIndex(1)
        app.processEvents()
        print("ready", flush=True)

        page.start_conversion()
        app.processEvents()
        app.processEvents()
        print("started", flush=True)
        page.cancel_conversion()
        print("cancel requested", flush=True)

        done = wait_until(app, lambda: page._worker is None, 30000)
        print(f"worker finished={done} status={page.status.text()}", flush=True)

        window.close()
        app.processEvents()
        print("closed", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
