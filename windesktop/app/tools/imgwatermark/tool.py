from app.core.registry import ToolSpec


def _make_page():
    from app.tools.imgwatermark.page import ImageWatermarkPage

    return ImageWatermarkPage(TOOL)


TOOL = ToolSpec(
    id="imgwatermark",
    title="图片加水印",
    summary="给 PNG / JPG 平铺文字水印，支持中文、透明度、字号、间距与倾斜角度",
    badge="水印",
    accent="#0EA5E9",
    page_factory=_make_page,
    order=20,
    keywords=("图片", "水印", "png", "jpg", "批量", "中文", "watermark"),
)
