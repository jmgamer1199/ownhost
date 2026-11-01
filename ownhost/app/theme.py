"""Visual theme: black, square corners, a monospaced font for labels and numbers and a sans-serif one
for reading, cyan as the app's colour and green / amber / red only for server states.

Fonts (SIL Open Font License, in assets/fonts): Cascadia Mono and Geist.
"""

import sys

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractScrollArea, QAbstractSpinBox, QApplication, QComboBox, QFrame, QLabel, QPushButton, QTabBar,
    QToolButton, QVBoxLayout, QWidget,
)

from ownhost.app import ASSETS

# ---- palette (the same as the web panel) ----
CONSOLE = "#050505"
BG = "#0a0a0a"
PANEL = "#0d0d0d"
RAISED = "#1a1a1a"
LINE = "#2a2a2a"
LINE_STRONG = "#3a3a3a"
DECOR = "#6b6b6b"        # decoration only: below 4.5:1 for small text
TEXT_FAINT = "#8a8a8a"
TEXT_SOFT = "#a3a3a3"
TEXT = "#ededed"

ACCENT = "#22d3ee"       # cyan: main buttons, active tab, selection, usage bars
ACCENT_HOVER = "#67e8f9"
ACCENT_DARK = "#062a33"
GOOD = "#4ade80"         # green: running, online
GOOD_DARK = "#0f2a19"
WARN = "#f5a524"         # amber: starting, stopping, warnings
WARN_DARK = "#2e1f05"
BAD = "#ff5c5c"          # red: stopped, crashed, delete, errors
BAD_DARK = "#2e0b0b"

DANGER_TEXT = BAD
DISABLED = "#5a5a5a"
OFFLINE = TEXT_FAINT

MONO = "Cascadia Mono"
SANS = "Geist"

STATUS_COLORS = {  # status -> (text and border, background)
    "running": (GOOD, GOOD_DARK),
    "stopped": (BAD, BAD_DARK),
    "crashed": (BAD, BAD_DARK),
    "starting": (WARN, WARN_DARK),
    "stopping": (WARN, WARN_DARK),
}
BUSY_COLORS = (ACCENT, ACCENT_DARK)  # installing, updating, backing up...
STATUS_DOT = {status: colors[0] for status, colors in STATUS_COLORS.items()}
for _busy in ("installing", "updating", "backing-up", "restoring", "importing", "installing-mod", "cloning"):
    STATUS_DOT[_busy] = ACCENT

