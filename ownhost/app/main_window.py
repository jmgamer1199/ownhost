import httpx
from PySide6.QtCore import QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFontMetrics, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter, QStackedWidget,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ownhost.app import ASSETS, theme
from ownhost.app.client import AgentClient, ApiError
from ownhost.app.dialogs import (
    AccountLoginDialog, CreateServerDialog, HostDialog, ImportModpackDialog, SettingsDialog,
)
from ownhost import BUILD, i18n, updates
from ownhost.i18n import tr
from ownhost.app import app_update
from ownhost.app.hosts import (
    Host, kill_local_agents, launch_local_agent, load_hosts, local_agent_config, save_hosts,
)
from ownhost.app.guests import OWNER, ROLE_NAMES, GuestsDialog, access_level
from ownhost.app.phone import PhoneDialog, panel_url
from ownhost.app.replicas import ReceivedBackupsDialog
from ownhost.app.server_panel import ServerPanel
from ownhost.app import firewall
from ownhost.app.autodiscover import scan
from ownhost.app.settings import load_settings, save_settings
from ownhost.app.status import STATUS
from ownhost.app.tasks import run_async
from ownhost.net import lan_ip, tailscale_ip
from ownhost.paths import default_data_dir

POLL_MS = 2000
SCAN_MS = 30000
ROLE = Qt.ItemDataRole.UserRole


STATE_ROLE = Qt.ItemDataRole.UserRole + 1  # (colour, state label) of a server row


