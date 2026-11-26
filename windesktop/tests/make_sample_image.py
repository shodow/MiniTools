"""生成测试用图片（渐变底 + 几何图形，模拟照片）。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def make_image(path: Path, size: tuple[int, int] = (1200, 800), label: str = "sample") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    gradient = Image.linear_gradient("L").resize(size)
    image = Image.merge(
        "RGB",
        (
            gradient.point(lambda v: 40 + v // 3),
            gradient.point(lambda v: 90 + v // 4),
            gradient.point(lambda v: 140 + v // 5),
        ),
    )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (width * 0.08, height * 0.15, width * 0.46, height * 0.55),
        radius=18,
        fill=(255, 250, 240),
    )
    draw.ellipse(
        (width * 0.55, height * 0.20, width * 0.88, height * 0.52),
        fill=(255, 214, 102),
    )
    draw.rectangle(
        (width * 0.08, height * 0.70, width * 0.92, height * 0.74),
        fill=(236, 240, 246),
    )
    draw.text((width * 0.10, height * 0.18), label, fill=(30, 41, 59))
    image.save(path)
    return path


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/_out/sample.png")
    print(make_image(target))