STYLESHEET = f"""
* {{
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QMainWindow, QDialog, QMessageBox, QProgressDialog, QInputDialog {{ background: {BG}; }}
QWidget#backdrop {{ background: {BG}; }}
QToolTip {{ color: {TEXT}; background: {RAISED}; border: 1px solid {LINE_STRONG}; padding: 4px 6px; }}
QLabel {{ background: transparent; }}
a {{ color: {ACCENT}; }}

/* ---------- panels ---------- */
QFrame#glass {{ background: {PANEL}; border: 1px solid {LINE}; }}
QLabel#panelTitle {{ color: {TEXT_FAINT}; font-family: "{MONO}"; font-size: 8pt; padding: 2px 2px 6px 2px; }}
QLabel#title {{ color: {TEXT}; font-family: "{SANS}"; font-size: 22pt; font-weight: 700; }}
QLabel#appTitle {{ color: {TEXT}; font-family: "{MONO}"; font-size: 11pt; font-weight: 700; }}
QLabel#subtitle, QLabel#muted {{ color: {TEXT_SOFT}; }}
QLabel#error {{ color: {BAD}; }}
QLabel#accent {{ color: {ACCENT}; }}
QLabel#ascii {{ color: {DECOR}; font-family: "{MONO}"; }}

/* ---------- buttons: square, outlined; the main one in cyan ---------- */
QPushButton {{
    background: transparent; border: 1px solid {LINE_STRONG}; border-radius: 0;
    padding: 6px 14px; min-height: 18px; color: {TEXT};
}}
QPushButton:hover {{ background: {RAISED}; border-color: {TEXT_FAINT}; }}
QPushButton:pressed {{ background: #262626; }}
QPushButton:focus {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {DISABLED}; border-color: {LINE}; background: transparent; }}
QDialog QPushButton:default, QMessageBox QPushButton:default {{ background: {ACCENT}; border-color: {ACCENT}; color: {BG}; }}
QDialog QPushButton:default:hover {{ background: {ACCENT_HOVER}; }}
QPushButton[kind="primary"] {{ background: {ACCENT}; border-color: {ACCENT}; color: {BG}; font-weight: 700; }}
QPushButton[kind="primary"]:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton[kind="primary"]:focus {{ border-color: {TEXT}; }}
QPushButton[kind="danger"] {{ color: {BAD}; border-color: {BAD}; }}
QPushButton[kind="danger"]:hover {{ background: {BAD_DARK}; }}
QPushButton[kind="primary"]:disabled, QPushButton[kind="danger"]:disabled {{
    background: transparent; border-color: {LINE}; color: {DISABLED};
}}
QPushButton::menu-indicator {{
    image: url("{{ASSETS}}/arrow-down.png"); width: 9px; height: 9px;
    subcontrol-origin: padding; subcontrol-position: right center; right: 9px;
}}
QPushButton[menu="true"] {{ padding-right: 28px; }}

/* ---------- fields ---------- */
QLineEdit, QAbstractSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {PANEL}; border: 1px solid {LINE_STRONG}; border-radius: 0; padding: 5px 10px; min-height: 18px;
}}
QLineEdit:hover, QAbstractSpinBox:hover, QComboBox:hover {{ border-color: {TEXT_FAINT}; }}
QLineEdit:focus, QAbstractSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QAbstractSpinBox:disabled, QComboBox:disabled {{ color: {DISABLED}; border-color: {LINE}; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 26px; border: none; }}
QComboBox::down-arrow {{ image: url("{{ASSETS}}/arrow-down.png"); width: 10px; height: 10px; }}
QComboBox QAbstractItemView {{
    background: {RAISED}; border: 1px solid {LINE_STRONG}; outline: none;
    selection-background-color: {ACCENT}; selection-color: {BG};
}}
QAbstractSpinBox {{ padding-right: 24px; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ subcontrol-origin: border; width: 22px; border: none; background: transparent; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; }}
QAbstractSpinBox::up-button:hover, QAbstractSpinBox::down-button:hover {{ background: {RAISED}; }}
QAbstractSpinBox::up-arrow {{ image: url("{{ASSETS}}/arrow-up.png"); width: 9px; height: 9px; }}
QAbstractSpinBox::down-arrow {{ image: url("{{ASSETS}}/arrow-down.png"); width: 9px; height: 9px; }}
QCheckBox, QRadioButton {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator, QAbstractItemView::indicator {{
    width: 14px; height: 14px; border: 1px solid {TEXT_FAINT}; border-radius: 0; background: {PANEL};
}}
QCheckBox::indicator:hover, QAbstractItemView::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {{
    image: url("{{ASSETS}}/check.png"); background: {ACCENT}; border-color: {ACCENT};
}}
QCheckBox:disabled {{ color: {DISABLED}; }}

/* ---------- tabs: text with a cyan line under the active one ---------- */
QTabWidget::pane {{ background: transparent; border: none; border-top: 1px solid {LINE}; top: -1px; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 8px 10px; margin-right: 0; color: {TEXT_SOFT}; font-family: "{MONO}"; font-size: 8.5pt;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: #ffffff; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:disabled {{ color: {DISABLED}; }}

/* ---------- lists and tables ---------- */
QTreeWidget, QTableWidget, QListView, QListWidget {{
    background: {PANEL}; border: 1px solid {LINE}; border-radius: 0;
    alternate-background-color: #111111; gridline-color: {LINE}; outline: none;
}}
QTreeWidget#hosts {{ background: transparent; border: none; show-decoration-selected: 0; }}
QTreeView::branch, QTreeView::branch:selected, QTreeView::branch:hover {{ background: transparent; image: none; }}
QTreeWidget#hosts::item {{ background: transparent; border: none; border-left: 2px solid transparent; padding: 7px 6px; }}
QTreeWidget#hosts::item:hover {{ background: #141414; }}
QTreeWidget#hosts::item:selected {{ background: {RAISED}; border-left: 2px solid {ACCENT}; color: #ffffff; }}
QListWidget#detected {{ background: transparent; border: none; outline: none; }}
QListWidget#detected::item {{
    background: transparent; border: 1px dashed {LINE_STRONG}; margin: 3px 0; padding: 7px 6px; color: {TEXT_SOFT};
}}
QListWidget#detected::item:hover {{ background: {RAISED}; color: {TEXT}; border-color: {ACCENT}; }}
QTableWidget::item, QListView::item {{ padding: 5px 4px; border-bottom: 1px solid #161616; }}
QTableWidget::item:hover, QListView::item:hover {{ background: #141414; }}
QTableWidget::item:selected, QListView::item:selected {{ background: {RAISED}; color: #ffffff; }}
QHeaderView {{ background: {PANEL}; }}
QHeaderView::section {{
    background: #121212; color: {TEXT_FAINT}; border: none; border-right: 1px solid {LINE};
    border-bottom: 1px solid {LINE}; padding: 6px 8px; font-family: "{MONO}"; font-size: 8pt;
}}
QTableCornerButton::section {{ background: transparent; border: none; }}

/* ---------- console ---------- */
QPlainTextEdit#console {{
    background: {CONSOLE}; color: #cfcfcf; border: 1px solid {LINE}; border-radius: 0; padding: 8px;
    font-family: "{MONO}"; selection-background-color: {ACCENT}; selection-color: {BG};
}}

/* ---------- scroll bars ---------- */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {LINE_STRONG}; border: none; border-radius: 0; min-height: 26px; min-width: 26px; }}
QScrollBar::handle:hover {{ background: {DECOR}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QSplitter::handle {{ background: {BG}; }}
QGroupBox {{ border: 1px solid {LINE}; margin-top: 14px; padding: 10px 8px 8px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {TEXT_FAINT}; }}
QMenu {{ background: {RAISED}; border: 1px solid {LINE_STRONG}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; }}
QMenu::item:selected {{ background: {ACCENT}; color: {BG}; }}
QMenu::item:disabled {{ color: {DISABLED}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 0; }}
QStatusBar {{ background: {BG}; color: {TEXT_SOFT}; border-top: 1px solid {LINE}; }}
QProgressBar {{ background: {RAISED}; border: 1px solid {LINE}; border-radius: 0; text-align: center; color: {TEXT}; }}
QProgressBar::chunk {{ background: {ACCENT}; }}
"""


