"""The "Players" tab: online players, operators, whitelist and banned players, without typing commands."""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QFrame,
)

from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async
from ownhost.i18n import tr

ACTION_NAMES = {
    "op": "hacer operador a", "deop": "quitar operador a", "whitelist_add": "añadir a la lista blanca a",
    "whitelist_remove": "quitar de la lista blanca a", "ban": "banear a", "pardon": "perdonar a",
    "whitelist_on": "activar la lista blanca", "whitelist_off": "desactivar la lista blanca",
}


NAME_ROLE = Qt.ItemDataRole.UserRole  # the real name (the one commands use) of each list row


def display_name(name: str, prefix: str | None) -> str:
    """With crossplay through Floodgate: "Steve (Bedrock)" (without the prefix) or "Alex (Java)"."""
    if not prefix:
        return name
    if name.startswith(prefix):
        return f"{name[len(prefix):]} (Bedrock)"
    return f"{name} (Java)"


def fill_names(widget: QListWidget, names: list[str], prefix: str | None) -> None:
    widget.clear()
    for name in names:
        item = QListWidgetItem(display_name(name, prefix))
        item.setData(NAME_ROLE, name)
        widget.addItem(item)


def list_names(widget: QListWidget) -> list[str]:
    return [widget.item(i).data(NAME_ROLE) for i in range(widget.count())]


