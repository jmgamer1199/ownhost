"""Automatic Java download (Eclipse Temurin, via the Adoptium API)."""

import platform
import shutil
import sys
import threading
from pathlib import Path

from ownhost.agent.downloads import Log, download, extract, get_json
from ownhost.i18n import tr

ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"


def _os() -> str:
    return {"win32": "windows", "darwin": "mac"}.get(sys.platform, "linux")


def _arch() -> str:
    m = platform.machine().lower()
    if m in ("amd64", "x86_64"):
        return "x64"
    if m in ("arm64", "aarch64"):
        return "aarch64"
    return m


class JavaManager:
    def __init__(self, root: Path):
        self.root = root
        self._lock = threading.Lock()

    def _find_java(self, major: int) -> Path | None:
        exe = "java.exe" if sys.platform == "win32" else "java"
        base = self.root / str(major)
        if not base.exists():
            return None
        for candidate in base.glob(f"*/bin/{exe}"):
            return candidate
        return None

    def ensure(self, major: int, log: Log) -> Path:
        """Returns the path to `java` of version `major`, downloading it if needed."""
        with self._lock:
            found = self._find_java(major)
            if found:
                return found
            log(tr("Java {major} no está instalado; descargándolo...", major=major))
            assets = get_json(
                ADOPTIUM.format(major=major),
                architecture=_arch(), image_type="jre", os=_os(), vendor="eclipse",
            )
            if not assets:
                raise RuntimeError(tr("Adoptium no ofrece Java {major} para {system}", major=major, system=f"{_os()}/{_arch()}"))
            package = assets[0]["binary"]["package"]
            target = self.root / str(major)
            if target.exists():
                shutil.rmtree(target)
            archive = download(package["link"], self.root / package["name"], log)
            extract(archive, target)
            archive.unlink()
            found = self._find_java(major)
            if not found:
                raise RuntimeError(tr("Java descargado pero no se encontró el ejecutable"))
            log(tr("Java {major} instalado.", major=major))
            return found
