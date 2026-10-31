"""Prepares an existing world (and the mods of its instance) for uploading to a server."""

import json
import os
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ownhost.i18n import tr


def default_saves_dir() -> Path:
    """Worlds folder of the official Minecraft launcher."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / ".minecraft" / "saves"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "minecraft" / "saves"
    return Path.home() / ".minecraft" / "saves"


@dataclass
class WorldSource:
    world: Path
    instance: Path | None = None  # instance folder (with mods/ and config/) if detected
    mods: list[Path] = field(default_factory=list)
    client_only: list[str] = field(default_factory=list)  # mods skipped because they are client-only
    temp_dir: tempfile.TemporaryDirectory | None = None  # if it came from a .zip

    @property
    def config(self) -> Path | None:
        if self.instance and (self.instance / "config").is_dir():
            return self.instance / "config"
        return None

    def cleanup(self) -> None:
        if self.temp_dir:
            self.temp_dir.cleanup()


def _find_level_dat(root: Path) -> Path | None:
    if (root / "level.dat").exists():
        return root
    found = sorted(root.rglob("level.dat"), key=lambda p: len(p.parts))
    return found[0].parent if found else None


def _is_client_only(jar: Path) -> bool:
    """Fabric/Quilt mods state whether they only work on the client (shaders, minimaps...)."""
    try:
        with zipfile.ZipFile(jar) as z:
            if "fabric.mod.json" in z.namelist():
                info = json.loads(z.read("fabric.mod.json").decode("utf-8", "replace"), strict=False)
                return info.get("environment") == "client"
    except (zipfile.BadZipFile, ValueError, OSError):
        pass
    return False


def inspect(path: Path) -> WorldSource:
    """Accepts a world folder or a .zip that contains one."""
    temp = None
    if path.is_file() and path.suffix.lower() == ".zip":
        temp = tempfile.TemporaryDirectory(prefix="ownhost-mundo-")
        with zipfile.ZipFile(path) as z:
            z.extractall(temp.name)
        root = Path(temp.name)
    else:
        root = path
    world = _find_level_dat(root)
    if not world:
        if temp:
            temp.cleanup()
        raise ValueError(tr("No se encontró level.dat. Elige la carpeta de un mundo de Minecraft "
                            "(normalmente está en .minecraft\\saves)."))
    source = WorldSource(world=world, temp_dir=temp)
    # Launcher instances (official, CurseForge, Prism, Modrinth...): <instance>/saves/<world>
    if world.parent.name == "saves" and (world.parent.parent / "mods").is_dir():
        source.instance = world.parent.parent
        for jar in sorted((source.instance / "mods").glob("*.jar")):
            if _is_client_only(jar):
                source.client_only.append(jar.name)
            else:
                source.mods.append(jar)
    return source


def build_zip(source: WorldSource, include_mods: bool, dest: Path, progress: Callable[[str], None]) -> None:
    """Packs world/ (+ mods/ and config/) to send it to the agent."""
    entries: list[tuple[Path, str]] = []
    for f in source.world.rglob("*"):
        if f.is_file() and f.name != "session.lock":
            entries.append((f, f"world/{f.relative_to(source.world).as_posix()}"))
    if include_mods:
        entries += [(jar, f"mods/{jar.name}") for jar in source.mods]
        if source.config:
            entries += [(f, f"config/{f.relative_to(source.config).as_posix()}")
                        for f in source.config.rglob("*") if f.is_file()]
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for i, (f, name) in enumerate(entries, 1):
            z.write(f, name)
            if i % 50 == 0 or i == len(entries):
                progress(tr("Preparando archivos... {done} / {total}", done=i, total=len(entries)))
