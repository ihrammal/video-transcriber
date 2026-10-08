"""make_icon.py -- generate the program icon (a drawn letter "I").

The icon is a rounded square with a deep blue gradient and a large, white,
serif capital "I" (Georgia Bold) with a soft shadow.  It is written twice:

    app-icon.ico          next to the build scripts (PyInstaller + Inno Setup)
    resources/app-icon.ico  bundled inside the program, used for the window
                            icon and the welcome / goodbye screens at run time

Run:  python make_icon.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
SIZES = (16, 24, 32, 48, 64, 128, 256)
SUPER = 4  # supersampling factor for smooth edges


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("georgiab.ttf", "georgia.ttf", "seguisb.ttf", "arialbd.ttf"):
        path = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", name)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _gradient(size: int) -> Image.Image:
    """Diagonal blue gradient, top-left light to bottom-right dark."""
    top = (46, 84, 196)     # #2E54C4
    bottom = (20, 34, 92)   # #14225C
    base = Image.new("RGB", (size, size))
    px = base.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2.0 * (size - 1))
            px[x, y] = (
                int(top[0] + (bottom[0] - top[0]) * t),
                int(top[1] + (bottom[1] - top[1]) * t),
                int(top[2] + (bottom[2] - top[2]) * t),
            )
    return base


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def render(size: int) -> Image.Image:
    """One finished icon of ``size`` x ``size`` pixels (RGBA)."""
    big = size * SUPER
    radius = big // 5

    canvas = _gradient(big)
    mask = _rounded_mask(big, radius)
    icon = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    icon.paste(canvas, (0, 0), mask)

    draw = ImageDraw.Draw(icon)

    # The letter: white Georgia Bold "I", centred, with a soft shadow.
    font = _font(int(big * 0.62))
    text = "I"
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    x = (big - tw) // 2 - box[0]
    y = (big - th) // 2 - box[1] + int(big * 0.01)

    shadow = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    off = max(2, big // 64)
    sdraw.text((x + off, y + off), text, font=font, fill=(10, 18, 50, 190))
    shadow = shadow.filter(ImageFilter.GaussianBlur(big / 96.0))
    icon = Image.alpha_composite(icon, shadow)

    draw = ImageDraw.Draw(icon)
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))

    return icon.resize((size, size), Image.LANCZOS)


def main() -> int:
    master = render(256)
    for target in (
        os.path.join(ROOT, "app-icon.ico"),
        os.path.join(ROOT, "resources", "app-icon.ico"),
    ):
        os.makedirs(os.path.dirname(target), exist_ok=True)
        master.save(target, format="ICO", sizes=[(s, s) for s in SIZES])
        print("wrote", target, os.path.getsize(target), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
