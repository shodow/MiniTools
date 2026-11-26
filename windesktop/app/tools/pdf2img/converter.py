"""PDF 转图片核心逻辑（纯 Python，不依赖 Qt，方便单测与复用）。

渲染后端：pypdfium2（PDFium 绑定，Apache-2.0/BSD-3）。
"""

from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

import pypdfium2 as pdfium

PDF_SUFFIX = {".pdf"}
FORMAT_EXT = {"png": "png", "jpg": "jpg", "jpeg": "jpg"}
OUTPUT_MODES = ("same", "subfolder", "custom")
CONFLICT_MODES = ("overwrite", "skip", "rename")


class ConvertCancelled(Exception):
    """用户中途取消。"""


# PDFium 不是线程安全的：同一进程内并发开/关文档会导致原生层崩溃，
# 所有涉及 PDFium 的调用都必须持有这把锁（见 convert_file / probe）。
_PDFIUM_LOCK = threading.RLock()


@dataclass
class ConvertOptions:
    fmt: str = "png"
    dpi: int = 200
    jpeg_quality: int = 90
    page_range: str = ""
    zero_pad: int = 3
    output_mode: str = "subfolder"
    custom_dir: str | None = None
    on_conflict: str = "overwrite"
    password: str = ""
    workers: int = 1  # PDFium 全局串行，多线程没有意义（见 _PDFIUM_LOCK）

    def ext(self) -> str:
        return FORMAT_EXT.get(self.fmt.lower(), "png")


@dataclass
class FileResult:
    source: Path
    ok: bool = False
    pages_total: int = 0
    pages_done: int = 0
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
    def page_count(self) -> int:
        return sum(f.pages_done for f in self.files)


# --------------------------------------------------------------------------- #
# 基础工具函数
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d*)\s*)?$")


def parse_page_range(spec: str, total: int) -> list[int]:
    """把 "1-5,8,10-" 解析成 1-based 页码列表；空字符串表示全部。"""
    if total <= 0:
        return []
    spec = (spec or "").strip()
    if not spec:
        return list(range(1, total + 1))

    picked: list[int] = []
    seen: set[int] = set()
    for chunk in re.split(r"[,，;；\s]+", spec):
        if not chunk:
            continue
        match = _TOKEN_RE.match(chunk)
        if not match:
            raise ValueError(f"页码格式无法识别：{chunk}")
        start_s, end_s = match.group(1), match.group(2)
        start = int(start_s)
        if end_s is None or end_s == "":
            end = total if "-" in chunk else start
        else:
            end = int(end_s)
        if start > end:
            start, end = end, start
        for page in range(max(1, start), min(total, end) + 1):
            if page not in seen:
                seen.add(page)
                picked.append(page)
    if not picked:
        raise ValueError("页码范围内没有有效页面")
    return picked


def check_page_range(spec: str) -> None:
    """只做语法校验（不知道总页数时用），格式非法抛出 ValueError。"""
    if not (spec or "").strip():
        return
    for chunk in re.split(r"[,，;；\s]+", spec):
        if chunk and not _TOKEN_RE.match(chunk):
            raise ValueError(f"页码格式无法识别：{chunk}")


def output_dir_for(pdf_path: Path, opts: ConvertOptions) -> Path:
    if opts.output_mode == "same":
        return pdf_path.parent
    if opts.output_mode == "custom" and opts.custom_dir:
        return Path(opts.custom_dir)
    return pdf_path.parent / f"{pdf_path.stem}_images"


def page_filename(pdf_path: Path, page_no: int, opts: ConvertOptions) -> str:
    pad = max(0, int(opts.zero_pad))
    number = f"{page_no:0{pad}d}" if pad else str(page_no)
    return f"{pdf_path.stem}_{number}.{opts.ext()}"


def _resolve_conflict(path: Path, mode: str) -> tuple[Path, bool]:
    """返回 (最终路径, 是否跳过)。"""
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


def open_pdf(path: Path, password: str = "") -> pdfium.PdfDocument:
    kwargs = {}
    if password:
        kwargs["password"] = password
    return pdfium.PdfDocument(str(path), **kwargs)


def probe(pdf_path: Path, password: str = "") -> int:
    """返回页数，顺便验证文件可读。"""
    with _PDFIUM_LOCK:
        doc = open_pdf(pdf_path, password)
        try:
            return len(doc)
        finally:
            doc.close()


# --------------------------------------------------------------------------- #
# 渲染
# --------------------------------------------------------------------------- #

def render_page(doc: pdfium.PdfDocument, index: int, opts: ConvertOptions, out_path: Path) -> None:
    """把第 index 页（0-based）渲染并保存到 out_path。"""
    page = doc[index]
    try:
        bitmap = page.render(scale=opts.dpi / 72.0)
        try:
            image = bitmap.to_pil()
        finally:
            bitmap.close()
    finally:
        page.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dpi = (opts.dpi, opts.dpi)
    if opts.ext() == "jpg":
        image.convert("RGB").save(
            out_path,
            "JPEG",
            quality=max(1, min(100, int(opts.jpeg_quality))),
            subsampling=0,
            dpi=dpi,
            optimize=True,
        )
    else:
        if image.mode not in ("RGB", "RGBA", "L"):
            image = image.convert("RGB")
        image.save(out_path, "PNG", dpi=dpi, optimize=True)


