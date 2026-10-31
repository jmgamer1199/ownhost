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

        # --- instalados ---
        self.installed_title = QLabel()
        self.installed_table = _table(["Nombre", "Versión", "Origen", "Estado"])
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.installed_table.horizontalHeader().setStretchLastSection(False)
        self.btn_toggle = QPushButton("Activar / desactivar")
        self.btn_toggle.clicked.connect(self._toggle)
        self.btn_remove = QPushButton("Eliminar")
        self.btn_remove.clicked.connect(self._remove)
        self.btn_updates = QPushButton("Buscar actualizaciones")
        self.btn_updates.setToolTip("Busca versiones nuevas de los mods para esta versión de Minecraft")
        self.btn_updates.clicked.connect(self._check_updates)
        note = QLabel("Reinicia el servidor para aplicar los cambios.")
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

        # --- buscador ---
        self.source = QComboBox()
        for key, label in SOURCES:
            self.source.addItem(label, key)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Buscar (déjalo vacío para ver los más populares)")
        self.query.returnPressed.connect(self._search)
        search_btn = QPushButton("Buscar")
        search_btn.clicked.connect(self._search)
        search_row = QHBoxLayout()
        search_row.addWidget(self.source)
        search_row.addWidget(self.query, 1)
        search_row.addWidget(search_btn)
        self.results_table = _table(["Nombre", "Autor", "Descargas", "Descripción"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.doubleClicked.connect(self._install)
        self.search_status = QLabel()
        self.search_status.setObjectName("muted")
        self.btn_page = QPushButton("Ver en la web")
        self.btn_page.clicked.connect(self._open_page)
        self.btn_install = QPushButton("Instalar")
        self.btn_install.clicked.connect(self._install)
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.search_status, 1)
        bottom_row.addWidget(self.btn_page)
        bottom_row.addWidget(self.btn_install)
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addWidget(QLabel("<b>Buscar e instalar</b>"))
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
            self.installed_title.setText(f"<b>{label} instalados</b>")
            # Hytale solo tiene mods en CurseForge; Minecraft, en los dos.
            sources = server.get("mod_sources") or [key for key, _ in SOURCES]
            self.source.blockSignals(True)
            self.source.clear()
            for key, name in SOURCES:
                if key in sources:
                    self.source.addItem(name, key)
            self.source.blockSignals(False)
            self.results_table.setRowCount(0)
            self.results = []
            self.search_status.setText("")

    def activate(self) -> None:
        """Se llama al abrir la pestaña."""
        self.reload()
        if not self.results and (self.source.currentData() != "curseforge" or curseforge_key()):
            self._search()

    def _error(self, msg: str) -> None:
        QMessageBox.warning(self, "Error", msg)

    # ---------- instalados ----------

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
                t.setItem(row, 2, QTableWidgetItem(SOURCE_NAMES.get(m["source"], "Manual")))
                t.setItem(row, 3, QTableWidgetItem("Activo" if m["enabled"] else "Desactivado"))

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
        if QMessageBox.question(self, "Eliminar", f"¿Eliminar «{mod['title']}»?") != QMessageBox.StandardButton.Yes:
            return
        sid, client = self.server["id"], self.client
        run_async(lambda: client.remove_mod(sid, mod["filename"]), lambda _: self.reload(), self._error)

    def _check_updates(self) -> None:
        sid, client, cf_key = self.server["id"], self.client, curseforge_key()
        self.btn_updates.setEnabled(False)
        self.btn_updates.setText("Buscando...")

        def done(updates: list):
            self._updates_found(updates)

        def failed(msg: str):
            self._updates_found(None)
            self._error(msg)

        run_async(lambda: client.mod_updates(sid, cf_key), done, failed)

    def _updates_found(self, updates: list | None) -> None:
        self.btn_updates.setEnabled(True)
        self.btn_updates.setText("Buscar actualizaciones")
        if updates is None:
            return
        if not updates and self.server.get("mod_sources") == ["curseforge"] and not curseforge_key():
            QMessageBox.information(self, "Actualizaciones", "Para buscar actualizaciones de estos mods hace "
                                    "falta tu clave de API de CurseForge (gratuita). Ponla en Ajustes.")
            return
        if not updates:
            QMessageBox.information(self, "Actualizaciones", "Todo está al día." + (
                "" if curseforge_key() else "\n\n(Los mods de CurseForge solo se comprueban si pones tu "
                                            "clave de API en Ajustes.)"))
            return
        dialog = UpdatesDialog(self, updates)
        if not dialog.exec() or not dialog.chosen():
            return
        sid, client, cf_key, chosen = self.server["id"], self.client, curseforge_key(), dialog.chosen()
        def started(_):
            # La lista se recarga cuando el agente termine (lo ve el sondeo de la ventana).
            self.reload_when_idle = True
            count = "1 mod" if len(chosen) == 1 else f"{len(chosen)} mods"
            self.window().statusBar().showMessage(
                f"Actualizando {count}: primero se hace una copia de seguridad. Mira la consola.", 10000)

        run_async(lambda: client.update_mods(sid, chosen, cf_key), started, self._error)

    # ---------- buscador ----------

    def _search(self) -> None:
        if not self.server:
            return
        sid, client = self.server["id"], self.client
        source, query = self.source.currentData(), self.query.text().strip()
        cf_key = curseforge_key()
        self.search_status.setText("Buscando...")

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
            self.search_status.setText(f"{len(results)} resultados compatibles con {version}. "
                                       "Doble clic para instalar." if results else
                                       f"Nada compatible con {version}.")

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
        self.search_status.setText(f"Instalando {r['title']}...")

        def done(added: list):
            self.btn_install.setEnabled(True)
            self.search_status.setText(f"Instalado: {', '.join(added)}" if added else "Ya estaba instalado.")
            self.reload()

        def failed(msg: str):
            self.btn_install.setEnabled(True)
            self.search_status.setText("")
            self._error(msg)

        run_async(lambda: client.install_mod(sid, source, r["id"], cf_key), done, failed)


class UpdatesDialog(QDialog):
    """Lista de mods con versión nueva, para elegir cuáles actualizar."""

    def __init__(self, parent, updates: list[dict]):
        super().__init__(parent)
        self.setWindowTitle("Actualizaciones de mods")
        self.setMinimumSize(560, 360)
        self.updates = updates
        self.list = QListWidget()
        for u in updates:
            current = u["current"] or u["filename"]
            item = QListWidgetItem(f"{u['title']}:  {current}  →  {u['latest']}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(item)
        note = QLabel("Antes de actualizar se hace una copia de seguridad del servidor. El servidor tiene que "
                      "estar apagado.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Actualizar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        count = "Hay 1 mod" if len(updates) == 1 else f"Hay {len(updates)} mods"
        layout.addWidget(QLabel(f"<b>{count} con versión nueva</b>"))
        layout.addWidget(self.list, 1)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def chosen(self) -> list[str]:
        return [u["filename"] for i, u in enumerate(self.updates)
                if self.list.item(i).checkState() == Qt.CheckState.Checked]
