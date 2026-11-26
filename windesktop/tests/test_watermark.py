"""水印引擎自测（python tests/test_watermark.py）。"""

from __future__ import annotations

import shutil
import os
import sys
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageChops  # noqa: E402

from app.tools.imgwatermark import converter  # noqa: E402
from make_sample_image import make_image  # noqa: E402

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


def differs(a: Image.Image, b: Image.Image) -> bool:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    return diff.getbbox() is not None


def changed_pixels(image: Image.Image, reference: Image.Image) -> int:
    diff = ImageChops.difference(image.convert("RGB"), reference.convert("RGB")).convert("L")
    histogram = diff.histogram()
    return sum(histogram[1:])  # 差值为 0 的不算


def test_font() -> None:
    print("字体")
    path = converter.find_default_font()
    check(bool(path) and Path(str(path)).is_file(), f"找到中文字体：{path}")
    font = converter.load_font(20)
    check(font is not None, "字体可加载")


def test_chinese_render(tmp: Path) -> None:
    print("中文水印")
    source = make_image(tmp / "中文.jpg", (900, 600), "中文样张")
    opts = converter.WatermarkOptions(text="版权所有 · 测试水印", opacity=75, font_size=24, spacing=40, angle=45)
    with Image.open(source) as raw:
        original = raw.convert("RGB").copy()
        marked = converter.apply_watermark(raw, opts)
    check(marked.size == original.size, "尺寸不变")
    count = changed_pixels(marked, original)
    check(count > 500, f"写入像素 {count} 个")
    marked_path = tmp / "out_chinese.png"
    marked.save(marked_path)
    check(marked_path.stat().st_size > 1000, "PNG 可保存")


def test_opacity(tmp: Path) -> None:
    print("透明度")
    source = make_image(tmp / "透明.png", (600, 400))
    base = Image.open(source)
    opaque = converter.apply_watermark(base, converter.WatermarkOptions(text="A", opacity=100, font_size=30, spacing=10))
    faint = converter.apply_watermark(base, converter.WatermarkOptions(text="A", opacity=10, font_size=30, spacing=10))
    zero = converter.apply_watermark(base, converter.WatermarkOptions(text="A", opacity=0, font_size=30, spacing=10))
    original = base.convert("RGBA")
    check(not differs(zero, original), "透明度 0 时不变")
    check(differs(opaque, faint), "透明度影响渲染")
    check(changed_pixels(opaque, original) > changed_pixels(faint, original), "100% 比 10% 更明显")


def test_layout(tmp: Path) -> None:
    print("字号 / 间距 / 角度")
    source = make_image(tmp / "布局.png", (800, 500))
    base = Image.open(source)
    original = base.convert("RGBA")
    small = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=12, spacing=20, angle=45))
    large = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=48, spacing=20, angle=45))
    check(changed_pixels(large, original) > changed_pixels(small, original), "字号越大覆盖越多")

    near = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=24, spacing=0, angle=45))
    far = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=24, spacing=200, angle=45))
    check(changed_pixels(near, original) > changed_pixels(far, original), "间距越大覆盖越少")

    flat = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=24, spacing=20, angle=0))
    tilted = converter.apply_watermark(base, converter.WatermarkOptions(text="水印", font_size=24, spacing=20, angle=45))
    check(differs(flat, tilted), "角度影响结果")

    plain = converter.apply_watermark(
        base, converter.WatermarkOptions(text="水印", font_size=24, spacing=20, angle=45, outline=False)
    )
    outlined = converter.apply_watermark(
        base, converter.WatermarkOptions(text="水印", font_size=24, spacing=20, angle=45, outline=True)
    )
    check(differs(plain, outlined), "描边开关影响结果")
    check(changed_pixels(outlined, original) > changed_pixels(plain, original), "描边覆盖更多像素")


def test_multiline_and_spaces(tmp: Path) -> None:
    print("多行 / 空格")
    source = make_image(tmp / "多行.png", (500, 400))
    base = Image.open(source)
    original = base.convert("RGBA")
    multiline = converter.apply_watermark(
        base, converter.WatermarkOptions(text="第一行\n第二行", font_size=18, spacing=30, angle=20)
    )
    check(changed_pixels(multiline, original) > 200, "多行文本可渲染")
    spaced = converter.apply_watermark(
        base, converter.WatermarkOptions(text="A B C", font_size=18, spacing=30, angle=0)
    )
    check(changed_pixels(spaced, original) > 100, "带空格的英文可渲染")


