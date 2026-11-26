"""转换引擎自测（不依赖 pytest，直接 python tests/test_converter.py 运行）。"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.tools.pdf2img import converter  # noqa: E402
from make_sample_pdf import make_pdf  # noqa: E402

from PIL import Image  # noqa: E402

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  ok   {label}")
    else:
        FAILED += 1
        print(f"  FAIL {label}")


def test_page_range() -> None:
    print("parse_page_range")
    check(converter.parse_page_range("", 3) == [1, 2, 3], "空字符串 → 全部")
    check(converter.parse_page_range("2-3", 5) == [2, 3], "区间 2-3")
    check(converter.parse_page_range("1,3,5", 5) == [1, 3, 5], "逗号分隔")
    check(converter.parse_page_range("3-", 4) == [3, 4], "开区间 3-")
    check(converter.parse_page_range("1-99", 3) == [1, 2, 3], "越界裁剪")
    try:
        converter.parse_page_range("abc", 3)
        check(False, "非法格式应报错")
    except ValueError:
        check(True, "非法格式报错")
    try:
        converter.check_page_range("1-3,7")
        check(True, "check_page_range 合法")
    except ValueError:
        check(False, "check_page_range 合法")


def test_single_png(tmp: Path) -> None:
    print("单文件 PNG")
    pdf = make_pdf(tmp / "报告A.pdf", pages=3)
    opts = converter.ConvertOptions(fmt="png", dpi=150, output_mode="subfolder", zero_pad=3)
    result = converter.convert_file(pdf, opts)
    check(result.ok, f"转换成功（{result.error}）")
    check(result.pages_done == 3, "页数 3")
    out_dir = tmp / "报告A_images"
    names = sorted(p.name for p in out_dir.glob("*.png"))
    check(names == ["报告A_001.png", "报告A_002.png", "报告A_003.png"], f"命名 {names}")
    width, height = Image.open(out_dir / "报告A_001.png").size
    check(abs(width - 1240) <= 2 and abs(height - 1754) <= 2, f"A4@150dpi 尺寸 {width}x{height}")


def test_jpg_range(tmp: Path) -> None:
    print("JPG + 页码范围")
    pdf = make_pdf(tmp / "scan.pdf", pages=4)
    opts = converter.ConvertOptions(
        fmt="jpg", dpi=96, jpeg_quality=80, page_range="2-3", output_mode="subfolder", zero_pad=2
    )
    result = converter.convert_file(pdf, opts)
    check(result.ok, f"转换成功（{result.error}）")
    names = sorted(p.name for p in (tmp / "scan_images").glob("*.jpg"))
    check(names == ["scan_02.jpg", "scan_03.jpg"], f"命名 {names}")
    image = Image.open(tmp / "scan_images" / "scan_02.jpg")
    check(image.format == "JPEG", "编码为 JPEG")
    check(image.size[0] == 794, f"96dpi 宽度 {image.size[0]}")


def test_conflict(tmp: Path) -> None:
    print("冲突策略")
    pdf = make_pdf(tmp / "dup.pdf", pages=1)
    opts = converter.ConvertOptions(fmt="png", dpi=72, output_mode="subfolder", zero_pad=1, on_conflict="rename")
    converter.convert_file(pdf, opts)
    converter.convert_file(pdf, opts)
    names = sorted(p.name for p in (tmp / "dup_images").glob("*.png"))
    check(len(names) == 2 and "dup_1 (1).png" in names, f"自动重命名 {names}")

    opts_skip = converter.ConvertOptions(fmt="png", dpi=72, output_mode="subfolder", zero_pad=1, on_conflict="skip")
    result = converter.convert_file(pdf, opts_skip)
    check(result.ok and result.skipped == 1 and not result.outputs, "跳过策略")


def test_no_pad(tmp: Path) -> None:
    print("不补零")
    pdf = make_pdf(tmp / "plain.pdf", pages=2)
    opts = converter.ConvertOptions(fmt="png", dpi=72, output_mode="same", zero_pad=0)
    converter.convert_file(pdf, opts)
    names = sorted(p.name for p in tmp.glob("plain_*.png"))
    check(names == ["plain_1.png", "plain_2.png"], f"命名 {names}")


def test_batch(tmp: Path) -> None:
    print("批量 + 进度")
    folder = tmp / "batch"
    make_pdf(folder / "a.pdf", pages=2)
    make_pdf(folder / "b.pdf", pages=3)
    (folder / "note.txt").write_text("not a pdf", encoding="utf-8")
    files = converter.collect_pdfs([folder], recursive=True)
    check(len(files) == 2, f"收集到 {len(files)} 个 PDF")

    seen: list[tuple[int, int]] = []
    opts = converter.ConvertOptions(fmt="png", dpi=72, output_mode="subfolder", workers=2)
    batch = converter.convert_batch(files, opts, on_progress=lambda d, t: seen.append((d, t)))
    check(batch.ok_count == 2 and batch.page_count == 5, f"批量结果 {batch.ok_count}/{batch.page_count}")
    check(bool(seen) and seen[-1] == (5, 5), f"进度终值 {seen[-1] if seen else None}")


def test_cancel(tmp: Path) -> None:
    print("取消")
    pdf = make_pdf(tmp / "cancel.pdf", pages=12)
    event = threading.Event()

    def on_page(*_args) -> None:
        event.set()

    opts = converter.ConvertOptions(fmt="png", dpi=72, output_mode="subfolder")
    result = converter.convert_file(pdf, opts, cancel=event, on_page=on_page)
    check(not result.ok and result.error == "已取消", f"取消生效：{result.error}")
    check(result.pages_done < 12, f"提前停止（完成 {result.pages_done} 页）")


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)  # noqa: F841
    tmp = Path(tempfile.mkdtemp(prefix="MiniTools-test-"))
    try:
        test_page_range()
        test_single_png(tmp)
        test_jpg_range(tmp)
        test_conflict(tmp)
        test_no_pad(tmp)
        test_batch(tmp)
        test_cancel(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n通过 {PASSED}，失败 {FAILED}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    # 直接用 _exit 跳过解释器退出阶段：PySide6 在进程收尾时偶尔会 abort（测试专用写法）
    code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)