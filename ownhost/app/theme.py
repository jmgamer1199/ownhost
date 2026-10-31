"""Tema visual Frutiger Aero, al estilo de Windows Vista / 7.

Cielo azul con nubes, pradera iluminada por el sol, un árbol y una hoja con gotas de agua;
paneles de cristal translúcido bien separados y botones-píldora brillantes.
"""

import math
import random
import sys

from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRectF, QSize, QSizeF, Qt
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPalette, QPen, QPixmap, QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QFrame, QLabel, QVBoxLayout, QWidget,
)

from ownhost.app import ASSETS

TEXT = "#06324a"          # azul marino: legible sobre cristal claro
TEXT_SOFT = "#2f5f78"
AQUA = "#1aa7e8"
DANGER_TEXT = "#b42318"
DISABLED = "rgba(6, 50, 74, 90)"

OFFLINE = "#6f8fa3"
STATUS_DOT = {
    "stopped": "#6f8fa3", "starting": "#d99a00", "running": "#16a34a", "stopping": "#d99a00",
    "crashed": "#dc2626", "installing": AQUA, "updating": AQUA, "backing-up": AQUA,
    "restoring": AQUA, "importing": AQUA, "installing-mod": AQUA, "cloning": AQUA,
}


def _gloss(top, upper, lower, bottom) -> str:
    # Brillo de Vista: mitad superior casi blanca, corte nítido a media altura y base saturada.
    return (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {top}, stop:0.48 {upper}, "
            f"stop:0.5 {lower}, stop:1 {bottom})")


BTN = _gloss("rgba(255,255,255,245)", "rgba(232,246,255,225)", "rgba(178,224,250,215)", "rgba(222,243,255,230)")
BTN_HOVER = _gloss("#ffffff", "rgba(240,250,255,240)", "rgba(140,210,250,230)", "rgba(205,238,255,240)")
BTN_PRESSED = _gloss("rgba(200,232,250,240)", "rgba(170,218,245,235)", "rgba(110,190,240,235)", "rgba(170,222,250,235)")
PRIMARY = _gloss("#f3ffe9", "#bff0a0", "#52c234", "#9be47a")
PRIMARY_HOVER = _gloss("#ffffff", "#cdf5b3", "#3fb51f", "#8cdc66")
DANGER = _gloss("#fff2ef", "#ffcfc4", "#ee6a4f", "#f9ad9a")
DANGER_HOVER = _gloss("#ffffff", "#ffdad1", "#e65233", "#f79c85")
SELECTED = _gloss("rgba(255,255,255,250)", "rgba(214,240,255,240)", "rgba(120,200,250,230)", "rgba(190,232,255,240)")
# Cristal de los paneles: translúcido para que se vea el paisaje, con brillo arriba.
GLASS = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,170), stop:0.12 rgba(240,250,255,120), "
         "stop:1 rgba(215,238,255,105))")
ROW = "rgba(255,255,255,95)"

