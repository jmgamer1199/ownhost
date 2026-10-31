from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout,
)

from ownhost.agent import DEFAULT_PORT
from ownhost.app.client import AgentClient
from ownhost.app.hosts import Host
from ownhost.app.settings import curseforge_key, embedded_curseforge_key, load_settings, save_settings
from ownhost.app.tasks import run_async, run_with_progress
from ownhost.app.world_import import WorldSource, default_saves_dir
from ownhost.app.world_import import inspect as inspect_world
from ownhost.discovery import discover
from ownhost.net import is_reachable, lan_ip, own_ips, tailscale_peers


class HostDialog(QDialog):
    """Añadir o editar un equipo con el agente instalado."""

    def __init__(self, parent=None, host: Host | None = None):
        super().__init__(parent)
        self.setWindowTitle("Editar equipo" if host else "Conectar a un equipo")
        self.setMinimumWidth(500)
        self.name = QLineEdit(host.name if host else "")
        self.name.setPlaceholderText("Homelab, PC del salón...")
        self.address = QLineEdit(host.address if host else "")
        # Ejemplo con la red real del usuario (192.168.0.x, 10.0.0.x...), no un número fijo.
        self.address.setPlaceholderText(lan_ip().rsplit(".", 1)[0] + ".x")
        self.port = QSpinBox(maximum=65535, value=host.port if host else DEFAULT_PORT)
        self.token = QLineEdit(host.token if host else "")
        self.token.setPlaceholderText("Vacío si el equipo está en tu Tailscale con tu misma cuenta")
        self._host = host

        help_text = QLabel("En el otro equipo abre Ownhost y pulsa «Usar este PC como servidor»: "
                           "en la ficha de «Este PC» verás su IP y su token. En Linux, el instalador "
                           "del agente los muestra al terminar. Si un amigo te ha dado un código de "
                           "acceso, escríbelo como token.")
        help_text.setWordWrap(True)

        # Equipos detectados solos: agentes que responden en la red local y equipos de Tailscale.
        self.found_box = QComboBox()
        self.found_box.addItem("Buscando equipos...", None)
        self.found_box.setEnabled(False)
        self.found_box.currentIndexChanged.connect(self._found_selected)
        self._found_lan: list[dict] | None = None
        self._found_tailscale: list[dict] | None = None

        form = QFormLayout()
        form.addRow("Detectados", self.found_box)
        form.addRow("Nombre", self.name)
        form.addRow("Dirección IP", self.address)
        form.addRow("Puerto", self.port)
        form.addRow("Token o código", self.token)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._test_and_accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)

        layout = QVBoxLayout(self)
        layout.addWidget(help_text)
        layout.addLayout(form)
        layout.addWidget(buttons)
        run_async(lambda: discover(DEFAULT_PORT), lambda r: self._found("lan", r), lambda _: self._found("lan", []))
        run_async(tailscale_peers, lambda r: self._found("tailscale", r), lambda _: self._found("tailscale", []))

    def _found(self, kind: str, results: list[dict]) -> None:
        if kind == "lan":
            own = own_ips()
            self._found_lan = [r for r in results if r["address"] not in own]
        else:
            self._found_tailscale = results
        if self._found_lan is None or self._found_tailscale is None:
            return  # esperamos a las dos búsquedas
        self.found_box.blockSignals(True)
        self.found_box.clear()
        options = [(f"{r['name']}  ({r['address']}, ownhost en la red local)",
                    {"name": r["name"], "ip": r["address"], "port": r.get("port", DEFAULT_PORT)})
                   for r in self._found_lan]
        lan_ips = {r["address"] for r in self._found_lan}
        options += [(f"{p['name']}  ({p['ip']}, Tailscale, {'conectado' if p['online'] else 'desconectado'})", p)
                    for p in self._found_tailscale if p["ip"] not in lan_ips]
        if options:
            self.found_box.addItem(f"Elegir entre {len(options)} equipos encontrados...", None)
            for label, data in options:
                self.found_box.addItem(label, data)
            self.found_box.setEnabled(True)
        else:
            self.found_box.addItem("No se encontró ningún equipo: escribe su IP abajo", None)
        self.found_box.blockSignals(False)

    def _found_selected(self) -> None:
        peer = self.found_box.currentData()
        if not peer:
            return
        self.address.setText(peer["ip"])
        if peer.get("port"):
            self.port.setValue(peer["port"])
        if not self.name.text().strip():
            self.name.setText(peer["name"])
        self.token.setFocus()

    def result_host(self) -> Host:
        host = Host(name=self.name.text().strip() or self.address.text().strip(),
                    address=self.address.text().strip(), token=self.token.text().strip(),
                    port=self.port.value())
        if self._host:
            host.id = self._host.id
        return host

    def _test_and_accept(self) -> None:
        host = self.result_host()
        if not host.address:
            QMessageBox.warning(self, "Faltan datos", "Indica la dirección del equipo.")
            return
        self.ok_button.setEnabled(False)
        self.ok_button.setText("Probando...")
        client = AgentClient(host)

        def done(_):
            client.close()
            self.accept()

        def failed(msg: str):
            client.close()
            # Si el equipo responde al ping pero no al agente, casi siempre es su cortafuegos.
            run_async(lambda: is_reachable(host.address), lambda up: explain(msg, up), lambda _: explain(msg, False))

        def explain(msg: str, reachable: bool):
            self.ok_button.setEnabled(True)
            self.ok_button.setText("OK")
            if reachable and msg != "Token incorrecto":
                msg = (f"El equipo {host.address} está encendido y responde, pero no deja conectar con el "
                       f"Ownhost (puerto {host.port}). Casi seguro es su cortafuegos.\n\n"
                       "En ese equipo, abre Ownhost y pulsa «Abrir puertos del cortafuegos» en la ficha "
                       "«Este PC» (en Linux), o permite Ownhost en el Firewall de Windows.")
            QMessageBox.warning(self, "No se pudo conectar", msg)

        run_async(client.info, done, failed)