class IndentedServers(QStyledItemDelegate):
    """Servers, slightly indented under their computer: a dot in the colour of their state, their icon,
    the name, and the state in small capitals on the right.
    (The tree's own indentation would also paint the selection in the gap on the left.)"""

    INDENT = 14
    DOT = 7

    def paint(self, painter, option, index) -> None:
        if not index.parent().isValid():
            super().paint(painter, option, index)
            return
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        icon = QIcon(opt.icon)  # copy: opt.icon is the same object that is cleared below
        opt.icon = QIcon()
        opt.features &= ~QStyleOptionViewItem.ViewItemFeature.HasDecoration
        color, state = index.data(STATE_ROLE) or (theme.OFFLINE, "")
        state_font = theme.mono_font(7.5)
        state_width = QFontMetrics(state_font).horizontalAdvance(state.upper()) + 10 if state else 0
        # Same room for the icon even if the server has none: keeps the names aligned.
        offset = self.INDENT + self.DOT + 8 + opt.decorationSize.width() + 6
        space = max(1, opt.fontMetrics.horizontalAdvance(" "))
        name_room = opt.rect.width() - offset - state_width - 12
        opt.text = " " * round(offset / space) + opt.fontMetrics.elidedText(
            opt.text, Qt.TextElideMode.ElideRight, max(20, name_room))
        widget = opt.widget
        (widget.style() if widget else QApplication.style()).drawControl(
            QStyle.ControlElement.CE_ItemViewItem, opt, painter, widget)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        center_y = opt.rect.center().y() + 1
        painter.drawEllipse(QPointF(opt.rect.left() + 8 + self.INDENT + self.DOT / 2, center_y), self.DOT / 2,
                            self.DOT / 2)
        if state:
            painter.setFont(state_font)
            painter.setPen(QColor(color))
            painter.drawText(opt.rect.adjusted(0, 0, -10, 0),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, state.upper())
        painter.restore()
        if not icon.isNull():
            size = opt.decorationSize
            rect = QRect(opt.rect.left() + 8 + self.INDENT + self.DOT + 8,
                         opt.rect.center().y() - size.height() // 2 + 1, size.width(), size.height())
            icon.paint(painter, rect)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ownhost")
        self.resize(1150, 720)
        self._placed = False

        self.hosts: list[Host] = load_hosts()
        self.clients: dict[str, AgentClient] = {}
        self.state: dict[str, dict] = {}  # host_id -> {online, info, servers, error}
        self.inflight: set[str] = set()
        # Agent notices already seen, per computer: (server, time, number). When connecting to a computer
        # the ones it already had are marked as seen, so old crashes are not shown.
        self.seen_events: dict[str, set[tuple]] = {}
        self.server_icons: dict[tuple[str, str], tuple[int | None, QIcon]] = {}  # (computer, server) -> (date, icon)
        self.local_launch_tried = False
        self.upgrading_agent = False
        self.local_ip = lan_ip()
        self.login_dialogs: dict[tuple[str, str], AccountLoginDialog] = {}
        self.dismissed_logins: set[str] = set()
        self.language_synced: set[str] = set()

        cfg = local_agent_config()
        if not self.hosts and cfg:
            self.hosts.append(Host(name=tr("Este PC"), address="127.0.0.1", token=cfg["token"], port=cfg["port"]))
            save_hosts(self.hosts)

        self._build_ui()
        for h in self.hosts:
            self.clients[h.id] = AgentClient(h)
        self._rebuild_tree()

        self.timer = QTimer(self, interval=POLL_MS)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        self.poll()

        # Look for other computers running Ownhost (local network and Tailscale)
        self.detected: list[dict] = []
        self.scanning = False
        self.scan_timer = QTimer(self, interval=SCAN_MS)
        self.scan_timer.timeout.connect(self.scan_network)
        self.scan_timer.start()
        QTimer.singleShot(1500, self.scan_network)

        # New version of the app (and of the agents on other computers)
        self.latest_release: dict | None = None
        updates.cleanup_old()
        if BUILD != "dev" and load_settings().get("check_updates", True):
            QTimer.singleShot(6000, lambda: app_update.check(self, on_release=self._release_known))

    # ---------- interface ----------

    def _build_ui(self) -> None:
        # Top bar: logo, name and version on the left; the main actions on the right.
        top = QHBoxLayout()
        top.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(
            26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        app_title = QLabel("OWNHOST")
        app_title.setObjectName("appTitle")
        version = QLabel(f"v{BUILD}" if BUILD != "dev" else "dev")
        version.setObjectName("panelTitle")
        top.addWidget(logo)
        top.addSpacing(4)
        top.addWidget(app_title)
        top.addWidget(version, 0, Qt.AlignmentFlag.AlignBottom)
        top.addStretch()
        for text, slot, kind in ((tr("＋  Nuevo servidor"), self.new_server, "primary"),
                                 (tr("Conectar a un equipo"), self.add_host, None),
                                 (tr("Ajustes"), self._settings, None)):
            button = QPushButton(text)
            button.setObjectName("top")
            if kind:
                button.setProperty("kind", kind)
            button.clicked.connect(slot)
            top.addWidget(button)

        self.tree = QTreeWidget()
        self.tree.setObjectName("hosts")
        self.tree.setHeaderHidden(True)
        # No indentation area: Qt would paint a loose piece of the selection there. The hierarchy is
        # shown by the computers' icon and bold text and the indented server text.
        self.tree.setIndentation(0)
        self.tree.setItemDelegate(IndentedServers(self.tree))
        self.tree.setRootIsDecorated(False)
        self.tree.setItemsExpandable(False)
        self.tree.setMinimumWidth(260)
        self.tree.itemSelectionChanged.connect(self._selection_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)

        self.stack = QStackedWidget()
        self.welcome = self._build_welcome()
        self.host_page = self._build_host_page()
        self.server_panel = ServerPanel()
        self.server_panel.move_targets = self._move_targets
        self.server_panel.on_moved = self._server_moved
        for w in (self.welcome, self.host_page, self.server_panel):
            self.stack.addWidget(w)

        # Black background with two panels: computers on the left, details on the right.
        splitter = QSplitter()
        self.detected_title = QLabel(tr("Detectados en tu red").upper())
        self.detected_title.setObjectName("panelTitle")
        self.detected_list = QListWidget()
        self.detected_list.setObjectName("detected")
        self.detected_list.setMaximumHeight(160)
        self.detected_list.itemClicked.connect(self._connect_detected)
        self.detected_title.hide()
        self.detected_list.hide()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.tree, 1)
        left_layout.addWidget(self.detected_title)
        left_layout.addWidget(self.detected_list)
        splitter.addWidget(theme.glass(left, tr("Equipos y servidores")))
        splitter.addWidget(theme.glass(self.stack, margins=18))
        splitter.setHandleWidth(12)  # gap between the two panels
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([290, 860])
        background = theme.Backdrop()
        layout = QVBoxLayout(background)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(10)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(background)

    def _build_welcome(self) -> QWidget:
        w = QWidget()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ASSETS / "icon.png")).scaled(
            96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        title = QLabel(tr("<span style='font-size:26pt'>Bienvenido</span><br>"
                          "<span style='font-size:11pt'>Tus servidores de Minecraft y Hytale, en toda tu red.</span>"))
        title.setObjectName("title")
        head = QHBoxLayout()
        head.addWidget(logo)
        head.addSpacing(12)
        head.addWidget(title, 1)
        text = QLabel(tr(
            "Cada equipo que hospeda servidores ejecuta un pequeño <b>agente</b>. "
            "Esta app se conecta a los agentes de tu red para crear, encender, apagar "
            "y actualizar servidores.<br><br>"
            "Empieza usando este PC como servidor, o conéctate por IP a otro equipo "
            "(por ejemplo tu homelab) donde ya esté funcionando."))
        text.setWordWrap(True)
        use_local = QPushButton(tr("Usar este PC como servidor"))
        use_local.setProperty("kind", "primary")
        use_local.clicked.connect(self.setup_local_agent)
        add = QPushButton(tr("Conectar a un equipo por IP..."))
        add.clicked.connect(self.add_host)
        row = QHBoxLayout()
        row.addWidget(use_local)
        row.addWidget(add)
        row.addStretch()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)
        layout.addLayout(head)
        layout.addWidget(text)
        layout.addLayout(row)
        layout.addStretch()
        layout.addWidget(theme.ascii_landscape())
        return w

    def _build_host_page(self) -> QWidget:
        w = QWidget()
        self.host_title = QLabel()
        self.host_info = QLabel()
        self.host_info.setWordWrap(True)
        self.host_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.host_info.setOpenExternalLinks(True)
        self.host_title.setObjectName("title")
        self.btn_host_new = QPushButton(tr("Nuevo servidor en este equipo"))
        self.btn_host_new.setProperty("kind", "primary")
        self.btn_host_new.clicked.connect(self.new_server)
        self.btn_host_start = QPushButton(tr("Iniciar agente local"))
        self.btn_host_start.clicked.connect(self._start_local_agent)
        self.btn_copy_token = QPushButton(tr("Copiar token"))
        self.btn_copy_token.clicked.connect(self._copy_token)
        # Linux with an active firewall (ufw/firewalld): open the ports with the system password.
        self.firewall_kind = firewall.detect()
        self.btn_firewall = QPushButton(tr("Abrir puertos del cortafuegos"))
        self.btn_firewall.setToolTip(tr("El cortafuegos ({kind}) bloquea a los demás equipos y "
                                        "a los jugadores. Pide tu contraseña.", kind=self.firewall_kind))
        self.btn_firewall.clicked.connect(lambda: self._open_firewall(ask=False))
        self.btn_agent_update = QPushButton(tr("Actualizar agente"))
        self.btn_agent_update.setToolTip(tr("Instala en ese equipo la última versión de Ownhost. Los servidores "
                                            "encendidos se apagan con «stop» y se vuelven a encender."))
        self.btn_agent_update.clicked.connect(self._update_agent)
        self.btn_received = QPushButton(tr("Copias de otros equipos..."))
        self.btn_received.setToolTip(tr("Copias de seguridad que otros equipos tuyos guardan en este"))
        self.btn_received.clicked.connect(self._received_backups)
        self.btn_phone = QPushButton(tr("Abrir en el móvil..."))
        self.btn_phone.setToolTip(tr("Código QR para abrir el panel web en el móvil (en casa o por Tailscale)"))
        self.btn_phone.clicked.connect(self._open_on_phone)
        self.btn_guests = QPushButton(tr("Accesos para amigos..."))
        self.btn_guests.setToolTip(tr("Da a tus amigos un código para encender o gestionar tus servidores"))
        self.btn_guests.clicked.connect(self._guests)
        edit = QPushButton(tr("Editar equipo"))
        edit.clicked.connect(lambda: self.edit_host(self._selected()[0]))
        remove = QPushButton(tr("Quitar de la lista"))
        remove.setProperty("kind", "danger")
        remove.clicked.connect(lambda: self.remove_host(self._selected()[0]))
        # Hidden until we know which computer it is: otherwise the window would widen on opening and never
        # shrink back (on a 1366 px laptop it would end up wider than the screen).
        for b in (self.btn_guests, self.btn_host_start, self.btn_copy_token, self.btn_firewall,
                  self.btn_agent_update, self.btn_received, self.btn_phone):
            b.hide()
        row = QHBoxLayout()
        for b in (self.btn_host_new, self.btn_phone, self.btn_guests, self.btn_received):
            row.addWidget(b)
        row.addStretch()
        manage = QHBoxLayout()
        for b in (self.btn_host_start, self.btn_copy_token, self.btn_firewall, self.btn_agent_update):
            manage.addWidget(b)
        manage.addStretch()
        manage.addWidget(edit)
        manage.addWidget(remove)
        layout = QVBoxLayout(w)
        layout.addWidget(self.host_title)
        layout.addWidget(self.host_info)
        layout.addLayout(row)
        layout.addLayout(manage)
        layout.addStretch()
        layout.addWidget(theme.ascii_landscape())
        return w

    # ---------- tree ----------

    def _host(self, host_id: str) -> Host | None:
        return next((h for h in self.hosts if h.id == host_id), None)

    def _selected(self) -> tuple[str | None, str | None]:
        items = self.tree.selectedItems()
        if not items:
            return None, None
        return items[0].data(0, ROLE)

    def _rebuild_tree(self) -> None:
        selected = self._selected()
        self.tree.blockSignals(True)
        self.tree.clear()
        for h in self.hosts:
            item = QTreeWidgetItem([h.name])
            item.setData(0, ROLE, (h.id, None))
            item.setIcon(0, self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            self.tree.addTopLevelItem(item)
            item.setExpanded(True)
        self.tree.blockSignals(False)
        for h in self.hosts:
            self._refresh_host_item(h.id)
        self._select(selected)

    def _select(self, key) -> None:
        if key and key[0]:
            for i in range(self.tree.topLevelItemCount()):
                top = self.tree.topLevelItem(i)
                if top.data(0, ROLE) == key:
                    self.tree.setCurrentItem(top)
                    return
                for j in range(top.childCount()):
                    if top.child(j).data(0, ROLE) == key:
                        self.tree.setCurrentItem(top.child(j))
                        return
        self._selection_changed()

    def _top_item(self, host_id: str) -> QTreeWidgetItem | None:
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, ROLE)[0] == host_id:
                return item
        return None

    def _refresh_host_item(self, host_id: str) -> None:
        host, item = self._host(host_id), self._top_item(host_id)
        if not host or not item:
            return
        st = self.state.get(host_id, {})
        if st.get("online"):
            item.setText(0, host.name)
            item.setForeground(0, QBrush())
            item.setToolTip(0, f"{host.address}:{host.port}")
        else:
            item.setText(0, tr("{name} (sin conexión)", name=host.name) if st else tr("{name} (conectando...)", name=host.name))
            item.setForeground(0, QBrush(QColor(theme.OFFLINE)))
            item.setToolTip(0, st.get("error", ""))

        servers = {s["id"]: s for s in st.get("servers", [])}
        existing = {}
        for j in reversed(range(item.childCount())):
            child = item.child(j)
            sid = child.data(0, ROLE)[1]
            if sid not in servers:
                item.removeChild(child)
            else:
                existing[sid] = child
        for sid, s in servers.items():
            child = existing.get(sid)
            if not child:
                child = QTreeWidgetItem()
                child.setData(0, ROLE, (host_id, sid))
                item.addChild(child)
            label, _ = STATUS.get(s["status"], (s["status"], ""))
            child.setText(0, s["name"])
            child.setData(0, STATE_ROLE, (theme.STATUS_DOT.get(s["status"], theme.OFFLINE), tr(label)))
            child.setToolTip(0, f"{s['game_name']} {s['version']} · {tr(label)}")
            self._update_server_icon(host_id, s, child)

    def _update_server_icon(self, host_id: str, s: dict, child: QTreeWidgetItem) -> None:
        key, version = (host_id, s["id"]), s.get("icon_version")
        cached = self.server_icons.get(key)
        if cached and cached[0] == version:
            child.setIcon(0, cached[1])
            return
        self.server_icons[key] = (version, QIcon())
        child.setIcon(0, QIcon())
        if not version:
            return
        client = self.clients[host_id]

        def loaded(data):
            if not data or self.server_icons.get(key, (None,))[0] != version:
                return
            pix = QPixmap()
            pix.loadFromData(data)
            self.server_icons[key] = (version, QIcon(pix))
            self._refresh_host_item(host_id)

        run_async(lambda: client.icon(s["id"]), loaded, lambda _: None)

    def _selection_changed(self) -> None:
        host_id, sid = self._selected()
        if not host_id:
            self.server_panel.clear()
            self.stack.setCurrentWidget(self.welcome if not self.hosts else self.host_page)
            if self.hosts:
                self.tree.setCurrentItem(self.tree.topLevelItem(0))
            return
        if sid:
            server = next((s for s in self.state.get(host_id, {}).get("servers", []) if s["id"] == sid), None)
            if server:
                self.server_panel.host_name = self._host(host_id).name
                self.server_panel.show_server(self.clients[host_id], server, self._addresses(host_id),
                                              self._host(host_id).is_local, self._level(host_id))
                self.stack.setCurrentWidget(self.server_panel)
                return
        self.server_panel.clear()
        self._show_host_page(host_id)
        self.stack.setCurrentWidget(self.host_page)

    def _web_links(self, host_id: str) -> str:
        """Links to the agent's web panel at each address that works from other devices
        (home network and Tailscale)."""
        host = self._host(host_id)
        if not host:
            return ""
        links = []
        for ip, description in self._addresses(host_id):
            url = panel_url(ip, host.port)
            links.append(f"<a href='{url}'>{url}</a> ({description})")
        return " · ".join(links)

    def _sync_agent_language(self, host_id: str, info: dict) -> None:
        """Your agents write their console and notices in your language (once per session and agent)."""
        if host_id in self.language_synced or self._level(host_id) < OWNER or "language" not in info:
            return
        self.language_synced.add(host_id)
        if info["language"] != i18n.language():
            client = self.clients[host_id]
            run_async(lambda: client._req("PUT", "/agent/language", json={"language": i18n.language()}),
                      lambda _: None, lambda _: None)

    def _level(self, host_id: str) -> int:
        return access_level(self.state.get(host_id, {}).get("info"))

    def _owned_online(self, exclude: str | None = None) -> list[tuple[Host, AgentClient]]:
        """Connected computers where servers can be created (yours, not a friend's)."""
        return [(h, self.clients[h.id]) for h in self.hosts if h.id != exclude
                and self.state.get(h.id, {}).get("online") and self._level(h.id) >= OWNER]

    def _settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.check_now.clicked.connect(lambda: app_update.check(self, manual=True, on_release=self._release_known))
        if dialog.exec() and dialog.language_changed:
            self._restart_for_language()

    def _restart_for_language(self) -> None:
        """The language is applied when the app starts: it reopens itself (servers keep running)."""
        if QMessageBox.question(self, tr("Idioma"), tr("Para cambiar el idioma, Ownhost se cerrará y se volverá a "
                                "abrir. Tus servidores siguen encendidos. ¿Reiniciar ahora?")) \
                != QMessageBox.StandardButton.Yes:
            return
        import subprocess
        import sys

        binary = updates.running_binary()
        if binary:
            updates.relaunch(binary, sys.argv[1:])
        else:
            subprocess.Popen([sys.executable, "-m", "ownhost.app"])
        QApplication.quit()

    def _release_known(self, release: dict | None) -> None:
        self.latest_release = release
        if (host_id := self._selected()[0]) and not self._selected()[1]:
            self._show_host_page(host_id)

    def _update_agent(self) -> None:
        host_id = self._selected()[0]
        host = self._host(host_id)
        if not host or QMessageBox.question(
                self, tr("Actualizar agente"),
                tr("¿Actualizar Ownhost en «{name}»? Los servidores encendidos se apagan guardando el mundo y se "
                   "vuelven a encender al terminar (un par de minutos).", name=host.name)) \
                != QMessageBox.StandardButton.Yes:
            return
        client = self.clients[host_id]
        run_async(lambda: client._req("POST", "/agent/update"),
                  lambda r: self.statusBar().showMessage(f"{host.name}: {r['detail']}...", 30000),
                  lambda msg: QMessageBox.warning(self, tr("Actualizar agente"), msg))
        self.btn_agent_update.hide()

    def _received_backups(self) -> None:
        host_id = self._selected()[0]
        host = self._host(host_id)
        if host:
            ReceivedBackupsDialog(self, self.clients[host_id], host.name,
                                  lambda server: self._server_moved(host_id, server)).exec()

    def _guests(self) -> None:
        host_id = self._selected()[0]
        host = self._host(host_id)
        if not host:
            return
        GuestsDialog(self, self.clients[host_id], host.name, self.state.get(host_id, {}).get("servers", []),
                     self._addresses(host_id), host.port).exec()

    def _addresses(self, host_id: str) -> list[tuple[str, str]]:
        """Addresses a computer can be reached at: [(ip, description)]."""
        host = self._host(host_id)
        info = self.state.get(host_id, {}).get("info") or {}
        if host.is_local:
            lan, ts = self.local_ip, tailscale_ip()
        else:
            lan, ts = info.get("lan_ip") or host.address, info.get("tailscale_ip")
        addresses = [(lan, tr("red local"))]
        if ts and ts != lan:
            addresses.append((ts, "Tailscale"))
        return addresses

    def _show_host_page(self, host_id: str) -> None:
        host = self._host(host_id)
        st = self.state.get(host_id, {})
        self.host_title.setText(host.name)
        info = st.get("info")
        if st.get("online") and info:
            used = info["memory_total_mb"] - info["memory_available_mb"]
            running = sum(1 for s in st["servers"] if s["state"] == "running")
            self.host_info.setText(
                tr("<b>{hostname}</b> · {os} · agente v{version}<br>", hostname=info["hostname"], os=info["os"],
                   version=info["version"])
                + tr("Dirección: {address}", address=f"{host.address}:{host.port}")
                + (f" · Tailscale: {info['tailscale_ip']}" if info.get("tailscale_ip") else "") + "<br>"
                + tr("CPU: {threads} hilos, {percent}% en uso<br>", threads=info["cpu_count"],
                     percent=info["cpu_percent"])
                + tr("RAM: {used} / {total} GB en uso<br>", used=f"{used / 1024:.1f}",
                     total=f"{info['memory_total_mb'] / 1024:.1f}")
                + tr("Servidores: {count} ({running} encendidos)<br>", count=len(st["servers"]), running=running)
                + (tr("Panel web (también desde el móvil, botón «Abrir en el móvil»): {links}", links=links)
                   if (links := self._web_links(host_id)) else "")
                + (tr("<br><br>Entras con el acceso de <b>{name}</b>: <b>{role}</b>.", name=access["name"],
                      role=tr(ROLE_NAMES.get(access["role"], access["role"])))
                   if (access := info.get("access")) and access.get("level", OWNER) < OWNER else ""))
            if host.is_local and (cfg := local_agent_config()):
                if ts := tailscale_ip():
                    extra = tr("<br><br>Para gestionar este PC desde otro equipo usa la IP <b>{ip}</b> (o <b>{ts}</b> "
                               "por Tailscale, desde fuera de casa), puerto <b>{port}</b> y el token (botón "
                               "«Copiar token»).", ip=self.local_ip, ts=ts, port=cfg["port"])
                else:
                    extra = tr("<br><br>Para gestionar este PC desde otro equipo usa la IP <b>{ip}</b>, puerto "
                               "<b>{port}</b> y el token (botón «Copiar token»).", ip=self.local_ip, port=cfg["port"])
                self.host_info.setText(self.host_info.text() + extra)
        else:
            self.host_info.setText(tr("Sin conexión con {address}", address=f"{host.address}:{host.port}") + "<br>"
                                   f"<span style='color:{theme.DANGER_TEXT}'>{st.get('error', '')}</span>")
        owner = self._level(host_id) >= OWNER
        self.btn_host_new.setEnabled(bool(st.get("online")))
        self.btn_host_new.setVisible(owner)
        self.btn_guests.setVisible(owner and bool(st.get("online")))
        self.btn_phone.setVisible(bool(st.get("online")) and bool(host.token))
        self.btn_received.setVisible(owner and bool(st.get("online")))
        # This PC's agent is updated by the app itself; other computers' agents, with this button.
        agent_build = (info or {}).get("build") or "dev"
        self.btn_agent_update.setVisible(
            owner and bool(st.get("online")) and not host.is_local and bool(self.latest_release)
            and updates.is_newer(self.latest_release["build"], agent_build))
        self.btn_host_start.setVisible(host.is_local and not st.get("online"))
        self.btn_copy_token.setVisible(host.is_local and bool(local_agent_config()))
        self.btn_firewall.setVisible(host.is_local and bool(self.firewall_kind))
        if host.is_local and self.firewall_kind and st.get("online") and not load_settings().get("firewall_asked"):
            self._open_firewall(ask=True)

    def _context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item:
            return
        host_id, sid = item.data(0, ROLE)
        if sid:
            return
        menu = QMenu(self)
        if self._level(host_id) >= OWNER:
            menu.addAction(tr("Nuevo servidor"), self.new_server)
        menu.addAction(tr("Editar equipo"), lambda: self.edit_host(host_id))
        menu.addAction(tr("Quitar de la lista"), lambda: self.remove_host(host_id))
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    # ---------- agent polling ----------

    def poll(self) -> None:
        for h in self.hosts:
            if h.id in self.inflight:
                continue
            self.inflight.add(h.id)
            client = self.clients[h.id]

            def fetch(client=client):
                return client.info(), client.servers()

            run_async(fetch,
                      lambda result, hid=h.id: self._poll_done(hid, result),
                      lambda msg, hid=h.id: self._poll_failed(hid, msg))

    def _poll_done(self, host_id: str, result) -> None:
        self.inflight.discard(host_id)
        if not self._host(host_id):
            return
        info, servers = result
        self.state[host_id] = {"online": True, "info": info, "servers": servers}
        self._sync_agent_language(host_id, info)
        self._show_events(host_id, servers)
        self._update_login_dialogs(host_id)
        self._after_poll(host_id)
        host = self._host(host_id)
        # Forward only: an older app never replaces a newer agent (with two versions open at once
        # they would keep replacing each other). Builds are dates.
        agent_build = info.get("build") or "dev"
        if host.is_local and BUILD != "dev" and (agent_build == "dev" or agent_build < BUILD):
            self._upgrade_local_agent(host_id, servers)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._placed:
            return
        self._placed = True
        # Fit on the screen (not under the taskbar) and centered.
        screen = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        frame = self.frameGeometry().size() - self.size()
        w = min(self.width(), screen.width() - frame.width())
        h = min(self.height(), screen.height() - frame.height())
        self.resize(w, h)
        self.move(screen.center().x() - (w + frame.width()) // 2, screen.center().y() - (h + frame.height()) // 2)

    def _show_events(self, host_id: str, servers: list[dict]) -> None:
        events = [(s["id"], e) for s in servers for e in s.get("events", [])]
        keys = {(sid, e["time"], e["id"]) for sid, e in events}
        if host_id not in self.seen_events:
            self.seen_events[host_id] = keys
            return
        seen = self.seen_events[host_id]
        new = [e for sid, e in events if (sid, e["time"], e["id"]) not in seen]
        seen |= keys
        if not new:
            return
        host = self._host(host_id)
        texts = [e["text"] for e in new]
        where = tr(" (en {name})", name=host.name) if host and not host.is_local else ""
        self.statusBar().showMessage(" · ".join(texts) + where, 30000)
        QApplication.alert(self)
        if any(e["kind"] == "crash" for e in new):
            # It stayed down: worth a window. If it only restarts, the status bar is enough.
            QMessageBox.warning(self, tr("Servidor caído"), "\n".join(texts) + where +
                                tr("\n\nMira la consola del servidor para ver el motivo."))

    # ---------- replace the local agent when a new version of the app is opened ----------

    def _upgrade_local_agent(self, host_id: str, servers: list[dict]) -> None:
        if self.upgrading_agent or any(s.get("task") for s in servers):
            return  # already running, or an install/backup is half-done: retried on the next poll
        self.upgrading_agent = True
        client = self.clients[host_id]
        running = [s["id"] for s in servers if s["state"] in ("starting", "running")]
        self.statusBar().showMessage(tr("Actualizando el agente de este PC a la versión nueva..."))
        run_async(lambda: self._replace_agent(client, running),
                  lambda restarted: self._agent_upgraded(restarted),
                  lambda msg: self._agent_upgrade_failed(msg))

    @staticmethod
    def _replace_agent(client: AgentClient, running: list[str]) -> list[str]:
        """Stop the servers with "stop", swap the agent and start again the ones that were running."""
        import time

        for sid in running:
            client.action(sid, "stop")
        deadline = time.time() + 120
        while running and time.time() < deadline:
            if all(client.server(sid)["state"] in ("stopped", "crashed") for sid in running):
                break
            time.sleep(1)
        try:
            client._req("POST", "/shutdown")  # new agents: they shut down by themselves
        except (ApiError, httpx.HTTPError):
            # Old agents lack this endpoint, and new ones can close so fast that they cut the
            # response: either way, carry on.
            pass
        time.sleep(2)
        try:
            kill_local_agents(client.host.port)
        except Exception:  # noqa: BLE001 - no permission to list processes: it already closed by itself
            pass
        launch_local_agent()
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                client.info()
                break
            except ApiError:
                time.sleep(1)
        else:
            raise ApiError(tr("El agente nuevo no ha arrancado; abre la app de nuevo"))
        restarted = []
        for sid in running:  # one by one: if one fails, the others still start
            try:
                client.action(sid, "start")
                restarted.append(sid)
            except ApiError:
                pass
        return restarted

    def _agent_upgraded(self, restarted: list[str]) -> None:
        self.upgrading_agent = False
        if not restarted:
            text = tr("Agente de este PC actualizado a la versión nueva.")
        elif len(restarted) == 1:
            text = tr("Agente de este PC actualizado a la versión nueva y 1 servidor vuelto a encender.")
        else:
            text = tr("Agente de este PC actualizado a la versión nueva y {count} servidores vueltos a encender.",
                      count=len(restarted))
        self.statusBar().showMessage(text, 8000)
        self.poll()

    def _agent_upgrade_failed(self, msg: str) -> None:
        self.upgrading_agent = False
        self.statusBar().showMessage(tr("No se pudo actualizar el agente de este PC: {msg}", msg=msg), 15000)

    def _poll_failed(self, host_id: str, msg: str) -> None:
        self.inflight.discard(host_id)
        host = self._host(host_id)
        if not host:
            return
        self.state[host_id] = {"online": False, "error": msg, "servers": []}
        if host.is_local and not self.local_launch_tried and local_agent_config():
            self.local_launch_tried = True
            launch_local_agent()
        self._after_poll(host_id)

    def _after_poll(self, host_id: str) -> None:
        self._refresh_host_item(host_id)
        sel_host, sid = self._selected()
        if sel_host != host_id:
            return
        if sid:
            server = next((s for s in self.state[host_id]["servers"] if s["id"] == sid), None)
            if server and self.stack.currentWidget() is self.server_panel:
                self.server_panel.update_server(server)
            elif server:
                self._selection_changed()
            else:
                self._select((host_id, None))
        else:
            self._show_host_page(host_id)

    # ---------- sign-in with the game account (Hytale) ----------

    def _update_login_dialogs(self, host_id: str) -> None:
        pending = set()
        for s in self.state[host_id]["servers"]:
            auth = s.get("auth")
            if not auth:
                continue
            key = (host_id, s["id"])
            ident = f"{auth['url']}|{auth.get('code')}"
            pending.add(key)
            if ident in self.dismissed_logins:
                continue
            dialog = self.login_dialogs.get(key)
            if not dialog:
                dialog = AccountLoginDialog(self, s["name"], s["game_name"])
                dialog.finished.connect(lambda _, k=key, d=dialog: self._login_closed(k, d))
                self.login_dialogs[key] = dialog
            if getattr(dialog, "ident", None) != ident:
                dialog.ident = ident
                dialog.set_auth(auth)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
        for key in [k for k in self.login_dialogs if k[0] == host_id and k not in pending]:
            dialog = self.login_dialogs.pop(key)
            dialog.auto_closed = True
            dialog.close()
            self.statusBar().showMessage(tr("Sesión iniciada correctamente."), 6000)

    def _login_closed(self, key, dialog: AccountLoginDialog) -> None:
        if not getattr(dialog, "auto_closed", False):
            # The user closed it: don't reopen it for this same code.
            self.dismissed_logins.add(dialog.ident)
        if self.login_dialogs.get(key) is dialog:
            del self.login_dialogs[key]

    # ---------- actions ----------

    def _set_hosts(self, hosts: list[Host]) -> None:
        for c in self.clients.values():
            c.close()
        self.hosts = hosts
        self.clients = {h.id: AgentClient(h) for h in hosts}
        self.state = {k: v for k, v in self.state.items() if self._host(k)}
        save_hosts(hosts)
        self._rebuild_tree()
        self.poll()

    def add_host(self) -> None:
        dialog = HostDialog(self)
        if dialog.exec():
            host = dialog.result_host()
            self._set_hosts(self.hosts + [host])
            self._select((host.id, None))

    def edit_host(self, host_id: str | None) -> None:
        host = self._host(host_id) if host_id else None
        if not host:
            return
        dialog = HostDialog(self, host)
        if dialog.exec():
            new = dialog.result_host()
            self._set_hosts([new if h.id == host_id else h for h in self.hosts])

    def remove_host(self, host_id: str | None) -> None:
        host = self._host(host_id) if host_id else None
        if not host:
            return
        if QMessageBox.question(self, tr("Quitar equipo"),
                                tr("¿Quitar «{name}» de la lista? Sus servidores no se borran.", name=host.name)) \
                == QMessageBox.StandardButton.Yes:
            # Keep the automatic search from adding it back (it stays under "Found on your network").
            hostname = (self.state.get(host_id, {}).get("info") or {}).get("hostname")
            if hostname:
                settings = load_settings()
                settings["ignored_agents"] = sorted(set(settings.get("ignored_agents", [])) | {hostname})
                save_settings(settings)
            self._set_hosts([h for h in self.hosts if h.id != host_id])
            self.scan_network()

    # ---------- computers found on the local network and on Tailscale ----------

    def scan_network(self) -> None:
        if self.scanning:
            return
        self.scanning = True
        run_async(scan, self._scan_done, lambda _: setattr(self, "scanning", False))

    def _is_known(self, entry: dict) -> bool:
        for h in self.hosts:
            hostname = (self.state.get(h.id, {}).get("info") or {}).get("hostname")
            if h.address in (entry["lan"], entry["tailscale"]) or (hostname and hostname == entry["hostname"]):
                return True
        return False

    def _scan_done(self, results: list[dict]) -> None:
        self.scanning = False
        ignored = set(load_settings().get("ignored_agents", []))
        added = []
        for entry in results:
            if self._is_known(entry):
                continue
            if entry["trusted"] and entry["hostname"] not in ignored:
                # Same owner on Tailscale: added automatically, and it also works away from home.
                added.append(Host(name=entry["name"], address=entry["tailscale"], token="", port=entry["port"]))
        if added:
            self._set_hosts(self.hosts + added)
            names = ", ".join(h.name for h in added)
            self.statusBar().showMessage(tr("Añadido automáticamente por Tailscale: {names}", names=names), 8000)
        self.detected = [e for e in results if not self._is_known(e)]
        self.detected_list.clear()
        for entry in self.detected:
            via = "Tailscale" if entry["tailscale"] and not entry["lan"] else tr("red local")
            item = QListWidgetItem(f"＋  {entry['name']}  ({via})")
            item.setToolTip(tr("Pulsa para conectarlo (te pedirá el token de ese equipo)"))
            self.detected_list.addItem(item)
        visible = bool(self.detected)
        self.detected_title.setVisible(visible)
        self.detected_list.setVisible(visible)

    def _connect_detected(self, item) -> None:
        entry = self.detected[self.detected_list.row(item)]
        dialog = HostDialog(self)
        dialog.name.setText(entry["name"])
        dialog.address.setText(entry["tailscale"] or entry["lan"])
        dialog.port.setValue(entry["port"])
        dialog.token.setFocus()
        if dialog.exec():
            host = dialog.result_host()
            self._set_hosts(self.hosts + [host])
            self._select((host.id, None))
            self.scan_network()

    def new_server(self) -> None:
        online = self._owned_online()
        if not online:
            QMessageBox.information(self, tr("Sin equipos"), tr("No hay ningún equipo tuyo conectado. "
                                    "Usa este PC o añade otro equipo primero.\n\n(En los equipos de un amigo "
                                    "solo puedes usar los servidores que te haya dejado.)"))
            return
        dialog = CreateServerDialog(self, online, self._selected()[0])
        ok = dialog.exec()
        if not ok and dialog.want_modpack:
            dialog = ImportModpackDialog(self, online, self._selected()[0])
            ok = dialog.exec()
        if ok:
            host_id = dialog.created_host_id
            state = self.state.setdefault(host_id, {"online": True, "servers": []})
            state["servers"] = state.get("servers", []) + [dialog.created]
            self._refresh_host_item(host_id)
            self._select((host_id, dialog.created["id"]))

    def _move_targets(self) -> list[tuple[Host, AgentClient]]:
        return self._owned_online(exclude=self._selected()[0])

    def _server_moved(self, host_id: str, server: dict) -> None:
        state = self.state.setdefault(host_id, {"online": True, "servers": []})
        if all(s["id"] != server["id"] for s in state.get("servers", [])):
            state["servers"] = state.get("servers", []) + [server]
        self._refresh_host_item(host_id)
        self._select((host_id, server["id"]))

    def setup_local_agent(self) -> None:
        if not local_agent_config():
            launch_local_agent()
        self.local_launch_tried = True
        self.statusBar().showMessage(tr("Arrancando el agente de este PC (la primera vez puede tardar un poco)..."))
        # On a laptop the AppImage takes a while to mount the first time: up to 60 s of leeway.
        self._wait_for_local_config(120)

    def _wait_for_local_config(self, tries: int) -> None:
        cfg = local_agent_config()
        if cfg:
            self.statusBar().clearMessage()
            if not any(h.is_local for h in self.hosts):
                host = Host(name=tr("Este PC"), address="127.0.0.1", token=cfg["token"], port=cfg["port"])
                self._set_hosts([host] + self.hosts)
                self._select((host.id, None))
            return
        if tries <= 0:
            self.statusBar().clearMessage()
            QMessageBox.warning(self, tr("Agente local"), tr("El agente de este PC no ha arrancado.\n\n"
                                "Mira qué ha pasado en:\n{path}", path=default_data_dir() / "agent.log"))
            return
        QTimer.singleShot(500, lambda: self._wait_for_local_config(tries - 1))

    def _open_firewall(self, ask: bool) -> None:
        kind = self.firewall_kind
        if not kind:
            return
        if ask:
            # Asked only once per computer; afterwards the button stays on the "This PC" page.
            settings = load_settings()
            settings["firewall_asked"] = True
            save_settings(settings)
            answer = QMessageBox.question(
                self, tr("Cortafuegos"),
                tr("Este equipo tiene el cortafuegos «{kind}» activado: bloquea a los demás equipos de la red "
                   "y a los jugadores.\n\n¿Abrir ahora los puertos de Ownhost y de los juegos? Te pedirá tu "
                   "contraseña.", kind=kind))
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.statusBar().showMessage(tr("Abriendo puertos del cortafuegos..."))

        def done(result):
            ok, msg = result
            self.statusBar().showMessage(msg, 8000)
            if not ok:
                QMessageBox.warning(self, tr("Cortafuegos"), msg)

        run_async(lambda: firewall.open_ports(kind), done, lambda msg: QMessageBox.warning(self, tr("Cortafuegos"), msg))

    def _open_on_phone(self) -> None:
        host = self._host(self._selected()[0])
        if not host:
            return
        addresses = [(ip, desc[:1].upper() + desc[1:]) for ip, desc in self._addresses(host.id)]
        PhoneDialog(self, host.name, addresses, host.port, host.token, self._level(host.id) >= OWNER).exec()

    def _copy_token(self) -> None:
        cfg = local_agent_config()
        if cfg:
            QApplication.clipboard().setText(cfg["token"])
            self.statusBar().showMessage(tr("Token copiado al portapapeles"), 3000)

    def _start_local_agent(self) -> None:
        launch_local_agent()
        self.btn_host_start.setEnabled(False)
        QTimer.singleShot(5000, lambda: self.btn_host_start.setEnabled(True))

    def closeEvent(self, event) -> None:
        self.server_panel.clear()
        super().closeEvent(event)