STYLESHEET = f"""
* {{
    color: {TEXT};
    selection-background-color: rgba(26, 167, 232, 110);
    selection-color: #021d2c;
}}
QDialog, QMessageBox, QProgressDialog, QInputDialog {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #e3f4ff, stop:1 #cdeec0);
}}
QToolTip {{ color: {TEXT}; background: #f7fcff; border: 1px solid {AQUA}; border-radius: 8px; padding: 4px 6px; }}
QLabel {{ background: transparent; }}

/* ---------- paneles de cristal ---------- */
QFrame#glass {{
    background: {GLASS};
    border: 1px solid rgba(255, 255, 255, 230);
    border-radius: 22px;
}}
QLabel#panelTitle {{ color: {TEXT_SOFT}; font-weight: 600; padding: 2px 6px; }}
QLabel#title {{ color: #032a40; font-family: "Segoe UI Light", "Segoe UI"; font-size: 24pt; }}
QLabel#appTitle {{ color: #ffffff; font-family: "Segoe UI Light", "Segoe UI"; font-size: 17pt; }}
QLabel#subtitle, QLabel#muted {{ color: {TEXT_SOFT}; }}
QLabel#error {{ color: {DANGER_TEXT}; }}
QLabel#accent {{ color: #0369a1; }}

/* ---------- barra superior sobre el cielo ---------- */
QPushButton#top {{
    background: {BTN}; border: 1px solid rgba(255,255,255,240); border-radius: 17px; padding: 7px 20px;
    color: {TEXT}; font-weight: 600;
}}
QPushButton#top:hover {{ background: {BTN_HOVER}; border-color: #ffffff; }}
QPushButton#top:pressed {{ background: {BTN_PRESSED}; }}

/* ---------- botones-píldora ---------- */
QPushButton {{
    background: {BTN}; border: 1px solid rgba(70, 150, 200, 170); border-radius: 15px;
    padding: 6px 18px; min-height: 18px; color: {TEXT};
}}
QPushButton:hover {{ background: {BTN_HOVER}; border-color: #2a9be0; }}
QPushButton:pressed {{ background: {BTN_PRESSED}; }}
QPushButton:default {{ border: 1px solid #1f8fd6; }}
QPushButton:disabled {{ background: rgba(255,255,255,90); border-color: rgba(120,170,200,100); color: {DISABLED}; }}
QPushButton[kind="primary"] {{ background: {PRIMARY}; border-color: #3a9e22; color: #0b3a05; font-weight: 600; }}
QPushButton[kind="primary"]:hover {{ background: {PRIMARY_HOVER}; }}
QPushButton[kind="danger"] {{ background: {DANGER}; border-color: #d0533a; color: #561208; }}
QPushButton[kind="danger"]:hover {{ background: {DANGER_HOVER}; }}
QPushButton[kind="primary"]:disabled, QPushButton[kind="danger"]:disabled {{
    background: rgba(255,255,255,90); border-color: rgba(120,170,200,100); color: {DISABLED};
}}
QPushButton::menu-indicator {{
    image: url("{{ASSETS}}/arrow-down.png"); width: 9px; height: 9px;
    subcontrol-origin: padding; subcontrol-position: right center; right: 9px;
}}
QPushButton[menu="true"] {{ padding-right: 28px; }}

/* ---------- campos ---------- */
QLineEdit, QAbstractSpinBox, QComboBox {{
    background: rgba(255,255,255,225); border: 1px solid rgba(90, 160, 205, 160); border-radius: 13px;
    padding: 5px 12px; min-height: 18px;
}}
QLineEdit:hover, QAbstractSpinBox:hover, QComboBox:hover {{ border-color: {AQUA}; }}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {{ border: 1px solid #1f8fd6; background: #ffffff; }}
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled {{ background: rgba(255,255,255,110); color: {DISABLED}; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 26px; border: none; }}
QComboBox::down-arrow {{ image: url("{{ASSETS}}/arrow-down.png"); width: 11px; height: 11px; }}
QComboBox QAbstractItemView {{
    background: #f7fcff; border: 1px solid {AQUA}; outline: none; selection-background-color: rgba(26,167,232,70);
}}
QAbstractSpinBox {{ padding-right: 24px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ subcontrol-origin: border; width: 22px; border: none; background: transparent; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: rgba(26, 167, 232, 45); border-radius: 8px; }}
QAbstractSpinBox::up-arrow {{ image: url("{{ASSETS}}/arrow-up.png"); width: 9px; height: 9px; }}
QAbstractSpinBox::down-arrow {{ image: url("{{ASSETS}}/arrow-down.png"); width: 9px; height: 9px; }}
QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QAbstractItemView::indicator {{
    width: 17px; height: 17px; border: 1px solid rgba(70, 150, 200, 190); border-radius: 9px; background: {BTN};
}}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {{ border-color: #1f8fd6; }}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {{ image: url("{{ASSETS}}/check.png"); background: {PRIMARY}; border-color: #3a9e22; }}
QCheckBox:disabled {{ color: {DISABLED}; }}

/* ---------- pestañas ---------- */
QTabWidget::pane {{
    background: rgba(255,255,255,85); border: 1px solid rgba(255,255,255,210); border-radius: 18px; top: -1px;
}}
QTabBar::tab {{
    background: rgba(255,255,255,105); border: 1px solid rgba(255,255,255,200); border-bottom: none;
    border-top-left-radius: 13px; border-top-right-radius: 13px;
    padding: 7px 12px; margin-right: 3px; color: {TEXT_SOFT};
}}
QTabBar::tab:hover {{ background: rgba(255,255,255,185); color: {TEXT}; }}
QTabBar::tab:selected {{ background: {BTN}; color: {TEXT}; font-weight: 600; border-color: rgba(70,150,200,170); }}
QTabBar::tab:disabled {{ color: rgba(47,95,120,90); }}

/* ---------- listas: cada fila es su propia píldora de cristal ---------- */
QTreeWidget, QTableWidget, QListView {{
    background: rgba(255,255,255,120); border: 1px solid rgba(255,255,255,210); border-radius: 16px;
    alternate-background-color: rgba(225,243,255,110); gridline-color: rgba(255,255,255,150); outline: none;
}}
QTreeWidget#hosts {{ background: transparent; border: none; show-decoration-selected: 0; }}
QTreeView::branch:selected, QTreeView::branch:hover {{ background: transparent; }}
QTreeWidget#hosts::branch, QTreeWidget#hosts::branch:selected, QTreeWidget#hosts::branch:hover {{
    background: transparent; border: none; image: none;
}}
QTreeWidget#hosts::item {{
    background: {ROW}; border: 1px solid rgba(255,255,255,190); border-radius: 13px;
    margin: 3px 2px; padding: 7px 6px;
}}
QTreeWidget#hosts::item:hover {{ background: rgba(255,255,255,170); }}
QListWidget#detected {{ background: transparent; border: none; outline: none; }}
QListWidget#detected::item {{
    background: rgba(255,255,255,60); border: 1px dashed rgba(255,255,255,220); border-radius: 13px;
    margin: 3px 2px; padding: 7px 6px; color: {TEXT_SOFT};
}}
QListWidget#detected::item:hover {{ background: rgba(255,255,255,170); color: {TEXT}; }}
QTreeWidget#hosts::item:selected {{ background: {SELECTED}; border: 1px solid rgba(40,150,220,180); color: #021d2c; }}
QTableWidget::item {{ padding: 6px 4px; border-bottom: 1px solid rgba(255,255,255,140); }}
QTableWidget::item:hover {{ background: rgba(255,255,255,150); }}
QTableWidget::item:selected {{ background: {SELECTED}; color: #021d2c; }}
QHeaderView::section {{
    background: {BTN}; color: {TEXT}; border: none; border-right: 1px solid rgba(255,255,255,170);
    border-bottom: 1px solid rgba(70,150,200,140); padding: 6px 8px; font-weight: 600;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

/* ---------- consola: cristal oscuro como el agua profunda ---------- */
QPlainTextEdit#console {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(8, 50, 90, 225), stop:1 rgba(3, 25, 50, 235));
    color: #c8f1ff; border: 1px solid rgba(255, 255, 255, 200); border-radius: 16px; padding: 10px;
    selection-background-color: rgba(26, 167, 232, 150); selection-color: #ffffff;
}}

/* ---------- barras de desplazamiento ---------- */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 4px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 4px; }}
QScrollBar::handle {{
    background: {BTN}; border: 1px solid rgba(70,150,200,150); border-radius: 5px; min-height: 26px; min-width: 26px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background: transparent; }}
QMenu {{ background: #f7fcff; border: 1px solid {AQUA}; border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 7px 24px; border-radius: 9px; }}
QMenu::item:selected {{ background: {SELECTED}; }}
QMenu::item:disabled {{ color: {DISABLED}; }}
QStatusBar {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e9f7ff, stop:1 #c9e9ff); color: {TEXT}; }}
QProgressBar {{ background: rgba(255,255,255,210); border: 1px solid rgba(70,150,200,150); border-radius: 9px; text-align: center; }}
QProgressBar::chunk {{ background: {PRIMARY}; border-radius: 8px; }}
"""

