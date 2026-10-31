"""Editing the server's configuration files (mods, plugins, properties) from the app.

Only text configuration files inside the server folder: no worlds, executables or credentials.
"""

import json
from pathlib import Path

from ownhost.agent.errors import UserError
from ownhost.i18n import tr

TEXT_EXTENSIONS = {".yml", ".yaml", ".json", ".json5", ".toml", ".properties", ".conf", ".cfg", ".ini", ".txt",
                   ".snbt", ".hocon", ".xml", ".mcmeta"}
MAX_SIZE = 1 << 20  # 1 MB: configuration files are much smaller
# Folders that make no sense to open (world, libraries, logs, pregeneration copies...)
SKIP_DIRS = {"world", "world_nether", "world_the_end", "libraries", "versions", "logs", "cache", "crash-reports",
             "universe", ".fabric", ".git", "__pycache__"}
# Only in the main folder: the BlueMap map data (its configuration is in plugins/ or config/)
ROOT_SKIP_DIRS = {"bluemap", "web"}
# Not even listed: logins and keys of the games and extensions.
PRIVATE_WORDS = ("auth", "credential", "token", "secret", "password", "session", "key")


def _private(name: str) -> bool:
    low = name.lower()
    return any(w in low for w in PRIVATE_WORDS) or low.startswith(".ownhost")


def _resolve(server_dir: Path, rel: str) -> Path:
    base = server_dir.resolve()
    path = (base / rel.replace("\\", "/").lstrip("/")).resolve()
    if path != base and base not in path.parents:
        raise UserError(tr("Ruta no válida"))
    if any(_private(part) for part in path.relative_to(base).parts):
        raise UserError(tr("Ese archivo no se puede abrir desde la app"))
    return path


def _editable(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS and not _private(path.name)


def listing(server_dir: Path, rel: str = "") -> list[dict]:
    """Folders (containing something editable) and editable files of a server folder."""
    folder = _resolve(server_dir, rel)
    if not folder.is_dir():
        raise UserError(tr("La carpeta no existe"))
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
        raise UserError(tr("Solo se pueden abrir archivos de configuración de texto"))
    if path.stat().st_size > MAX_SIZE:
        raise UserError(tr("El archivo es demasiado grande para editarlo aquí"))
    return path.read_text(encoding="utf-8", errors="replace")


def write(server_dir: Path, rel: str, content: str) -> None:
    path = _resolve(server_dir, rel)
    if not path.is_file() or not _editable(path):
        raise UserError(tr("Solo se pueden guardar archivos de configuración que ya existan"))
    if len(content.encode("utf-8")) > MAX_SIZE:
        raise UserError(tr("El archivo es demasiado grande"))
    if path.suffix.lower() == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise UserError(tr("El JSON no es válido (línea {line}): revísalo antes de guardar", line=e.lineno)) from None
    # Saved separately first: if something fails halfway, the original file stays intact.
    tmp = path.with_name(path.name + ".ownhost-tmp")
    tmp.write_text(content, encoding="utf-8", newline="")
    tmp.replace(path)