def pill_style(status: str) -> str:
    """Server state label: coloured text and border on a dark tone of the same colour."""
    color, background = STATUS_COLORS.get(status, BUSY_COLORS)
    return (f"QLabel {{ background: {background}; color: {color}; border: 1px solid {color}; border-radius: 0; "
            f"padding: 4px 12px; font-family: '{MONO}'; font-weight: 700; }}")


def _load_fonts() -> None:
    for path in sorted((ASSETS / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(path))


def mono_font(point_size: float = 10, bold: bool = False) -> QFont:
    font = QFont(MONO)
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSizeF(point_size)
    font.setBold(bold)
    return font


def apply(app: QApplication) -> None:
    app.setStyle("Fusion")
    _load_fonts()
    text_font = QFont(SANS, 10)
    text_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(text_font)
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, BG), (QPalette.ColorRole.Base, PANEL),
        (QPalette.ColorRole.AlternateBase, "#111111"), (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.WindowText, TEXT), (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Button, RAISED), (QPalette.ColorRole.Highlight, ACCENT),
        (QPalette.ColorRole.HighlightedText, BG), (QPalette.ColorRole.Link, ACCENT),
        (QPalette.ColorRole.LinkVisited, ACCENT),
        (QPalette.ColorRole.ToolTipBase, RAISED), (QPalette.ColorRole.ToolTipText, TEXT),
        (QPalette.ColorRole.PlaceholderText, TEXT_FAINT), (QPalette.ColorRole.Light, LINE_STRONG),
        (QPalette.ColorRole.Midlight, LINE), (QPalette.ColorRole.Mid, LINE), (QPalette.ColorRole.Dark, BG),
        (QPalette.ColorRole.Shadow, "#000000"),
    ):
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(DISABLED))
    app.setPalette(palette)
    # The theme's images need an absolute path (also inside the exe/AppImage).
    app.setStyleSheet(STYLESHEET.replace("{ASSETS}", ASSETS.as_posix()))
    app._field_fixes = FieldFixes(app)  # kept so the garbage collector does not delete it
    app.installEventFilter(app._field_fixes)
    if sys.platform == "win32":
        _dark_title_bars(app)


