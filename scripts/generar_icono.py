"""Dibuja el icono de la app y los pequeños gráficos del tema, en ownhost/app/assets/:

    icon.png (256 px), icon.ico (Windows), arrow-down.png, arrow-up.png, check.png

Solo hace falta ejecutarlo si se cambia el diseño:
    python scripts/generar_icono.py
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient,
)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from ownhost.app.theme import _leaf_with_drops  # noqa: E402  (la misma hoja que el fondo de la app)

OUT = ROOT / "ownhost" / "app" / "assets"


def draw(size: int) -> QImage:
    """Icono Frutiger Aero: cielo, pradera y una hoja con gotas de rocío bajo un brillo de cristal."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256

    tile = QRectF(10 * s, 10 * s, 236 * s, 236 * s)
    clip = QPainterPath()
    clip.addRoundedRect(tile, 60 * s, 60 * s)
    p.setPen(Qt.PenStyle.NoPen)
    base = QLinearGradient(0, tile.top(), 0, tile.bottom())
    base.setColorAt(0, QColor("#0563c9"))
    base.setColorAt(0.6, QColor("#4fb8f5"))
    base.setColorAt(1, QColor("#d9f4ff"))
    p.setBrush(base)
    p.drawPath(clip)
    p.setClipPath(clip)
    meadow = QPainterPath(QPointF(0, 256 * s))
    meadow.lineTo(0, 190 * s)
    meadow.cubicTo(QPointF(80 * s, 165 * s), QPointF(170 * s, 205 * s), QPointF(256 * s, 178 * s))
    meadow.lineTo(256 * s, 256 * s)
    grass = QLinearGradient(0, 165 * s, 0, 256 * s)
    grass.setColorAt(0, QColor("#d6f75f"))
    grass.setColorAt(1, QColor("#2f8f1f"))
    p.setBrush(grass)
    p.drawPath(meadow)

    _leaf_with_drops(p, QPointF(36 * s, 210 * s), 200 * s, -42)

    # Pequeñas burbujas
    for cx, cy, r in ((62, 70, 13), (196, 186, 10), (78, 196, 7)):
        g = QRadialGradient(QPointF(cx * s, cy * s), r * s)
        g.setColorAt(0, QColor(255, 255, 255, 30))
        g.setColorAt(0.85, QColor(255, 255, 255, 120))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(cx * s, cy * s), r * s, r * s)

    # Brillo de gota en la mitad superior
    shine = QPainterPath()
    shine.addRoundedRect(QRectF(18 * s, 16 * s, 220 * s, 108 * s), 54 * s, 54 * s)
    gloss = QLinearGradient(0, 16 * s, 0, 124 * s)
    gloss.setColorAt(0, QColor(255, 255, 255, 170))
    gloss.setColorAt(1, QColor(255, 255, 255, 8))
    p.setBrush(gloss)
    p.drawPath(shine)
    p.setClipping(False)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 220), 2.5 * s))
    p.drawRoundedRect(tile.adjusted(1 * s, 1 * s, -1 * s, -1 * s), 59 * s, 59 * s)
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(data)


def write_ico(path: Path, sizes: list[int]) -> None:
    """ICO con las imágenes en PNG dentro (formato admitido desde Windows Vista)."""
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
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
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
    ink = QColor("#0b5d73")
    _stroke([(6, 10), (16, 22), (26, 10)], ink, 4.5).save(str(OUT / "arrow-down.png"))
    _stroke([(6, 22), (16, 10), (26, 22)], ink, 4.5).save(str(OUT / "arrow-up.png"))
    _stroke([(6, 17), (13, 24), (26, 8)], QColor("#0d3b12"), 4.5).save(str(OUT / "check.png"))
    print(f"Gráficos generados en {OUT}")
