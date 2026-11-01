"""Opening folders and links with the system's programs (file manager, browser) on Linux.

Qt opens them with xdg-open, which inherits the packaged app's libraries (LD_LIBRARY_PATH)
and fails silently: the "Open folder" button and the links did nothing. install() makes every
QDesktopServices.openUrl (and every clickable link in a QLabel) go through xdg-open launched
with the system's own environment (see ownhost.sysenv).
"""

import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtGui import QDesktopServices

from ownhost.sysenv import clean_env

SCHEMES = ("file", "http", "https")


def open_with_system(target: str) -> bool:
    """Opens a path or a URL with xdg-open (or gio), outside the app's environment."""
    if xdg := shutil.which("xdg-open"):
        args = [xdg, target]
    elif gio := shutil.which("gio"):
        args = [gio, "open", target]
    else:
        return False
    try:
        subprocess.Popen(args, env=clean_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
    except OSError:
        return False
    return True


class _Opener(QObject):
    @Slot(QUrl)
    def open(self, url: QUrl) -> None:
        open_with_system(url.toLocalFile() if url.isLocalFile() else url.toString())


_opener: _Opener | None = None


def install() -> None:
    global _opener
    if not sys.platform.startswith("linux") or _opener is not None:
        return
    _opener = _Opener()
    for scheme in SCHEMES:
        QDesktopServices.setUrlHandler(scheme, _opener, "open")
    refresh_menu_icon()


MENU_ICON = Path.home() / ".local/share/icons/hicolor/256x256/apps/ownhost.png"


def refresh_menu_icon() -> None:
    """Linux: the menu icon (copied by install-app-linux.sh) is a separate file that an update of the
    AppImage doesn't touch. If this version's icon is different, it's replaced, so the menu shows it."""
    from ownhost.app import ASSETS

    try:
        if not MENU_ICON.exists():
            return  # app not added to the menu: nothing to refresh
        new = (ASSETS / "icon.png").read_bytes()
        if MENU_ICON.read_bytes() == new:
            return
        MENU_ICON.write_bytes(new)
        MENU_ICON.parents[2].touch()  # hicolor/: the icon caches see the change
    except OSError:
        return
    for cmd in (["gtk-update-icon-cache", "-q", "-t", str(MENU_ICON.parents[2])],
                ["kbuildsycoca6", "--noincremental"], ["kbuildsycoca5", "--noincremental"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.Popen(cmd, env=clean_env(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            except OSError:
                pass
            if cmd[0].startswith("kbuildsycoca"):
                break
