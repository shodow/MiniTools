"""生成 app/assets/app.ico（安装包与 exe 图标）。用 Pillow 现画，无需外部资源。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "app" / "assets" / "app.ico"
ASSETS = OUT.parent
SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw_chevron(direction: str, color: tuple[int, int, int, int] = (107, 114, 128, 255)) -> Image.Image:
    """生成下拉/上拉小三角（QSS 用），尺寸 20x12，显示时缩到 10x6。"""
    width, height = 20, 12
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw_ctx = ImageDraw.Draw(image)
    if direction == "down":
        points = [(2, 2), (width - 2, 2), (width // 2, height - 2)]
    else:
        points = [(2, height - 2), (width - 2, height - 2), (width // 2, 2)]
    draw_ctx.polygon(points, fill=color)
    return image


def draw(size: int) -> Image.Image:
    scale = 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw_ctx = ImageDraw.Draw(image)

    radius = int(canvas * 0.24)
    # 竖直渐变：上浅下深
    for y in range(canvas):
        ratio = y / max(1, canvas - 1)
        r = int(59 + (29 - 59) * ratio)
        g = int(130 + (78 - 130) * ratio)
        b = int(246 + (216 - 246) * ratio)
        draw_ctx.rectangle([0, y, canvas, y], fill=(r, g, b, 255))

    mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, canvas - 1, canvas - 1], radius=radius, fill=255)
    image.putalpha(mask)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", int(canvas * 0.52))
    except OSError:
        font = ImageFont.load_default()

    text = "M"
    box = draw_ctx.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw_ctx.text(((canvas - tw) / 2 - box[0], (canvas - th) / 2 - box[1]), text, font=font, fill=(255, 255, 255, 255))

    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images = [draw(size) for size in SIZES]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {OUT}")

    for name, direction in (("chevron_down.png", "down"), ("chevron_up.png", "up")):
        path = ASSETS / name
        draw_chevron(direction).save(path, format="PNG")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
