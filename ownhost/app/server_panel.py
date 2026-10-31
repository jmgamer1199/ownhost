from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt, QTime, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QImage, QPixmap, QTextCursor
from PySide6.QtWebSockets import QWebSocket
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QInputDialog, QMenu, QMessageBox, QPlainTextEdit, QProgressDialog, QPushButton, QScrollArea, QSpinBox, QStyle, QTableWidget,
    QTableWidgetItem, QTimeEdit,
    QTabWidget, QVBoxLayout, QWidget,
)

from ownhost.app.client import AgentClient
from ownhost.app.dialogs import ImportWorldDialog, MoveDialog, ask_version
from ownhost.app.guests import MANAGE, MODERATE, OWNER, PLAY
from ownhost.app.mods_tab import ModsTab
from ownhost.app.metrics_tab import MetricsTab
from ownhost.app.players_tab import PlayersTab
from ownhost.app import theme
from ownhost.app.status import STATUS, format_uptime

# Extras de Geyser: (clave en el agente, texto, explicación)
EXTRAS = [
    ("xbox", "Que aparezca en la pestaña Amigos de las consolas (MCXboxBroadcast)",
     "Switch, Xbox y PlayStation no pueden añadir servidores por IP. Con esto, el servidor aparece como "
     "partida de un amigo a través de Xbox Live, también desde fuera de casa."),
    ("cosmetics", "Mostrar capas y orejas de los jugadores de Java (ThirdPartyCosmetics)",
     "Los jugadores de Bedrock verán las capas y orejas de servicios de terceros que llevan los de Java."),
    ("emote_offhand", "Cambiar el objeto de la mano secundaria con un gesto (EmoteOffhand)",
     "Bedrock no tiene la tecla de cambiar de mano: con esta extensión se hace con un gesto."),
]
from ownhost.app.tasks import run_async, run_with_progress
from ownhost.app.transfer import import_world, move_server


class ServerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: AgentClient | None = None
        self.server: dict | None = None
        self.addresses: list[tuple[str, str]] = []
        self.is_local = False
        self.level = OWNER  # permisos con los que estamos conectados a ese equipo
        # Los pone la ventana principal: equipos a los que se puede mover y aviso al terminar.
        self.move_targets = lambda: []
        self.on_moved = lambda host_id, server: None

        self.title = QLabel()
        self.title.setObjectName("title")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("subtitle")
        self.status = QLabel()
        self.stats = QLabel()
        self.address = QLabel()
        self.address.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)

        self.btn_start = QPushButton("▶  Encender")
        self.btn_start.setProperty("kind", "primary")
        self.btn_stop = QPushButton("■  Apagar")
        self.btn_restart = QPushButton("⟳  Reiniciar")
        self.btn_kill = QPushButton("✕  Forzar cierre")
        self.btn_kill.setProperty("kind", "danger")
        self.btn_login = QPushButton("Iniciar sesión...")
        self.btn_login.setToolTip("Vuelve a pedir el inicio de sesión con tu cuenta del juego")
        self.btn_login.clicked.connect(lambda: self._action("login"))
        self.btn_update = QPushButton("Actualizar...")
        self.btn_backup = QPushButton("Copia de seguridad")
        # Clonar y mover van juntos en un menú para que la fila de herramientas no sea tan larga.
        self.btn_move = QPushButton("Clonar o mover")
        self.btn_move.setProperty("menu", True)
        move_menu = QMenu(self.btn_move)
        self.act_clone = move_menu.addAction("Clonar en este equipo...", self._clone)
        self.act_clone.setToolTip("Crea otro servidor igual (mundo, mods y ajustes) con otro puerto")
        self.act_move = move_menu.addAction("Mover a otro equipo...", self._move)
        move_menu.setToolTipsVisible(True)
        self.btn_move.setMenu(move_menu)
        self.btn_folder = QPushButton("Abrir carpeta")
        self.btn_folder.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.btn_folder.clicked.connect(self._open_folder)
        self.btn_world = QPushButton("Mundo")
        self.btn_world.setProperty("menu", True)
        world_menu = QMenu(self.btn_world)
        self.act_import_world = world_menu.addAction("Importar un mundo...", self._import_world)
        self.act_download_world = world_menu.addAction("Descargar una copia...",
                                                       lambda: self.tabs.setCurrentWidget(self.backups_tab))
        self.btn_world.setMenu(world_menu)
        self.btn_delete = QPushButton("Eliminar")
        self.btn_delete.setProperty("kind", "danger")
        self.btn_start.clicked.connect(lambda: self._action("start"))
        self.btn_stop.clicked.connect(lambda: self._action("stop"))
        self.btn_restart.clicked.connect(lambda: self._action("restart"))
        self.btn_kill.clicked.connect(self._kill)
        self.btn_update.clicked.connect(self._update)
        self.btn_backup.clicked.connect(lambda: self._action("backup"))
        self.btn_delete.clicked.connect(self._delete)

        # Dos filas: encendido arriba, herramientas abajo (así no se amontonan).
        power = QHBoxLayout()
        for b in (self.btn_start, self.btn_stop, self.btn_restart, self.btn_kill, self.btn_login):
            power.addWidget(b)
        power.addStretch()
        tools = QHBoxLayout()
        for b in (self.btn_folder, self.btn_world, self.btn_update, self.btn_backup, self.btn_move):
            tools.addWidget(b)
        tools.addStretch()
        tools.addWidget(self.btn_delete)
        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        buttons.addLayout(power)
        buttons.addLayout(tools)

        self.tabs = QTabWidget()
        self.console_tab = self._build_console()
        self.tabs.addTab(self.console_tab, "Consola")
        self.players_tab = PlayersTab()
        self.tabs.addTab(self.players_tab, "Jugadores")
        self.metrics_tab = MetricsTab()
        self.tabs.addTab(self.metrics_tab, "Rendimiento")
        self.mods_tab = ModsTab()
        self.tabs.addTab(self.mods_tab, "Mods")
        # Los ajustes crecen con la multiplataforma y sus extras: con desplazamiento si no caben.
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setFrameShape(QFrame.Shape.NoFrame)
        settings_scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        settings_scroll.setWidget(self._build_settings())
        self.settings_tab = settings_scroll
        self.tabs.addTab(settings_scroll, "Ajustes")
        self.properties_tab = self._build_properties()
        self.tabs.addTab(self.properties_tab, "Propiedades")
        self.backups_tab = self._build_backups()
        self.tabs.addTab(self.backups_tab, "Copias de seguridad")
        self.tabs.currentChanged.connect(self._tab_changed)

        header = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self.title)
        left.addWidget(self.subtitle)
        left.addWidget(self.address)
        right = QVBoxLayout()
        right.addWidget(self.status)
        right.addWidget(self.stats)
        header.addLayout(left, 1)
        header.addLayout(right)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.error)
        layout.addLayout(buttons)
        layout.addWidget(self.tabs, 1)

        self.ws = QWebSocket()
        self.ws.textMessageReceived.connect(self._console_text)
        self.ws.disconnected.connect(self._ws_disconnected)
        self.reconnect_timer = QTimer(self, singleShot=True, interval=3000)
        self.reconnect_timer.timeout.connect(self._open_console)

    # ---------- construcción de pestañas ----------

    def _build_console(self) -> QWidget:
        w = QWidget()
        self.console = QPlainTextEdit(readOnly=True)
        self.console.setObjectName("console")
        self.console.setMaximumBlockCount(3000)
        self.console.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.console.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.command = QLineEdit()
        self.command.setPlaceholderText("Escribe un comando (p. ej. say hola, op TuNombre) y pulsa Enter")
        self.command.returnPressed.connect(self._send_command)
        layout = QVBoxLayout(w)
        layout.addWidget(self.console, 1)
        layout.addWidget(self.command)
        return w

    def _build_settings(self) -> QWidget:
        w = QWidget()
        self.set_name = QLineEdit()
        self.set_memory = QSpinBox(minimum=512, maximum=65536, singleStep=512, suffix=" MB")
        self.set_port = QSpinBox(minimum=1, maximum=65535)
        self.set_autostart = QCheckBox("Encender automáticamente cuando arranque el agente")
        self.set_autoupdate = QCheckBox("Actualizar automáticamente al encender")
        self.set_autoupdate.setToolTip(
            "Antes de encender, instala la última build compatible y hace una copia de seguridad.\n"
            "En Minecraft Java no cambia la versión de Minecraft (para no romper mundos ni mods);\n"
            "en Bedrock instala siempre la última, porque los jugadores la necesitan.")
        # Descripción y límite de jugadores (server.properties). Con Geyser, Bedrock ve los mismos.
        self.set_motd = QLineEdit()
        self.set_motd.setPlaceholderText("Lo que se ve debajo del nombre en la lista de servidores")
        self.set_max_players = QSpinBox(minimum=1, maximum=1000)
        self.props_loaded_for: str | None = None
        save = QPushButton("Guardar")
        save.clicked.connect(self._save_settings)
        form = QFormLayout(w)
        self.settings_form = form
        self.icon_preview = QLabel()
        self.icon_preview.setFixedSize(64, 64)
        self.icon_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_preview.setStyleSheet("border: 1px solid rgba(6,50,74,40); border-radius: 6px;")
        icon_change = QPushButton("Cambiar icono...")
        icon_change.clicked.connect(self._choose_icon)
        self.icon_remove = QPushButton("Quitar")
        self.icon_remove.clicked.connect(self._remove_icon)
        icon_note = QLabel("Se ve en la lista de servidores de Minecraft. Cualquier imagen vale: se recorta "
                           "y se ajusta a 64x64. Se aplica al reiniciar.")
        icon_note.setObjectName("muted")
        icon_note.setWordWrap(True)
        icon_buttons = QVBoxLayout()
        icon_buttons.addWidget(icon_change)
        icon_buttons.addWidget(self.icon_remove)
        icon_row = QHBoxLayout()
        icon_row.addWidget(self.icon_preview)
        icon_row.addLayout(icon_buttons)
        icon_row.addWidget(icon_note, 1)
        self.icon_row = QWidget()
        self.icon_row.setLayout(icon_row)
        self.icon_loaded: tuple | None = None
        form.addRow("Icono", self.icon_row)
        form.addRow("Nombre", self.set_name)
        form.addRow("Descripción", self.set_motd)
        form.addRow("Jugadores máximos", self.set_max_players)
        form.addRow("Memoria máxima", self.set_memory)
        form.addRow("Puerto", self.set_port)
        form.addRow(self.set_autostart)
        form.addRow(self.set_autoupdate)
        self.set_autorestart = QCheckBox("Volver a encenderlo si se cae")
        self.set_autorestart.setToolTip("Si el servidor se cierra por un error, se vuelve a encender a los 10 "
                                        "segundos.\nSi se cae más de 3 veces en 10 minutos, se queda apagado.")
        form.addRow(self.set_autorestart)

        # Tareas programadas
        self.set_backup_hours = QSpinBox(minimum=0, maximum=168, suffix=" h")
        self.set_backup_hours.setSpecialValueText("Nunca")
        self.set_backup_hours.setToolTip("Solo se hace la copia si el servidor se ha usado desde la anterior.")
        self.set_keep_backups = QSpinBox(minimum=1, maximum=100)
        self.set_restart_on = QCheckBox("Reiniciar cada día a las")
        self.set_restart_at = QTimeEdit()
        self.set_restart_at.setDisplayFormat("HH:mm")
        self.set_restart_on.toggled.connect(self.set_restart_at.setEnabled)
        restart_row = QHBoxLayout()
        restart_row.addWidget(self.set_restart_on)
        restart_row.addWidget(self.set_restart_at)
        restart_row.addStretch()
        self.set_idle_stop = QSpinBox(minimum=0, maximum=1440, singleStep=5, suffix=" min")
        self.set_idle_stop.setSpecialValueText("Nunca")
        self.set_idle_stop.setToolTip("Si no hay ningún jugador conectado durante ese tiempo, el servidor se apaga "
                                      "solo (ahorra luz y memoria). Solo en Minecraft.")
        form.addRow(QLabel("<br><b>Tareas automáticas</b>"))
        form.addRow("Copia de seguridad cada", self.set_backup_hours)
        form.addRow("Copias automáticas a guardar", self.set_keep_backups)
        form.addRow(restart_row)
        form.addRow("Apagar si nadie juega durante", self.set_idle_stop)
        note = QLabel("Los jugadores reciben un aviso 1 minuto antes del reinicio. "
                      "Los cambios de memoria se aplican la próxima vez que se encienda el servidor.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        form.addRow(note)
        form.addRow(save)

        # --- Mapa web y pregeneración ---
        self.addons_title = QLabel("<br><b>Mapa y mundo</b>")
        self.addons_note = QLabel("Solo en servidores Paper, Fabric, Forge o NeoForge.")
        self.addons_note.setObjectName("muted")
        self.map_box = QCheckBox("Mapa del mundo en el navegador (BlueMap)")
        self.map_box.setToolTip("Un mapa en 3D del mundo que se abre en el navegador, también desde el móvil.\n"
                                "Se dibuja poco a poco mientras el servidor está encendido.")
        self.map_box.toggled.connect(lambda on: self._toggle_addon("map", on))
        self.map_link = QLabel()
        self.map_link.setOpenExternalLinks(True)
        self.map_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.pregen_box = QCheckBox("Generar el mundo por adelantado (Chunky)")
        self.pregen_box.setToolTip("Crea de antemano el terreno alrededor del centro del mundo: así no hay "
                                   "tirones cuando los jugadores exploran zonas nuevas.")
        self.pregen_box.toggled.connect(lambda on: self._toggle_addon("pregen", on))
        self.pregen_radius = QSpinBox(minimum=100, maximum=100_000, singleStep=500, value=3000, suffix=" bloques")
        self.pregen_radius.setToolTip("Distancia desde el centro (0, 0). 3000 bloques tarda unos minutos; "
                                      "10 000 puede tardar horas y ocupar varios GB.")
        self.pregen_start = QPushButton("Generar")
        self.pregen_start.clicked.connect(lambda: self._pregen("start"))
        self.pregen_cancel = QPushButton("Cancelar")
        self.pregen_cancel.clicked.connect(lambda: self._pregen("cancel"))
        pregen_row = QHBoxLayout()
        pregen_row.addWidget(QLabel("Radio"))
        pregen_row.addWidget(self.pregen_radius)
        pregen_row.addWidget(self.pregen_start)
        pregen_row.addWidget(self.pregen_cancel)
        pregen_row.addStretch()
        self.pregen_row = QWidget()
        self.pregen_row.setLayout(pregen_row)
        self.pregen_status = QLabel()
        self.pregen_status.setObjectName("muted")
        self.pregen_status.setWordWrap(True)
        for row in (self.addons_title, self.addons_note, self.map_box, self.map_link, self.pregen_box,
                    self.pregen_row, self.pregen_status):
            form.addRow(row)

        # --- Multiplataforma (Geyser) ---
        self.crossplay_title = QLabel("<br><b>Multiplataforma (Geyser)</b>")
        self.crossplay_status = QLabel()
        self.crossplay_status.setWordWrap(True)
        self.crossplay_floodgate = QCheckBox("Sin necesitar cuenta de Java (Floodgate)")
        self.crossplay_floodgate.setChecked(True)
        self.crossplay_button = QPushButton()
        self.crossplay_button.clicked.connect(self._toggle_crossplay)
        form.addRow(self.crossplay_title)
        form.addRow(self.crossplay_status)
        form.addRow(self.crossplay_floodgate)
        form.addRow(self.crossplay_button)

        # --- Extras de Geyser ---
        self.extras_title = QLabel("<br><b>Extras para los jugadores de Bedrock</b>")
        self.extras_note = QLabel("El paquete que acerca Bedrock a Java (posturas de soportes de armadura, "
                                  "partículas, flechas espectrales...) ya viene incluido en Geyser.")
        self.extras_note.setObjectName("muted")
        self.extras_note.setWordWrap(True)
        form.addRow(self.extras_title)
        form.addRow(self.extras_note)
        self.extra_boxes: dict[str, QCheckBox] = {}
        for key, text, tip in EXTRAS:
            box = QCheckBox(text)
            box.setToolTip(tip)
            box.toggled.connect(lambda checked, k=key: self._toggle_extra(k, checked))
            self.extra_boxes[key] = box
            form.addRow(box)
        self.xbox_info = QLabel()
        self.xbox_info.setWordWrap(True)
        self.xbox_info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(self.xbox_info)
        return w

    def _build_properties(self) -> QWidget:
        w = QWidget()
        self.props = QTableWidget(0, 2)
        self.props.setHorizontalHeaderLabels(["Propiedad", "Valor"])
        self.props.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.props.horizontalHeader().setStretchLastSection(True)
        self.props.verticalHeader().setVisible(False)
        reload_btn = QPushButton("Recargar")
        reload_btn.clicked.connect(self._load_properties)
        save = QPushButton("Guardar")
        save.clicked.connect(self._save_properties)
        note = QLabel("El servidor crea este archivo en su primer arranque. "
                      "Reinicia el servidor para aplicar los cambios.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        row = QHBoxLayout()
        row.addWidget(note, 1)
        row.addWidget(reload_btn)
        row.addWidget(save)
        layout = QVBoxLayout(w)
        layout.addWidget(self.props, 1)
        layout.addLayout(row)
        return w

    def _build_backups(self) -> QWidget:
        w = QWidget()
        self.backups = QTableWidget(0, 3)
        self.backups.setHorizontalHeaderLabels(["Archivo", "Tamaño", "Fecha"])
        self.backups.horizontalHeader().setStretchLastSection(True)
        self.backups.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.backups.verticalHeader().setVisible(False)
        self.backups.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.backups.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.backups.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        create = QPushButton("Crear copia ahora")
        create.clicked.connect(lambda: self._action("backup"))
        self.backup_download = download = QPushButton("Descargar...")
        download.setToolTip("Guarda la copia en este PC (para editar el mundo o guardarla aparte)")
        download.clicked.connect(self._download_backup)
        self.backup_restore = restore = QPushButton("Restaurar")
        restore.clicked.connect(self._restore_backup)
        self.backup_delete = delete = QPushButton("Eliminar")
        delete.clicked.connect(self._delete_backup)
        reload_btn = QPushButton("Recargar")
        reload_btn.clicked.connect(self._load_backups)
        row = QHBoxLayout()
        row.addWidget(create)
        row.addStretch()
        for b in (reload_btn, download, restore, delete):
            row.addWidget(b)
        layout = QVBoxLayout(w)
        layout.addWidget(self.backups, 1)
        layout.addLayout(row)
        return w

    # ---------- datos ----------

    def show_server(self, client: AgentClient, server: dict, addresses: list[tuple[str, str]],
                    is_local: bool = False, level: int = OWNER) -> None:
        self.is_local = is_local
        changed = (not self.server or self.server["id"] != server["id"] or self.client is not client
                   or level != self.level)
        self.level = level
        self.client = client
        self.addresses = addresses
        self.server = server
        self._refresh_header()
        if changed:
            self._fill_settings()
            self.console.clear()
            self._open_console()
            self.props.setRowCount(0)
            self.backups.setRowCount(0)
            mods_index = self.tabs.indexOf(self.mods_tab)
            self.tabs.setTabEnabled(self.tabs.indexOf(self.properties_tab), server["has_properties"])
            self.tabs.setTabEnabled(mods_index, bool(server.get("mods_label")))
            self.tabs.setTabText(mods_index, server.get("mods_label") or "Mods")
            if server.get("mods_label"):
                self.mods_tab.set_server(client, server)
            self.players_tab.set_server(client, server)
            self.metrics_tab.set_server(client, server)
            self.tabs.setTabEnabled(self.tabs.indexOf(self.players_tab), server["game"] in ("minecraft", "bedrock"))
            self._apply_level()
            if not self.tabs.isTabEnabled(self.tabs.currentIndex()) or not self.tabs.isTabVisible(
                    self.tabs.currentIndex()):
                self.tabs.setCurrentIndex(next(i for i in range(self.tabs.count())
                                               if self.tabs.isTabVisible(i) and self.tabs.isTabEnabled(i)))
            self._tab_changed(self.tabs.currentIndex())

    def _apply_level(self) -> None:
        """Con el acceso de un amigo solo se ve lo que su permiso deja hacer."""
        level = self.level
        tabs = {self.console_tab: MODERATE, self.players_tab: PLAY, self.metrics_tab: PLAY, self.mods_tab: MANAGE,
                self.settings_tab: MANAGE, self.properties_tab: MANAGE, self.backups_tab: MODERATE}
        for widget, needed in tabs.items():
            self.tabs.setTabVisible(self.tabs.indexOf(widget), level >= needed)
        for widget, needed in ((self.btn_kill, MODERATE), (self.btn_backup, MODERATE), (self.btn_update, MANAGE),
                               (self.btn_folder, OWNER), (self.btn_move, OWNER),
                               (self.btn_delete, OWNER), (self.backup_download, OWNER),
                               (self.backup_restore, MANAGE), (self.backup_delete, MANAGE)):
            widget.setVisible(level >= needed)
        self.act_download_world.setVisible(level >= OWNER)
        # Sin descargar ni importar, el menú «Mundo» se quedaría vacío.
        self.btn_world.setVisible(level >= OWNER or level >= MANAGE and bool(self.server.get("world_import")))
        self.players_tab.set_can_edit(level >= MODERATE)

    def update_server(self, server: dict) -> None:
        if self.server and server["id"] == self.server["id"]:
            was_task = self.server.get("task")
            # Las respuestas de las acciones no traen la carpeta: se conserva la del último sondeo.
            server.setdefault("path", self.server.get("path"))
            self.server = server
            self._refresh_header()
            self.players_tab.update_online(server)
            if was_task == "backing-up" and not server.get("task"):
                self._load_backups()
            if self.mods_tab.reload_when_idle and not server.get("task"):
                self.mods_tab.reload_when_idle = False
                self.mods_tab.reload()

    def clear(self) -> None:
        self.server = None
        self.client = None
        self.reconnect_timer.stop()
        self.ws.abort()

    def _refresh_header(self) -> None:
        s = self.server
        label, color = STATUS.get(s["status"], (s["status"], "gray"))
        self.title.setText(s["name"])
        build = f" (build {s['build']})" if s.get("build") and s["build"].isdigit() else (
            f" ({s['build']})" if s.get("build") else "")
        version = s["version"]
        if version == "latest":  # Hytale: el downloader siempre baja la última; la versión real es la build
            version, build = s.get("build") or "", ""
        pack = (s.get("extra") or {}).get("modpack")
        self.subtitle.setText(f"{s['game_name']} · {s.get('flavor_name', s['flavor'])} {version}{build}".rstrip()
                              + (f" · modpack {pack['name']} {pack['version']}".rstrip() if pack else ""))
        text = "Conectar a: " + " · ".join(f"<b>{ip}:{s['port']}</b> ({label})" for ip, label in self.addresses)
        if cp := s.get("crossplay"):
            ip = self.addresses[0][0] if self.addresses else ""
            text += f"<br>Bedrock: <b>{ip}</b> puerto <b>{cp['bedrock_port']}</b>"
        self.address.setText(text)
        self._refresh_crossplay()
        self._refresh_addons()
        self.status.setText(f"● {label}")
        self.status.setStyleSheet(theme.pill_style(s["status"]))
        st = s.get("stats") or {}
        if st:
            self.stats.setText(f"CPU {st['cpu_percent']}% · RAM {st['memory_mb']} MB · "
                               f"{format_uptime(st['uptime_s'])}")
        else:
            self.stats.setText("")
        self.error.setText(s.get("error") or "")
        self.error.setVisible(bool(s.get("error")))

        busy = bool(s.get("task"))
        state = s["state"]
        on = state in ("starting", "running", "stopping")
        self.btn_start.setEnabled(not busy and not on)
        self.btn_stop.setEnabled(state in ("starting", "running"))
        self.btn_restart.setEnabled(not busy and state == "running")
        self.btn_kill.setEnabled(on)
        self.btn_update.setEnabled(not busy and not on)
        self.btn_backup.setEnabled(not busy)
        self.btn_delete.setEnabled(not busy and not on)
        self.btn_move.setEnabled(not busy and state != "stopping")
        self._refresh_icon()
        self.act_import_world.setVisible(bool(s.get("world_import")))
        self.act_import_world.setEnabled(not busy and not on)
        self.btn_folder.setEnabled(self.is_local)
        self.btn_folder.setToolTip("" if self.is_local else
                                   "La carpeta está en el otro equipo: ábrela desde Ownhost en ese equipo")
        self.btn_login.setVisible(bool(s.get("device_auth")) and self.level >= MANAGE)
        self.btn_login.setEnabled(state in ("starting", "running") and not s.get("auth"))
        self.command.setEnabled(state in ("starting", "running"))

    def _refresh_addons(self) -> None:
        s = self.server
        java = s["game"] == "minecraft"
        supported = bool(s.get("addons_supported"))
        for w in (self.addons_title, self.addons_note):
            w.setVisible(java)
        self.addons_note.setVisible(java and not supported)
        web_map, pregen_on = s.get("map"), bool(s.get("pregen_installed"))
        for box, on in ((self.map_box, bool(web_map)), (self.pregen_box, pregen_on)):
            box.setVisible(java and supported)
            box.blockSignals(True)
            box.setChecked(on)
            box.blockSignals(False)
            box.setEnabled(not s.get("task"))
        running = s["state"] == "running"
        if web_map and self.addresses:
            url = f"http://{self.addresses[0][0]}:{web_map['port']}/"
            self.map_link.setText(f"Abrir el mapa: <a href='{url}'>{url}</a>" if running else
                                  f"El mapa estará en <b>{url}</b> cuando el servidor esté encendido.")
        self.map_link.setVisible(java and supported and bool(web_map))
        progress = s.get("pregen") or {}
        busy = progress.get("state") == "running"
        self.pregen_row.setVisible(java and supported and pregen_on)
        self.pregen_status.setVisible(java and supported and pregen_on)
        self.pregen_start.setEnabled(running and not busy)
        self.pregen_cancel.setEnabled(running and busy)
        if busy:
            eta = f", quedan {progress['eta']}" if progress.get("eta") else ""
            text = f"Generando: {progress['percent']:.0f} % ({progress['chunks']:,} chunks{eta})".replace(",", ".")
        elif progress.get("state") == "finished":
            text = f"Mundo generado: {progress['chunks']:,} chunks.".replace(",", ".")
        elif not running:
            text = "Enciende el servidor para generar el mundo (si acabas de instalar Chunky, reinícialo)."
        else:
            text = "Pulsa «Generar». Los jugadores pueden seguir jugando mientras tanto."
        self.pregen_status.setText(text)

    def _toggle_addon(self, key: str, enabled: bool) -> None:
        sid, client = self.server["id"], self.client
        if enabled:
            self.statusBar_message("Descargando " + ("BlueMap..." if key == "map" else "Chunky..."))

        def done(server: dict):
            self.update_server(server)
            if enabled and server["state"] == "running":
                QMessageBox.information(self, "Reinicia el servidor",
                                        "Instalado. Reinicia el servidor para que empiece a funcionar.")

        def failed(msg: str):
            self._error(msg)
            self._refresh_addons()

        run_async(lambda: client.set_addon(sid, key, enabled), done, failed)

    def _pregen(self, action: str) -> None:
        sid, client, radius = self.server["id"], self.client, self.pregen_radius.value()
        self._call(lambda: client.pregenerate(sid, action, radius), self.update_server)

    def statusBar_message(self, text: str) -> None:
        if (bar := getattr(self.window(), "statusBar", None)) is not None:
            bar().showMessage(text, 8000)

    def _refresh_crossplay(self) -> None:
        s = self.server
        supported, cp = s.get("crossplay_supported"), s.get("crossplay")
        for w in (self.crossplay_title, self.crossplay_status, self.crossplay_button):
            w.setVisible(s["game"] == "minecraft")
        self.crossplay_floodgate.setVisible(bool(supported and not cp))
        if not supported:
            self.crossplay_status.setText("Solo disponible en servidores Paper, Fabric o NeoForge.")
            self.crossplay_button.setVisible(False)
            for w in (self.extras_title, self.extras_note, *self.extra_boxes.values(), self.xbox_info):
                w.setVisible(False)
            return
        if cp:
            self.crossplay_status.setText(
                f"Activada. Los jugadores de Bedrock entran por el puerto <b>{cp['bedrock_port']}</b>"
                + (", sin cuenta de Java." if cp.get("floodgate") else ".")
                + f" Para jugar desde fuera de casa, abre en el router el {cp['bedrock_port']} (TCP y UDP) y el "
                  f"{cp['bedrock_port'] + 1} (UDP), o usad Tailscale.<br>"
                + f"Los jugadores de Bedrock ven el nombre <b>{s['name']}</b> y la misma descripción y límite "
                  "de jugadores que en Java (los de arriba).")
            self.crossplay_button.setText("Desactivar multiplataforma")
        else:
            self.crossplay_status.setText("Permite que jugadores de Bedrock (móvil, consola, Windows) "
                                          "entren a este servidor de Java.")
            self.crossplay_button.setText("Activar multiplataforma")
        busy = bool(s.get("task")) or s["state"] != "stopped" and s["state"] != "crashed"
        self.crossplay_button.setEnabled(not busy)
        self.crossplay_button.setToolTip("Apaga el servidor primero" if busy else "")

        # Extras (solo con la multiplataforma activada)
        extras = (cp or {}).get("extras", {})
        for w in (self.extras_title, self.extras_note, *self.extra_boxes.values()):
            w.setVisible(bool(cp))
        for key, box in self.extra_boxes.items():
            box.blockSignals(True)
            box.setChecked(key in extras)
            box.blockSignals(False)
            box.setEnabled(not busy)
        if cp and "xbox" in extras:
            gamertag = s.get("xbox_gamertag")
            if s.get("xbox_problem") == "no_profile":
                self.xbox_info.setText(
                    f"<span style='color:{theme.DANGER_TEXT}'>La cuenta de Microsoft aún no tiene <b>perfil de "
                    "Xbox</b>.</span> Entra en <a href='https://www.xbox.com/'>xbox.com</a> con la cuenta "
                    "secundaria, crea el perfil (eligiendo un gamertag) y después reinicia el servidor.")
                self.xbox_info.setOpenExternalLinks(True)
            elif gamertag:
                self.xbox_info.setText(
                    f"En la consola (Switch, Xbox, PlayStation), añade como amigo a <b>{gamertag}</b>. "
                    "El servidor aparecerá en la pestaña <b>Amigos</b> cuando esté encendido.")
            else:
                self.xbox_info.setText(
                    "Al encender el servidor se abrirá una ventana para iniciar sesión con una <b>cuenta de "
                    "Microsoft secundaria</b> (créala solo para esto, no uses la tuya). Después te diré "
                    "a quién añadir como amigo.")
            self.xbox_info.setVisible(True)
        else:
            self.xbox_info.setVisible(False)

    def _toggle_extra(self, key: str, enabled: bool) -> None:
        sid, client = self.server["id"], self.client
        if key == "xbox" and enabled:
            answer = QMessageBox.question(
                self, "Amigos de Xbox",
                "Para que el servidor salga en la pestaña Amigos de las consolas, hace falta iniciar sesión "
                "con una cuenta de Microsoft.\n\nUsa una cuenta SECUNDARIA creada solo para esto, sin datos "
                "personales ni de pago: la extensión imita a un cliente de Xbox y Microsoft podría "
                "bloquear esa cuenta. Tu cuenta principal no corre ningún riesgo.\n\n¿Continuar?")
            if answer != QMessageBox.StandardButton.Yes:
                self._refresh_crossplay()
                return
        def failed(msg: str):
            self._error(msg)
            self._refresh_crossplay()  # la casilla vuelve a mostrar el estado real

        run_async(lambda: client.set_crossplay_extra(sid, key, enabled), self.update_server, failed)

    def _toggle_crossplay(self) -> None:
        sid, client = self.server["id"], self.client
        if self.server.get("crossplay"):
            if QMessageBox.question(self, "Multiplataforma", "¿Quitar Geyser? Los jugadores de Bedrock "
                                    "no podrán entrar.") != QMessageBox.StandardButton.Yes:
                return
            self._call(lambda: client.disable_crossplay(sid), self.update_server)
        else:
            floodgate = self.crossplay_floodgate.isChecked()
            self._call(lambda: client.enable_crossplay(sid, floodgate), self.update_server)

    def _fill_settings(self) -> None:
        s = self.server
        self.set_name.setText(s["name"])
        self.set_memory.setValue(s["memory_mb"])
        self.set_port.setValue(s["port"])
        self.set_autostart.setChecked(s["auto_start"])
        self.set_autoupdate.setChecked(s.get("auto_update", True))
        self.set_autorestart.setChecked(s.get("auto_restart", True))
        sched = s.get("schedule") or {}
        self.set_backup_hours.setValue(int(sched.get("backup_hours") or 0))
        self.set_keep_backups.setValue(int(sched.get("keep_backups") or 7))
        at = QTime.fromString(sched.get("restart_at") or "", "HH:mm")
        self.set_restart_on.setChecked(at.isValid())
        self.set_restart_at.setTime(at if at.isValid() else QTime(5, 0))
        self.set_restart_at.setEnabled(at.isValid())
        self.set_idle_stop.setValue(int(sched.get("idle_stop_minutes") or 0))
        self.settings_form.setRowVisible(self.set_idle_stop, s["game"] in ("minecraft", "bedrock"))
        # Descripción solo en Minecraft Java; límite de jugadores en Java y en Bedrock nativo.
        java, bedrock = s["game"] == "minecraft", s["game"] == "bedrock"
        self.settings_form.setRowVisible(self.set_motd, java)
        self.settings_form.setRowVisible(self.set_max_players, java or bedrock)
        self.props_loaded_for = None
        if (java or bedrock) and self.level >= MANAGE:
            sid, client = s["id"], self.client

            def loaded(props: dict):
                if not self.server or self.server["id"] != sid:
                    return
                self.set_motd.setText(props.get("motd", ""))
                players = props.get("max-players", "20")
                self.set_max_players.setValue(int(players) if players.isdigit() else 20)
                self.props_loaded_for = sid

            run_async(lambda: client.properties(sid), loaded, lambda _: None)

    def _tab_changed(self, index: int) -> None:
        if not self.server:
            return
        widget = self.tabs.widget(index)
        if widget is self.properties_tab and self.server["has_properties"]:
            self._load_properties()
        elif widget is self.backups_tab:
            self._load_backups()
        elif widget is self.mods_tab and self.server.get("mods_label"):
            self.mods_tab.activate()
        elif widget is self.players_tab:
            self.players_tab.reload()
        if widget is self.metrics_tab:
            self.metrics_tab.activate()
        else:
            self.metrics_tab.deactivate()

    def _error(self, msg: str) -> None:
        QMessageBox.warning(self, "Error", msg)

    def _call(self, fn, on_done=None) -> None:
        run_async(fn, on_done, self._error)

    # ---------- consola ----------

    def _open_console(self) -> None:
        if not self.server or not self.client or self.level < MODERATE:
            return
        self.ws.abort()
        self.console.clear()
        self.ws.open(QUrl(self.client.ws_url(self.server["id"])))

    def _ws_disconnected(self) -> None:
        if self.server:
            self.reconnect_timer.start()

    def _console_text(self, text: str) -> None:
        if not text:
            return
        bar = self.console.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        self.console.appendPlainText(text)
        if at_bottom:
            self.console.moveCursor(QTextCursor.MoveOperation.End)
            bar.setValue(bar.maximum())

    def _send_command(self) -> None:
        text = self.command.text().strip()
        if not text or not self.server:
            return
        self.command.clear()
        sid = self.server["id"]
        self._call(lambda: self.client.command(sid, text.lstrip("/") if self.server["game"] == "minecraft" else text))

    # ---------- acciones ----------

    def _action(self, action: str) -> None:
        sid, client = self.server["id"], self.client
        self._call(lambda: client.action(sid, action), self.update_server)

    def _kill(self) -> None:
        if QMessageBox.question(self, "Forzar cierre",
                                "Se cerrará el proceso sin guardar. ¿Continuar?") == QMessageBox.StandardButton.Yes:
            self._action("kill")

    def _update(self) -> None:
        s, client = self.server, self.client

        def got_versions(versions):
            version = ask_version(self, versions, s["version"])
            if version:
                self._call(lambda: client.update(s["id"], version), self.update_server)

        self._call(lambda: client.versions(s["game"], s["flavor"]), got_versions)

    def _move(self) -> None:
        targets = self.move_targets()
        if not targets:
            QMessageBox.information(self, "Mover servidor",
                                    "No hay otro equipo conectado. Añade el destino con "
                                    "«Conectar a un equipo (IP)» primero.")
            return
        s, src = self.server, self.client
        dialog = MoveDialog(self, s, targets)
        if not dialog.exec():
            return
        host, dst = dialog.target()
        delete_original = dialog.delete_original.isChecked()

        bar = QProgressDialog("Preparando...", None, 0, 0, self)
        bar.setWindowTitle(f"Moviendo «{s['name']}» a {host.name}")
        bar.setMinimumWidth(420)
        bar.setMinimumDuration(0)
        bar.setAutoClose(False)
        bar.show()

        def done(new: dict):
            bar.close()
            QMessageBox.information(self, "Servidor movido",
                                    f"«{new['name']}» ya está en {host.name}, puerto {new['port']}.\n"
                                    f"Los jugadores deben conectarse a {host.address}:{new['port']}.")
            self.on_moved(host.id, new)

        def failed(msg: str):
            bar.close()
            self._error(msg)

        run_with_progress(lambda progress: move_server(src, s["id"], dst, delete_original, progress),
                          bar.setLabelText, done, failed)

    def _clone(self) -> None:
        s, client = self.server, self.client
        name, ok = QInputDialog.getText(self, "Clonar servidor",
                                        "Nombre del servidor nuevo (tendrá otro puerto):",
                                        text=f"{s['name']} (copia)")
        if not ok:
            return
        self._call(lambda: client.clone(s["id"], name.strip()),
                   lambda _: self.window().statusBar().showMessage(
                       f"Clonando «{s['name']}»: el servidor nuevo aparecerá en la lista en unos momentos.", 8000))

    # ---------- icono ----------

    def _refresh_icon(self) -> None:
        s = self.server
        self.settings_form.setRowVisible(self.icon_row, bool(s.get("icon_supported")))
        key = (id(self.client), s["id"], s.get("icon_version"))
        if not s.get("icon_supported") or key == self.icon_loaded:
            return
        self.icon_loaded = key
        self.icon_remove.setEnabled(bool(s.get("icon_version")))
        if not s.get("icon_version"):
            self.icon_preview.setPixmap(QPixmap())
            self.icon_preview.setText("Sin icono")
            return
        sid, client = s["id"], self.client

        def show(data):
            if data and self.server and self.server["id"] == sid:
                pix = QPixmap()
                pix.loadFromData(data)
                self.icon_preview.setPixmap(pix)

        run_async(lambda: client.icon(sid), show, lambda _: None)

    def _choose_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir icono", str(Path.home()),
                                              "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if not path:
            return
        image = QImage(path)
        if image.isNull():
            self._error("No se pudo abrir la imagen.")
            return
        # recorte cuadrado centrado y 64x64, que es lo único que acepta Minecraft
        side = min(image.width(), image.height())
        image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
        image = image.scaled(64, 64, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buf, "PNG")
        png, sid, client = bytes(data.data()), self.server["id"], self.client
        self._call(lambda: client.set_icon(sid, png), self.update_server)

    def _remove_icon(self) -> None:
        sid, client = self.server["id"], self.client
        self._call(lambda: client.delete_icon(sid), self.update_server)

    def _delete(self) -> None:
        s, client = self.server, self.client
        answer = QMessageBox.question(
            self, "Eliminar servidor",
            f"¿Eliminar «{s['name']}»? Se borrarán el mundo y todas sus copias de seguridad. "
            "Esto no se puede deshacer.")
        if answer == QMessageBox.StandardButton.Yes:
            self._call(lambda: client.delete(s["id"]))

    def _save_settings(self) -> None:
        sid, client = self.server["id"], self.client
        changes = {"name": self.set_name.text().strip(), "memory_mb": self.set_memory.value(),
                   "port": self.set_port.value(), "auto_start": self.set_autostart.isChecked(),
                   "auto_update": self.set_autoupdate.isChecked(),
                   "auto_restart": self.set_autorestart.isChecked(),
                   "schedule": {"backup_hours": self.set_backup_hours.value(),
                                "keep_backups": self.set_keep_backups.value(),
                                "restart_at": self.set_restart_at.time().toString("HH:mm")
                                if self.set_restart_on.isChecked() else None,
                                "idle_stop_minutes": self.set_idle_stop.value()}}
        props = {}
        if self.props_loaded_for == sid:  # solo si se llegaron a leer (si no, se borrarían)
            props["max-players"] = str(self.set_max_players.value())
            if self.server["game"] == "minecraft":
                props["motd"] = self.set_motd.text().strip()

        def save():
            if props:
                client.set_properties(sid, props)
            return client.patch(sid, **changes)

        def saved(server: dict):
            self.update_server(server)
            if server["state"] in ("running", "starting"):
                self.window().statusBar().showMessage("Guardado. Reinicia el servidor para aplicar los cambios.", 6000)

        self._call(save, saved)

    def _load_properties(self) -> None:
        sid, client = self.server["id"], self.client

        def done(props: dict):
            self.props.setRowCount(0)
            for key in sorted(props):
                row = self.props.rowCount()
                self.props.insertRow(row)
                key_item = QTableWidgetItem(key)
                key_item.setFlags(key_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.props.setItem(row, 0, key_item)
                self.props.setItem(row, 1, QTableWidgetItem(props[key]))

        self._call(lambda: client.properties(sid), done)

    def _save_properties(self) -> None:
        sid, client = self.server["id"], self.client
        props = {self.props.item(r, 0).text(): self.props.item(r, 1).text() for r in range(self.props.rowCount())}
        self._call(lambda: client.set_properties(sid, props),
                   lambda _: QMessageBox.information(self, "Guardado", "Propiedades guardadas."))

    def _load_backups(self) -> None:
        sid, client = self.server["id"], self.client

        def done(backups: list):
            self.backups.setRowCount(0)
            for b in backups:
                row = self.backups.rowCount()
                self.backups.insertRow(row)
                self.backups.setItem(row, 0, QTableWidgetItem(b["name"]))
                self.backups.setItem(row, 1, QTableWidgetItem(f"{b['size_mb']} MB"))
                self.backups.setItem(row, 2, QTableWidgetItem(b["created"].replace("T", " ")))

        self._call(lambda: client.backups(sid), done)

    def _open_folder(self) -> None:
        if self.server and self.server.get("path"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.server["path"]))

    def _import_world(self) -> None:
        s, client = self.server, self.client
        dialog = ImportWorldDialog(self, s)
        if not dialog.exec():
            return
        source, include_mods = dialog.source, dialog.include_mods.isChecked()
        bar = QProgressDialog("Preparando...", None, 0, 0, self)
        bar.setWindowTitle(f"Importando mundo en «{s['name']}»")
        bar.setMinimumWidth(420)
        bar.setMinimumDuration(0)
        bar.setAutoClose(False)
        bar.show()

        def done(_):
            bar.close()
            QMessageBox.information(self, "Mundo importado",
                                    "Mundo importado. Enciende el servidor para cargarlo.\n"
                                    "El mundo anterior está en «Copias de seguridad».")

        def failed(msg: str):
            bar.close()
            self._error(msg)

        run_with_progress(lambda progress: import_world(client, s["id"], source, include_mods, progress),
                          bar.setLabelText, done, failed)

    def _download_backup(self) -> None:
        name = self._selected_backup()
        if not name:
            QMessageBox.information(self, "Descargar copia", "Selecciona una copia de la lista "
                                    "(o crea una con «Crear copia ahora»).")
            return
        dest, _ = QFileDialog.getSaveFileName(self, "Guardar copia", f"{self.server['name']}-{name}",
                                              "Archivo zip (*.zip)")
        if not dest:
            return
        sid, client = self.server["id"], self.client
        self._call(lambda: client.download_backup(sid, name, Path(dest), lambda n: None),
                   lambda _: QMessageBox.information(self, "Descargada", f"Copia guardada en:\n{dest}"))

    def _selected_backup(self) -> str | None:
        rows = self.backups.selectionModel().selectedRows()
        return self.backups.item(rows[0].row(), 0).text() if rows else None

    def _restore_backup(self) -> None:
        name = self._selected_backup()
        if not name:
            return
        sid, client = self.server["id"], self.client
        if QMessageBox.question(self, "Restaurar copia",
                                f"Se sustituirá el mundo actual por la copia {name}. ¿Continuar?"
                                ) == QMessageBox.StandardButton.Yes:
            self._call(lambda: client.restore_backup(sid, name))

    def _delete_backup(self) -> None:
        name = self._selected_backup()
        if not name:
            return
        sid, client = self.server["id"], self.client
        if QMessageBox.question(self, "Eliminar copia", f"¿Eliminar {name}?") == QMessageBox.StandardButton.Yes:
            self._call(lambda: client.delete_backup(sid, name), lambda _: self._load_backups())
