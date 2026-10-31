"""Moves a server from one computer to another: backup, transfer and import."""

import tempfile
import time
from pathlib import Path
from typing import Callable

from ownhost.app.client import AgentClient, ApiError
from ownhost.app.world_import import WorldSource, build_zip
from ownhost.i18n import tr

Progress = Callable[[str], None]
# Hytale may sit waiting for you to sign in to the target's downloader.
INSTALL_TIMEOUT = 30 * 60


def _wait(client: AgentClient, sid: str, done: Callable[[dict], bool], timeout: float) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        s = client.server(sid)
        if done(s):
            return s
        time.sleep(1)
    raise ApiError(tr("Se agotó el tiempo de espera"))


def import_world(client: AgentClient, sid: str, source: WorldSource, include_mods: bool,
                 progress: Progress) -> dict:
    """Packs a local world (and the mods of its instance) and installs it on the server."""
    try:
        with tempfile.TemporaryDirectory(prefix="ownhost-mundo-zip-") as tmp:
            archive = Path(tmp) / "mundo.zip"
            build_zip(source, include_mods, archive, progress)
            total_mb = archive.stat().st_size / (1 << 20)
            client.import_world(sid, archive,
                                lambda n: progress(tr("Enviando... {done} / {total} MB", done=f"{n / (1 << 20):.0f}",
                                                                     total=f"{total_mb:.0f}")))
    finally:
        source.cleanup()
    progress(tr("Copia de seguridad del mundo anterior e instalación del nuevo..."))
    s = _wait(client, sid, lambda s: not s["task"], INSTALL_TIMEOUT)
    if s.get("error"):
        raise ApiError(tr("No se pudo importar el mundo: {error}", error=s["error"]))
    return s


def move_server(src: AgentClient, sid: str, dst: AgentClient, delete_original: bool,
                progress: Progress) -> dict:
    server = src.server(sid)

    if server["state"] != "stopped":
        progress(tr("Apagando el servidor..."))
        if server["state"] in ("starting", "running"):
            src.action(sid, "stop")
        _wait(src, sid, lambda s: s["state"] in ("stopped", "crashed"), 120)

    progress(tr("Creando copia de seguridad..."))
    src.action(sid, "backup")
    s = _wait(src, sid, lambda s: not s["task"], INSTALL_TIMEOUT)
    if s.get("error"):
        raise ApiError(tr("Falló la copia de seguridad: {error}", error=s["error"]))
    backups = src.backups(sid)
    if not backups:
        raise ApiError(tr("No se encontró la copia de seguridad"))
    backup = backups[0]  # the most recent one
    total_mb = backup["size_mb"]

    with tempfile.TemporaryDirectory(prefix="ownhost-mover-") as tmp:
        archive = Path(tmp) / backup["name"]
        src.download_backup(sid, backup["name"], archive,
                            lambda n: progress(tr("Recibiendo copia... {done} / {total} MB",
                                                         done=f"{n / (1 << 20):.0f}", total=f"{total_mb:.0f}")))
        new = dst.import_server(archive, server["name"],
                                lambda n: progress(tr("Enviando al otro equipo... {done} / {total} MB",
                                                           done=f"{n / (1 << 20):.0f}", total=f"{total_mb:.0f}")))

    progress(tr("Instalando en el otro equipo (puedes ver el progreso en su consola)..."))
    new = _wait(dst, new["id"], lambda s: not s["task"], INSTALL_TIMEOUT)
    if new.get("error"):
        raise ApiError(tr("Falló la instalación en el otro equipo: {error}. El servidor original sigue intacto.",
                          error=new["error"]))

    if delete_original:
        progress(tr("Borrando el servidor original..."))
        src.delete(sid)
    return new
