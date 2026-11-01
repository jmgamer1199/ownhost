"""Draws the app icon and the small theme graphics into ownhost/app/assets/:

    icon.png (256 px), icon.ico (Windows), arrow-down.png, arrow-up.png, check.png

Only needs to be run if the design changes:
    python scripts/generate_icon.py
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ownhost" / "app" / "assets"

BG = QColor("#0a0a0a")
EDGE = QColor("#2a2a2a")
UNIT = QColor("#1a1a1a")
VENT = QColor("#333333")
CYAN = QColor("#22d3ee")
GREEN = QColor("#4ade80")
RED = QColor("#ff5c5c")


def draw(size: int) -> QImage:
    """Three server units on black, square corners: the top one selected (cyan edge) and running
    (green light), the other two stopped (red lights)."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    s = size / 256
    small = size <= 32  # at taskbar size: no vents and thicker units, so it stays readable

    p.setPen(Qt.PenStyle.NoPen)
    margin = 0 if small else 8
    p.fillRect(QRectF(margin * s, margin * s, (256 - 2 * margin) * s, (256 - 2 * margin) * s), BG)
    if not small:
        p.setPen(QPen(EDGE, max(1.0, 2 * s)))
        p.drawRect(QRectF(margin * s, margin * s, (256 - 2 * margin) * s, (256 - 2 * margin) * s))
        p.setPen(Qt.PenStyle.NoPen)

    left, width = (36, 184) if small else (52, 152)
    height, step, top = (52, 64, 34) if small else (36, 48, 62)
    for i, light in enumerate((GREEN, RED, RED)):
        y = top + i * step
        p.fillRect(QRectF(left * s, y * s, width * s, height * s), UNIT)
        p.fillRect(QRectF(left * s, y * s, (14 if small else 8) * s, height * s),
                   CYAN if i == 0 else QColor("#3a3a3a"))
        if not small:
            for k in range(4):
                p.fillRect(QRectF((76 + k * 18) * s, (y + 13) * s, 10 * s, 10 * s), VENT)
        dot = 22 if small else 12
        p.fillRect(QRectF((left + width - dot - (14 if small else 14)) * s, (y + (height - dot) / 2) * s,
                          dot * s, dot * s), light)
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data)


def write_ico(path: Path, sizes: list[int]) -> None:
    """ICO with PNG images inside (format supported since Windows Vista)."""
    images = [png_bytes(draw(n)) for n in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for n, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    path.write_bytes(header + entries + b"".join(images))


def _stroke(points: list[tuple[float, float]], color: QColor, width: float) -> QImage:
    img = QImage(32, 32, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    p.setPen(pen)
    path = QPainterPath(QPointF(*points[0]))
    for pt in points[1:]:
        path.lineTo(*pt)
    p.drawPath(path)
    p.end()
    return img


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    draw(256).save(str(OUT / "icon.png"))
    write_ico(OUT / "icon.ico", [16, 24, 32, 48, 64, 128, 256])
    ink = QColor("#a3a3a3")
    _stroke([(7, 11), (16, 21), (25, 11)], ink, 3.5).save(str(OUT / "arrow-down.png"))
    _stroke([(7, 21), (16, 11), (25, 21)], ink, 3.5).save(str(OUT / "arrow-up.png"))
    _stroke([(6, 17), (13, 24), (26, 8)], QColor("#0a0a0a"), 4.5).save(str(OUT / "check.png"))
    print(f"Graphics generated in {OUT}")