def played(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    return tr("{hours} h {minutes} min", hours=h, minutes=rem // 60) if h else tr("{minutes} min", minutes=rem // 60)


def last_seen(ts: float, online: bool) -> str:
    if online:
        return tr("Jugando ahora")
    when = datetime.fromtimestamp(ts)
    today = datetime.now().date()
    if when.date() == today:
        return tr("Hoy, {time}", time=f"{when:%H:%M}")
    if when.date() == today - timedelta(days=1):
        return tr("Ayer, {time}", time=f"{when:%H:%M}")
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

        self.btn_op_online = btn(tr("Hacer operador"), lambda: self._on_selected(self.online, "op"))
        self.btn_kick = btn(tr("Echar"), lambda: self._on_selected(self.online, "kick"))
        self.btn_ban_online = btn(tr("Banear"), lambda: self._on_selected(self.online, "ban", confirm=True), "danger")
        self.btn_deop = btn(tr("Quitar operador"), lambda: self._on_selected(self.ops, "deop"))
        self.btn_wl_remove = btn(tr("Quitar"), lambda: self._on_selected(self.whitelist, "whitelist_remove"))
        self.btn_pardon = btn(tr("Perdonar"), lambda: self._on_selected(self.banned, "pardon"))
        self.whitelist_on = QCheckBox(tr("Solo pueden entrar los de la lista blanca"))
        self.whitelist_on.toggled.connect(self._toggle_whitelist)

        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("Nombre del jugador"))
        self.name.setToolTip(tr("Los jugadores de Bedrock que entran por Geyser llevan un «.» delante del nombre"))
        add_op = btn(tr("Hacer operador"), lambda: self._on_name("op"))
        add_wl = btn(tr("Añadir a la lista blanca"), lambda: self._on_name("whitelist_add"))
        add_ban = btn(tr("Banear"), lambda: self._on_name("ban", confirm=True), "danger")
        name_row = QHBoxLayout()
        name_row.addWidget(self.name, 1)
        for b in (add_op, add_wl, add_ban):
            name_row.addWidget(b)
        self.add_ban = add_ban
        self.name_row = name_row
        self.can_edit = True

        # Stats: who has played the most and when they last joined
        self.stats = QTableWidget(0, 4)
        self.stats.setHorizontalHeaderLabels([tr("Jugador"), tr("Tiempo jugado"), tr("Veces que ha entrado"), tr("Última vez")])
        self.stats.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stats.verticalHeader().setVisible(False)
        self.stats.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.stats.setMinimumHeight(90)
        self.stats_empty = QLabel(tr("Todavía no ha entrado nadie. Aquí verás quién juega más y cuándo entró por última vez."))
        self.stats_empty.setObjectName("muted")

        self.info = QLabel()
        self.info.setObjectName("muted")
        self.info.setWordWrap(True)

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.addWidget(_section(tr("Conectados ahora"), self.online,
                                [self.btn_op_online, self.btn_kick, self.btn_ban_online]), 0, 0)
        grid.addWidget(_section(tr("Operadores"), self.ops, [self.btn_deop]), 0, 1)
        wl = _section(tr("Lista blanca"), self.whitelist, [self.btn_wl_remove])
        wl.layout().insertWidget(1, self.whitelist_on)
        grid.addWidget(wl, 1, 0)
        self.banned_section = _section(tr("Baneados"), self.banned, [self.btn_pardon])
        grid.addWidget(self.banned_section, 1, 1)

        # Scrollable if it doesn't fit (laptop screens): the lists and the stats take up a lot of space.
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
        layout.addWidget(QLabel(tr("<b>Estadísticas</b>")))
        layout.addWidget(self.stats, 1)
        layout.addWidget(self.stats_empty)
        layout.addWidget(self.info)

    def set_can_edit(self, can: bool) -> None:
        """With the "Start and stop" permission only the lists are shown."""
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
        """On every app poll: the online players change often."""
        if self.server and server["id"] == self.server["id"]:
            self.server = server
            names = server.get("players_online", [])
            prefix = server.get("bedrock_prefix")
            if names != list_names(self.online) or prefix != self.data.get("bedrock_prefix"):
                self.data["bedrock_prefix"] = prefix
                fill_names(self.online, names, prefix)

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
            name = display_name(r["name"], (self.server or {}).get("bedrock_prefix"))
            for col, text in enumerate((name, played(r["seconds"]), str(r["sessions"]),
                                        last_seen(r["last_seen"], r["online"]))):
                self.stats.setItem(row, col, QTableWidgetItem(text))
        self.stats.setVisible(bool(rows))
        self.stats_empty.setVisible(not rows)

    def _loaded(self, data: dict) -> None:
        self.data = data
        for widget, key in ((self.online, "online"), (self.ops, "ops"), (self.whitelist, "whitelist"),
                            (self.banned, "banned")):
            fill_names(widget, data.get(key, []), data.get("bedrock_prefix"))
        self.whitelist_on.blockSignals(True)
        self.whitelist_on.setChecked(data.get("whitelist_enabled", False))
        self.whitelist_on.blockSignals(False)
        bans = "ban" in data.get("supports", [])
        self.banned_section.setVisible(bans)
        for b in (self.btn_ban_online, self.add_ban):
            b.setVisible(bans and self.can_edit)
        pending = data.get("pending") or []
        running = self.server["state"] == "running"
        text = (tr("Los cambios se aplican al momento.") if running else
                tr("El servidor está apagado: los cambios se aplicarán en cuanto se encienda."))
        if not self.can_edit:
            text = tr("Tu acceso solo deja ver las listas.")
        if data.get("whitelist_enabled") and not data.get("whitelist"):
            text = tr("⚠ La lista blanca está activada pero vacía: no puede entrar nadie. Añade jugadores o "
                      "desactívala.") + " " + text
        if pending:
            actions = ", ".join(f"{tr(ACTION_NAMES[a]) if a in ACTION_NAMES else a} {n}".strip() for a, n in pending)
            text += " " + tr("Pendientes: {actions}.", actions=actions)
        self.info.setText(text)

    def _act(self, action: str, name: str = "") -> None:
        sid, client = self.server["id"], self.client

        def done(_):
            self.name.clear()
            # The server takes a moment to save its lists
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self.reload)

        run_async(lambda: client.player_action(sid, action, name), done,
                  lambda msg: QMessageBox.warning(self, tr("Jugadores"), msg))

    def _on_selected(self, widget: QListWidget, action: str, confirm: bool = False) -> None:
        item = widget.currentItem()
        if not item:
            QMessageBox.information(self, tr("Jugadores"), tr("Selecciona un jugador de la lista."))
            return
        if confirm and QMessageBox.question(
                self, tr("Jugadores"), tr("¿{action} {name}?", action=tr(ACTION_NAMES[action]).capitalize(),
                                          name=item.text())) \
                != QMessageBox.StandardButton.Yes:
            return
        self._act(action, item.data(NAME_ROLE) or item.text())

    def _on_name(self, action: str, confirm: bool = False) -> None:
        name = self.name.text().strip()
        if not name:
            return
        if confirm and QMessageBox.question(self, tr("Jugadores"), tr("¿Banear a {name}?", name=name)) != QMessageBox.StandardButton.Yes:
            return
        self._act(action, name)

    def _toggle_whitelist(self, on: bool) -> None:
        self._act("whitelist_on" if on else "whitelist_off")