STATUS_PILL = {
    "running": ("#f0ffe6", "#52c234", "#0f4d05"),
    "starting": ("#fff8e0", "#f2bd32", "#6b4a00"),
    "stopping": ("#fff8e0", "#f2bd32", "#6b4a00"),
    "crashed": ("#fff0ec", "#ee6a4f", "#761a0a"),
}
STATUS_PILL_DEFAULT = ("#f2faff", "#8ccff2", "#0b4466")


def pill_style(status: str) -> str:
    top, bottom, text = STATUS_PILL.get(status, STATUS_PILL_DEFAULT)
    return (f"QLabel {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.48 {top}, "
            f"stop:0.5 {bottom}, stop:1 {top}); color: {text}; border: 1px solid {bottom}; "
            f"border-radius: 13px; padding: 4px 16px; font-weight: 600; }}")


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    family = "Segoe UI" if sys.platform == "win32" else app.font().family()
    app.setFont(QFont(family, 10))
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#dcefff"), (QPalette.ColorRole.Base, "#ffffff"),
        (QPalette.ColorRole.AlternateBase, "#eef8ff"), (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.WindowText, TEXT), (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Button, "#e8f6ff"), (QPalette.ColorRole.Highlight, "#5cc1f2"),
        (QPalette.ColorRole.HighlightedText, "#021d2c"), (QPalette.ColorRole.Link, "#0369a1"),
        (QPalette.ColorRole.ToolTipBase, "#f7fcff"), (QPalette.ColorRole.ToolTipText, TEXT),
        (QPalette.ColorRole.PlaceholderText, "#7f9db0"),
    ):
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(6, 50, 74, 90))
    app.setPalette(palette)
    # Las imágenes del tema necesitan ruta absoluta (también dentro del exe/AppImage).
    app.setStyleSheet(STYLESHEET.replace("{ASSETS}", ASSETS.as_posix()))
    app._field_fixes = FieldFixes(app)  # se guarda para que no lo borre el recolector
    app.installEventFilter(app._field_fixes)


