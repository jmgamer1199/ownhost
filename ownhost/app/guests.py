"""Friend access: codes with limited permissions so others can manage your servers."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async
from ownhost.i18n import tr

# Permission levels (the same as in the agent). Each one includes the previous ones.
# The texts are the Spanish keys: they are translated with tr() where they are shown.
PLAY, MODERATE, MANAGE, OWNER = 1, 2, 3, 9
ROLES = [
    ("play", "Encender y apagar",
     "Ve sus servidores y quién está jugando, y puede encenderlos, apagarlos y reiniciarlos."),
    ("moderate", "Moderar",
     "Lo anterior, y además la consola, los jugadores (operadores, lista blanca, baneos) y hacer copias "
     "de seguridad."),
    ("manage", "Gestionar",
     "Lo anterior, y además los ajustes, las propiedades, los mods, actualizar, restaurar copias e importar "
     "mundos. No puede borrar servidores, crear otros ni ver tu carpeta."),
]
ROLE_NAMES = {key: name for key, name, _ in ROLES} | {"owner": "Dueño", "backup": "Recibir copias (otro equipo)"}


def access_level(info: dict | None) -> int:
    """Level the app is connected to a computer with (old agents don't say: owner)."""
    return ((info or {}).get("access") or {}).get("level", OWNER)


class GuestsDialog(QDialog):
    def __init__(self, parent, client: AgentClient, host_name: str, servers: list[dict],
                 addresses: list[tuple[str, str]], port: int):
        super().__init__(parent)
        self.setWindowTitle(tr("Accesos para amigos · {host}", host=host_name))
        self.setMinimumSize(620, 380)
        self.client, self.servers, self.addresses, self.port = client, servers, addresses, port
        self.guests: list[dict] = []

        intro = QLabel(tr("Dale a cada amigo su propio código para que encienda o gestione tus servidores desde su "
                          "Ownhost o desde el navegador del móvil, sin darle tu token. Puedes quitarle el acceso "
                          "cuando quieras."))
        intro.setWordWrap(True)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([tr("Nombre"), tr("Permiso"), tr("Servidores")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.empty = QLabel(tr("Todavía no has dado acceso a nadie."))
        self.empty.setObjectName("muted")

        new = QPushButton(tr("Nuevo acceso..."))
        new.setProperty("kind", "primary")
        new.clicked.connect(self._new)
        self.remove = QPushButton(tr("Quitar acceso"))
        self.remove.setProperty("kind", "danger")
        self.remove.clicked.connect(self._remove)
        close = QPushButton(tr("Cerrar"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addWidget(new)
        row.addWidget(self.remove)
        row.addStretch()
        row.addWidget(close)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.empty)
        layout.addLayout(row)
        self._load()

    def _load(self) -> None:
        run_async(self.client.guests, self._loaded, lambda msg: QMessageBox.warning(self, tr("Accesos"), msg))

    def _loaded(self, guests: list[dict]) -> None:
        self.guests = guests
        names = {s["id"]: s["name"] for s in self.servers}
        self.table.setRowCount(0)
        for g in guests:
            row = self.table.rowCount()
            self.table.insertRow(row)
            servers = (tr("Todos") if g["servers"] is None else
                       ", ".join(names.get(sid, tr("(borrado)")) for sid in g["servers"]) or tr("Ninguno"))
            for col, text in enumerate((g["name"], tr(ROLE_NAMES.get(g["role"], g["role"])), servers)):
                self.table.setItem(row, col, QTableWidgetItem(text))
        self.empty.setVisible(not guests)
        self.remove.setEnabled(bool(guests))

    def _new(self) -> None:
        dialog = NewGuestDialog(self, self.servers)
        if not dialog.exec():
            return
        name, role, servers = dialog.values()

        def created(guest: dict):
            self._load()
            CodeDialog(self, guest, self.addresses, self.port).exec()

        run_async(lambda: self.client.create_guest(name, role, servers), created,
                  lambda msg: QMessageBox.warning(self, tr("Accesos"), msg))

    def _remove(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, tr("Accesos"), tr("Selecciona un acceso de la lista."))
            return
        guest = self.guests[rows[0].row()]
        if QMessageBox.question(self, tr("Quitar acceso"),
                                tr("¿Quitar el acceso de {name}? Su código dejará de funcionar al momento.",
                                   name=guest["name"])) != QMessageBox.StandardButton.Yes:
            return
        run_async(lambda: self.client.delete_guest(guest["id"]), lambda _: self._load(),
                  lambda msg: QMessageBox.warning(self, tr("Accesos"), msg))


class NewGuestDialog(QDialog):
    def __init__(self, parent, servers: list[dict]):
        super().__init__(parent)
        self.setWindowTitle(tr("Nuevo acceso"))
        self.setMinimumWidth(500)
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("Nombre de tu amigo"))
        self.role = QComboBox()
        for key, name, _ in ROLES:
            self.role.addItem(tr(name), key)
        self.role_help = QLabel()
        self.role_help.setObjectName("muted")
        self.role_help.setWordWrap(True)
        self.role.currentIndexChanged.connect(lambda i: self.role_help.setText(tr(ROLES[i][2])))
        self.role_help.setText(tr(ROLES[0][2]))

        self.all_servers = QCheckBox(tr("Todos los servidores (también los que crees después)"))
        self.server_list = QListWidget()
        self.server_list.setMaximumHeight(140)
        for s in servers:
            item = QListWidgetItem(s["name"])
            item.setData(Qt.ItemDataRole.UserRole, s["id"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.server_list.addItem(item)
        self.all_servers.toggled.connect(lambda on: self.server_list.setEnabled(not on))
        self.all_servers.setChecked(not servers)

        form = QFormLayout()
        form.addRow(tr("Nombre"), self.name)
        form.addRow(tr("Permiso"), self.role)
        form.addRow("", self.role_help)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr("Crear código"))
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel(tr("<b>Servidores que puede ver</b>")))
        layout.addWidget(self.all_servers)
        layout.addWidget(self.server_list)
        layout.addWidget(buttons)

    def _checked(self) -> list[str]:
        return [self.server_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.server_list.count())
                if self.server_list.item(i).checkState() == Qt.CheckState.Checked]

    def _accept(self) -> None:
        if not self.name.text().strip():
            QMessageBox.warning(self, tr("Nuevo acceso"), tr("Ponle un nombre (el de tu amigo, para reconocerlo luego)."))
            return
        if not self.all_servers.isChecked() and not self._checked():
            QMessageBox.warning(self, tr("Nuevo acceso"),
                                tr("Elige al menos un servidor, o marca «Todos los servidores»."))
            return
        self.accept()

    def values(self) -> tuple[str, str, list[str] | None]:
        return (self.name.text().strip(), self.role.currentData(),
                None if self.all_servers.isChecked() else self._checked())


class CodeDialog(QDialog):
    """The code can only be seen now: the agent stores a fingerprint, not the code."""

    def __init__(self, parent, guest: dict, addresses: list[tuple[str, str]], port: int):
        super().__init__(parent)
        self.setWindowTitle(tr("Código para {name}", name=guest["name"]))
        self.setMinimumWidth(540)
        code = QLineEdit(guest["token"])
        code.setReadOnly(True)
        copy = QPushButton(tr("Copiar"))
        copy.clicked.connect(lambda: (QGuiApplication.clipboard().setText(guest["token"]),
                                      copy.setText(tr("Copiado"))))
        code_row = QHBoxLayout()
        code_row.addWidget(code, 1)
        code_row.addWidget(copy)

        where = tr(" o ").join(f"<b>{ip}</b> ({label})" for ip, label in addresses)
        first = addresses[0][0] if addresses else ""
        steps = QLabel(tr(
            "Pásale este código a <b>{name}</b> por un canal privado. Con él puede entrar:<br><br>"
            "• <b>Desde Ownhost</b>: «Conectar a un equipo», dirección {where}, puerto <b>{port}</b>, y el "
            "código en «Token o código».<br>"
            "• <b>Desde el navegador del móvil</b>: abre <b>http://{first}:{port}/</b> y escribe el código.<br><br>"
            "Tiene que estar en tu red local, o en tu Tailscale (desde Tailscale puedes compartirle solo este "
            "equipo con «Share»).<br><br>"
            "<b>Guárdalo ahora:</b> no se puede volver a ver. Si se pierde, quita este acceso y crea otro.",
            name=guest["name"], where=where, port=port, first=first))
        steps.setWordWrap(True)
        steps.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addLayout(code_row)
        layout.addWidget(steps)
        layout.addWidget(buttons)
