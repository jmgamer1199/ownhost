"""Copias de seguridad en otro equipo: cada copia que se hace se envía también al agente elegido.

El equipo que las guarda da un código especial («recibir copias») que solo sirve para enviarle copias:
con él no se puede ver ni tocar nada más. Así, si se rompe el disco de un equipo, las copias de sus
servidores siguen en otro y se pueden restaurar allí con un clic.
"""

import json
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

import httpx

from ownhost.agent.errors import UserError

SAFE = re.compile(r"[^A-Za-z0-9_.-]+")
KEY = re.compile(r"^[A-Za-z0-9_.-]+--[0-9a-f]{6,32}$")
BACKUP_NAME = re.compile(r"^[\w.-]+\.zip$")
DEFAULT_KEEP = 3


def _safe(text: str) -> str:
    return SAFE.sub("_", text).strip("._")[:60] or "equipo"


class ReplicaStore:
    """Las copias que otros equipos envían a este."""

    def __init__(self, data_dir: Path):
        self.root = data_dir / "replicas"
        self.lock = threading.Lock()

    def folder(self, source: str, sid: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{6,32}", sid):
            raise UserError("Servidor no válido")
        return self.root / f"{_safe(source)}--{sid}"

    def store(self, source: str, sid: str, name: str, server_name: str, game: str, upload: Path, keep: int) -> None:
        if not BACKUP_NAME.match(name):
            upload.unlink(missing_ok=True)
            raise UserError("Nombre de copia no válido")
        folder = self.folder(source, sid)
        with self.lock:
            folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(upload), folder / name)
            (folder / "info.json").write_text(json.dumps({
                "source": source, "server_id": sid, "server_name": server_name, "game": game,
                "updated": time.time()}), encoding="utf-8")
            for old in sorted(folder.glob("*.zip"), reverse=True)[max(1, keep):]:
                old.unlink(missing_ok=True)

    def listing(self) -> list[dict]:
        result = []
        if not self.root.exists():
            return result
        for folder in sorted(self.root.iterdir()):
            info_file = folder / "info.json"
            if not folder.is_dir() or not info_file.exists():
                continue
            info = json.loads(info_file.read_text(encoding="utf-8"))
            backups = [{"name": z.name, "size_mb": round(z.stat().st_size / (1 << 20), 1),
                        "date": datetime.fromtimestamp(z.stat().st_mtime).isoformat(timespec="seconds")}
                       for z in sorted(folder.glob("*.zip"), reverse=True)]
            result.append({**info, "key": folder.name, "backups": backups})
        return result

    def path(self, key: str, name: str) -> Path:
        if not KEY.match(key) or not BACKUP_NAME.match(name):
            raise UserError("Copia no válida")
        path = self.root / key / name
        if not path.is_file():
            raise UserError("Esa copia ya no existe")
        return path

    def delete(self, key: str) -> None:
        if not KEY.match(key) or not (self.root / key).is_dir():
            raise UserError("No existe")
        shutil.rmtree(self.root / key)


def _client(cfg: dict) -> httpx.Client:
    return httpx.Client(base_url=f"http://{cfg['address']}:{cfg['port']}/api",
                        headers={"Authorization": f"Bearer {cfg['token']}"}, timeout=httpx.Timeout(30, connect=5))


def check(cfg: dict) -> None:
    """Comprueba que el otro equipo responde y acepta el código, antes de guardar la configuración."""
    try:
        with _client(cfg) as c:
            r = c.get("/replicas/check")
    except httpx.HTTPError:
        raise UserError(f"No se puede conectar con {cfg['address']}:{cfg['port']}. ¿Está encendido y en la red?") \
            from None
    if r.status_code in (401, 403):
        raise UserError("El otro equipo no ha aceptado el código de copias")
    if r.status_code == 404:
        raise UserError("El otro equipo tiene una versión de Ownhost sin copias remotas: actualízalo")
    r.raise_for_status()


def reachable(cfg: dict) -> str:
    """La primera de las direcciones del otro equipo que responde y acepta el código."""
    errors = []
    for address in cfg["addresses"]:
        try:
            check({**cfg, "address": address})
            return address
        except UserError as e:
            if "no ha aceptado" in str(e):
                raise
            errors.append(address)
    raise UserError(f"Este equipo no llega al otro por {', '.join(errors)} (puerto {cfg['port']}). "
                    "¿Está encendido, en la misma red o en tu Tailscale, y con el cortafuegos abierto?")


def send(cfg: dict, source: str, sid: str, server_name: str, game: str, archive: Path) -> None:
    def chunks():
        with open(archive, "rb") as f:
            while chunk := f.read(1 << 20):
                yield chunk

    with _client(cfg) as c:
        r = c.put(f"/replicas/{source}/{sid}/{archive.name}", content=chunks(),
                  params={"server_name": server_name, "game": game, "keep": cfg.get("keep", DEFAULT_KEEP)},
                  headers={"Content-Type": "application/zip", "Content-Length": str(archive.stat().st_size)},
                  timeout=httpx.Timeout(None, connect=10))
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail")
        except ValueError:
            detail = r.text
        raise RuntimeError(detail or f"error {r.status_code}")
