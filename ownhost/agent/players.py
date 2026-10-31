"""Jugadores: quién está conectado, operadores, lista blanca, baneados.

- Los conectados se sacan de la consola (mensajes de entrada y salida del juego).
- Las listas se leen de los archivos del servidor (ops.json, whitelist.json...).
- Las acciones (dar op, banear...) se mandan como comandos de consola. Si el servidor está apagado
  quedan pendientes y se aplican en cuanto se enciende: así no hace falta saber el UUID de nadie.
"""

import json
import re
from pathlib import Path

# Java (Vanilla/Paper/Fabric/Forge, con o sin Geyser) y Bedrock nativo
JOIN_RE = [
    re.compile(r"\]: (?:\[[^\]]*\] )?(\S{1,40}) joined the game"),
    re.compile(r"Player connected: ([^,]{1,40}), xuid"),
]
LEAVE_RE = [
    re.compile(r"\]: (?:\[[^\]]*\] )?(\S{1,40}) left the game"),
    re.compile(r"Player disconnected: ([^,]{1,40}), xuid"),
]

ACTIONS = ("op", "deop", "whitelist_add", "whitelist_remove", "ban", "pardon", "kick",
           "whitelist_on", "whitelist_off")
# Nombres de jugador válidos (Java: 3-16 letras/números/_; Bedrock con Floodgate lleva un "." delante
# y puede tener espacios: en Bedrock nativo se ponen comillas y en Java se cambian por «_», como Floodgate).
NAME_RE = re.compile(r"^\.?[\w .\-]{1,32}$")


def track(online: set[str], line: str) -> bool:
    """Actualiza `online` con una línea de consola. Devuelve True si ha cambiado."""
    for rx in JOIN_RE:
        if m := rx.search(line):
            online.add(m.group(1))
            return True
    for rx in LEAVE_RE:
        if m := rx.search(line):
            online.discard(m.group(1))
            return True
    return False


def _names(path: Path, key: str = "name") -> list[str]:
    try:
        return sorted({e.get(key) for e in json.loads(path.read_text(encoding="utf-8")) if e.get(key)},
                      key=str.lower)
    except (OSError, ValueError, AttributeError):
        return []


def lists(game_id: str, server_dir: Path) -> dict:
    """Operadores, lista blanca y baneados que el servidor tiene guardados."""
    props = server_dir / "server.properties"
    text = props.read_text(encoding="utf-8", errors="replace") if props.exists() else ""
    if game_id == "bedrock":
        on = re.search(r"^allow-list=true", text, re.MULTILINE) is not None
        return {"ops": [], "whitelist": _names(server_dir / "allowlist.json"), "banned": [],
                "whitelist_enabled": on, "supports": ["op", "deop", "whitelist", "kick"]}
    on = re.search(r"^white-list=true", text, re.MULTILINE) is not None
    return {"ops": _names(server_dir / "ops.json"), "whitelist": _names(server_dir / "whitelist.json"),
            "banned": _names(server_dir / "banned-players.json"), "whitelist_enabled": on,
            "supports": ["op", "deop", "whitelist", "ban", "pardon", "kick"]}


def command(game_id: str, action: str, name: str = "") -> str:
    """Comando de consola para una acción."""
    if action not in ACTIONS:
        raise ValueError(action)
    if action not in ("whitelist_on", "whitelist_off") and not NAME_RE.match(name):
        raise ValueError(name)
    if game_id == "bedrock":
        who = f'"{name}"' if " " in name else name
    else:
        # Java no admite comillas ni espacios: Floodgate cambia los espacios de los nombres de Bedrock por «_».
        who = name.replace(" ", "_")
    allow = "allowlist" if game_id == "bedrock" else "whitelist"
    return {
        "op": f"op {who}", "deop": f"deop {who}",
        "whitelist_add": f"{allow} add {who}", "whitelist_remove": f"{allow} remove {who}",
        "ban": f"ban {who}", "pardon": f"pardon {who}", "kick": f"kick {who}",
        "whitelist_on": f"{allow} on", "whitelist_off": f"{allow} off",
    }[action]
