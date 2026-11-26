"""端到端流程测试：真实点击“开始转换”，等待后台线程完成，检查输出文件。"""

from __future__ import annotations

import os
import shutil
import os
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
    tmp = Path(tempfile.mkdtemp(prefix="MiniTools-flow-"))
    failures = 0
    app = create_app([])
    window = MainWindow()
    window.show()
    app.processEvents()

    try:
        src = tmp / "src"
        make_pdf(src / "年度总结.pdf", pages=3)
        make_pdf(src / "合同.pdf", pages=2)

        window.open_tool("pdf2img")
        page = window._pages["pdf2img"]
        page.add_paths([str(src)])
        app.processEvents()
        assert page.file_list.count() == 2, page.file_list.count()
        print(f"  ok   文件列表 {page.file_list.count()} 项 / {page.count_label.text()}")

        page.fmt_combo.setCurrentIndex(1)          # JPG
        page.dpi_spin.setValue(120)
        page.mode_combo.setCurrentIndex(1)         # 同名子文件夹
        page.pad_spin.setValue(3)
        page.start_conversion()
        app.processEvents()

        done = wait_until(app, lambda: page._worker is None, 90000)
        if not done:
            failures += 1
            print("  FAIL 转换超时")
            page.shutdown()
        else:
            print(f"  ok   转换结束：{page.status.text()}")
            jpgs = sorted((src / "年度总结_images").glob("*.jpg"))
            names = [p.name for p in jpgs]
            print(f"       输出 {names}")
            if names != ["年度总结_001.jpg", "年度总结_002.jpg", "年度总结_003.jpg"]:
                failures += 1
                print("  FAIL 命名不符合预期")
            if not (src / "合同_images" / "合同_001.jpg").exists():
                failures += 1
                print("  FAIL 第二个文件未输出")
            if page.btn_open.isVisible():
                print("  ok   “打开输出位置”已显示")

        # 取消流程
        make_pdf(src / "长文档.pdf", pages=30)
        page.add_paths([str(src / "长文档.pdf")])
        page.start_conversion()
        app.processEvents()
        app.processEvents()
        page.cancel_conversion()
        done = wait_until(app, lambda: page._worker is None, 60000)
        if not done:
            failures += 1
            print("  FAIL 取消后未退出")
        else:
            print(f"  ok   取消结束：{page.status.text()}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n流程测试通过" if not failures else f"\n流程测试失败 {failures} 项")
    return 1 if failures else 0


if __name__ == "__main__":
    # 直接用 _exit 跳过解释器退出阶段：PySide6 在进程收尾时偶尔会 abort（测试专用写法）
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
