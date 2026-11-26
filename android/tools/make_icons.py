"""生成 Android 启动图标（mipmap-*dpi/ic_launcher.png）。

用法：python tools/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "app" / "src" / "main" / "res"
DENSITIES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}


def draw(size: int) -> Image.Image:
    scale = 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw_ctx = ImageDraw.Draw(image)

    for y in range(canvas):
        ratio = y / max(1, canvas - 1)
        r = int(59 + (29 - 59) * ratio)
        g = int(130 + (78 - 130) * ratio)
        b = int(246 + (216 - 246) * ratio)
        draw_ctx.rectangle([0, y, canvas, y], fill=(r, g, b, 255))

    mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, canvas - 1, canvas - 1], radius=int(canvas * 0.24), fill=255
    )
    image.putalpha(mask)

    try:
        font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", int(canvas * 0.52))
    except OSError:
        font = ImageFont.load_default()

    box = draw_ctx.textbbox((0, 0), "M", font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw_ctx.text(
        ((canvas - tw) / 2 - box[0], (canvas - th) / 2 - box[1]),
        "M",
        font=font,
        fill=(255, 255, 255, 255),
    )
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    for density, size in DENSITIES.items():
        target = RES / f"mipmap-{density}"
        target.mkdir(parents=True, exist_ok=True)
        path = target / "ic_launcher.png"
        draw(size).save(path, format="PNG")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
