"""Pestaña «Jugadores»: conectados, operadores, lista blanca y baneados, sin escribir comandos."""

from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QFrame,
)

from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async

ACTION_NAMES = {
    "op": "hacer operador a", "deop": "quitar operador a", "whitelist_add": "añadir a la lista blanca a",
    "whitelist_remove": "quitar de la lista blanca a", "ban": "banear a", "pardon": "perdonar a",
    "whitelist_on": "activar la lista blanca", "whitelist_off": "desactivar la lista blanca",
}


def played(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    return f"{h} h {rem // 60} min" if h else f"{rem // 60} min"


def last_seen(ts: float, online: bool) -> str:
    if online:
        return "Jugando ahora"
    when = datetime.fromtimestamp(ts)
    today = datetime.now().date()
    if when.date() == today:
        return f"Hoy, {when:%H:%M}"
    if when.date() == today - timedelta(days=1):
        return f"Ayer, {when:%H:%M}"
    return f"{when:%d/%m/%Y}"


def _section(title: str, widget: QWidget, buttons: list[QPushButton]) -> QWidget:
    box = QWidget()
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(f"<b>{title}</b>")
    layout.addWidget(label)
    layout.addWidget(widget, 1)
    row = QHBoxLayout()
    for b in buttons:
        row.addWidget(b)
    row.addStretch()
    layout.addLayout(row)
    return box


class PlayersTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: AgentClient | None = None
        self.server: dict | None = None
        self.data: dict = {}

        self.online = QListWidget()
        self.ops = QListWidget()
        self.whitelist = QListWidget()
        self.banned = QListWidget()
        for w in (self.online, self.ops, self.whitelist, self.banned):
            w.setObjectName("players")
            w.setMinimumHeight(50)

        def btn(text, slot, kind=None):
            b = QPushButton(text)
            if kind:
                b.setProperty("kind", kind)
            b.clicked.connect(slot)
            return b

        self.btn_op_online = btn("Hacer operador", lambda: self._on_selected(self.online, "op"))
        self.btn_kick = btn("Echar", lambda: self._on_selected(self.online, "kick"))
        self.btn_ban_online = btn("Banear", lambda: self._on_selected(self.online, "ban", confirm=True), "danger")
        self.btn_deop = btn("Quitar operador", lambda: self._on_selected(self.ops, "deop"))
        self.btn_wl_remove = btn("Quitar", lambda: self._on_selected(self.whitelist, "whitelist_remove"))
        self.btn_pardon = btn("Perdonar", lambda: self._on_selected(self.banned, "pardon"))
        self.whitelist_on = QCheckBox("Solo pueden entrar los de la lista blanca")
        self.whitelist_on.toggled.connect(self._toggle_whitelist)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Nombre del jugador")
        self.name.setToolTip("Los jugadores de Bedrock que entran por Geyser llevan un «.» delante del nombre")
        add_op = btn("Hacer operador", lambda: self._on_name("op"))
        add_wl = btn("Añadir a la lista blanca", lambda: self._on_name("whitelist_add"))
        add_ban = btn("Banear", lambda: self._on_name("ban", confirm=True), "danger")
        name_row = QHBoxLayout()
        name_row.addWidget(self.name, 1)
        for b in (add_op, add_wl, add_ban):
            name_row.addWidget(b)
        self.add_ban = add_ban
        self.name_row = name_row
        self.can_edit = True

        # Estadísticas: quién ha jugado más y cuándo entró por última vez
        self.stats = QTableWidget(0, 4)
        self.stats.setHorizontalHeaderLabels(["Jugador", "Tiempo jugado", "Veces que ha entrado", "Última vez"])
        self.stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats.verticalHeader().setVisible(False)
        self.stats.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.stats.setMinimumHeight(90)
        self.stats_empty = QLabel("Todavía no ha entrado nadie. Aquí verás quién juega más y cuándo entró por última vez.")
        self.stats_empty.setObjectName("muted")

        self.info = QLabel()
        self.info.setObjectName("muted")
        self.info.setWordWrap(True)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.addWidget(_section("Conectados ahora", self.online,
                                [self.btn_op_online, self.btn_kick, self.btn_ban_online]), 0, 0)
        grid.addWidget(_section("Operadores", self.ops, [self.btn_deop]), 0, 1)
        wl = _section("Lista blanca", self.whitelist, [self.btn_wl_remove])
        wl.layout().insertWidget(1, self.whitelist_on)
        grid.addWidget(wl, 1, 0)
        self.banned_section = _section("Baneados", self.banned, [self.btn_pardon])
        grid.addWidget(self.banned_section, 1, 1)

        # Con desplazamiento si no cabe (pantallas de portátil): las listas y las estadísticas ocupan mucho.
        content = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.setWidget(content)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        layout.addLayout(name_row)
        layout.addLayout(grid, 1)
        layout.addWidget(QLabel("<b>Estadísticas</b>"))
        layout.addWidget(self.stats, 1)
        layout.addWidget(self.stats_empty)
        layout.addWidget(self.info)

    def set_can_edit(self, can: bool) -> None:
        """Con el permiso «Encender y apagar» solo se ven las listas."""
        self.can_edit = can
        for i in range(self.name_row.count()):
            if w := self.name_row.itemAt(i).widget():
                w.setVisible(can)
        for b in (self.btn_op_online, self.btn_kick, self.btn_ban_online, self.btn_deop, self.btn_wl_remove,
                  self.btn_pardon):
            b.setVisible(can)
        self.whitelist_on.setEnabled(can)

    def set_server(self, client: AgentClient, server: dict) -> None:
        changed = not self.server or self.server["id"] != server["id"] or self.client is not client
        self.client, self.server = client, server
        if changed:
            for w in (self.online, self.ops, self.whitelist, self.banned):
                w.clear()

    def update_online(self, server: dict) -> None:
        """Con cada sondeo de la app: los conectados cambian a menudo."""
        if self.server and server["id"] == self.server["id"]:
            self.server = server
            names = server.get("players_online", [])
            if names != [self.online.item(i).text() for i in range(self.online.count())]:
                self.online.clear()
                self.online.addItems(names)

    def reload(self) -> None:
        if not self.server:
            return
        sid, client = self.server["id"], self.client
        run_async(lambda: client.players(sid), self._loaded, lambda msg: self.info.setText(msg))
        run_async(lambda: client.player_stats(sid), self._stats_loaded, lambda _: None)

    def _stats_loaded(self, rows: list[dict]) -> None:
        self.stats.setRowCount(0)
        for r in rows:
            row = self.stats.rowCount()
            self.stats.insertRow(row)
            for col, text in enumerate((r["name"], played(r["seconds"]), str(r["sessions"]),
                                        last_seen(r["last_seen"], r["online"]))):
                self.stats.setItem(row, col, QTableWidgetItem(text))
        self.stats.setVisible(bool(rows))
        self.stats_empty.setVisible(not rows)

    def _loaded(self, data: dict) -> None:
        self.data = data
        for widget, key in ((self.online, "online"), (self.ops, "ops"), (self.whitelist, "whitelist"),
                            (self.banned, "banned")):
            widget.clear()
            widget.addItems(data.get(key, []))
        self.whitelist_on.blockSignals(True)
        self.whitelist_on.setChecked(data.get("whitelist_enabled", False))
        self.whitelist_on.blockSignals(False)
        bans = "ban" in data.get("supports", [])
        self.banned_section.setVisible(bans)
        for b in (self.btn_ban_online, self.add_ban):
            b.setVisible(bans and self.can_edit)
        pending = data.get("pending") or []
        running = self.server["state"] == "running"
        text = ("Los cambios se aplican al momento." if running else
                "El servidor está apagado: los cambios se aplicarán en cuanto se encienda.")
        if not self.can_edit:
            text = "Tu acceso solo deja ver las listas."
        if data.get("whitelist_enabled") and not data.get("whitelist"):
            text = ("⚠ La lista blanca está activada pero vacía: no puede entrar nadie. Añade jugadores o "
                    "desactívala. " + text)
        if pending:
            text += f" Pendientes: {', '.join(f'{ACTION_NAMES.get(a, a)} {n}'.strip() for a, n in pending)}."
        self.info.setText(text)

    def _act(self, action: str, name: str = "") -> None:
        sid, client = self.server["id"], self.client

        def done(_):
            self.name.clear()
            # El servidor tarda un momento en guardar sus listas
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self.reload)

        run_async(lambda: client.player_action(sid, action, name), done,
                  lambda msg: QMessageBox.warning(self, "Jugadores", msg))

    def _on_selected(self, widget: QListWidget, action: str, confirm: bool = False) -> None:
        item = widget.currentItem()
        if not item:
            QMessageBox.information(self, "Jugadores", "Selecciona un jugador de la lista.")
            return
        if confirm and QMessageBox.question(self, "Jugadores", f"¿{ACTION_NAMES[action].capitalize()} {item.text()}?") \
                != QMessageBox.StandardButton.Yes:
            return
        self._act(action, item.text())

    def _on_name(self, action: str, confirm: bool = False) -> None:
        name = self.name.text().strip()
        if not name:
            return
        if confirm and QMessageBox.question(self, "Jugadores", f"¿Banear a {name}?") != QMessageBox.StandardButton.Yes:
            return
        self._act(action, name)

    def _toggle_whitelist(self, on: bool) -> None:
        self._act("whitelist_on" if on else "whitelist_off")
