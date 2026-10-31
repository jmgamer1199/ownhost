"""Cuánta memoria darle a un servidor: según el juego, los mods, los jugadores y lo que tiene el equipo."""

import json
import zipfile
from pathlib import Path

from PySide6.QtWidgets import QLabel, QSpinBox

from ownhost.app import theme

# Base por tipo de servidor (MB), pensada para ~5 jugadores.
BASE = {"vanilla": 2048, "paper": 2048, "fabric": 3072, "forge": 4096, "neoforge": 4096}
HYTALE = 4096
PER_EXTRA_PLAYER = 128  # a partir del 5.º jugador
SYSTEM_RESERVE = 2048   # lo que se deja al sistema y a las demás aplicaciones


def recommend(game: str, flavor: str, players: int, mods: int = 0, modpack: bool = False) -> int:
    base = HYTALE if game == "hytale" else BASE.get(flavor, 2048)
    if modpack:  # los modpacks muy grandes piden mucho más
        base = 4096 if mods < 80 else 6144 if mods < 200 else 8192
    mb = base + max(0, players - 5) * PER_EXTRA_PLAYER
    return int(round(mb / 512) * 512)


def count_modpack_mods(archive: Path) -> int:
    """Número de mods de un .mrpack o .zip de CurseForge (0 si no se puede leer)."""
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
    return f"{mb / 1024:.1f}".replace(".", ",").replace(",0", "") + " GB"


class MemoryAdvice:
    """Pone la memoria recomendada en el campo (mientras el usuario no la cambie a mano) y lo explica."""

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
            # Nunca más de lo que el equipo puede dar dejando sitio al sistema.
            mb = max(1024, min(mb, (self.info["memory_total_mb"] - SYSTEM_RESERVE) // 512 * 512))
        self.recommended = mb
        if not self.manual:
            self.spin.blockSignals(True)
            self.spin.setValue(mb)
            self.spin.blockSignals(False)
        self.why = (f"{mods} mod{'' if mods == 1 else 's'}, " if mods else "") + f"{players} jugadores a la vez"
        self._explain()

    def _explain(self) -> None:
        text = f"Recomendado: <b>{gb(self.recommended)}</b> ({self.why})."
        if self.info:
            free, total = self.info["memory_available_mb"], self.info["memory_total_mb"]
            text += f" El equipo tiene {gb(free)} libres de {gb(total)}."
            if self.spin.value() > free:
                text += (f" <span style='color:{theme.DANGER_TEXT}'>⚠ Es más de lo que tiene libre ahora: si los "
                         "demás programas no la sueltan, el equipo irá lento.</span>")
        self.label.setText(text)