class FieldFixes(QObject):
    """Arreglos de los campos en toda la app:
    - La rueda del ratón no cambia números ni desplegables si no tienen el foco: al bajar por una
      página de ajustes se cambiaba la memoria o el puerto sin querer. La página se desplaza.
    - El texto de los campos numéricos con el mismo margen que el resto (Qt ignora el padding)."""

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Polish and isinstance(obj, (QAbstractSpinBox, QComboBox)):
            obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            if isinstance(obj, QAbstractSpinBox) and obj.lineEdit():
                obj.lineEdit().setTextMargins(10, 0, 0, 0)
        elif event.type() == QEvent.Type.Wheel and isinstance(obj, (QAbstractSpinBox, QComboBox)) \
                and not obj.hasFocus():
            area = obj.parent()
            while area and not isinstance(area, QAbstractScrollArea):
                area = area.parent()
            if area:
                QApplication.sendEvent(area.verticalScrollBar(), event)
            return True
        return False


# ---------------------------------------------------------------------------------------------
# Paisaje del fondo
# ---------------------------------------------------------------------------------------------

def _cloud(p: QPainter, x: float, y: float, size: float, rnd: random.Random) -> None:
    """Nube esponjosa: varias bolas blancas con la base ligeramente azulada."""
    puffs = [(x + dx * size, y + dy * size, r * size) for dx, dy, r in
             ((-0.9, 0.15, 0.45), (-0.35, -0.2, 0.62), (0.3, -0.32, 0.7), (0.95, 0.0, 0.5), (0.2, 0.2, 0.55))]
    for px, py, r in puffs:
        r *= rnd.uniform(0.9, 1.1)
        g = QRadialGradient(QPointF(px - r * 0.25, py - r * 0.35), r * 1.25)
        g.setColorAt(0, QColor(255, 255, 255, 250))
        g.setColorAt(0.6, QColor(248, 252, 255, 235))
        g.setColorAt(0.9, QColor(205, 230, 248, 160))
        g.setColorAt(1, QColor(205, 230, 248, 0))
        p.setBrush(g)
        p.drawEllipse(QPointF(px, py), r, r)