class CreateServerDialog(QDialog):
    def __init__(self, parent, hosts: list[tuple[Host, AgentClient]], selected_host_id: str | None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo servidor")
        self.setMinimumWidth(500)
        self.hosts = hosts
        self.games: list[dict] = []

        self.host_box = QComboBox()
        for host, _ in hosts:
            self.host_box.addItem(host.name, host.id)
        if selected_host_id:
            self.host_box.setCurrentIndex(max(0, self.host_box.findData(selected_host_id)))
        self.name = QLineEdit()
        self.name.setPlaceholderText("Survival con amigos")
        self.game_box = QComboBox()
        self.flavor_box = QComboBox()
        self.version_box = QComboBox()
        self.memory = QSpinBox(minimum=512, maximum=65536, singleStep=512, value=2048, suffix=" MB")
        self.port = QSpinBox(minimum=0, maximum=65535, value=0)
        self.port.setSpecialValueText("Automático")
        self.eula = QCheckBox("Acepto el EULA de Minecraft")
        self.eula_link = QLabel('<a href="https://aka.ms/MinecraftEULA">Leer el EULA</a>')
        self.eula_link.setOpenExternalLinks(True)
        self.status = QLabel()
        self.status.setObjectName("muted")

        form = QFormLayout()
        form.addRow("Equipo", self.host_box)
        form.addRow("Nombre", self.name)
        form.addRow("Juego", self.game_box)
        form.addRow("Tipo", self.flavor_box)
        form.addRow("Versión", self.version_box)
        form.addRow("Memoria máxima", self.memory)
        form.addRow("Puerto", self.port)
        form.addRow(self.eula)
        form.addRow(self.eula_link)
        self.account_note = QLabel("Necesitas una cuenta del juego: al crear el servidor se abrirá una "
                                   "ventana para iniciar sesión con ella.")
        self.account_note.setWordWrap(True)
        self.account_note.setObjectName("accent")
        form.addRow(self.account_note)
        self.crossplay = QCheckBox("Multiplataforma: que también entren jugadores de Bedrock\n"
                                   "(móvil, consola, Windows) con Geyser")
        self.floodgate = QCheckBox("Sin necesitar cuenta de Java (Floodgate)")
        self.floodgate.setChecked(True)
        self.crossplay.toggled.connect(self.floodgate.setEnabled)
        self.floodgate.setEnabled(False)
        form.addRow(self.crossplay)
        form.addRow(self.floodgate)
        self.whitelist = QCheckBox("Solo pueden entrar los jugadores que añadas (lista blanca)")
        self.whitelist.setToolTip("Si la activas, añade a tus amigos en la pestaña Jugadores. "
                                  "Se puede cambiar cuando quieras.")
        form.addRow(self.whitelist)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Crear")
        self.want_modpack = False
        modpack = self.buttons.addButton("Desde un modpack...", QDialogButtonBox.ButtonRole.ActionRole)
        modpack.setToolTip("Importa un modpack de Modrinth (.mrpack) o de CurseForge (.zip)")
        modpack.clicked.connect(self._choose_modpack)
        self.buttons.accepted.connect(self._create)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addWidget(self.buttons)

        self.host_box.currentIndexChanged.connect(self._load_games)
        self.game_box.currentIndexChanged.connect(self._game_changed)
        self.flavor_box.currentIndexChanged.connect(self._load_versions)
        self.flavor_box.currentIndexChanged.connect(self._update_crossplay)
        self._load_games()

    def _client(self) -> AgentClient:
        return self.hosts[self.host_box.currentIndex()][1]

    def _game(self) -> dict | None:
        i = self.game_box.currentIndex()
        return self.games[i] if 0 <= i < len(self.games) else None

    def _load_games(self) -> None:
        self.status.setText("Cargando juegos...")

        def done(games):
            self.games = games
            self.game_box.blockSignals(True)
            self.game_box.clear()
            for g in games:
                self.game_box.addItem(g["name"], g["id"])
            self.game_box.blockSignals(False)
            self._game_changed()

        run_async(self._client().games, done, self.status.setText)

    def _game_changed(self) -> None:
        game = self._game()
        if not game:
            return
        self.flavor_box.blockSignals(True)
        self.flavor_box.clear()
        for f in game["flavors"]:
            self.flavor_box.addItem(f["name"], f["id"])
        self.flavor_box.blockSignals(False)
        self.eula.setVisible(game["needs_eula"])
        self.eula_link.setVisible(game["needs_eula"])
        self.account_note.setVisible(game.get("device_auth", False))
        self.whitelist.setVisible(game["id"] in ("minecraft", "bedrock"))
        self.memory.setValue(4096 if game["id"] == "hytale" else 2048)
        self._load_versions()
        self._update_crossplay()

    def _update_crossplay(self) -> None:
        # Geyser solo existe para Paper, Fabric y NeoForge.
        supported = self.flavor_box.currentData() in ("paper", "fabric", "neoforge")
        self.crossplay.setVisible(supported)
        self.floodgate.setVisible(supported)
        if not supported:
            self.crossplay.setChecked(False)
        # Sin hueco vacío abajo cuando se ocultan opciones
        QTimer.singleShot(0, lambda: self.resize(self.width(), self.sizeHint().height()))

    def _load_versions(self) -> None:
        game = self._game()
        flavor = self.flavor_box.currentData()
        if not game or not flavor:
            return
        self.version_box.clear()
        self.version_box.setEnabled(False)
        self.status.setText("Cargando versiones...")

        def done(versions):
            if (self._game() or {}).get("id") != game["id"] or self.flavor_box.currentData() != flavor:
                return  # el usuario cambió de opción mientras cargaba
            self.version_box.addItems(versions)
            self.version_box.setEnabled(True)
            self.status.setText("")

        run_async(lambda: self._client().versions(game["id"], flavor), done, self.status.setText)

    def _create(self) -> None:
        game = self._game()
        if not game or not self.version_box.currentText():
            return
        if game["needs_eula"] and not self.eula.isChecked():
            QMessageBox.warning(self, "EULA", "Para crear un servidor de Minecraft debes aceptar el EULA.")
            return
        body = {
            "name": self.name.text().strip() or f"{game['name']} {self.version_box.currentText()}",
            "game": game["id"],
            "flavor": self.flavor_box.currentData(),
            "version": self.version_box.currentText(),
            "memory_mb": self.memory.value(),
            "port": self.port.value() or None,
            "accept_eula": self.eula.isChecked(),
            "crossplay_enabled": self.crossplay.isChecked(),
            "floodgate": self.floodgate.isChecked(),
            "whitelist": self.whitelist.isChecked() and game["id"] in ("minecraft", "bedrock"),
        }
        self.buttons.setEnabled(False)
        self.status.setText("Creando...")

        def failed(msg: str):
            self.buttons.setEnabled(True)
            self.status.setText("")
            QMessageBox.warning(self, "No se pudo crear", msg)

        self.created_host_id = self.host_box.currentData()
        run_async(lambda: self._client().create(**body), self._done, failed)

    def _done(self, server: dict) -> None:
        self.created = server
        self.accept()

    def _choose_modpack(self) -> None:
        self.want_modpack = True
        self.reject()


class ImportModpackDialog(QDialog):
    """Crea un servidor a partir de un modpack de Modrinth (.mrpack) o CurseForge (.zip)."""

    def __init__(self, parent, hosts: list[tuple[Host, AgentClient]], selected_host_id: str | None):
        super().__init__(parent)
        self.setWindowTitle("Importar un modpack")
        self.setMinimumWidth(540)
        self.hosts = hosts
        self.host_box = QComboBox()
        for host, _ in hosts:
            self.host_box.addItem(host.name, host.id)
        if selected_host_id:
            self.host_box.setCurrentIndex(max(0, self.host_box.findData(selected_host_id)))
        self.path = QLineEdit()
        self.path.setPlaceholderText("Archivo .mrpack o .zip del modpack")
        browse = QPushButton("Elegir...")
        browse.clicked.connect(self._browse)
        file_row = QHBoxLayout()
        file_row.addWidget(self.path, 1)
        file_row.addWidget(browse)
        self.name = QLineEdit()
        self.name.setPlaceholderText("El del modpack")
        self.memory = QSpinBox(minimum=1024, maximum=65536, singleStep=512, value=4096, suffix=" MB")
        self.eula = QCheckBox("Acepto el EULA de Minecraft")
        eula_link = QLabel('<a href="https://aka.ms/MinecraftEULA">Leer el EULA</a>')
        eula_link.setOpenExternalLinks(True)
        self.whitelist = QCheckBox("Solo pueden entrar los jugadores que añadas (lista blanca)")
        help_text = QLabel("Descarga el modpack desde Modrinth (botón «Download» → .mrpack) o desde CurseForge "
                           "(el archivo .zip normal, no el «Server Pack»). Los mods que solo sirven para el "
                           "juego (shaders, minimapas...) se descartan solos. Para los de CurseForge hace falta "
                           "tu clave de API en Ajustes.")
        help_text.setWordWrap(True)
        help_text.setObjectName("muted")
        self.status = QLabel()
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Equipo", self.host_box)
        form.addRow("Modpack", file_row)
        form.addRow("Nombre", self.name)
        form.addRow("Memoria máxima", self.memory)
        form.addRow(self.eula)
        form.addRow(eula_link)
        form.addRow(self.whitelist)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importar")
        self.buttons.accepted.connect(self._import)
        self.buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(help_text)
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addWidget(self.buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Elegir modpack", str(Path.home() / "Downloads"),
                                              "Modpacks (*.mrpack *.zip)")
        if path:
            self.path.setText(str(Path(path)))

    def _import(self) -> None:
        archive = Path(self.path.text().strip().strip('"'))
        if not archive.is_file():
            QMessageBox.warning(self, "Modpack", "Elige el archivo del modpack.")
            return
        if not self.eula.isChecked():
            QMessageBox.warning(self, "EULA", "Para crear un servidor de Minecraft debes aceptar el EULA.")
            return
        client = self.hosts[self.host_box.currentIndex()][1]
        self.created_host_id = self.host_box.currentData()
        params = {"memory_mb": self.memory.value(), "accept_eula": "true",
                  "whitelist": str(self.whitelist.isChecked()).lower()}
        if self.name.text().strip():
            params["name"] = self.name.text().strip()
        total_mb = archive.stat().st_size / (1 << 20)
        cf_key = curseforge_key()
        self.buttons.setEnabled(False)

        def upload(progress):
            return client.import_modpack(archive, lambda n: progress(
                f"Enviando el modpack... {n / (1 << 20):.1f} / {total_mb:.1f} MB"), cf_key, **params)

        def done(server: dict):
            self.created = server
            self.accept()

        def failed(msg: str):
            self.buttons.setEnabled(True)
            self.status.setText("")
            QMessageBox.warning(self, "No se pudo importar", msg)

        run_with_progress(upload, self.status.setText, done, failed)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        self.setMinimumWidth(460)
        self.settings = load_settings()
        self.cf_key = QLineEdit(self.settings.get("curseforge_key", ""))
        self.cf_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        help_text = QLabel(
            "Modrinth funciona sin configurar nada. Para buscar en <b>CurseForge</b> hace falta una "
            "clave de API gratuita: entra en "
            '<a href="https://console.curseforge.com/">console.curseforge.com</a>, inicia sesión y '
            "copia la clave de la sección «API keys».")
        help_text.setWordWrap(True)
        help_text.setOpenExternalLinks(True)
        form = QFormLayout()
        form.addRow("Clave de CurseForge", self.cf_key)
        self.check_updates = QCheckBox("Buscar versiones nuevas de Ownhost al abrir la app")
        self.check_updates.setChecked(self.settings.get("check_updates", True))
        self.check_now = QPushButton("Buscar ahora")
        updates_row = QHBoxLayout()
        updates_row.addWidget(self.check_updates, 1)
        updates_row.addWidget(self.check_now)
        if embedded_curseforge_key():
            self.cf_key.setPlaceholderText("Incluida en la app (opcional: pon aquí la tuya)")
            help_text.setText("CurseForge y Modrinth ya funcionan: esta versión de la app incluye una clave "
                              "de CurseForge. Solo necesitas rellenar el campo si quieres usar la tuya.")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(help_text)
        layout.addLayout(form)
        layout.addSpacing(8)
        layout.addLayout(updates_row)
        layout.addWidget(buttons)

    def _save(self) -> None:
        self.settings["curseforge_key"] = self.cf_key.text().strip()
        self.settings["check_updates"] = self.check_updates.isChecked()
        save_settings(self.settings)
        self.accept()


class MoveDialog(QDialog):
    """Elegir a qué equipo mover un servidor."""

    def __init__(self, parent, server: dict, targets: list[tuple[Host, AgentClient]]):
        super().__init__(parent)
        self.setWindowTitle("Mover a otro equipo")
        self.targets = targets
        self.target_box = QComboBox()
        for host, _ in targets:
            self.target_box.addItem(f"{host.name} ({host.address})")
        self.delete_original = QCheckBox("Borrar el servidor de este equipo cuando termine")
        text = QLabel(
            f"Se apagará «{server['name']}», se hará una copia de seguridad y se instalará en el "
            "equipo elegido con la misma versión, el mundo, la configuración y los mods.<br><br>"
            "Si no marcas la casilla, el original se queda aquí apagado por si algo falla.")
        text.setWordWrap(True)
        form = QFormLayout()
        form.addRow("Destino", self.target_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Mover")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(text)
        layout.addLayout(form)
        layout.addWidget(self.delete_original)
        layout.addWidget(buttons)

    def target(self) -> tuple[Host, AgentClient]:
        return self.targets[self.target_box.currentIndex()]


class ImportWorldDialog(QDialog):
    """Elegir un mundo (carpeta o .zip) para sustituir el del servidor."""

    def __init__(self, parent, server: dict):
        super().__init__(parent)
        self.setWindowTitle("Importar un mundo")
        self.setMinimumWidth(520)
        self.server = server
        self.source: WorldSource | None = None

        intro = QLabel(
            f"El mundo elegido sustituirá al de <b>{server['name']}</b> "
            f"(Minecraft {server['version']}). Antes se hará una copia de seguridad del actual.<br>"
            "Usa un mundo de la misma versión de Minecraft o anterior; uno más nuevo no cargará.")
        intro.setWordWrap(True)
        self.path = QLineEdit()
        self.path.setReadOnly(True)
        self.path.setPlaceholderText("Ningún mundo elegido")
        pick_folder = QPushButton("Carpeta del mundo...")
        pick_folder.clicked.connect(self._pick_folder)
        pick_zip = QPushButton("Archivo .zip...")
        pick_zip.clicked.connect(self._pick_zip)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.include_mods = QCheckBox()
        self.include_mods.setVisible(False)

        row = QHBoxLayout()
        row.addWidget(self.path, 1)
        row.addWidget(pick_folder)
        row.addWidget(pick_zip)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Importar")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self._cancel)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(row)
        layout.addWidget(self.info)
        layout.addWidget(self.include_mods)
        layout.addWidget(self.buttons)
        # Que el diálogo crezca cuando las etiquetas con texto largo ocupan más líneas.
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinimumSize)

    def _start_dir(self) -> str:
        saves = default_saves_dir()
        return str(saves if saves.exists() else Path.home())

    def _pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Carpeta del mundo (la que contiene level.dat)",
                                                self._start_dir())
        if path:
            self._load(Path(path))

    def _pick_zip(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Mundo en .zip", str(Path.home() / "Downloads"),
                                              "Archivo zip (*.zip)")
        if path:
            self._load(Path(path))

    def _load(self, path: Path) -> None:
        if self.source:
            self.source.cleanup()
            self.source = None
        self.path.setText(str(path))
        self.info.setText("Analizando...")
        self.include_mods.setVisible(False)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        run_async(lambda: inspect_world(path), self._loaded,
                  lambda msg: self.info.setText(f"<span style='color:#ff9a8f'>{msg}</span>"))

    def _loaded(self, source: WorldSource) -> None:
        self.source = source
        lines = [f"Mundo encontrado: <b>{source.world.name}</b>"]
        server_has_mods = bool(self.server.get("mods_label"))
        if source.instance and (source.mods or source.config):
            lines.append(f"Viene de la instancia «{source.instance.name}», que tiene {len(source.mods)} mods.")
            self.include_mods.setText("Copiar también sus mods y su configuración (sustituyen a los actuales)")
            self.include_mods.setVisible(True)
            self.include_mods.setChecked(server_has_mods)
            self.include_mods.setEnabled(server_has_mods)
            if not server_has_mods:
                lines.append("El mundo viene de una instancia con mods, pero este servidor no admite mods: "
                             "crea uno Fabric, Forge o NeoForge con la misma versión.")
            if source.client_only:
                lines.append(f"Se omiten {len(source.client_only)} mods que solo funcionan en el cliente "
                             f"({', '.join(source.client_only[:4])}{'...' if len(source.client_only) > 4 else ''}).")
        self.info.setText("<br>".join(lines))
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        self.adjustSize()

    def _cancel(self) -> None:
        if self.source:
            self.source.cleanup()
        self.reject()