def convert_file(
    pdf_path: Path,
    opts: ConvertOptions,
    cancel: threading.Event | None = None,
    on_page: Callable[[Path, int, Path], None] | None = None,
) -> FileResult:
    """转换单个 PDF，异常被收敛到 FileResult.error 中。

    PDFium 的初始化/销毁是全局状态，多个线程同时开合文档会偶发原生崩溃
    （实测出现过 0xC000001D illegal instruction），因此这里整段串行化。
    """
    with _PDFIUM_LOCK:
        return _convert_file_locked(pdf_path, opts, cancel, on_page)


def _convert_file_locked(
    pdf_path: Path,
    opts: ConvertOptions,
    cancel: threading.Event | None = None,
    on_page: Callable[[Path, int, Path], None] | None = None,
) -> FileResult:
    result = FileResult(source=pdf_path)
    try:
        doc = open_pdf(pdf_path, opts.password)
    except Exception as exc:  # noqa: BLE001
        message = str(exc) or exc.__class__.__name__
        if "password" in message.lower() or "encrypt" in message.lower():
            message = "PDF 已加密，请输入正确密码"
        result.error = f"无法打开：{message}"
        return result

    try:
        total = len(doc)
        result.pages_total = total
        pages = parse_page_range(opts.page_range, total)
        out_dir = output_dir_for(pdf_path, opts)
        out_dir.mkdir(parents=True, exist_ok=True)

        for page_no in pages:
            if cancel is not None and cancel.is_set():
                raise ConvertCancelled()
            target = out_dir / page_filename(pdf_path, page_no, opts)
            target, skip = _resolve_conflict(target, opts.on_conflict)
            if skip:
                result.skipped += 1
                result.pages_done += 1
                if on_page is not None:
                    on_page(pdf_path, page_no, target)
                continue
            render_page(doc, page_no - 1, opts, target)
            result.outputs.append(target)
            result.pages_done += 1
            if on_page is not None:
                on_page(pdf_path, page_no, target)
        result.ok = True
    except ConvertCancelled:
        result.error = "已取消"
    except Exception as exc:  # noqa: BLE001
        result.error = f"{exc.__class__.__name__}: {exc}"
    finally:
        doc.close()
    return result


def collect_pdfs(paths: Sequence[Path], recursive: bool = True) -> list[Path]:
    """展开文件/文件夹，去重并按路径排序。"""
    found: list[Path] = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            pattern = "**/*" if recursive else "*"
            for item in sorted(path.glob(pattern)):
                if item.is_file() and item.suffix.lower() in PDF_SUFFIX:
                    key = item.resolve()
                    if key not in seen:
                        seen.add(key)
                        found.append(item)
        elif path.suffix.lower() in PDF_SUFFIX:
            key = path.resolve()
            if key not in seen:
                seen.add(key)
                found.append(path)
    return found


def count_pages(files: Sequence[Path], password: str = "") -> tuple[int, list[tuple[Path, str]]]:
    """预统计总页数；返回 (可转换页数, [(失败文件, 原因)])。"""
    total = 0
    errors: list[tuple[Path, str]] = []
    for path in files:
        try:
            total += probe(path, password)
        except Exception as exc:  # noqa: BLE001
            errors.append((path, str(exc) or exc.__class__.__name__))
    return total, errors


def convert_batch(
    files: Sequence[Path],
    opts: ConvertOptions,
    cancel: threading.Event | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    on_file_done: Callable[[FileResult], None] | None = None,
    on_log: Callable[[str], None] | None = None,
    total_pages: int | None = None,
) -> BatchResult:
    """并发转换一批 PDF，跨文件汇总进度。"""
    batch = BatchResult()
    files = list(files)
    if not files:
        return batch

    if total_pages is None:
        total_pages, _ = count_pages(files, opts.password)
    done_pages = 0
    lock = threading.Lock()

    def _page_cb(src: Path, page_no: int, target: Path) -> None:
        nonlocal done_pages
        with lock:
            done_pages += 1
            current = done_pages
        if on_progress is not None:
            on_progress(current, total_pages)
        if on_log is not None:
            on_log(f"{src.name} 第 {page_no} 页 → {target.name}")

    workers = max(1, min(int(opts.workers or 1), len(files), 8))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(convert_file, path, opts, cancel, _page_cb): path for path in files
        }
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
                        on_log(f"完成 {path.name}：{result.pages_done} 页")
                    else:
                        on_log(f"失败 {path.name}：{result.error}")
            if batch.cancelled or (cancel is not None and cancel.is_set()):
                batch.cancelled = True
                for pending in futures:
                    pending.cancel()
                break

    batch.files.sort(key=lambda r: str(r.source).lower())
    return batch
