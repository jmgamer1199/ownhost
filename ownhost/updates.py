"""Actualizaciones desde las Releases de GitHub del proyecto.

Cada versión publicada lleva la etiqueta «v<compilación>» (p. ej. v20261031150000, la misma fecha que
genera scripts/embed_key.py) y tres archivos: Ownhost.exe, Ownhost-x86_64.AppImage y Ownhost (binario
de Linux). La app y el agente comparan esa fecha con la suya y, si es más nueva, descargan el archivo
de su sistema y sustituyen su propio ejecutable.
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import httpx

from ownhost import BUILD
from ownhost.sysenv import clean_env

REPO = "jmgamer1199/ownhost"
# OWNHOST_RELEASES_API: solo para probar las actualizaciones con un servidor de pruebas.
LATEST = os.environ.get("OWNHOST_RELEASES_API") or f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
MIN_SIZE = 5 << 20  # un ejecutable de Ownhost nunca pesa menos: protege de descargas cortadas


def latest_release() -> dict | None:
    """La última versión publicada, o None si todavía no hay ninguna."""
    r = httpx.get(LATEST, timeout=15, follow_redirects=True,
                  headers={"Accept": "application/vnd.github+json", "User-Agent": "Ownhost"})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    data = r.json()
    return {
        "build": data["tag_name"].lstrip("v"),
        "name": data.get("name") or data["tag_name"],
        "notes": (data.get("body") or "").strip(),
        "url": data.get("html_url") or RELEASES_PAGE,
        "assets": {a["name"]: a["browser_download_url"] for a in data.get("assets", [])},
    }


def is_newer(build: str, current: str = BUILD) -> bool:
    # Las compilaciones son fechas (AAAAMMDDhhmmss): se comparan como texto. «dev» nunca se actualiza.
    return current != "dev" and build.isdigit() and current.isdigit() and build > current


def build_date(build: str) -> str:
    return f"{build[6:8]}/{build[4:6]}/{build[0:4]}" if len(build) >= 8 and build.isdigit() else build


def running_binary() -> Path | None:
    """El ejecutable que se sustituye al actualizar (None si se ejecuta desde el código o con pip)."""
    if os.environ.get("APPIMAGE"):
        return Path(os.environ["APPIMAGE"])
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    return None


def asset_name() -> str | None:
    if sys.platform == "win32":
        return "Ownhost.exe"
    if sys.platform.startswith("linux") and platform.machine().lower() in ("x86_64", "amd64"):
        return "Ownhost-x86_64.AppImage" if os.environ.get("APPIMAGE") else "Ownhost"
    return None


def download_url(release: dict) -> str | None:
    """Archivo de esta versión para este sistema, si se puede actualizar solo."""
    name = asset_name()
    return release["assets"].get(name) if name and running_binary() else None


def install(url: str, progress=lambda done, total: None) -> Path:
    """Descarga la versión nueva y la pone en lugar del ejecutable actual. Devuelve su ruta."""
    binary = running_binary()
    if not binary:
        raise RuntimeError("Esta copia de Ownhost no se puede actualizar sola")
    new = binary.with_name(binary.name + ".new")
    with httpx.stream("GET", url, timeout=httpx.Timeout(60, connect=15), follow_redirects=True,
                      headers={"User-Agent": "Ownhost"}) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        with open(new, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                done += len(chunk)
                progress(done, total)
    if new.stat().st_size < MIN_SIZE or (total and new.stat().st_size != total):
        new.unlink(missing_ok=True)
        raise RuntimeError("La descarga ha llegado incompleta; vuelve a intentarlo")
    if sys.platform == "win32":
        # Windows no deja sobrescribir un .exe en uso, pero sí cambiarle el nombre.
        binary.rename(binary.with_name(f"{binary.name}.{int(time.time())}.old"))
        new.rename(binary)
    else:
        new.chmod(0o755)
        os.replace(new, binary)  # el proceso en marcha sigue con el archivo antiguo hasta que se cierra
    return binary


def cleanup_old() -> None:
    """Borra los ejecutables antiguos que quedaron al actualizar en Windows (ya no están en uso)."""
    binary = running_binary()
    if not binary:
        return
    for old in binary.parent.glob(binary.name + ".*.old"):
        try:
            old.unlink()
        except OSError:
            pass  # otra ventana antigua sigue abierta: se borrará la próxima vez


def relaunch(binary: Path, args: list[str]) -> None:
    """Abre la versión nueva, independiente de este proceso (que se cerrará a continuación)."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    # Sin las bibliotecas de esta versión y sin reutilizar su carpeta temporal (PyInstaller onefile).
    env = clean_env({"PYINSTALLER_RESET_ENVIRONMENT": "1"})
    subprocess.Popen([str(binary), *args], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, env=env, **kwargs)
