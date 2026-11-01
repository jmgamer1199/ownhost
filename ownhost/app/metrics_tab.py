"""“Performance” tab: CPU, RAM and players over the last hours, and disk usage."""

import math
import time
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout,
    QWidget,
)

from ownhost.app import theme
from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async
from ownhost.i18n import language, tr

SERIES = QColor(theme.ACCENT)    # cyan: contrast >= 3:1 on SURFACE
SURFACE = QColor(theme.PANEL)
GRID = QColor(255, 255, 255, 26)
TEXT = QColor(theme.TEXT)
TEXT_SOFT = QColor(theme.TEXT_SOFT)
WARNING = QColor(theme.WARN)
CRITICAL = QColor(theme.BAD)
RANGES = [(1, "1 h"), (6, "6 h"), (24, "24 h")]


def _decimal(text: str) -> str:
    """Decimal comma in Spanish, decimal point in English."""
    return text.replace(".", ",") if language() == "es" else text


def nice_ceiling(value: float) -> float:
    """“Round” axis ceiling: 1, 2, 2.5, 5 or 10 times a power of 10."""
    if value <= 0:
        return 1
    exp = 10 ** math.floor(math.log10(value))
    for m in (1, 2, 2.5, 5, 10):
        if value <= m * exp:
            return m * exp
    return 10 * exp


def compact(value: float) -> str:
    """1234 -> "1.2K"; 12.5 -> "12.5"; 0.25 -> "0.25" (decimal comma in Spanish)."""
    if value >= 1000:
        text = f"{value / 1000:.1f}".rstrip("0").rstrip(".") + "K"
    elif value >= 100:
        text = f"{value:.0f}"
    else:
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    return _decimal(text)


def size_text(n: int) -> str:
    for unit, div in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= div:
            return _decimal(f"{n / div:.1f} {unit}".replace(".0 ", " "))
    return f"{n} B"


