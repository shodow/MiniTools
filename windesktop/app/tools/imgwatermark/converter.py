"""图片加水印核心逻辑（纯 Pillow，不依赖 Qt，方便单测与复用）。

水印用平铺方式铺满整张图：每个印章是旋转过的一段文字，印章之间留 spacing 像素间距。
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable, Sequence

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

IMAGE_SUFFIX = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
FORMAT_EXT = {"png": "png", "jpg": "jpg"}
OUTPUT_MODES = ("same", "subfolder", "custom")
CONFLICT_MODES = ("overwrite", "skip", "rename")

# Windows 自带的中文字体，按优先级尝试
FONT_CANDIDATES = (
    "msyh.ttc",      # 微软雅黑
    "msyhbd.ttc",    # 微软雅黑粗体
    "msyhl.ttc",     # 微软雅黑细体
    "simhei.ttf",    # 黑体
    "deng.ttf",      # 等线
    "simsun.ttc",    # 宋体
)


class WatermarkCancelled(Exception):
    """用户中途取消。"""


@dataclass
class WatermarkOptions:
    text: str = ""
    opacity: int = 75          # 0-100
    font_size: int = 20        # 像素
    spacing: int = 60          # 印章之间的间距（像素）
    angle: int = 45            # 逆时针旋转角度
    color: str = "#FFFFFF"
    outline: bool = True       # 给文字加一圈深色描边，浅色背景上也看得清
    fmt: str = "keep"          # keep | png | jpg
    jpeg_quality: int = 92
    output_mode: str = "subfolder"
    custom_dir: str | None = None
    on_conflict: str = "overwrite"
    workers: int = 3
    font_path: str | None = None

    def alpha(self) -> int:
        return max(0, min(100, int(self.opacity))) * 255 // 100


@dataclass
class FileResult:
    source: Path
    ok: bool = False
    outputs: list[Path] = field(default_factory=list)
    skipped: int = 0
    error: str = ""


@dataclass
class BatchResult:
    files: list[FileResult] = field(default_factory=list)
    cancelled: bool = False

    @property
    def ok_count(self) -> int:
        return sum(1 for f in self.files if f.ok)

    @property
    def fail_count(self) -> int:
        return sum(1 for f in self.files if not f.ok)

    @property
    def image_count(self) -> int:
        return sum(len(f.outputs) for f in self.files)


# --------------------------------------------------------------------------- #
# 字体
# --------------------------------------------------------------------------- #

def _font_dirs() -> list[Path]:
    dirs = [Path("C:/Windows/Fonts")]
    local = Path.home() / "AppData/Local/Microsoft/Windows/Fonts"
    if local.is_dir():
        dirs.append(local)
    return dirs


@lru_cache(maxsize=8)
def find_default_font() -> str | None:
    """找一个能显示中文的系统字体，返回绝对路径。"""
    for directory in _font_dirs():
        for name in FONT_CANDIDATES:
            candidate = directory / name
            if candidate.is_file():
                return str(candidate)
    # 兜底：字体目录里任意一个 CJK 字体
    for directory in _font_dirs():
        if not directory.is_dir():
            continue
        for pattern in ("*yahei*", "*hei*", "*sim*", "*noto*sans*cjk*"):
            for candidate in sorted(directory.glob(pattern)):
                if candidate.suffix.lower() in (".ttf", ".ttc", ".otf"):
                    return str(candidate)
    return None


@lru_cache(maxsize=32)
def load_font(size: int, font_path: str | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = max(4, int(size))
    path = font_path or find_default_font()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10
    except TypeError:  # pragma: no cover - 老版本 Pillow
        return ImageFont.load_default()


# --------------------------------------------------------------------------- #
# 水印绘制
# --------------------------------------------------------------------------- #

def _parse_color(color: str) -> tuple[int, int, int]:
    try:
        rgb = ImageColor.getrgb(color)
    except ValueError:
        rgb = (255, 255, 255)
    return rgb[:3]


def build_stamp(opts: WatermarkOptions) -> Image.Image:
    """生成一个旋转后的水印印章（RGBA）。"""
    text = opts.text or ""
    font = load_font(opts.font_size, opts.font_path)
    rgb = _parse_color(opts.color)
    fill = (*rgb, opts.alpha())

    # 量尺寸：用一张足够大的临时画布
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = text.split("\n") if text else [""]
    spacing_line = max(2, int(opts.font_size * 0.28))
    widths, heights = [], []
    for line in lines:
        box = measure.textbbox((0, 0), line or " ", font=font)
        widths.append(max(1, box[2] - box[0]))
        heights.append(max(1, box[3] - box[1]))
    stroke = 0
    if opts.outline:
        stroke = 1 if opts.font_size < 40 else 2
    alpha = opts.alpha()
    stroke_alpha = 0 if alpha == 0 else min(230, int(alpha * 0.9) + 10)

    text_w = max(widths) + stroke * 2 + 4
    text_h = sum(heights) + spacing_line * (len(lines) - 1) + stroke * 2 + 4

    canvas = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    y = 2
    for line, height in zip(lines, heights):
        draw.text(
            (2, y),
            line or " ",
            font=font,
            fill=fill,
            stroke_width=stroke,
            stroke_fill=(0, 0, 0, stroke_alpha) if stroke else None,
        )
        y += height + spacing_line

    if opts.angle % 360 == 0:
        return canvas
    return canvas.rotate(
        float(opts.angle),
        expand=True,
        resample=Image.Resampling.BICUBIC,
    )


def apply_watermark(image: Image.Image, opts: WatermarkOptions) -> Image.Image:
    """在 PIL 图片上平铺水印，返回新图片（RGBA）。"""
    base = ImageOps.exif_transpose(image).convert("RGBA")
    if not (opts.text or "").strip() or opts.alpha() == 0:
        return base

    stamp = build_stamp(opts)
    if stamp.width == 0 or stamp.height == 0:
        return base

    spacing = max(0, int(opts.spacing))
    step_x = stamp.width + spacing
    step_y = stamp.height + spacing
    width, height = base.size

    # 从负偏移开始铺，保证边缘也有水印
    for y in range(-stamp.height, height + step_y, step_y):
        for x in range(-stamp.width, width + step_x, step_x):
            base.paste(stamp, (x, y), stamp)
    return base


# --------------------------------------------------------------------------- #
# 文件处理
# --------------------------------------------------------------------------- #

def output_dir_for(src: Path, opts: WatermarkOptions) -> Path:
    if opts.output_mode == "same":
        return src.parent
    if opts.output_mode == "custom" and opts.custom_dir:
        return Path(opts.custom_dir)
    return src.parent / f"{src.stem}_watermark"


def target_suffix(src: Path, opts: WatermarkOptions) -> str:
    if opts.fmt in FORMAT_EXT:
        return "." + FORMAT_EXT[opts.fmt]
    suffix = src.suffix.lower()
    if suffix == ".jpeg":
        return ".jpg"
    if suffix in IMAGE_SUFFIX:
        return suffix
    return ".png"


def output_path_for(src: Path, opts: WatermarkOptions) -> Path:
    return output_dir_for(src, opts) / f"{src.stem}{target_suffix(src, opts)}"


def _resolve_conflict(path: Path, mode: str) -> tuple[Path, bool]:
    if not path.exists() or mode == "overwrite":
        return path, False
    if mode == "skip":
        return path, True
    stem, suffix = path.stem, path.suffix
    index = 1
    while True:
        candidate = path.with_name(f"{stem} ({index}){suffix}")
        if not candidate.exists():
            return candidate, False
        index += 1


def _save_image(result: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        canvas = Image.new("RGBA", result.size, (255, 255, 255, 255))
        canvas.alpha_composite(result)
        canvas.convert("RGB").save(path, "JPEG", quality=92, subsampling=0, optimize=True)
    elif suffix == ".webp":
        result.save(path, "WEBP", quality=92)
    elif suffix == ".bmp":
        result.convert("RGB").save(path, "BMP")
    else:
        result.save(path, "PNG", optimize=True)


def process_file(
    src: Path,
    opts: WatermarkOptions,
    cancel: threading.Event | None = None,
) -> FileResult:
    """处理单张图片，异常收敛到 FileResult.error。"""
    result = FileResult(source=src)
    if cancel is not None and cancel.is_set():
        result.error = "已取消"
        return result
    try:
        with Image.open(src) as raw:
            raw.load()
            marked = apply_watermark(raw, opts)
            target, skip = _resolve_conflict(output_path_for(src, opts), opts.on_conflict)
            if skip:
                result.skipped += 1
                result.ok = True
                return result
            if target.suffix.lower() in (".jpg", ".jpeg"):
                _save_jpeg(marked, target, opts.jpeg_quality)
            else:
                _save_image(marked, target)
            result.outputs.append(target)
            result.ok = True
    except WatermarkCancelled:
        result.error = "已取消"
    except FileNotFoundError:
        result.error = "文件不存在"
    except OSError as exc:
        result.error = f"无法读取图片：{exc}"
    except Exception as exc:  # noqa: BLE001
        result.error = f"{exc.__class__.__name__}: {exc}"
    return result


def _save_jpeg(image: Image.Image, path: Path, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
    canvas.alpha_composite(image)
    canvas.convert("RGB").save(
        path,
        "JPEG",
        quality=max(1, min(100, int(quality))),
        subsampling=0,
        optimize=True,
    )


def collect_images(paths: Sequence[Path], recursive: bool = True) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            for item in sorted(path.glob(pattern)):
                if item.is_file() and item.suffix.lower() in IMAGE_SUFFIX:
                    key = item.resolve()
                    if key not in seen:
                        seen.add(key)
                        found.append(item)
        elif path.suffix.lower() in IMAGE_SUFFIX:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                found.append(path)
    return found


def convert_batch(
    files: Sequence[Path],
    opts: WatermarkOptions,
    cancel: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    on_file_done: Callable[[FileResult], None] | None = None,
    on_log: Callable[[str], None] | None = None,
) -> BatchResult:
    batch = BatchResult()
    files = list(files)
    total = len(files)
    if total == 0:
        return batch

    done = 0
    lock = threading.Lock()

    def _tick(src: Path, target: Path) -> None:
        nonlocal done
        with lock:
            done += 1
            current = done
        if on_progress is not None:
            on_progress(current, total)
        if on_log is not None:
            on_log(f"{src.name} → {target.name}")

    def _run(src: Path) -> FileResult:
        result = process_file(src, opts, cancel)
        for out in result.outputs:
            _tick(src, out)
        return result

    workers = max(1, min(int(opts.workers or 1), total, 8))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run, path): path for path in files}
        for future in as_completed(futures):
            path = futures[future]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                result = FileResult(source=path, error=f"{exc.__class__.__name__}: {exc}")
            if result.error == "已取消":
                batch.cancelled = True
            else:
                batch.files.append(result)
                if on_file_done is not None:
                    on_file_done(result)
                if on_log is not None:
                    if result.ok:
                        detail = "跳过（已存在）" if result.skipped else "完成"
                        on_log(f"{path.name} {detail}")
                    else:
                        on_log(f"失败 {path.name}：{result.error}")
            if batch.cancelled or (cancel is not None and cancel.is_set()):
                batch.cancelled = True
                for pending in futures:
                    pending.cancel()
                break

    batch.files.sort(key=lambda r: str(r.source).lower())
    return batch
