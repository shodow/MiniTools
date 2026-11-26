"""水印页端到端流程测试：走界面按钮完成一次批量处理。"""

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

from PIL import Image, ImageChops  # noqa: E402
from PySide6.QtCore import QElapsedTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.main import create_app  # noqa: E402
from app.ui.main_window import MainWindow  # noqa: E402
from make_sample_image import make_image  # noqa: E402


def wait_until(app: QApplication, predicate, timeout_ms: int = 90000) -> bool:
    timer = QElapsedTimer()
    timer.start()
    while timer.elapsed() < timeout_ms:
        app.processEvents()
        if predicate():
            return True
    return False


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="MiniTools-wmflow-"))
    failures = 0
    app = create_app([])
    window = MainWindow()
    window.show()
    app.processEvents()

    try:
        src = tmp / "src"
        make_image(src / "旅拍_01.png", (900, 600), "PHOTO 1")
        make_image(src / "旅拍_02.jpg", (800, 600), "PHOTO 2")

        window.open_tool("imgwatermark")
        page = window._pages["imgwatermark"]
        page.add_paths([str(src)])
        app.processEvents()
        if page.file_list.count() != 2:
            failures += 1
            print(f"  FAIL 文件列表 {page.file_list.count()} 项")
        else:
            print(f"  ok   文件列表 2 项 / {page.count_label.text()}")

        page.text_edit.setPlainText("© 旅拍 2026")
        page.opacity_spin.setValue(70)
        page.size_spin.setValue(26)
        page.spacing_spin.setValue(50)
        page.angle_spin.setValue(40)
        page.mode_combo.setCurrentIndex(1)   # 同名子文件夹
        page.fmt_combo.setCurrentIndex(0)    # 保持原格式
        page.refresh_preview()
        app.processEvents()
        if page.preview.pixmap() is None or page.preview.pixmap().isNull():
            failures += 1
            print("  FAIL 预览未渲染")
        else:
            print("  ok   预览已渲染")

        page.start_conversion()
        app.processEvents()
        if not wait_until(app, lambda: page._worker is None):
            failures += 1
            print("  FAIL 处理超时")
            page.shutdown()
        else:
            print(f"  ok   处理结束：{page.status.text()}")
            png_out = src / "旅拍_01_watermark" / "旅拍_01.png"
            jpg_out = src / "旅拍_02_watermark" / "旅拍_02.jpg"
            for path in (png_out, jpg_out):
                if not path.is_file():
                    failures += 1
                    print(f"  FAIL 缺少输出 {path.name}")
            if png_out.is_file():
                with Image.open(src / "旅拍_01.png") as before, Image.open(png_out) as after:
                    diff = ImageChops.difference(
                        before.convert("RGB"), after.convert("RGB")
                    ).convert("L")
                    changed = sum(diff.histogram()[1:])
                if changed <= 0:
                    failures += 1
                    print("  FAIL 输出与原图一致（没加水印）")
                else:
                    print(f"  ok   水印像素 {changed} 个")
            if page.btn_open.isVisible():
                print("  ok   “打开输出位置”已显示")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n水印流程测试通过" if not failures else f"\n水印流程测试失败 {failures} 项")
    return 1 if failures else 0


if __name__ == "__main__":
    # 直接用 _exit 跳过解释器退出阶段：PySide6 在进程收尾时偶尔会 abort（测试专用写法）
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