class LineChart(QWidget):
    """A single series and a single axis. Gaps (server stopped) break the line."""

    PAD_L, PAD_R, PAD_T, PAD_B = 46, 58, 10, 24

    def __init__(self, unit: str, floor_max: float, parent=None):
        super().__init__(parent)
        self.unit = unit
        self.floor_max = floor_max
        self.points: list[tuple[float, float]] = []
        self.start = self.end = 0.0
        self.interval = 60
        self.reference: tuple[float, str] | None = None
        self.hover: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, points, start, end, interval, reference=None) -> None:
        self.points, self.start, self.end, self.interval = points, start, end, interval
        self.reference = reference
        self.hover = None
        self.update()

    # geometry
    def _plot(self) -> QRectF:
        return QRectF(self.PAD_L, self.PAD_T, self.width() - self.PAD_L - self.PAD_R,
                      self.height() - self.PAD_T - self.PAD_B)

    def _ymax(self) -> float:
        top = max([v * 1.05 for _, v in self.points] + [self.floor_max] +
                  ([self.reference[0] * 1.05] if self.reference else []))
        # 4 divisions of a round step (1, 2, 2.5, 5...): ticks like 0/1/2/3/4, never 1.88
        return nice_ceiling(top / 4) * 4

    def _xy(self, t: float, v: float, plot: QRectF, ymax: float) -> QPointF:
        span = max(self.end - self.start, 1)
        return QPointF(plot.left() + (t - self.start) / span * plot.width(),
                       plot.bottom() - v / ymax * plot.height())

    def _time_step(self) -> int:
        span = self.end - self.start
        for step in (600, 900, 1800, 3600, 7200, 14400):
            if span / step <= 6:
                return step
        return 21600

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(SURFACE)
        p.drawRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5))
        plot = self._plot()
        if plot.width() < 40 or plot.height() < 30:
            return
        ymax = self._ymax()
        small = QFont(self.font())
        small.setPointSizeF(max(7.5, self.font().pointSizeF() - 1))
        p.setFont(small)

        # grid and Y axis (4 divisions)
        for i in range(5):
            v = ymax * i / 4
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_SOFT)
            p.drawText(QRectF(0, y - 8, self.PAD_L - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       compact(v))
        # X axis: round hours
        step = self._time_step()
        t = math.ceil(self.start / step) * step
        while t <= self.end:
            x = self._xy(t, 0, plot, ymax).x()
            p.drawText(QRectF(x - 30, plot.bottom() + 4, 60, 16), Qt.AlignmentFlag.AlignHCenter,
                       datetime.fromtimestamp(t).strftime("%H:%M"))
            t += step

        # labelled reference line (e.g. allocated memory)
        if self.reference:
            value, label = self.reference
            y = self._xy(0, value, plot, ymax).y()
            p.setPen(QPen(TEXT_SOFT, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(TEXT_SOFT)
            p.drawText(QRectF(plot.left() + 4, y - 16, plot.width(), 14), Qt.AlignmentFlag.AlignLeft, label)

        if not self.points:
            p.setPen(TEXT_SOFT)
            p.drawText(plot, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                       tr("Sin datos en este periodo. Se guarda una muestra por minuto mientras el servidor está encendido."))
            return

        # continuous segments (a gap of more than 2.5 samples breaks the line)
        segments, current, last_t = [], [], None
        for t, v in self.points:
            if last_t is not None and t - last_t > self.interval * 2.5:
                segments.append(current)
                current = []
            current.append(self._xy(t, v, plot, ymax))
            last_t = t
        segments.append(current)

        wash = QColor(SERIES)
        wash.setAlphaF(0.10)
        for seg in segments:
            if len(seg) == 1:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(SERIES)
                p.drawEllipse(seg[0], 2.5, 2.5)
                continue
            line = QPainterPath(seg[0])
            for pt in seg[1:]:
                line.lineTo(pt)
            area = QPainterPath(line)
            area.lineTo(seg[-1].x(), plot.bottom())
            area.lineTo(seg[0].x(), plot.bottom())
            area.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(wash)
            p.drawPath(area)
            pen = QPen(SERIES, 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(line)

        # last value: dot with a background-coloured ring and a label at the end
        t, v = self.points[-1]
        end = self._xy(t, v, plot, ymax)
        self._dot(p, end)
        p.setPen(TEXT)
        bold = QFont(small)
        bold.setBold(True)
        p.setFont(bold)
        p.drawText(QRectF(end.x() + 8, end.y() - 9, self.PAD_R, 18), Qt.AlignmentFlag.AlignVCenter,
                   f"{compact(v)}{self.unit}")
        p.setFont(small)

        # hover: vertical crosshair + dot + tooltip
        if self.hover is not None:
            t, v = self.points[self.hover]
            pt = self._xy(t, v, plot, ymax)
            p.setPen(QPen(TEXT_SOFT, 1))
            p.drawLine(QPointF(pt.x(), plot.top()), QPointF(pt.x(), plot.bottom()))
            self._dot(p, pt)
            text = f"{datetime.fromtimestamp(t):%H:%M}   {compact(v)}{self.unit}"
            w = p.fontMetrics().horizontalAdvance(text) + 16
            box = QRectF(pt.x() + 10, plot.top() + 2, w, 22)
            if box.right() > self.width() - 4:
                box.moveRight(pt.x() - 10)
            p.setPen(QPen(GRID, 1))
            p.setBrush(QColor(theme.RAISED))
            p.drawRect(box)
            p.setPen(TEXT)
            p.drawText(box, Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _dot(p: QPainter, c: QPointF) -> None:
        p.setPen(QPen(SURFACE, 2))
        p.setBrush(SERIES)
        p.drawEllipse(c, 4.5, 4.5)

    def mouseMoveEvent(self, event) -> None:
        if not self.points:
            return
        plot = self._plot()
        x = event.position().x()
        if not plot.left() - 10 <= x <= plot.right() + 10:
            self._set_hover(None)
            return
        span = max(self.end - self.start, 1)
        t = self.start + (x - plot.left()) / plot.width() * span
        i = min(range(len(self.points)), key=lambda k: abs(self.points[k][0] - t))
        # far from any sample (server stopped): no tooltip
        self._set_hover(i if abs(self.points[i][0] - t) <= max(self.interval * 2, span / 60) else None)

    def leaveEvent(self, event) -> None:
        self._set_hover(None)

    def _set_hover(self, i) -> None:
        if i != self.hover:
            self.hover = i
            self.update()


class Meter(QWidget):
    """Disk usage bar: blue normally, amber from 80 %, red from 90 %."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fraction = 0.0
        self.setFixedHeight(10)

    def set_fraction(self, f: float) -> None:
        self.fraction = max(0.0, min(1.0, f))
        self.update()

    def color(self) -> QColor:
        return CRITICAL if self.fraction >= 0.9 else WARNING if self.fraction >= 0.8 else SERIES

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        track = QColor(self.color())
        track.setAlphaF(0.18)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRect(r)
        p.setBrush(self.color())
        p.drawRect(QRectF(r.left(), r.top(), r.width() * self.fraction, r.height()))


def _tile(label: str) -> tuple[QWidget, QLabel, QLabel]:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    title = QLabel(label)
    title.setObjectName("muted")
    value = QLabel("—")
    f = value.font()
    f.setPointSizeF(f.pointSizeF() + 5)
    f.setBold(True)
    value.setFont(f)
    note = QLabel()
    note.setObjectName("muted")
    lay.addWidget(title)
    lay.addWidget(value)
    lay.addWidget(note)
    return w, value, note


class MetricsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: AgentClient | None = None
        self.server: dict | None = None
        self.hours = 1
        self._loading = False

        # period (a row of buttons above the charts)
        top = QHBoxLayout()
        self.range_group = QButtonGroup(self)
        for hours, text in RANGES:
            b = QPushButton(text)
            b.setCheckable(True)
            b.setChecked(hours == self.hours)
            b.clicked.connect(lambda _=False, h=hours: self._set_range(h))
            self.range_group.addButton(b)
            top.addWidget(b)
        top.addStretch()
        self.updated = QLabel()
        self.updated.setObjectName("muted")
        top.addWidget(self.updated)

        # disk
        disk = QHBoxLayout()
        w1, self.server_size, self.server_note = _tile(tr("Servidor (mundo, mods y ajustes)"))
        w2, self.backups_size, self.backups_note = _tile(tr("Copias de seguridad"))
        w3, self.free_size, self.free_note = _tile(tr("Espacio libre en el disco"))
        self.meter = Meter()
        w3.layout().insertWidget(2, self.meter)
        for w in (w1, w2, w3):
            disk.addWidget(w, 1)

        # charts: one per measure, each with its own scale
        self.cpu = LineChart("%", floor_max=5)
        self.ram = LineChart(" GB", floor_max=0.5)
        self.players = LineChart("", floor_max=4)
        self.cpu_title = QLabel(tr("<b>CPU</b> <span>· % del procesador del equipo</span>"))
        self.ram_title = QLabel(tr("<b>Memoria RAM</b>"))
        self.players_title = QLabel(tr("<b>Jugadores conectados</b>"))
        charts = QGridLayout()
        charts.setVerticalSpacing(4)
        for row, (title, chart) in enumerate(((self.cpu_title, self.cpu), (self.ram_title, self.ram),
                                              (self.players_title, self.players))):
            charts.addWidget(title, row * 2, 0)
            charts.addWidget(chart, row * 2 + 1, 0)
            charts.setRowStretch(row * 2 + 1, 1)

        # Disk and charts scroll: in short windows they don't force the window to grow.
        content = QWidget()
        inner = QVBoxLayout(content)
        inner.setContentsMargins(0, 0, 6, 0)
        inner.addLayout(disk)
        inner.addLayout(charts, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(scroll, 1)

        self.timer = QTimer(self, interval=60_000)
        self.timer.timeout.connect(self.reload)

    def set_server(self, client: AgentClient, server: dict) -> None:
        if not self.server or self.server["id"] != server["id"] or self.client is not client:
            for chart in (self.cpu, self.ram, self.players):
                chart.set_data([], 0, 0, 60)
            for label in (self.server_size, self.backups_size, self.free_size):
                label.setText("—")
        self.client, self.server = client, server
        self.players_title.setVisible(server["game"] in ("minecraft", "bedrock"))
        self.players.setVisible(server["game"] in ("minecraft", "bedrock"))

    def activate(self) -> None:
        self.reload()
        self.timer.start()

    def deactivate(self) -> None:
        self.timer.stop()

    def _set_range(self, hours: int) -> None:
        self.hours = hours
        self.reload()

    def reload(self) -> None:
        if not self.server or self._loading or not self.isVisible():
            return
        self._loading = True
        sid, client, hours = self.server["id"], self.client, self.hours

        def done(data):
            self._loading = False
            if self.server and self.server["id"] == sid:
                self._show(data, hours)

        def failed(msg):
            self._loading = False
            self.updated.setText(msg)

        run_async(lambda: client.metrics(sid, hours), done, failed)

    def _show(self, data: dict, hours: int) -> None:
        end = time.time()
        start = end - hours * 3600
        pts, step = data["points"], data.get("interval", 60)
        self.cpu.set_data([(p[0], p[1]) for p in pts], start, end, step)
        limit = data.get("memory_limit_mb")
        # RAM in GB: "1.3 GB" reads better than "1.3K MB"
        self.ram.set_data([(p[0], p[2] / 1024) for p in pts], start, end, step,
                          (limit / 1024, tr("Asignada: {size} GB", size=compact(limit / 1024))) if limit else None)
        self.players.set_data([(p[0], p[3]) for p in pts], start, end, step)
        maxp = data.get("max_players")
        self.players_title.setText(tr("<b>Jugadores conectados</b> · máximo {max}", max=maxp) if maxp
                                   else tr("<b>Jugadores conectados</b>"))
        self.ram_title.setText(tr("<b>Memoria RAM</b> · la que usa el proceso (Java usa algo más que la asignada)")
                               if self.server["game"] == "minecraft" else tr("<b>Memoria RAM</b>"))

        d = data["disk"]
        self.server_size.setText(size_text(d["server_bytes"]))
        self.backups_size.setText(size_text(d["backups_bytes"]) if d["backups_bytes"] else tr("Ninguna"))
        self.free_size.setText(size_text(d["disk_free"]))
        used = 1 - d["disk_free"] / d["disk_total"] if d["disk_total"] else 0
        self.meter.set_fraction(used)
        warn = " · " + tr("⚠ Queda poco espacio") if used >= 0.9 else ""
        self.free_note.setText(tr("de {total} ({percent} usado)", total=size_text(d["disk_total"]),
                                  percent=f"{used:.0%}") + warn)
        self.updated.setText(tr("Actualizado a las {time}", time=f"{datetime.now():%H:%M}"))
