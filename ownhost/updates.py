"""Updates from the project's GitHub Releases.

Each published version has the tag "v<build>" (e.g. v20261031150000, the same date that
scripts/embed_key.py generates) and three files: Ownhost.exe, Ownhost-x86_64.AppImage and Ownhost (Linux
binary). The app and the agent compare that date with their own and, if it is newer, download the file
for their system and replace their own executable.
"""

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import httpx

from ownhost import BUILD
from ownhost.i18n import tr
from ownhost.sysenv import clean_env

REPO = "jmgamer1199/ownhost"
# OWNHOST_RELEASES_API: only for testing updates with a test server.
LATEST = os.environ.get("OWNHOST_RELEASES_API") or f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
MIN_SIZE = 5 << 20  # an Ownhost executable is never smaller: guards against cut-off downloads


def latest_release() -> dict | None:
    """The latest published version, or None if there is none yet."""
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
    # Builds are dates (YYYYMMDDhhmmss): compared as text. "dev" never updates.
    return current != "dev" and build.isdigit() and current.isdigit() and build > current


def build_date(build: str) -> str:
    return f"{build[6:8]}/{build[4:6]}/{build[0:4]}" if len(build) >= 8 and build.isdigit() else build


def running_binary() -> Path | None:
    """The executable replaced when updating (None if running from source or pip)."""
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
    """File of this version for this system, if it can update itself."""
    name = asset_name()
    return release["assets"].get(name) if name and running_binary() else None


def install(url: str, progress=lambda done, total: None) -> Path:
    """Downloads the new version and puts it in place of the current executable. Returns its path."""
    binary = running_binary()
    if not binary:
        raise RuntimeError(tr("Esta copia de Ownhost no se puede actualizar sola"))
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
        raise RuntimeError(tr("La descarga ha llegado incompleta; vuelve a intentarlo"))
    if sys.platform == "win32":
        # Windows does not allow overwriting an .exe in use, but does allow renaming it.
        binary.rename(binary.with_name(f"{binary.name}.{int(time.time())}.old"))
        new.rename(binary)
    else:
        new.chmod(0o755)
        os.replace(new, binary)  # the running process keeps using the old file until it closes
    return binary


def cleanup_old() -> None:
    """Deletes the old executables left after updating on Windows (no longer in use)."""
    binary = running_binary()
    if not binary:
        return
    for old in binary.parent.glob(binary.name + ".*.old"):
        try:
            old.unlink()
        except OSError:
            pass  # another old window is still open: it will be deleted next time


def relaunch(binary: Path, args: list[str]) -> None:
    """Opens the new version, independent of this process (which closes right after)."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    # Without this version's libraries and without reusing its temp folder (PyInstaller onefile).
    env = clean_env({"PYINSTALLER_RESET_ENVIRONMENT": "1"})
    if os.environ.get("APPDIR", "").startswith("/tmp/appimage_extracted_"):
        # Started with --appimage-extract-and-run (systems without FUSE): the new one must start the same way.
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
    subprocess.Popen([str(binary), *args], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, env=env, **kwargs)
