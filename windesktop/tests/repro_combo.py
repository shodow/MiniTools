"""复现 test_flow 的崩溃：先用正常转换，再取消一次批量。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    tmp = Path(tempfile.mkdtemp(prefix="minitools-combo-"))
    app = create_app([])
    window = MainWindow()
    window.show()
    app.processEvents()
    try:
        src = tmp / "src"
        make_pdf(src / "年度总结.pdf", pages=3)
        make_pdf(src / "合同.pdf", pages=2)
        long_pdf = make_pdf(src / "长文档.pdf", pages=30)

        window.open_tool("pdf2img")
        page = window._pages["pdf2img"]
        for index in range(rounds):
            page.add_paths([str(src / "年度总结.pdf"), str(src / "合同.pdf")])
            page.mode_combo.setCurrentIndex(1)
            page.start_conversion()
            app.processEvents()
            if not wait_until(app, lambda: page._worker is None, 90000):
                print(f"round{index} first conversion timeout", flush=True)
                return 2
            print(f"round{index} converted", flush=True)

            page.add_paths([str(long_pdf)])
            page.start_conversion()
            app.processEvents()
            app.processEvents()
            page.cancel_conversion()
            if not wait_until(app, lambda: page._worker is None, 60000):
                print(f"round{index} cancel timeout", flush=True)
                return 2
            print(f"round{index} cancelled ok: {page.status.text()}", flush=True)
            page.clear_files()
            app.processEvents()

        window.close()
        app.processEvents()
        print("combo done", flush=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)