def _dark_title_bars(app: QApplication) -> None:
    """Windows: dark title bar on every window, so it doesn't stand out white above the black app."""
    app._dark_titles = DarkTitleBars(app)
    app.installEventFilter(app._dark_titles)


class DarkTitleBars(QObject):
    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow():
            try:
                import ctypes

                value = ctypes.c_int(1)
                # DWMWA_USE_IMMERSIVE_DARK_MODE (20 on Windows 10 20H1 and later, 19 before)
                for attribute in (20, 19):
                    if ctypes.windll.dwmapi.DwmSetWindowAttribute(int(obj.winId()), attribute, ctypes.byref(value),
                                                                  ctypes.sizeof(value)) == 0:
                        break
            except (OSError, AttributeError):
                pass
        return False


class FieldFixes(QObject):
    """App-wide field fixes:
    - The mouse wheel does not change numbers or drop-downs unless they have focus: scrolling down a
      settings page used to change the memory or the port by accident. The page scrolls instead.
    - Text in numeric fields gets the same margin as the rest (Qt ignores the padding)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Buttons and tabs: monospaced capitals, like the labels on a device. (Set on each widget: with a
        # style sheet active, QApplication.setFont(font, class) is ignored.)
        self.label_font = mono_font(8.5)
        self.label_font.setCapitalization(QFont.Capitalization.AllUppercase)
        self.label_font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 104)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Type.Polish and isinstance(obj, (QPushButton, QTabBar, QToolButton)) \
                and not obj.property("ownhostFont"):
            obj.setProperty("ownhostFont", True)
            font = QFont(self.label_font)
            font.setBold(obj.font().bold())
            obj.setFont(font)
        if event.type() == QEvent.Type.Polish and isinstance(obj, (QAbstractSpinBox, QComboBox)):
            obj.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            if isinstance(obj, QAbstractSpinBox) and obj.lineEdit():
                obj.lineEdit().setTextMargins(8, 0, 0, 0)
        elif event.type() == QEvent.Type.Wheel and isinstance(obj, (QAbstractSpinBox, QComboBox)) \
                and not obj.hasFocus():
            area = obj.parent()
            while area and not isinstance(area, QAbstractScrollArea):
                area = area.parent()
            if area:
                QApplication.sendEvent(area.verticalScrollBar(), event)
            return True
        return False


class Backdrop(QWidget):
    """Window background: plain black."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("backdrop")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(BG))
        p.end()


def ascii_landscape() -> QLabel:
    """The ASCII landscape at the bottom of the computer and welcome pages (scripts/generate_ascii.py)."""
    label = QLabel()
    label.setObjectName("ascii")
    label.setTextFormat(Qt.TextFormat.PlainText)
    try:
        label.setText((ASSETS / "landscape.txt").read_text(encoding="utf-8").rstrip("\n"))
    except OSError:
        pass
    label.setFont(mono_font(7))
    label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
    label.setAccessibleName(" ")  # decoration: screen readers skip it
    label.setMinimumSize(1, 1)    # never forces the window wider or taller
    return label


def glass(content: QWidget, title: str | None = None, margins: int = 14) -> QFrame:
    """Wraps a widget in a panel with a thin border (and an optional small capitals title)."""
    frame = QFrame()
    frame.setObjectName("glass")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(margins, margins, margins, margins)
    layout.setSpacing(8)
    if title:
        label = QLabel(title.upper())
        label.setObjectName("panelTitle")
        layout.addWidget(label)
    layout.addWidget(content, 1)
    return frame
