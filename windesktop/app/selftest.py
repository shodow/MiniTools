"""打包后自检：`MiniTools.exe --selftest`。

用于确认 exe 里 Qt、PDFium、Pillow 都能正常加载，并且转换链路可用。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path


def _artifact_dir() -> Path:
    """自检产物目录：%LOCALAPPDATA%\\MiniTools\\logs（源码运行时退到 tests/_out）。"""
    base: Path | None = None
    try:
        from PySide6.QtCore import QStandardPaths

        location = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.AppLocalDataLocation
        )
        if location:
            base = Path(location)
    except Exception:  # noqa: BLE001 - 退到下面的默认位置
        base = None

    if base is None:
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local"
        base = base / "MiniTools"

    target = base / "logs"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path(__file__).resolve().parent.parent / "tests" / "_out"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    return target


def _make_pdf(path: Path, pages: int = 2) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QFont, QPageSize, QPainter, QPdfWriter

    writer = QPdfWriter(str(path))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(72)
    painter = QPainter()
    if not painter.begin(writer):
        raise RuntimeError("无法初始化 QPainter")
    try:
        for index in range(1, pages + 1):
            if index > 1:
                writer.newPage()
            rect = painter.viewport()
            painter.fillRect(rect, QColor("#FFFFFF"))
            font = QFont("Segoe UI", 30)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QColor("#1D4ED8"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"SelfTest {index}")
    finally:
        painter.end()


def _make_photo(path: Path) -> None:
    """自检用底图：渐变 + 两个色块，避免依赖外部图片。"""
    from PIL import Image, ImageDraw

    gradient = Image.linear_gradient("L").resize((900, 600))
    image = Image.merge(
        "RGB",
        (
            gradient.point(lambda v: 40 + v // 3),
            gradient.point(lambda v: 90 + v // 4),
            gradient.point(lambda v: 140 + v // 5),
        ),
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((80, 120, 420, 360), radius=18, fill=(255, 250, 240))
    draw.ellipse((500, 140, 800, 380), fill=(255, 214, 102))
    image.save(path)


def run_safe() -> int:
    """供入口调用：任何异常都写进日志，便于打包后排查。"""
    try:
        return run()
    except Exception:  # noqa: BLE001
        import traceback

        detail = traceback.format_exc()
        print(detail, file=sys.stderr, flush=True)
        try:
            (_artifact_dir() / "selftest-crash.log").write_text(detail, encoding="utf-8")
        except OSError:
            pass
        return 1


def run() -> int:
    from PySide6 import __version__ as pyside_version
    from PIL import __version__ as pillow_version

    import pypdfium2
    from PySide6.QtWidgets import QApplication

    from app.core import registry
    from app.main import create_app
    from app.tools.pdf2img import converter
    from app.ui.main_window import MainWindow

    lines: list[str] = []

    def log(text: str) -> None:
        lines.append(text)
        print(text, flush=True)

    app: QApplication = create_app([])
    log(f"PySide6   {pyside_version}")
    log(f"PDFium    {pypdfium2.PYPDFIUM_INFO.version}")
    log(f"Pillow    {pillow_version}")
    log(f"产物目录  {_artifact_dir()}")

    failures: list[str] = []
    work_root = _artifact_dir() / "work"
    work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="selftest-", dir=work_root) as tmp:
        tmp_dir = Path(tmp)
        pdf = tmp_dir / "自检样本.pdf"
        _make_pdf(pdf, pages=2)
        log(f"样本 PDF  {pdf.stat().st_size} bytes")

        options = converter.ConvertOptions(fmt="png", dpi=100, output_mode="subfolder", zero_pad=3)
        result = converter.convert_file(pdf, options)
        if not result.ok:
            failures.append(f"转换失败：{result.error}")
        names = sorted(p.name for p in (tmp_dir / "自检样本_images").glob("*.png"))
        log(f"输出文件  {names}")
        if names != ["自检样本_001.png", "自检样本_002.png"]:
            failures.append("输出文件名不符合预期")

        window = MainWindow()
        window.resize(1140, 780)
        window.show()
        window.open_tool("pdf2img")
        app.processEvents()
        page = window._pages.get("pdf2img")
        tools = registry.all_tools()
        log(f"工具卡片  {[tool.id for tool in tools]}")
        if not tools:
            failures.append("工具注册表为空")
        if page is None:
            failures.append("工具页面未创建")
        else:
            log(f"界面      主窗口 ok，卡片页面 {page.__class__.__name__} ok")

        # ---- 图片加水印（含中文字体）----
        from app.tools.imgwatermark import converter as watermark

        font_path = watermark.find_default_font()
        log(f"中文字体  {font_path}")
        if not font_path:
            failures.append("找不到可渲染中文的系统字体")

        photo_path = tmp_dir / "自检图片.png"
        _make_photo(photo_path)
        wm_opts = watermark.WatermarkOptions(
            text="自检水印 · 中文",
            opacity=75,
            font_size=28,
            spacing=40,
            angle=45,
            output_mode="subfolder",
        )
        wm_result = watermark.process_file(photo_path, wm_opts)
        if not wm_result.ok:
            failures.append(f"水印处理失败：{wm_result.error}")
        else:
            out = wm_result.outputs[0]
            log(f"水印输出  {out.name}（{out.stat().st_size} bytes）")
            if out.stat().st_size < 1000:
                failures.append("水印输出文件异常")

        window.open_tool("imgwatermark")
        app.processEvents()
        wm_page = window._pages.get("imgwatermark")
        if wm_page is None:
            failures.append("水印页面未创建")
        else:
            log(f"界面      水印页面 {wm_page.__class__.__name__} ok")
            wm_page.text_edit.setPlainText("© MiniTools 自检")
            wm_page.refresh_preview()
            app.processEvents()
            shot = _artifact_dir() / "selftest-watermark.png"
            if window.grab().save(str(shot)):
                log(f"界面截图  {shot}")

        screenshot = _artifact_dir() / "selftest-ui.png"
        window.open_tool("pdf2img")
        app.processEvents()
        if window.grab().save(str(screenshot)):
            log(f"界面截图  {screenshot}")
        window.close()
        app.processEvents()

    for item in failures:
        log(f"SELFTEST FAIL: {item}")
    log("SELFTEST OK" if not failures else "SELFTEST FAILED")

    try:
        report = _artifact_dir() / "selftest.log"
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0 if not failures else 1