def _tree(p: QPainter, x: float, ground: float, height: float) -> None:
    trunk = QPainterPath(QPointF(x - height * 0.04, ground))
    trunk.cubicTo(QPointF(x - height * 0.03, ground - height * 0.3), QPointF(x - height * 0.02, ground - height * 0.45),
                  QPointF(x, ground - height * 0.55))
    trunk.cubicTo(QPointF(x + height * 0.02, ground - height * 0.45), QPointF(x + height * 0.03, ground - height * 0.3),
                  QPointF(x + height * 0.05, ground))
    bark = QLinearGradient(x - height * 0.05, 0, x + height * 0.05, 0)
    bark.setColorAt(0, QColor("#3d2a17"))
    bark.setColorAt(0.5, QColor("#6b4a2b"))
    bark.setColorAt(1, QColor("#3d2a17"))
    p.setBrush(bark)
    p.drawPath(trunk)
    cy = ground - height * 0.68
    for dx, dy, r in ((-0.22, 0.08, 0.2), (0.2, 0.06, 0.21), (0, -0.12, 0.25), (-0.12, -0.05, 0.2),
                      (0.12, -0.04, 0.2), (0, 0.1, 0.2), (-0.3, -0.02, 0.15), (0.3, -0.03, 0.15)):
        c = QPointF(x + dx * height, cy + dy * height)
        rr = r * height
        g = QRadialGradient(c - QPointF(rr * 0.35, rr * 0.45), rr * 1.3)
        g.setColorAt(0, QColor("#b9ec6a"))
        g.setColorAt(0.5, QColor("#5fb82f"))
        g.setColorAt(1, QColor("#2c7a1f"))
        p.setBrush(g)
        p.drawEllipse(c, rr, rr)


def _drop(p: QPainter, c: QPointF, r: float) -> None:
    """Gota de agua brillante (lente con reflejo)."""
    g = QRadialGradient(c + QPointF(r * 0.2, r * 0.3), r * 1.1)
    g.setColorAt(0, QColor(255, 255, 255, 60))
    g.setColorAt(0.7, QColor(180, 230, 255, 70))
    g.setColorAt(0.95, QColor(255, 255, 255, 190))
    g.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(g)
    p.drawEllipse(c, r, r)
    hl = QRadialGradient(c - QPointF(r * 0.35, r * 0.4), r * 0.4)
    hl.setColorAt(0, QColor(255, 255, 255, 240))
    hl.setColorAt(1, QColor(255, 255, 255, 0))
    p.setBrush(hl)
    p.drawEllipse(c - QPointF(r * 0.35, r * 0.4), r * 0.4, r * 0.28)


