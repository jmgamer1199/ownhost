"""Settings of one computer: start with the computer, and let it be switched on from the network."""

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QMessageBox, QVBoxLayout

from ownhost.app.client import AgentClient
from ownhost.app.tasks import run_async
from ownhost.i18n import tr


def autostart_text(options: dict) -> str:
    """What starting with the computer means on that computer's system."""
    kind = options["autostart"]["kind"]
    if kind == "registry":
        return tr("Se inicia cuando inicias sesión en Windows. Si el PC entra solo a tu cuenta, será nada más "
                  "encenderlo.")
    if kind == "desktop":
        return tr("Se inicia cuando inicias sesión en el escritorio. En un servidor sin pantalla, usa el servicio "
                  "del sistema (install-agent-service.sh): ese sí arranca con el equipo aunque nadie inicie sesión.")
    if kind == "service":
        return tr("Este equipo usa el servicio del sistema «ownhost-agent»: arranca siempre con el equipo. Para "
                  "quitarlo, en ese equipo: sudo systemctl disable --now ownhost-agent")
    return tr("En este sistema no se puede cambiar desde aquí.")


def wake_text(options: dict) -> str:
    """How to get a computer ready to be switched on from the network."""
    text = tr("Solo funciona dentro de tu red de casa (no por Tailscale ni desde fuera). El equipo tiene que tener "
              "activado Wake-on-LAN en la BIOS/UEFI y en su tarjeta de red.")
    if options.get("os") == "Linux":
        text += " " + tr("En Linux, por ejemplo: sudo ethtool -s <tarjeta> wol g")
    elif options.get("os") == "Windows":
        text += " " + tr("En Windows: Administrador de dispositivos → tu tarjeta de red → Administración de energía → "
                         "«Permitir que este dispositivo reactive el equipo».")
    mac = options["wake"].get("mac")
    if options["wake"]["enabled"] and mac:
        text += "<br>" + tr("Dirección física de la tarjeta: {mac}", mac=mac)
    return text


class ComputerSettingsDialog(QDialog):
    def __init__(self, parent, client: AgentClient, name: str):
        super().__init__(parent)
        self.client = client
        self.options: dict | None = None
        self.setWindowTitle(tr("Ajustes de {name}", name=name))
        self.setMinimumWidth(520)
        self.autostart = QCheckBox(tr("Iniciar Ownhost al encender el equipo"))
        self.autostart_help = QLabel()
        self.wake = QCheckBox(tr("Permitir encender este equipo desde otros equipos de mi red"))
        self.wake_help = QLabel()
        for label in (self.autostart_help, self.wake_help):
            label.setWordWrap(True)
            label.setObjectName("muted")
        self.status = QLabel(tr("Cargando..."))
        self.status.setObjectName("muted")
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(False)
        for w in (self.autostart, self.wake):
            w.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.addWidget(self.autostart)
        layout.addWidget(self.autostart_help)
        layout.addSpacing(10)
        layout.addWidget(self.wake)
        layout.addWidget(self.wake_help)
        layout.addSpacing(6)
        layout.addWidget(self.status)
        layout.addWidget(self.buttons)
        run_async(client.agent_options, self._loaded, lambda msg: self.status.setText(msg))

    def _loaded(self, options: dict) -> None:
        self.options = options
        auto = options["autostart"]
        self.autostart.setChecked(auto["enabled"])
        self.autostart.setEnabled(auto["changeable"])
        self.autostart_help.setText(autostart_text(options))
        self.wake.setChecked(options["wake"]["enabled"])
        self.wake.setEnabled(True)
        self.wake_help.setText(wake_text(options))
        self.status.setText("")
        self.buttons.button(QDialogButtonBox.StandardButton.Save).setEnabled(True)

    def _save(self) -> None:
        if not self.options:
            return
        changes = {}
        if self.options["autostart"]["changeable"] and self.autostart.isChecked() != self.options["autostart"]["enabled"]:
            changes["autostart"] = self.autostart.isChecked()
        if self.wake.isChecked() != self.options["wake"]["enabled"]:
            changes["wake"] = self.wake.isChecked()
        if not changes:
            self.accept()
            return
        self.buttons.setEnabled(False)
        self.status.setText(tr("Guardando..."))

        def failed(msg: str) -> None:
            self.buttons.setEnabled(True)
            self.status.setText("")
            QMessageBox.warning(self, tr("Ajustes del equipo"), msg)

        run_async(lambda: self.client.set_agent_options(**changes), lambda _: self.accept(), failed)
