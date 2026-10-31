"""Backups on another computer: choose where they are sent and restore the ones received."""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout,
)

from ownhost.app import theme
from ownhost.app.client import AgentClient
from ownhost.app.hosts import Host
from ownhost.app.tasks import run_async
from ownhost.i18n import decimal, tr

DATA = Qt.ItemDataRole.UserRole


def target_addresses(source: list[tuple[str, str]], info: dict, host: Host) -> list[str]:
    """Addresses through which the source computer could reach the target one, most likely first.

    The source agent tries each one and keeps the first that answers.
    """
    lan, ts = info.get("lan_ip"), info.get("tailscale_ip")
    source_lan = source[0][0] if source else ""
    same_network = bool(lan) and lan.rsplit(".", 1)[0] == source_lan.rsplit(".", 1)[0]
    ordered = [lan, ts] if same_network or not ts else [ts, lan]
    return list(dict.fromkeys(a for a in [*ordered, host.address] if a))


def enable(source_client: AgentClient, sid: str, source_name: str, source_addresses: list[tuple[str, str]],
           target: Host, target_client: AgentClient) -> dict:
    """Asks the target computer for a code that only allows receiving backups and gives it to the source one."""
    info = target_client.info()
    guest = target_client.create_guest(tr("Copias de {name}", name=source_name), "backup", None)
    try:
        return source_client._req("PUT", f"/servers/{sid}/replica", json={
            "addresses": target_addresses(source_addresses, info, target), "port": target.port,
            "token": guest["token"], "target_name": target.name, "source_name": source_name})
    except Exception:
        target_client.delete_guest(guest["id"])  # do not leave an unused code behind
        raise


def disable(source_client: AgentClient, sid: str) -> dict:
    return source_client._req("DELETE", f"/servers/{sid}/replica")


def status_text(replica: dict | None) -> str:
    if not replica:
        return tr("Las copias solo se guardan en este equipo.")
    last = replica.get("last")
    text = tr("Cada copia se guarda también en <b>{target}</b> (las {keep} últimas).",
              target=replica["target_name"], keep=replica.get("keep", 3))
    if not last:
        return text + " " + tr("Todavía no se ha enviado ninguna: se enviará con la próxima copia.")
    when = datetime.fromtimestamp(last["time"]).strftime("%d/%m %H:%M")
    if last.get("ok"):
        return text + " " + tr("Última enviada: {when}.", when=when)
    return text + (f"<br><span style='color:{theme.DANGER_TEXT}'>"
                   + tr("⚠ El {when} no se pudo enviar: {error}", when=when, error=last.get("error", ""))
                   + "</span>")


class ReceivedBackupsDialog(QDialog):
    """Backups that other computers have sent to this one, to restore them here if the other one fails."""

    def __init__(self, parent, client: AgentClient, host_name: str, on_restored):
        super().__init__(parent)
        self.setWindowTitle(tr("Copias de otros equipos · {host}", host=host_name))
        self.setMinimumSize(600, 380)
        self.client, self.on_restored = client, on_restored
        intro = QLabel(tr("Copias de seguridad que otros equipos guardan en este. Si uno se estropea, restaura aquí "
                          "su servidor: se crea uno nuevo con el mundo, los mods y la configuración de esa copia."))
        intro.setWordWrap(True)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("Servidor / copia"), tr("Tamaño"), tr("Fecha")])
        self.tree.setColumnWidth(0, 300)
        self.empty = QLabel(tr("Ningún equipo guarda copias aquí todavía. Se activa en Ajustes de cada servidor, "
                               "en «Copia en otro equipo»."))
        self.empty.setObjectName("muted")
        self.empty.setWordWrap(True)
        restore = QPushButton(tr("Restaurar aquí..."))
        restore.setProperty("kind", "primary")
        restore.clicked.connect(self._restore)
        delete = QPushButton(tr("Borrar las copias de ese servidor"))
        delete.setProperty("kind", "danger")
        delete.clicked.connect(self._delete)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.accept)
        row = QHBoxLayout()
        row.addWidget(restore)
        row.addWidget(delete)
        row.addStretch()
        row.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.empty)
        layout.addLayout(row)
        self._load()

    def _load(self) -> None:
        run_async(lambda: self.client._req("GET", "/replicas"), self._loaded,
                  lambda msg: QMessageBox.warning(self, tr("Copias"), msg))

    def _loaded(self, groups: list[dict]) -> None:
        self.tree.clear()
        for g in groups:
            top = QTreeWidgetItem([tr("{server}  (de {source})", server=g["server_name"], source=g["source"]), "", ""])
            top.setData(0, DATA, {"key": g["key"], "server_name": g["server_name"]})
            for b in g["backups"]:
                date = datetime.fromisoformat(b["date"]).strftime("%d/%m/%Y %H:%M")
                child = QTreeWidgetItem([b["name"], decimal(f"{b['size_mb']:.1f}") + " MB", date])
                child.setData(0, DATA, {"key": g["key"], "name": b["name"], "server_name": g["server_name"]})
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        self.tree.setVisible(bool(groups))
        self.empty.setVisible(not groups)

    def _selected(self) -> dict | None:
        item = self.tree.currentItem()
        return item.data(0, DATA) if item else None

    def _restore(self) -> None:
        sel = self._selected()
        if not sel:
            QMessageBox.information(self, tr("Copias"), tr("Elige una copia de la lista."))
            return
        if "name" not in sel:  # the server was chosen: its most recent backup
            item = self.tree.currentItem()
            if not item.childCount():
                return
            sel = item.child(0).data(0, DATA)
        name, ok = QInputDialog.getText(self, tr("Restaurar aquí"), tr("Nombre del servidor nuevo:"),
                                        text=tr("{name} (restaurado)", name=sel["server_name"]))
        if not ok:
            return

        def done(server: dict):
            self.on_restored(server)
            self.accept()

        run_async(lambda: self.client._req("POST", f"/replicas/{sel['key']}/{sel['name']}/restore",
                                           json={"name": name.strip()}),
                  done, lambda msg: QMessageBox.warning(self, tr("No se pudo restaurar"), msg))

    def _delete(self) -> None:
        sel = self._selected()
        if not sel:
            return
        if QMessageBox.question(self, tr("Borrar copias"), tr(
                "¿Borrar de este equipo todas las copias de «{name}»? Las del equipo original no se tocan.",
                name=sel["server_name"])) \
                != QMessageBox.StandardButton.Yes:
            return
        run_async(lambda: self.client._req("DELETE", f"/replicas/{sel['key']}"), lambda _: self._load(),
                  lambda msg: QMessageBox.warning(self, tr("Copias"), msg))