def _leaf_with_drops(p: QPainter, base: QPointF, length: float, angle: float) -> None:
    p.save()
    p.translate(base)
    p.rotate(angle)
    w = length * 0.42
    shape = QPainterPath(QPointF(0, 0))
    shape.cubicTo(QPointF(length * 0.25, -w), QPointF(length * 0.8, -w * 0.8), QPointF(length, 0))
    shape.cubicTo(QPointF(length * 0.8, w * 0.8), QPointF(length * 0.25, w), QPointF(0, 0))
    g = QLinearGradient(0, -w, 0, w)
    g.setColorAt(0, QColor("#c8f56b"))
    g.setColorAt(0.5, QColor("#5cc42c"))
    g.setColorAt(1, QColor("#2a8a1e"))
    p.setBrush(g)
    p.drawPath(shape)
    p.save()
    p.setClipPath(shape, Qt.ClipOperation.IntersectClip)  # nervios y brillo dentro de la hoja
    p.setPen(QPen(QColor(230, 255, 200, 170), max(1.5, length * 0.008)))
    p.drawLine(QPointF(length * 0.02, 0), QPointF(length * 0.95, 0))
    for k in range(1, 6):
        x = length * k / 6.5
        p.drawLine(QPointF(x, 0), QPointF(x + length * 0.1, -w * 0.55))
        p.drawLine(QPointF(x, 0), QPointF(x + length * 0.1, w * 0.55))
    p.setPen(Qt.PenStyle.NoPen)
    shine = QPainterPath(QPointF(length * 0.08, -w * 0.15))
    shine.cubicTo(QPointF(length * 0.3, -w * 0.85), QPointF(length * 0.7, -w * 0.7), QPointF(length * 0.92, -w * 0.08))
    shine.cubicTo(QPointF(length * 0.6, -w * 0.4), QPointF(length * 0.3, -w * 0.45), QPointF(length * 0.08, -w * 0.15))
    p.setBrush(QColor(255, 255, 255, 80))
    p.drawPath(shine)
    p.restore()
    for fx, fy, fr in ((0.35, -0.25, 0.05), (0.6, 0.2, 0.04), (0.78, -0.12, 0.03), (0.5, -0.05, 0.025)):
        _drop(p, QPointF(length * fx, w * fy), length * fr)
    p.restore()


def paint_scene(p: QPainter, w: int, h: int) -> None:
    rnd = random.Random(2007)
    p.setPen(Qt.PenStyle.NoPen)

    # Cielo
    sky = QLinearGradient(0, 0, 0, h * 0.75)
    sky.setColorAt(0, QColor("#0563c9"))
    sky.setColorAt(0.45, QColor("#2fa0ef"))
    sky.setColorAt(0.85, QColor("#9fdcff"))
    sky.setColorAt(1, QColor("#e4f7ff"))
    p.fillRect(QRectF(0, 0, w, h), sky)

    # Sol arriba a la derecha con rayos hacia abajo y a la izquierda (el título queda sobre azul limpio)
    sun = QPointF(w * 0.9, h * 0.02)
    for i in range(14):
        a = math.radians(95 + i * 7)
        spread = math.radians(1.6)
        far = max(w, h) * 1.3
        ray = QPainterPath(sun)
        ray.lineTo(sun + QPointF(math.cos(a - spread) * far, math.sin(a - spread) * far))
        ray.lineTo(sun + QPointF(math.cos(a + spread) * far, math.sin(a + spread) * far))
        ray.closeSubpath()
        g = QRadialGradient(sun, far * 0.7)
        g.setColorAt(0, QColor(255, 255, 255, 70 if i % 2 else 40))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(g)
        p.drawPath(ray)
    halo = QRadialGradient(sun, max(w, h) * 0.45)
    halo.setColorAt(0, QColor(255, 255, 255, 255))
    halo.setColorAt(0.06, QColor(255, 255, 235, 220))
    halo.setColorAt(0.3, QColor(255, 255, 255, 60))
    halo.setColorAt(1, QColor(255, 255, 255, 0))
    p.fillRect(QRectF(0, 0, w, h), halo)

    # Nubes
    # (ninguna en la franja superior izquierda, donde va el título de la app)
    for cx, cy, size in ((0.42, 0.24, 0.07), (0.66, 0.16, 0.08), (0.88, 0.32, 0.07), (0.5, 0.44, 0.05),
                         (0.12, 0.42, 0.06)):
        _cloud(p, w * cx, h * cy, min(w, h) * size * 1.6, rnd)

    # Colinas lejanas con bruma
    far_hill = QPainterPath(QPointF(0, h))
    far_hill.lineTo(0, h * 0.66)
    far_hill.cubicTo(QPointF(w * 0.3, h * 0.6), QPointF(w * 0.6, h * 0.7), QPointF(w, h * 0.62))
    far_hill.lineTo(w, h)
    g = QLinearGradient(0, h * 0.6, 0, h * 0.8)
    g.setColorAt(0, QColor("#9ad9a8"))
    g.setColorAt(1, QColor("#5fb86e"))
    p.setBrush(g)
    p.drawPath(far_hill)

    # Pradera iluminada
    meadow = QPainterPath(QPointF(0, h))
    meadow.lineTo(0, h * 0.74)
    meadow.cubicTo(QPointF(w * 0.35, h * 0.66), QPointF(w * 0.65, h * 0.8), QPointF(w, h * 0.7))
    meadow.lineTo(w, h)
    meadow.closeSubpath()
    g = QLinearGradient(0, h * 0.66, 0, h)
    g.setColorAt(0, QColor("#d6f75f"))
    g.setColorAt(0.25, QColor("#8fd63a"))
    g.setColorAt(1, QColor("#2f8f1f"))
    p.setBrush(g)
    p.drawPath(meadow)
    light = QRadialGradient(QPointF(w * 0.3, h * 0.72), w * 0.4)
    light.setColorAt(0, QColor(255, 255, 200, 120))
    light.setColorAt(1, QColor(255, 255, 200, 0))
    p.setBrush(light)
    p.drawPath(meadow)

    _tree(p, w * 0.78, h * 0.76, h * 0.42)

    # Hoja con gotas de rocío en la esquina inferior derecha
    _leaf_with_drops(p, QPointF(w * 1.02, h * 0.98), min(w, h) * 0.42, -150)

    # Gotas y burbujas sueltas
    for _ in range(16):
        _drop(p, QPointF(rnd.uniform(0, w), rnd.uniform(0, h * 0.7)), rnd.uniform(5, 18))


