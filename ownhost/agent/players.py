"""Players: who is online, operators, whitelist, banned.

- Online players come from the console (the game's join and leave messages).
- The lists are read from the server files (ops.json, whitelist.json...).
- Actions (op, ban...) are sent as console commands. If the server is stopped they stay pending and
  are applied as soon as it starts: that way nobody's UUID is needed.
"""

import json
import re
from pathlib import Path

# Java (Vanilla/Paper/Fabric/Forge, with or without Geyser) and native Bedrock. Since Minecraft 26.x the
# server writes its own messages with a "System chat: " prefix: "[Server thread/INFO]: System chat: Steve joined the game".
JOIN_RE = [
    re.compile(r"\]: (?:System chat: )?(?:\[[^\]]*\] )?(\S{1,40}) joined the game"),
    re.compile(r"Player connected: ([^,]{1,40}), xuid"),
]
LEAVE_RE = [
    re.compile(r"\]: (?:System chat: )?(?:\[[^\]]*\] )?(\S{1,40}) left the game"),
    re.compile(r"Player disconnected: ([^,]{1,40}), xuid"),
]

ACTIONS = ("op", "deop", "whitelist_add", "whitelist_remove", "ban", "pardon", "kick",
           "whitelist_on", "whitelist_off")
# Valid player names (Java: 3-16 letters/digits/_; Bedrock through Floodgate has a leading "." and may
# contain spaces: native Bedrock quotes them and Java replaces them with "_", like Floodgate does).
NAME_RE = re.compile(r"^\.?[\w .\-]{1,32}$")


def track(online: set[str], line: str) -> bool:
    """Updates `online` with a console line. Returns True if it changed."""
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
    """Operators, whitelist and banned players stored by the server."""
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
    """Console command for an action."""
    if action not in ACTIONS:
        raise ValueError(action)
    if action not in ("whitelist_on", "whitelist_off") and not NAME_RE.match(name):
        raise ValueError(name)
    if game_id == "bedrock":
        who = f'"{name}"' if " " in name else name
    else:
        # Java does not allow quotes or spaces: Floodgate replaces spaces in Bedrock names with "_".
        who = name.replace(" ", "_")
    allow = "allowlist" if game_id == "bedrock" else "whitelist"
    return {
        "op": f"op {who}", "deop": f"deop {who}",
        "whitelist_add": f"{allow} add {who}", "whitelist_remove": f"{allow} remove {who}",
        "ban": f"ban {who}", "pardon": f"pardon {who}", "kick": f"kick {who}",
        "whitelist_on": f"{allow} on", "whitelist_off": f"{allow} off",
    }[action]