class AccountLoginDialog(QDialog):
    """Ventana para iniciar sesión con la cuenta del juego (Hytale) mediante un código."""

    def __init__(self, parent, server_name: str, game_name: str):
        super().__init__(parent)
        self.setWindowTitle(f"Iniciar sesión en {game_name}")
        self.setMinimumWidth(460)
        self.url = ""
        self.code = ""
        self.explanation = QLabel()
        self.explanation.setWordWrap(True)
        self.server_name = server_name
        self.game_name = game_name

        self.code_label = QLabel()
        font = self.code_label.font()
        font.setPointSize(font.pointSize() + 12)
        font.setBold(True)
        font.setLetterSpacing(font.SpacingType.AbsoluteSpacing, 3)
        self.code_label.setFont(font)
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.open_btn = QPushButton("Abrir página de inicio de sesión")
        self.open_btn.setDefault(True)
        self.open_btn.clicked.connect(self._open)
        self.copy_btn = QPushButton("Copiar código")
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.code))
        waiting = QLabel("Esperando a que inicies sesión... Esta ventana se cerrará sola.")
        waiting.setObjectName("muted")

        row = QHBoxLayout()
        row.addWidget(self.open_btn)
        row.addWidget(self.copy_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(self.explanation)
        layout.addWidget(self.code_label)
        layout.addLayout(row)
        layout.addWidget(waiting)

    def set_auth(self, auth: dict) -> None:
        self.url, self.code = auth["url"], auth.get("code") or ""
        self.kind = auth.get("kind", "game")
        if self.kind == "xbox":
            self.setWindowTitle("Iniciar sesión con Microsoft (amigos de Xbox)")
            self.explanation.setText(
                f"El servidor <b>{self.server_name}</b> va a aparecer en la pestaña Amigos de las consolas.<br>"
                "Para eso necesita una <b>cuenta de Microsoft secundaria</b> (no uses la tuya).<br><br>"
                "1. Pulsa <b>Abrir página de inicio de sesión</b>.<br>"
                "2. Introduce este código y entra con la cuenta secundaria:")
        else:
            purpose = ("descargar los archivos del juego" if auth.get("source") == "downloader"
                       else "que el servidor pueda aceptar jugadores")
            self.explanation.setText(
                f"El servidor <b>{self.server_name}</b> necesita tu cuenta de {self.game_name} para {purpose}.<br><br>"
                "1. Pulsa <b>Abrir página de inicio de sesión</b>.<br>"
                "2. Entra con tu cuenta e introduce este código si te lo pide:")
        self.code_label.setText(self.code or "(el código aparece en la página)")
        self.copy_btn.setEnabled(bool(self.code))

    def _open(self) -> None:
        url = self.url
        if self.code and "user_code=" not in url and getattr(self, "kind", "game") != "xbox":
            url += ("&" if "?" in url else "?") + f"user_code={self.code}"
        QDesktopServices.openUrl(QUrl(url))


def ask_version(parent, versions: list[str], current: str) -> str | None:
    index = versions.index(current) if current in versions else 0
    version, ok = QInputDialog.getItem(
        parent, "Actualizar servidor",
        "Versión (elegir la misma descarga la última build de esa versión).\n"
        "Se hará una copia de seguridad antes de actualizar.",
        versions, index, False, Qt.WindowType.Dialog,
    )
    return version if ok else None
