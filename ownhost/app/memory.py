"""How much memory to give a server: based on the game, the mods, the players and what the computer has."""

import json
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QLabel, QSpinBox

from ownhost.app import theme
from ownhost.i18n import decimal, tr

# Base per server type (MB), meant for ~5 players.
BASE = {"vanilla": 2048, "paper": 2048, "fabric": 3072, "forge": 4096, "neoforge": 4096}
HYTALE = 4096
PER_EXTRA_PLAYER = 128  # from the 5th player on
SYSTEM_RESERVE = 2048   # what is left for the system and the other applications


def recommend(game: str, flavor: str, players: int, mods: int = 0, modpack: bool = False) -> int:
    base = HYTALE if game == "hytale" else BASE.get(flavor, 2048)
    if modpack:  # very large modpacks need much more
        base = 4096 if mods < 80 else 6144 if mods < 200 else 8192
    mb = base + max(0, players - 5) * PER_EXTRA_PLAYER
    return int(round(mb / 512) * 512)


def count_modpack_mods(archive: Path) -> int:
    """Number of mods in a .mrpack or CurseForge .zip (0 if it cannot be read)."""
    try:
        with zipfile.ZipFile(archive) as z:
            names = set(z.namelist())
            if "modrinth.index.json" in names:
                files = json.loads(z.read("modrinth.index.json")).get("files", [])
                return sum(1 for f in files if f.get("path", "").startswith("mods/"))
            if "manifest.json" in names:
                return len(json.loads(z.read("manifest.json")).get("files", []))
    except (OSError, ValueError, zipfile.BadZipFile):
        pass
    return 0


def gb(mb: float) -> str:
    return decimal(f"{mb / 1024:.1f}".removesuffix(".0")) + " GB"


class MemoryAdvice:
    """Puts the recommended memory in the field (as long as the user has not changed it by hand) and explains it."""

    def __init__(self, spin: QSpinBox, label: QLabel):
        self.spin, self.label = spin, label
        self.info: dict | None = None
        self.recommended = spin.value()
        self.manual = False
        self.why = ""
        self.label.setWordWrap(True)
        self.label.setObjectName("muted")
        spin.valueChanged.connect(self._edited)

    def _edited(self, value: int) -> None:
        if value != self.recommended:
            self.manual = True
        self._explain()

    def set_host_info(self, info: dict | None) -> None:
        self.info = info
        self._explain()

    def update(self, game: str, flavor: str, players: int, mods: int = 0, modpack: bool = False) -> None:
        mb = recommend(game, flavor, players, mods, modpack)
        if self.info:
            # Never more than the computer can give while leaving room for the system.
            mb = max(1024, min(mb, (self.info["memory_total_mb"] - SYSTEM_RESERVE) // 512 * 512))
        self.recommended = mb
        if not self.manual:
            self.spin.blockSignals(True)
            self.spin.setValue(mb)
            self.spin.blockSignals(False)
        mods_text = (tr("1 mod") if mods == 1 else tr("{count} mods", count=mods)) + ", " if mods else ""
        self.why = mods_text + tr("{count} jugadores a la vez", count=players)
        self._explain()

    def _explain(self) -> None:
        text = tr("Recomendado: <b>{memory}</b> ({why}).", memory=gb(self.recommended), why=self.why)
        if self.info:
            free, total = self.info["memory_available_mb"], self.info["memory_total_mb"]
            text += " " + tr("El equipo tiene {free} libres de {total}.", free=gb(free), total=gb(total))
            if self.spin.value() > free:
                text += (f" <span style='color:{theme.DANGER_TEXT}'>"
                         + tr("⚠ Es más de lo que tiene libre ahora: si los demás programas no la sueltan, el "
                              "equipo irá lento.") + "</span>")
        self.label.setText(text)
