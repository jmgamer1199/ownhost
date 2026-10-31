"""Update the app from GitHub Releases (see ownhost/updates.py)."""

import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from ownhost import BUILD, updates
from ownhost.app.settings import load_settings, save_settings
from ownhost.app.tasks import run_async
from ownhost.i18n import tr


def check(parent, manual: bool = False, on_release=lambda release: None) -> None:
    """Look for a new version. On app start it only speaks up if there is one; from Settings it always answers."""
    def done(release: dict | None):
        on_release(release)
        if not release or not updates.is_newer(release["build"]):
            if manual:
                QMessageBox.information(parent, tr("Actualizaciones"),
                                        tr("Ya tienes la última versión.") if release or BUILD == "dev" else
                                        tr("Todavía no hay ninguna versión publicada."))
            return
        settings = load_settings()
        if not manual and settings.get("skipped_build") == release["build"]:
            return
        offer(parent, release)

    def failed(msg: str):
        if manual:
            QMessageBox.warning(parent, tr("Actualizaciones"),
                                tr("No se pudo comprobar si hay versión nueva:\n{msg}", msg=msg))

    run_async(updates.latest_release, done, failed)


def offer(parent, release: dict) -> None:
    date = updates.build_date(release["build"])
    notes = release["notes"][:800] + ("..." if len(release["notes"]) > 800 else "")
    url = updates.download_url(release)
    box = QMessageBox(parent)
    box.setWindowTitle(tr("Versión nueva"))
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(tr("<b>Hay una versión nueva de Ownhost</b> (del {date}).", date=date))
    box.setInformativeText((notes + "\n\n" if notes else "") + (
        tr("Se descarga, la app se cierra y se vuelve a abrir sola. Tus servidores siguen encendidos.") if url else
        tr("Esta copia no se puede actualizar sola: descárgala desde la página de versiones.")))
    install = box.addButton(tr("Actualizar ahora") if url else tr("Abrir la página"),
                            QMessageBox.ButtonRole.AcceptRole)
    later = box.addButton(tr("Ahora no"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(install)
    box.exec()
    if box.clickedButton() is later:
        settings = load_settings()
        settings["skipped_build"] = release["build"]  # don't ask again about this version on start
        save_settings(settings)
        return
    if not url:
        QDesktopServices.openUrl(QUrl(release["url"]))
        return
    _install(parent, url)


def _install(parent, url: str) -> None:
    progress = QProgressDialog(tr("Descargando la versión nueva..."), None, 0, 100, parent)
    progress.setWindowTitle(tr("Actualizando"))
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    progress.show()
    state = {"pct": 0}

    def report(done: int, total: int):
        state["pct"] = int(done * 100 / total) if total else 0

    def tick():
        progress.setValue(state["pct"])

    from PySide6.QtCore import QTimer
    timer = QTimer(progress, interval=200)
    timer.timeout.connect(tick)
    timer.start()

    def done(binary):
        timer.stop()
        progress.close()
        updates.relaunch(binary, sys.argv[1:])
        QApplication.quit()

    def failed(msg: str):
        timer.stop()
        progress.close()
        QMessageBox.warning(parent, tr("Actualizando"), tr("No se pudo actualizar:\n{msg}", msg=msg))

    run_async(lambda: updates.install(url, report), done, failed)
