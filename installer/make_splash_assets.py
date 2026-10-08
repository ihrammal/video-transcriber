"""make_splash_assets.py -- render the branded splash artwork used by the
PyInstaller bootloader and by the Inno Setup wizard.

Run once whenever the artwork or the version changes::

    python installer\\make_splash_assets.py

Outputs::

    installer/splash/splash.png       580x220  bootloader splash (onefile)
    installer/splash/splash.bmp        580x220  same artwork as 24-bit BMP
    installer/splash/wiz-image.bmp     164x314  wizard left banner
    installer/splash/wiz-small.bmp      55x58   wizard title-bar image
"""

from __future__ import annotations

import os
import struct
import sys

# Must run on the real Windows platform: Qt's "offscreen" platform has no
# usable font database and draws every glyph as an empty box.


from PyQt6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtGui import (  # noqa: E402
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPolygonF,
)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(HERE, "splash")
ICON = os.path.join(ROOT, "app-icon.ico")
ICON_PNG = os.path.join(OUT_DIR, "icon-128.png")

BG = QColor("#141418")
GOLD = QColor("#FFC107")
WHITE = QColor("#FFFFFF")
MUTED = QColor("#8A8A94")

# Kept in sync with vt_bootstrap.APP_VERSION.
VERSION = "2.0.0"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _extract_icon_png(size: int = 128) -> str:
    """Pull one PNG frame out of app-icon.ico without touching Qt's icon loader."""
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ICON, "rb") as fh:
        data = fh.read()
    _rsvd, kind, count = struct.unpack("<HHH", data[:6])
    if kind != 1:
        raise SystemExit("{} is not an ICO file".format(ICON))

    best = None
    for i in range(count):
        w, h, _cc, _res, _pl, _bc, nbytes, offset = struct.unpack(
            "<BBBBHHII", data[6 + i * 16 : 6 + (i + 1) * 16]
        )
        frame = data[offset : offset + nbytes]
        if not frame.startswith(_PNG_MAGIC):
            continue
        side = w or 256
        if best is None or abs(side - size) < abs(best[0] - size):
            best = (side, frame)
    if best is None:
        raise SystemExit("no PNG frame found in " + ICON)

    with open(ICON_PNG, "wb") as fh:
        fh.write(best[1])
    print("extracted {}x{} icon frame -> {}".format(best[0], best[0], ICON_PNG))
    return ICON_PNG


def _icon() -> QImage:
    """Brand mark as a QImage (Qt's QPixmap/.ico path is avoided on purpose)."""
    path = ICON_PNG if os.path.exists(ICON_PNG) else _extract_icon_png()
    img = QImage(path)
    if img.isNull():
        raise SystemExit("could not decode " + path)
    return img


def _draw_icon(p: QPainter, x: float, y: float, size: float) -> None:
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    p.drawImage(QRectF(x, y, size, size), _icon())


def _save(img: QImage, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    rgb = img.convertToFormat(QImage.Format.Format_RGB888)
    if not rgb.save(path, "BMP"):
        raise SystemExit("could not write " + path)
    print("wrote {} ({}x{})".format(path, rgb.width(), rgb.height()))
    return path


def _save_png(img: QImage, name: str) -> str:
    path = os.path.join(OUT_DIR, name)
    if not img.save(path, "PNG"):
        raise SystemExit("could not write " + path)
    print("wrote {} ({}x{})".format(path, img.width(), img.height()))
    return path


def _rounded_bg(p: QPainter, w: int, h: int, radius: int, border: int) -> None:
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BG)
    p.drawRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setPen(QPen(GOLD, border))
    p.setBrush(Qt.BrushStyle.NoBrush)
    inset = border / 2.0
    p.drawRoundedRect(
        QRectF(inset, inset, w - border, h - border), radius, radius
    )


