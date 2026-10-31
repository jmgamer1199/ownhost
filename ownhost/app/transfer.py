"""Mover un servidor de un equipo a otro: copia de seguridad, envío e importación."""

import tempfile
import time
from pathlib import Path
from typing import Callable

from ownhost.app.client import AgentClient, ApiError
from ownhost.app.world_import import WorldSource, build_zip

Progress = Callable[[str], None]
# Hytale puede quedarse esperando a que inicies sesión en el downloader del destino.
INSTALL_TIMEOUT = 30 * 60


def _wait(client: AgentClient, sid: str, done: Callable[[dict], bool], timeout: float) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        s = client.server(sid)
        if done(s):
            return s
        time.sleep(1)
    raise ApiError("Se agotó el tiempo de espera")


def import_world(client: AgentClient, sid: str, source: WorldSource, include_mods: bool,
                 progress: Progress) -> dict:
    """Empaqueta un mundo local (y los mods de su instancia) y lo instala en el servidor."""
    try:
        with tempfile.TemporaryDirectory(prefix="ownhost-mundo-zip-") as tmp:
            archive = Path(tmp) / "mundo.zip"
            build_zip(source, include_mods, archive, progress)
            total_mb = archive.stat().st_size / (1 << 20)
            client.import_world(sid, archive,
                                lambda n: progress(f"Enviando... {n / (1 << 20):.0f} / {total_mb:.0f} MB"))
    finally:
        source.cleanup()
    progress("Copia de seguridad del mundo anterior e instalación del nuevo...")
    s = _wait(client, sid, lambda s: not s["task"], INSTALL_TIMEOUT)
    if s.get("error"):
        raise ApiError(f"No se pudo importar el mundo: {s['error']}")
    return s


def move_server(src: AgentClient, sid: str, dst: AgentClient, delete_original: bool,
                progress: Progress) -> dict:
    server = src.server(sid)

    if server["state"] != "stopped":
        progress("Apagando el servidor...")
        if server["state"] in ("starting", "running"):
            src.action(sid, "stop")
        _wait(src, sid, lambda s: s["state"] in ("stopped", "crashed"), 120)

    progress("Creando copia de seguridad...")
    src.action(sid, "backup")
    s = _wait(src, sid, lambda s: not s["task"], INSTALL_TIMEOUT)
    if s.get("error"):
        raise ApiError(f"Falló la copia de seguridad: {s['error']}")
    backups = src.backups(sid)
    if not backups:
        raise ApiError("No se encontró la copia de seguridad")
    backup = backups[0]  # la más reciente
    total_mb = backup["size_mb"]

    with tempfile.TemporaryDirectory(prefix="ownhost-mover-") as tmp:
        archive = Path(tmp) / backup["name"]
        src.download_backup(sid, backup["name"], archive,
                            lambda n: progress(f"Recibiendo copia... {n / (1 << 20):.0f} / {total_mb:.0f} MB"))
        new = dst.import_server(archive, server["name"],
                                lambda n: progress(f"Enviando al otro equipo... {n / (1 << 20):.0f} / {total_mb:.0f} MB"))

    progress("Instalando en el otro equipo (puedes ver el progreso en su consola)...")
    new = _wait(dst, new["id"], lambda s: not s["task"], INSTALL_TIMEOUT)
    if new.get("error"):
        raise ApiError(f"Falló la instalación en el otro equipo: {new['error']}. "
                       "El servidor original sigue intacto.")

    if delete_original:
        progress("Borrando el servidor original...")
        src.delete(sid)
    return new
