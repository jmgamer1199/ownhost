"""Actualizar la app desde las Releases de GitHub (ver ownhost/updates.py)."""

import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from ownhost import BUILD, updates
from ownhost.app.settings import load_settings, save_settings
from ownhost.app.tasks import run_async


def check(parent, manual: bool = False, on_release=lambda release: None) -> None:
    """Busca una versión nueva. Al abrir la app solo avisa si la hay; desde Ajustes, dice siempre algo."""
    def done(release: dict | None):
        on_release(release)
        if not release or not updates.is_newer(release["build"]):
            if manual:
                QMessageBox.information(parent, "Actualizaciones",
                                        "Ya tienes la última versión." if release or BUILD == "dev" else
                                        "Todavía no hay ninguna versión publicada.")
            return
        settings = load_settings()
        if not manual and settings.get("skipped_build") == release["build"]:
            return
        offer(parent, release)

    def failed(msg: str):
        if manual:
            QMessageBox.warning(parent, "Actualizaciones", f"No se pudo comprobar si hay versión nueva:\n{msg}")

    run_async(updates.latest_release, done, failed)


def offer(parent, release: dict) -> None:
    date = updates.build_date(release["build"])
    notes = release["notes"][:800] + ("..." if len(release["notes"]) > 800 else "")
    url = updates.download_url(release)
    box = QMessageBox(parent)
    box.setWindowTitle("Versión nueva")
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(f"<b>Hay una versión nueva de Ownhost</b> (del {date}).")
    box.setInformativeText((notes + "\n\n" if notes else "") + (
        "Se descarga, la app se cierra y se vuelve a abrir sola. Tus servidores siguen encendidos." if url else
        "Esta copia no se puede actualizar sola: descárgala desde la página de versiones."))
    install = box.addButton("Actualizar ahora" if url else "Abrir la página", QMessageBox.ButtonRole.AcceptRole)
    later = box.addButton("Ahora no", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(install)
    box.exec()
    if box.clickedButton() is later:
        settings = load_settings()
        settings["skipped_build"] = release["build"]  # no se vuelve a preguntar por esta versión al abrir
        save_settings(settings)
        return
    if not url:
        QDesktopServices.openUrl(QUrl(release["url"]))
        return
    _install(parent, url)


def _install(parent, url: str) -> None:
    progress = QProgressDialog("Descargando la versión nueva...", None, 0, 100, parent)
    progress.setWindowTitle("Actualizando")
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
        QMessageBox.warning(parent, "Actualizando", f"No se pudo actualizar:\n{msg}")

    run_async(lambda: updates.install(url, report), done, failed)
