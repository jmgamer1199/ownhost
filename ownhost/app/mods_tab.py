from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from ownhost.app.client import AgentClient
from ownhost.app.settings import curseforge_key
from ownhost.app.tasks import run_async
from ownhost.i18n import tr

SOURCES = [("modrinth", "Modrinth"), ("curseforge", "CurseForge")]


SOURCE_NAMES = {"modrinth": "Modrinth", "curseforge": "CurseForge", "modpack": "Modpack"}


def _table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.horizontalHeader().setStretchLastSection(True)
    t.setMinimumHeight(56)  # header and one row: so the window fits on laptop screens
    return t


def _format_downloads(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n / 1_000:.0f} k"
    return str(n)


class ModsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: AgentClient | None = None
        self.server: dict | None = None
        self.results: list[dict] = []
        self.installed: list[dict] = []
        self.reload_when_idle = False

        # --- installed ---
        self.installed_title = QLabel()
        self.installed_table = _table([tr("Nombre"), tr("Versión"), tr("Origen"), tr("Estado")])
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.installed_table.horizontalHeader().setStretchLastSection(False)
        self.btn_toggle = QPushButton(tr("Activar / desactivar"))
        self.btn_toggle.clicked.connect(self._toggle)
        self.btn_remove = QPushButton(tr("Eliminar"))
        self.btn_remove.clicked.connect(self._remove)
        self.btn_updates = QPushButton(tr("Buscar actualizaciones"))
        self.btn_updates.setToolTip(tr("Busca versiones nuevas de los mods para esta versión de Minecraft"))
        self.btn_updates.clicked.connect(self._check_updates)
        note = QLabel(tr("Reinicia el servidor para aplicar los cambios."))
        note.setObjectName("muted")
        row = QHBoxLayout()
        row.addWidget(note, 1)
        row.addWidget(self.btn_updates)
        row.addWidget(self.btn_toggle)
        row.addWidget(self.btn_remove)
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self.installed_title)
        top_layout.addWidget(self.installed_table, 1)
        top_layout.addLayout(row)

        # --- search ---
        self.source = QComboBox()
        for key, label in SOURCES:
            self.source.addItem(tr(label), key)
        self.query = QLineEdit()
        self.query.setPlaceholderText(tr("Buscar (déjalo vacío para ver los más populares)"))
        self.query.returnPressed.connect(self._search)
        search_btn = QPushButton(tr("Buscar"))
        search_btn.clicked.connect(self._search)
        search_row = QHBoxLayout()
        search_row.addWidget(self.source)
        search_row.addWidget(self.query, 1)
        search_row.addWidget(search_btn)
        self.results_table = _table([tr("Nombre"), tr("Autor"), tr("Descargas"), tr("Descripción")])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.doubleClicked.connect(self._install)
        self.search_status = QLabel()
        self.search_status.setObjectName("muted")
        self.btn_page = QPushButton(tr("Ver en la web"))
        self.btn_page.clicked.connect(self._open_page)
        self.btn_install = QPushButton(tr("Instalar"))
        self.btn_install.clicked.connect(self._install)
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.search_status, 1)
        bottom_row.addWidget(self.btn_page)
        bottom_row.addWidget(self.btn_install)
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(QLabel(tr("<b>Buscar e instalar</b>")))
        bottom_layout.addLayout(search_row)
        bottom_layout.addWidget(self.results_table, 1)
        bottom_layout.addLayout(bottom_row)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setSizes([200, 400])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def set_server(self, client: AgentClient, server: dict) -> None:
        changed = not self.server or self.server["id"] != server["id"] or self.client is not client
        self.client, self.server = client, server
        if changed:
            self.reload_when_idle = False
            label = server.get("mods_label") or "Mods"
            self.installed_title.setText(tr("<b>{label} instalados</b>", label=label))
            # Hytale only has mods on CurseForge; Minecraft, on both.
            sources = server.get("mod_sources") or [key for key, _ in SOURCES]
            self.source.blockSignals(True)
            self.source.clear()
            for key, name in SOURCES:
                if key in sources:
                    self.source.addItem(tr(name), key)
            self.source.blockSignals(False)
            self.results_table.setRowCount(0)
            self.results = []
            self.search_status.setText("")

    def activate(self) -> None:
        """Called when the tab is opened."""
        self.reload()
        if not self.results and (self.source.currentData() != "curseforge" or curseforge_key()):
            self._search()

    def _error(self, msg: str) -> None:
        QMessageBox.warning(self, tr("Error"), msg)

    # ---------- installed ----------

    def reload(self) -> None:
        sid, client = self.server["id"], self.client

        def done(mods: list):
            self.installed = mods
            t = self.installed_table
            t.setRowCount(0)
            for m in mods:
                row = t.rowCount()
                t.insertRow(row)
                t.setItem(row, 0, QTableWidgetItem(m["title"]))
                t.setItem(row, 1, QTableWidgetItem(m["version"]))
                t.setItem(row, 2, QTableWidgetItem(tr(SOURCE_NAMES.get(m["source"], "Manual"))))
                t.setItem(row, 3, QTableWidgetItem(tr("Activo") if m["enabled"] else tr("Desactivado")))

        run_async(lambda: client.mods(sid), done, self._error)

    def _selected_installed(self) -> dict | None:
        rows = self.installed_table.selectionModel().selectedRows()
        return self.installed[rows[0].row()] if rows else None

    def _toggle(self) -> None:
        mod = self._selected_installed()
        if not mod:
            return
        sid, client = self.server["id"], self.client
        run_async(lambda: client.toggle_mod(sid, mod["filename"], not mod["enabled"]),
                  lambda _: self.reload(), self._error)

    def _remove(self) -> None:
        mod = self._selected_installed()
        if not mod:
            return
        if QMessageBox.question(self, tr("Eliminar"), tr("¿Eliminar «{title}»?", title=mod["title"])) != QMessageBox.StandardButton.Yes:
            return
        sid, client = self.server["id"], self.client
        run_async(lambda: client.remove_mod(sid, mod["filename"]), lambda _: self.reload(), self._error)

    def _check_updates(self) -> None:
        sid, client, cf_key = self.server["id"], self.client, curseforge_key()
        self.btn_updates.setEnabled(False)
        self.btn_updates.setText(tr("Buscando..."))

        def done(updates: list):
            self._updates_found(updates)

        def failed(msg: str):
            self._updates_found(None)
            self._error(msg)

        run_async(lambda: client.mod_updates(sid, cf_key), done, failed)

    def _updates_found(self, updates: list | None) -> None:
        self.btn_updates.setEnabled(True)
        self.btn_updates.setText(tr("Buscar actualizaciones"))
        if updates is None:
            return
        if not updates and self.server.get("mod_sources") == ["curseforge"] and not curseforge_key():
            QMessageBox.information(self, tr("Actualizaciones"), tr(
                "Para buscar actualizaciones de estos mods hace falta tu clave de API de CurseForge (gratuita). "
                "Ponla en Ajustes."))
            return
        if not updates:
            QMessageBox.information(self, tr("Actualizaciones"), tr("Todo está al día.") + (
                "" if curseforge_key() else "\n\n" + tr("(Los mods de CurseForge solo se comprueban si pones tu "
                                                         "clave de API en Ajustes.)")))
            return
        dialog = UpdatesDialog(self, updates)
        if not dialog.exec() or not dialog.chosen():
            return
        sid, client, cf_key, chosen = self.server["id"], self.client, curseforge_key(), dialog.chosen()
        def started(_):
            # The list reloads when the agent finishes (the window's polling notices it).
            self.reload_when_idle = True
            text = (tr("Actualizando 1 mod: primero se hace una copia de seguridad. Mira la consola.")
                    if len(chosen) == 1 else
                    tr("Actualizando {count} mods: primero se hace una copia de seguridad. Mira la consola.",
                       count=len(chosen)))
            self.window().statusBar().showMessage(text, 10000)

        run_async(lambda: client.update_mods(sid, chosen, cf_key), started, self._error)

    # ---------- search ----------

    def _search(self) -> None:
        if not self.server:
            return
        sid, client = self.server["id"], self.client
        source, query = self.source.currentData(), self.query.text().strip()
        cf_key = curseforge_key()
        self.search_status.setText(tr("Buscando..."))

        def done(results: list):
            self.results = results
            t = self.results_table
            t.setRowCount(0)
            for r in results:
                row = t.rowCount()
                t.insertRow(row)
                t.setItem(row, 0, QTableWidgetItem(r["title"]))
                t.setItem(row, 1, QTableWidgetItem(r["author"]))
                downloads = QTableWidgetItem(_format_downloads(r["downloads"]))
                downloads.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                t.setItem(row, 2, downloads)
                desc = QTableWidgetItem(r["description"])
                desc.setToolTip(r["description"])
                t.setItem(row, 3, desc)
            version = self.server["version"]
            self.search_status.setText(
                tr("{count} resultados compatibles con {version}. Doble clic para instalar.",
                   count=len(results), version=version) if results else
                tr("Nada compatible con {version}.", version=version))

        def failed(msg: str):
            self.search_status.setText("")
            self._error(msg)

        run_async(lambda: client.search_mods(sid, source, query, cf_key), done, failed)

    def _selected_result(self) -> dict | None:
        rows = self.results_table.selectionModel().selectedRows()
        return self.results[rows[0].row()] if rows else None

    def _open_page(self) -> None:
        r = self._selected_result()
        if r and r["url"]:
            QDesktopServices.openUrl(QUrl(r["url"]))

    def _install(self) -> None:
        r = self._selected_result()
        if not r:
            return
        sid, client = self.server["id"], self.client
        source, cf_key = self.source.currentData(), curseforge_key()
        self.btn_install.setEnabled(False)
        self.search_status.setText(tr("Instalando {title}...", title=r["title"]))

        def done(added: list):
            self.btn_install.setEnabled(True)
            self.search_status.setText(tr("Instalado: {names}", names=", ".join(added)) if added
                                       else tr("Ya estaba instalado."))
            self.reload()

        def failed(msg: str):
            self.btn_install.setEnabled(True)
            self.search_status.setText("")
            self._error(msg)

        run_async(lambda: client.install_mod(sid, source, r["id"], cf_key), done, failed)


class UpdatesDialog(QDialog):
    """List of mods with a new version, to choose which ones to update."""

    def __init__(self, parent, updates: list[dict]):
        super().__init__(parent)
        self.setWindowTitle(tr("Actualizaciones de mods"))
        self.setMinimumSize(560, 360)
        self.updates = updates
        self.list = QListWidget()
        for u in updates:
            current = u["current"] or u["filename"]
            item = QListWidgetItem(f"{u['title']}:  {current}  →  {u['latest']}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)
        note = QLabel(tr("Antes de actualizar se hace una copia de seguridad del servidor. El servidor tiene que "
                         "estar apagado."))
        note.setObjectName("muted")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Actualizar"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr("<b>Hay 1 mod con versión nueva</b>") if len(updates) == 1 else
                                tr("<b>Hay {count} mods con versión nueva</b>", count=len(updates))))
        layout.addWidget(self.list, 1)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def chosen(self) -> list[str]:
        return [u["filename"] for i, u in enumerate(self.updates)
                if self.list.item(i).checkState() == Qt.CheckState.Checked]
