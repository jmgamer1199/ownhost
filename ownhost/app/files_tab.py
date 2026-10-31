"""“Files” tab: edit the mod and plugin configuration without opening the server folder."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async
from ownhost.i18n import tr

PATH = Qt.ItemDataRole.UserRole
IS_DIR = Qt.ItemDataRole.UserRole + 1


class FilesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client: AgentClient | None = None
        self.server: dict | None = None
        self.current: str | None = None
        self.saved_text = ""

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(200)
        self.tree.itemExpanded.connect(self._expand)
        self.tree.itemClicked.connect(self._open)

        self.title = QLabel(tr("Elige un archivo de la izquierda"))
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("console")
        self.editor.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.editor.setEnabled(False)
        self.editor.textChanged.connect(self._changed)
        self.save_btn = QPushButton(tr("Guardar"))
        self.save_btn.setProperty("kind", "primary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save)
        reload_btn = QPushButton(tr("Recargar"))
        reload_btn.clicked.connect(self.reload)
        note = QLabel(tr("Configuración de mods, plugins y del servidor. Reinicia el servidor para aplicar los cambios."))
        note.setObjectName("muted")
        note.setWordWrap(True)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(self.title)
        rl.addWidget(self.editor, 1)
        row = QHBoxLayout()
        row.addWidget(note, 1)
        row.addWidget(reload_btn)
        row.addWidget(self.save_btn)
        rl.addLayout(row)
        splitter = QSplitter()
        splitter.addWidget(self.tree)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([240, 600])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def set_server(self, client: AgentClient, server: dict) -> None:
        if self.server and self.server["id"] == server["id"] and self.client is client:
            return
        self.client, self.server = client, server
        self.tree.clear()
        self._close_file()

    def activate(self) -> None:
        if not self.tree.topLevelItemCount():
            self.reload()

    def reload(self) -> None:
        if self.current and self.editor.toPlainText() != self.saved_text and QMessageBox.question(
                self, tr("Archivos"), tr("Hay cambios sin guardar. ¿Descartarlos?")) != QMessageBox.StandardButton.Yes:
            return
        self.tree.clear()
        self._close_file()
        self._load_dir(None, "")

    def _load_dir(self, parent: QTreeWidgetItem | None, path: str) -> None:
        sid, client = self.server["id"], self.client

        def done(entries: list[dict]):
            if parent is not None:
                parent.takeChildren()
            for e in entries:
                item = QTreeWidgetItem([("📁 " if e["dir"] else "") + e["name"]])
                item.setData(0, PATH, f"{path}/{e['name']}".lstrip("/"))
                item.setData(0, IS_DIR, e["dir"])
                if e["dir"]:
                    item.addChild(QTreeWidgetItem(["..."]))  # loaded when expanded
                (parent.addChild if parent is not None else self.tree.addTopLevelItem)(item)
            if parent is None and not entries:
                self.title.setText(tr("Este servidor aún no tiene archivos de configuración (se crean al encenderlo)."))

        run_async(lambda: client.files(sid, path), done, lambda msg: QMessageBox.warning(self, tr("Archivos"), msg))

    def _expand(self, item: QTreeWidgetItem) -> None:
        if item.childCount() == 1 and item.child(0).data(0, PATH) is None:
            self._load_dir(item, item.data(0, PATH))

    def _open(self, item: QTreeWidgetItem) -> None:
        if item.data(0, IS_DIR) or item.data(0, PATH) is None:
            return
        path = item.data(0, PATH)
        if self.current and self.editor.toPlainText() != self.saved_text and QMessageBox.question(
                self, tr("Archivos"), tr("Hay cambios sin guardar. ¿Descartarlos?")) != QMessageBox.StandardButton.Yes:
            return
        sid, client = self.server["id"], self.client

        def done(content: str):
            self.current, self.saved_text = path, content
            self.editor.blockSignals(True)
            self.editor.setPlainText(content)
            self.editor.blockSignals(False)
            self.editor.setEnabled(True)
            self._changed()

        run_async(lambda: client.read_file(sid, path), done, lambda msg: QMessageBox.warning(self, tr("Archivos"), msg))

    def _changed(self) -> None:
        dirty = bool(self.current) and self.editor.toPlainText() != self.saved_text
        self.save_btn.setEnabled(dirty)
        if self.current:
            self.title.setText(f"<b>{self.current}</b>" + ("  · " + tr("sin guardar") if dirty else ""))

    def _save(self) -> None:
        sid, client, path, text = self.server["id"], self.client, self.current, self.editor.toPlainText()

        def done(_):
            self.saved_text = text
            self._changed()
            self.window().statusBar().showMessage(tr("Guardado {path}. Reinicia el servidor para aplicarlo.", path=path), 8000)

        run_async(lambda: client.write_file(sid, path, text), done,
                  lambda msg: QMessageBox.warning(self, tr("No se pudo guardar"), msg))

    def _close_file(self) -> None:
        self.current, self.saved_text = None, ""
        self.editor.blockSignals(True)
        self.editor.clear()
        self.editor.blockSignals(False)
        self.editor.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.title.setText(tr("Elige un archivo de la izquierda"))