def make_splash() -> str:
    """580x220 bootloader splash (matches the in-app Qt splash geometry)."""
    w, h = 580, 220
    img = QImage(w, h, QImage.Format.Format_RGB888)
    img.fill(BG)
    p = QPainter(img)
    _rounded_bg(p, w, h, 16, 3)

    # Faint gold glow in the upper-right corner for depth.
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 193, 7, 16))
    p.drawEllipse(QRectF(w - 210, -110, 320, 260))

    _draw_icon(p, (w - 54) / 2.0, 18, 54)

    p.setPen(WHITE)
    f = QFont("Segoe UI")
    f.setBold(True)
    f.setPixelSize(34)
    p.setFont(f)
    p.drawText(
        QRectF(0, 78, w, 46),
        Qt.AlignmentFlag.AlignCenter,
        "Accessible Video Transcriber",
    )

    f2 = QFont("Segoe UI")
    f2.setPixelSize(22)
    p.setFont(f2)
    p.setPen(GOLD)
    p.drawText(QRectF(0, 124, w, 32), Qt.AlignmentFlag.AlignCenter, "By Iman Rammal")

    p.end()
    return _save(img, "splash.bmp")


def make_splash_png() -> str:
    """Same artwork as a PNG: the bootloader splash only accepts PNG."""
    w, h = 580, 220
    img = QImage(w, h, QImage.Format.Format_RGB888)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(BG)
    p.drawRoundedRect(QRectF(0, 0, w, h), 16, 16)
    p.setBrush(QColor(255, 193, 7, 16))
    p.drawEllipse(QRectF(w - 210, -110, 320, 260))

    _draw_icon(p, (w - 54) / 2.0, 18, 54)

    p.setPen(WHITE)
    f = QFont("Segoe UI")
    f.setBold(True)
    f.setPixelSize(34)
    p.setFont(f)
    p.drawText(
        QRectF(0, 78, w, 46),
        Qt.AlignmentFlag.AlignCenter,
        "Accessible Video Transcriber",
    )

    f2 = QFont("Segoe UI")
    f2.setPixelSize(22)
    p.setFont(f2)
    p.setPen(GOLD)
    p.drawText(QRectF(0, 124, w, 32), Qt.AlignmentFlag.AlignCenter, "By Iman Rammal")
    p.end()
    return _save_png(img, "splash.png")


def make_wiz_image() -> str:
    """164x314 wizard banner (Inno Setup default geometry)."""
    w, h = 164, 314
    img = QImage(w, h, QImage.Format.Format_RGB888)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Soft gold wedge down the right-hand edge.
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 193, 7, 22))
    p.drawPolygon(
        QPolygonF([QPointF(w, 0), QPointF(w, h), QPointF(w - 64, h)])
    )

    _draw_icon(p, (w - 66) / 2.0, 44, 66)

    p.setPen(WHITE)
    f = QFont("Segoe UI")
    f.setBold(True)
    f.setPixelSize(17)
    p.setFont(f)
    p.drawText(
        QRectF(10, 116, w - 20, 86),
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        "Accessible\nVideo\nTranscriber",
    )

    p.setPen(QPen(GOLD, 3))
    p.drawLine(62, 206, w - 62, 206)

    f2 = QFont("Segoe UI")
    f2.setPixelSize(11)
    p.setFont(f2)
    p.setPen(GOLD)
    p.drawText(QRectF(0, 216, w, 18), Qt.AlignmentFlag.AlignCenter, "By Iman Rammal")

    f3 = QFont("Segoe UI")
    f3.setPixelSize(10)
    p.setFont(f3)
    p.setPen(MUTED)
    p.drawText(
        QRectF(0, 244, w, 16), Qt.AlignmentFlag.AlignCenter, "version " + VERSION
    )

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(GOLD)
    p.drawRect(0, h - 8, w, 8)
    p.end()
    return _save(img, "wiz-image.bmp")


def make_wiz_small() -> str:
    """55x58 wizard title image (Inno Setup default geometry)."""
    w, h = 55, 58
    img = QImage(w, h, QImage.Format.Format_RGB888)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(GOLD, 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 8, 8)
    _draw_icon(p, (w - 34) / 2.0, (h - 34) / 2.0, 34)
    p.end()
    return _save(img, "wiz-small.bmp")


# Module-level reference: PyQt destroys a QApplication whose Python wrapper is
# collected, and painting afterwards aborts the process with 0xC0000409.
_APP = None


def main() -> int:
    global _APP
    if not os.path.exists(ICON):
        raise SystemExit("missing " + ICON)
    os.makedirs(OUT_DIR, exist_ok=True)
    _APP = QApplication([])
    make_splash()
    make_splash_png()
    make_wiz_image()
    make_wiz_small()
    return 0



if __name__ == "__main__":
    sys.exit(main())
