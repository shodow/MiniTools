from app.core.registry import ToolSpec


def _make_page():
    from app.tools.pdf2img.page import PdfToImagePage

    return PdfToImagePage(TOOL)


TOOL = ToolSpec(
    id="pdf2img",
    title="PDF 转图片",
    summary="把 PDF 的每一页导出为 PNG / JPG，支持整个文件夹批量转换",
    badge="PDF",
    accent="#2563EB",
    page_factory=_make_page,
    order=10,
    keywords=("pdf", "图片", "jpg", "png", "转换", "批量", "渲染"),
)
