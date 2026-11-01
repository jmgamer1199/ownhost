"""Open the web panel on a phone: a QR code per address (home network and Tailscale).

The QR code carries the access code after "#" (http://ip:port/#code=...): browsers never send that
part over the network, and the panel saves it and removes it from the address bar.
"""

import io
from urllib.parse import quote

import segno
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTabWidget, QVBoxLayout, QWidget)

from ownhost.i18n import tr


def panel_url(ip: str, port: int, code: str = "") -> str:
    return f"http://{ip}:{port}/" + (f"#code={quote(code, safe='')}" if code else "")


def qr_pixmap(text: str, size: int = 260) -> QPixmap:
    buffer = io.BytesIO()
    segno.make(text, error="m").save(buffer, kind="png", scale=8, border=3, dark="#000000", light="#ffffff")
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.getvalue(), "PNG")
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)


class PhoneDialog(QDialog):
    def __init__(self, parent, host_name: str, addresses: list[tuple[str, str]], port: int, code: str,
                 owner: bool):
        super().__init__(parent)
        self.setWindowTitle(tr("Abrir «{name}» en el móvil", name=host_name))
        tabs = QTabWidget()
        for ip, description in addresses:
            tabs.addTab(self._page(ip, port, code, description), description)
        help_text = QLabel(tr("Escanea el código con la cámara del móvil: se abre el panel web ya con tu acceso. "
                              "<b>Red local</b> funciona con el móvil en el wifi de casa; <b>Tailscale</b>, desde "
                              "cualquier sitio con la app de Tailscale en el móvil y la misma cuenta."))
        help_text.setWordWrap(True)
        warn = QLabel(tr("Este código da acceso completo a tus servidores: no lo compartas. Para amigos usa "
                         "«Accesos para amigos».") if owner else
                      tr("Este código es tu acceso a este equipo: no lo compartas."))
        warn.setObjectName("muted")
        warn.setWordWrap(True)
        code_box = QLineEdit(code)
        code_box.setReadOnly(True)
        code_box.setEchoMode(QLineEdit.EchoMode.Password)
        show = QPushButton(tr("Mostrar"))
        show.setCheckable(True)
        show.toggled.connect(lambda on: code_box.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        copy = QPushButton(tr("Copiar"))
        copy.clicked.connect(lambda: QApplication.clipboard().setText(code))
        code_row = QHBoxLayout()
        code_row.addWidget(QLabel(tr("Código de acceso:")))
        code_row.addWidget(code_box, 1)
        code_row.addWidget(show)
        code_row.addWidget(copy)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(help_text)
        layout.addWidget(tabs)
        layout.addLayout(code_row)
        layout.addWidget(warn)
        layout.addWidget(buttons)
        self.setMinimumWidth(480)

    def _page(self, ip: str, port: int, code: str, description: str) -> QWidget:
        page = QWidget()
        image = QLabel()
        image.setPixmap(qr_pixmap(panel_url(ip, port, code)))
        image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image.setAccessibleName(tr("Código QR del panel web ({where})", where=description))
        url = panel_url(ip, port)
        link = QLabel(f"<a href='{url}'>{url}</a>")
        link.setOpenExternalLinks(True)
        link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QVBoxLayout(page)
        layout.addWidget(image)
        layout.addWidget(link)
        return page