def test_output(tmp: Path) -> None:
    print("输出格式与命名")
    source = make_image(tmp / "输出.jpg", (400, 300))
    opts = converter.WatermarkOptions(text="水印", font_size=20, spacing=30, fmt="png", output_mode="subfolder")
    result = converter.process_file(source, opts)
    check(result.ok, f"处理成功（{result.error}）")
    target = tmp / "输出_watermark" / "输出.png"
    check(target.is_file(), f"输出 {target.name}")
    with Image.open(target) as out:
        check(out.format == "PNG", "编码为 PNG")

    keep = converter.WatermarkOptions(text="水印", font_size=20, spacing=30, fmt="keep", output_mode="same")
    result = converter.process_file(source, keep)
    check(result.ok and result.outputs[0].suffix == ".jpg", f"保持原格式 → {result.outputs[0].name}")

    jpg = converter.WatermarkOptions(text="水印", font_size=20, spacing=30, fmt="jpg", jpeg_quality=70, output_mode="subfolder")
    result = converter.process_file(source, jpg)
    with Image.open(result.outputs[0]) as out:
        check(out.format == "JPEG", "编码为 JPEG")


def test_conflict(tmp: Path) -> None:
    print("冲突策略")
    source = make_image(tmp / "冲突.png", (200, 200))
    opts = converter.WatermarkOptions(text="水印", output_mode="subfolder", on_conflict="rename")
    converter.process_file(source, opts)
    converter.process_file(source, opts)
    names = sorted(p.name for p in (tmp / "冲突_watermark").glob("*.png"))
    check(len(names) == 2 and "冲突 (1).png" in names, f"自动重命名 {names}")

    skip_opts = converter.WatermarkOptions(text="水印", output_mode="subfolder", on_conflict="skip")
    result = converter.process_file(source, skip_opts)
    check(result.ok and result.skipped == 1 and not result.outputs, "跳过策略")


def test_batch(tmp: Path) -> None:
    print("批量 + 进度")
    folder = tmp / "batch"
    make_image(folder / "a.png", (300, 200))
    make_image(folder / "b.jpg", (300, 200))
    (folder / "note.txt").write_text("not an image", encoding="utf-8")
    files = converter.collect_images([folder], recursive=True)
    check(len(files) == 2, f"收集到 {len(files)} 张图片")

    seen: list[tuple[int, int]] = []
    opts = converter.WatermarkOptions(text="批量", font_size=16, spacing=20, output_mode="subfolder", workers=2)
    batch = converter.convert_batch(files, opts, on_progress=lambda d, t: seen.append((d, t)))
    check(batch.ok_count == 2 and batch.image_count == 2, f"批量结果 {batch.ok_count}/{batch.image_count}")
    check(bool(seen) and seen[-1] == (2, 2), f"进度终值 {seen[-1] if seen else None}")
    check((folder / "a_watermark" / "a.png").is_file(), "子文件夹输出")


def test_broken_file(tmp: Path) -> None:
    print("损坏文件")
    broken = tmp / "broken.png"
    broken.write_bytes(b"not really a png")
    result = converter.process_file(broken, converter.WatermarkOptions(text="x", output_mode="same"))
    check(not result.ok and bool(result.error), f"报错而不是崩溃：{result.error}")


def test_cancel(tmp: Path) -> None:
    print("取消")
    event = threading.Event()
    source = make_image(tmp / "取消.png", (400, 300))
    event.set()
    result = converter.process_file(source, converter.WatermarkOptions(text="水印"), cancel=event)
    check(not result.ok and result.error == "已取消", f"取消生效：{result.error}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="MiniTools-wm-"))
    try:
        test_font()
        test_chinese_render(tmp)
        test_opacity(tmp)
        test_layout(tmp)
        test_multiline_and_spaces(tmp)
        test_output(tmp)
        test_conflict(tmp)
        test_batch(tmp)
        test_broken_file(tmp)
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
