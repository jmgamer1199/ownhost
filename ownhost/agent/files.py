"""Editar los archivos de configuración del servidor (mods, plugins, propiedades) desde la app.

Solo archivos de texto de configuración y dentro de la carpeta del servidor: nada de mundos, ejecutables
ni credenciales.
"""

import json
from pathlib import Path

from ownhost.agent.errors import UserError

TEXT_EXTENSIONS = {".yml", ".yaml", ".json", ".json5", ".toml", ".properties", ".conf", ".cfg", ".ini", ".txt",
                   ".snbt", ".hocon", ".xml", ".mcmeta"}
MAX_SIZE = 1 << 20  # 1 MB: los archivos de configuración son mucho más pequeños
# Carpetas que no tiene sentido abrir (mundo, librerías, registros, copias de las pregeneraciones...)
SKIP_DIRS = {"world", "world_nether", "world_the_end", "libraries", "versions", "logs", "cache", "crash-reports",
             "universe", ".fabric", ".git", "__pycache__"}
# Solo en la carpeta principal: los datos del mapa de BlueMap (su configuración está en plugins/ o config/)
ROOT_SKIP_DIRS = {"bluemap", "web"}
# Ni siquiera se listan: inicios de sesión y claves de los juegos y extensiones.
PRIVATE_WORDS = ("auth", "credential", "token", "secret", "password", "session", "key")


def _private(name: str) -> bool:
    low = name.lower()
    return any(w in low for w in PRIVATE_WORDS) or low.startswith(".ownhost")


def _resolve(server_dir: Path, rel: str) -> Path:
    base = server_dir.resolve()
    path = (base / rel.replace("\\", "/").lstrip("/")).resolve()
    if path != base and base not in path.parents:
        raise UserError("Ruta no válida")
    if any(_private(part) for part in path.relative_to(base).parts):
        raise UserError("Ese archivo no se puede abrir desde la app")
    return path


def _editable(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and not _private(path.name)


def listing(server_dir: Path, rel: str = "") -> list[dict]:
    """Carpetas (que contengan algo editable) y archivos editables de una carpeta del servidor."""
    folder = _resolve(server_dir, rel)
    if not folder.is_dir():
        raise UserError("La carpeta no existe")
    entries = []
    for p in sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if p.is_dir():
            root_only = rel == "" and (p.name.lower() in ROOT_SKIP_DIRS or (p / "level.dat").exists())
            if p.name.lower() in SKIP_DIRS or _private(p.name) or root_only:
                continue
            if _has_editable(p):
                entries.append({"name": p.name, "dir": True})
        elif _editable(p) and p.stat().st_size <= MAX_SIZE:
            entries.append({"name": p.name, "dir": False, "size": p.stat().st_size})
    return entries


def _has_editable(folder: Path, depth: int = 0) -> bool:
    try:
        for p in folder.iterdir():
            if p.is_file() and _editable(p):
                return True
            if p.is_dir() and depth < 3 and p.name.lower() not in SKIP_DIRS and _has_editable(p, depth + 1):
                return True
    except OSError:
        pass
    return False


def read(server_dir: Path, rel: str) -> str:
    path = _resolve(server_dir, rel)
    if not path.is_file() or not _editable(path):
        raise UserError("Solo se pueden abrir archivos de configuración de texto")
    if path.stat().st_size > MAX_SIZE:
        raise UserError("El archivo es demasiado grande para editarlo aquí")
    return path.read_text(encoding="utf-8", errors="replace")


def write(server_dir: Path, rel: str, content: str) -> None:
    path = _resolve(server_dir, rel)
    if not path.is_file() or not _editable(path):
        raise UserError("Solo se pueden guardar archivos de configuración que ya existan")
    if len(content.encode("utf-8")) > MAX_SIZE:
        raise UserError("El archivo es demasiado grande")
    if path.suffix.lower() == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise UserError(f"El JSON no es válido (línea {e.lineno}): revísalo antes de guardar") from None
    # Se guarda primero aparte: si algo falla a medias, el archivo original sigue intacto.
    tmp = path.with_name(path.name + ".ownhost-tmp")
    tmp.write_text(content, encoding="utf-8", newline="")
    tmp.replace(path)