class Backdrop(QWidget):
    """Fondo de la ventana. Se dibuja una vez por tamaño y se guarda: el resto del tiempo solo se copia."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracked: set[QWidget] = set()
        self._scene: QPixmap | None = None
        self._scene_size = QSize()

    def eventFilter(self, obj, event) -> bool:
        # Si un panel se mueve o cambia de tamaño, hay que repintar su sombra.
        if event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide):
            self.update()
        return False

    def _ensure_scene(self) -> QPixmap:
        if self._scene is None or self._scene_size != self.size():
            ratio = self.devicePixelRatioF()
            pix = QPixmap(self.size() * ratio)
            pix.setDevicePixelRatio(ratio)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            paint_scene(painter, self.width(), self.height())
            painter.end()
            self._scene, self._scene_size = pix, self.size()
        return self._scene

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.drawPixmap(0, 0, self._ensure_scene())
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Sombra suave bajo los paneles de cristal
        p.setPen(Qt.PenStyle.NoPen)
        for frame in self.findChildren(QFrame, "glass"):
            if not frame.isVisible():
                continue
            if frame not in self._tracked:
                frame.installEventFilter(self)
                self._tracked.add(frame)
            r = QRectF(QPointF(frame.mapTo(self, QPoint(0, 0))), QSizeF(frame.size()))
            for i in range(12, 0, -1):
                p.setBrush(QColor(0, 40, 90, 8))
                p.drawRoundedRect(r.adjusted(-i, -i + 8, i, i + 8), 22 + i, 22 + i)
        p.end()


def glass(content: QWidget, title: str | None = None, margins: int = 14) -> QFrame:
    """Envuelve un widget en un panel de cristal."""
    frame = QFrame()
    frame.setObjectName("glass")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(8)
    if title:
        label = QLabel(title)
        label.setObjectName("panelTitle")
        layout.addWidget(label)
    layout.addWidget(content, 1)
    return frame
