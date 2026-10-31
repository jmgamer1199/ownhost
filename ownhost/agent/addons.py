"""One-click add-ons: web map of the world (BlueMap) and pregeneration (Chunky).

Both exist as a Paper plugin and as a Fabric, Forge and NeoForge mod, and are downloaded from Modrinth.
"""

import re
from pathlib import Path

from ownhost.agent.errors import UserError
from ownhost.i18n import tr

MAP_PROJECT = "bluemap"
PREGEN_PROJECT = "chunky"
DEFAULT_MAP_PORT = 8100
SUPPORTED = ("paper", "fabric", "forge", "neoforge")

# Chunky writes things like:
#   [Chunky] Task running for minecraft:overworld. Processed: 3000 chunks (11.94%), ETA: 0:01:15, Rate: ...
#   [Chunky] Task finished for minecraft:overworld. Processed: 25129 chunks (100.00%), Total time: 0:10:21
CHUNKY_RE = re.compile(r"Task (running|finished|stopped|cancelled|paused) for (\S+?)\.? Processed: (\d+) chunks "
                       r"\(([\d.,]+)%\)(?:, ETA: ([\d:]+))?", re.IGNORECASE)


def check_supported(flavor: str) -> None:
    if flavor not in SUPPORTED:
        raise UserError(tr("Solo está disponible en servidores Paper, Fabric, Forge o NeoForge"))


def bluemap_dir(server_dir: Path, flavor: str) -> Path:
    return server_dir / ("plugins/BlueMap" if flavor == "paper" else "config/bluemap")


def configure_map(server_dir: Path, flavor: str, port: int) -> None:
    """Before each start: accepts the download of Mojang's resources (BlueMap needs it to draw the map)
    and sets the web port. If BlueMap has not created its configuration yet, a minimal one is created."""
    folder = bluemap_dir(server_dir, flavor)
    folder.mkdir(parents=True, exist_ok=True)
    _set(folder / "core.conf", r"^(\s*accept-download\s*:\s*).*$", "accept-download: true", r"\g<1>true")
    _set(folder / "webserver.conf", r"^(\s*port\s*:\s*)\d+.*$", f"port: {port}", rf"\g<1>{port}")


def _set(path: Path, pattern: str, line: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    regex = re.compile(pattern, re.MULTILINE)
    if regex.search(text):
        text = regex.sub(replacement, text, count=1)
    else:
        text = (text.rstrip() + "\n" if text.strip() else "") + line + "\n"
    path.write_text(text, encoding="utf-8")


def parse_chunky(line: str) -> dict | None:
    m = CHUNKY_RE.search(line)
    if not m:
        return None
    state, world, chunks, percent, eta = m.groups()
    # Depending on the system language, Java writes "64,89%" or "64.89%".
    return {"state": state.lower(), "world": world, "chunks": int(chunks),
            "percent": float(percent.replace(",", ".")), "eta": eta}
