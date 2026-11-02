"""Players: who is online, operators, whitelist, banned.

- Online players come from the console (the game's join and leave messages).
- The lists are read from the server files (ops.json, whitelist.json, permissions.json...).
- With the server on, actions (op, ban...) are sent as console commands.
- With the server off, the files are edited directly, so the lists change at once. That needs each
  player's id (UUID or XUID): it is taken from the players who already joined, from the server's own
  caches or, for Java, asked to Mojang / GeyserMC. If it can't be known, the action stays pending and
  is sent as a command as soon as the server starts.
"""

import hashlib
import json
import re
import threading
import uuid as uuidlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from ownhost.agent.games.base import read_properties, write_properties

# Java (Vanilla/Paper/Fabric/Forge, with or without Geyser), native Bedrock and Hytale. Since Minecraft 26.x
# the server writes its own messages with a "System chat: " prefix: "[Server thread/INFO]: System chat: Steve joined the game".
JOIN_RE = [
    re.compile(r"\]: (?:System chat: )?(?:\[[^\]]*\] )?(\S{1,40}) joined the game"),
    re.compile(r"Player connected: ([^,]{1,40}), xuid"),
    re.compile(r"\[Universe\|P\] Adding player '(.{1,40}?) \([0-9a-f-]{36}\)"),
]
LEAVE_RE = [
    re.compile(r"\]: (?:System chat: )?(?:\[[^\]]*\] )?(\S{1,40}) left the game"),
    re.compile(r"Player disconnected: ([^,]{1,40}), xuid"),
    re.compile(r"\[Universe\|P\] Removing player '(.{1,40}?)' \("),
]
# Lines that tell a player's id: Bedrock's XUID and Hytale's UUID.
IDENTITY_RE = [
    re.compile(r"Player connected: ([^,]{1,40}), xuid: (\d+)"),
    re.compile(r"\[Universe\|P\] Adding player '(.{1,40}?) \(([0-9a-f-]{36})\)"),
]

ACTIONS = ("op", "deop", "whitelist_add", "whitelist_remove", "ban", "pardon", "kick",
           "whitelist_on", "whitelist_off")
# Valid player names (Java: 3-16 letters/digits/_; Bedrock through Floodgate has a leading "." and may
# contain spaces: native Bedrock quotes them and Java replaces them with "_", like Floodgate does).
NAME_RE = re.compile(r"^\.?[\w .\-]{1,40}$")
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)

# Hytale: the whitelist is a permission, operators a group and the switch a setting of config.json.
HYTALE_JOIN = "hytale.server.join"
HYTALE_OP = "hytale:Admin"


FLOODGATE_CONFIGS = ("plugins/floodgate/config.yml", "config/floodgate/config.yml")  # Paper / Fabric, NeoForge
PREFIX_RE = re.compile(r"""^username-prefix:\s*(?:"([^"]*)"|'([^']*)'|(\S*))""", re.MULTILINE)
_prefix_cache: dict[Path, tuple[float, str]] = {}


def bedrock_prefix(server_dir: Path, crossplay: dict | None) -> str | None:
    """With crossplay through Floodgate, the prefix of Bedrock players' names (by default "."), so
    the app can show who plays on Bedrock and who on Java. None if it can't be known (no Floodgate:
    Bedrock players then sign in with a Java account and look like any other)."""
    if not crossplay or not crossplay.get("floodgate"):
        return None
    for relative in FLOODGATE_CONFIGS:
        path = server_dir / relative
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        cached = _prefix_cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1] or None  # an empty prefix: Bedrock names look like Java ones
        try:
            m = PREFIX_RE.search(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        prefix = next((g for g in m.groups() if g is not None), ".") if m else "."
        _prefix_cache[path] = (mtime, prefix)
        return prefix or None
    return "."  # Floodgate hasn't written its config yet (first start): its default prefix


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


def identity(line: str) -> tuple[str, str] | None:
    """(name, id) if the line tells a player's XUID (Bedrock) or UUID (Hytale)."""
    for rx in IDENTITY_RE:
        if m := rx.search(line):
            return m.group(1), m.group(2)
    return None


class KnownPlayers:
    """Name <-> id of everyone who has joined (Bedrock and Hytale only write ids in their files)."""

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        try:
            self.ids: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))  # name -> id
        except (OSError, ValueError):
            self.ids = {}

    def remember(self, name: str, player_id: str) -> None:
        with self.lock:
            if self.ids.get(name) == player_id:
                return
            for old in [n for n, i in self.ids.items() if i == player_id]:
                del self.ids[old]  # renamed
            self.ids[name] = player_id
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.ids, indent=1), encoding="utf-8")
            except OSError:
                pass

    def seed_from_logs(self, folder: Path) -> None:
        """The first time: the players who joined before this list existed, from the server's old logs."""
        if self.ids or self.path.exists():
            return
        found: dict[str, str] = {}
        logs = sorted((p for p in folder.glob("*.log") if p.is_file()), key=lambda p: p.stat().st_mtime)
        for log in logs[-30:]:
            try:
                with log.open(encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if "player" in line and (hit := identity(line)):
                            found[hit[0]] = hit[1]
            except OSError:
                continue
        for name, player_id in found.items():
            self.remember(name, player_id)
        if not found:
            self.remember_none()

    def remember_none(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")
        except OSError:
            pass

    def id_of(self, name: str) -> str | None:
        if UUID_RE.match(name):
            return name.lower()
        lower = name.lower()
        return next((i for n, i in self.ids.items() if n.lower() == lower), None)

    def name_of(self, player_id: str) -> str:
        return next((n for n, i in self.ids.items() if i == player_id), player_id)


# ---------- reading the lists ----------

def _load(path: Path, default):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _sorted(names) -> list[str]:
    return sorted({n for n in names if n}, key=str.lower)


def _names(path: Path, key: str = "name") -> list[str]:
    return _sorted(e.get(key) for e in _load(path, []) if isinstance(e, dict))


def lists(game_id: str, server_dir: Path, known: KnownPlayers) -> dict:
    """Operators, whitelist and banned players stored by the server."""
    if game_id == "hytale":
        users = _load(server_dir / "permissions.json", {}).get("users") or {}
        bans = _load(server_dir / "bans.json", {}).get("Bans") or []
        config = _load(server_dir / "config.json", {})
        return {"ops": _sorted(known.name_of(u) for u, d in users.items() if HYTALE_OP in (d.get("groups") or [])),
                "whitelist": _sorted(known.name_of(u) for u, d in users.items()
                                     if HYTALE_JOIN in (d.get("permissions") or [])),
                "banned": _sorted(known.name_of(b.get("Target", "")) for b in bans if isinstance(b, dict)),
                "whitelist_enabled": bool(config.get("RequireJoinPermission")),
                "supports": ["op", "deop", "whitelist", "ban", "pardon", "kick"]}
    props = read_properties(server_dir / "server.properties")
    if game_id == "bedrock":
        ops = [known.name_of(e.get("xuid", "")) for e in _load(server_dir / "permissions.json", [])
               if isinstance(e, dict) and e.get("permission") == "operator"]
        return {"ops": _sorted(ops), "whitelist": _names(server_dir / "allowlist.json"), "banned": [],
                "whitelist_enabled": props.get("allow-list", "").strip() == "true",
                "supports": ["op", "deop", "whitelist", "kick"]}
    return {"ops": _names(server_dir / "ops.json"), "whitelist": _names(server_dir / "whitelist.json"),
            "banned": _names(server_dir / "banned-players.json"),
            "whitelist_enabled": props.get("white-list", "").strip() == "true",
            "supports": ["op", "deop", "whitelist", "ban", "pardon", "kick"]}


def with_pending(data: dict, pending: list) -> dict:
    """The lists as they will be once the pending actions are applied (so a name added with the
    server off shows up at once). `pending_names` says which ones are still waiting."""
    keys = {"whitelist_add": ("whitelist", True), "whitelist_remove": ("whitelist", False),
            "op": ("ops", True), "deop": ("ops", False), "ban": ("banned", True), "pardon": ("banned", False)}
    waiting = set()
    for action, name in pending:
        if action in keys:
            key, add = keys[action]
            current = [n for n in data.get(key, []) if n.lower() != name.lower()]
            data[key] = _sorted(current + [name]) if add else current
            if add:
                waiting.add(name)
        elif action in ("whitelist_on", "whitelist_off"):
            data["whitelist_enabled"] = action == "whitelist_on"
    data["pending_names"] = sorted(waiting, key=str.lower)
    return data


# ---------- commands (server on) ----------

def command(game_id: str, action: str, name: str = "") -> str:
    """Console command for an action."""
    if action not in ACTIONS:
        raise ValueError(action)
    if action not in ("whitelist_on", "whitelist_off") and not NAME_RE.match(name) and not UUID_RE.match(name):
        raise ValueError(name)
    if game_id == "hytale":
        return {
            "op": f"/op add {name}", "deop": f"/op remove {name}",
            "whitelist_add": f"/whitelist add {name}", "whitelist_remove": f"/whitelist remove {name}",
            "ban": f"/ban {name}", "pardon": f"/unban {name}", "kick": f"/kick {name}",
            "whitelist_on": "/whitelist enable", "whitelist_off": "/whitelist disable",
        }[action]
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


# ---------- Java ids ----------

def _dashed(hex32: str) -> str:
    return str(uuidlib.UUID(hex=hex32))


def offline_uuid(name: str) -> str:
    """The UUID a server in offline mode gives a name (the same as Java's UUID.nameUUIDFromBytes)."""
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode()).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30
    digest[8] = (digest[8] & 0x3F) | 0x80
    return str(uuidlib.UUID(bytes=bytes(digest)))


def java_profile(server_dir: Path, name: str, prefix: str | None, get_json) -> tuple[str, str] | None:
    """(name, UUID) of a Java server player, or None if it can't be known now.
    `get_json(url)` fetches from the internet (it raises an exception if it can't)."""
    lower = name.lower()
    for entry in _load(server_dir / "usercache.json", []):  # everyone who has joined
        if isinstance(entry, dict) and str(entry.get("name", "")).lower() == lower and entry.get("uuid"):
            return entry["name"], entry["uuid"]
    if prefix and name.startswith(prefix):
        # Bedrock through Floodgate: its UUID comes from the Xbox XUID, which GeyserMC knows.
        gamertag = name[len(prefix):]
        for candidate in dict.fromkeys((gamertag, gamertag.replace("_", " "))):
            try:
                xuid = int(get_json(f"https://api.geysermc.org/v2/xbox/xuid/{quote(candidate)}")["xuid"])
            except Exception:
                continue
            return name.replace(" ", "_"), _dashed(f"{xuid:032x}")
        return None
    props = read_properties(server_dir / "server.properties")
    if props.get("online-mode", "true").strip() == "false":
        return name, offline_uuid(name)
    for url in (f"https://api.minecraftservices.com/minecraft/profile/lookup/name/{quote(name)}",
                f"https://api.mojang.com/users/profiles/minecraft/{quote(name)}"):
        try:
            data = get_json(url)
            return data["name"], _dashed(data["id"])
        except Exception:
            continue
    return None


# ---------- editing the files (server off) ----------

def _drop(entries: list, name: str) -> list:
    return [e for e in entries if not (isinstance(e, dict) and str(e.get("name", "")).lower() == name.lower())]


def edit_offline(game_id: str, server_dir: Path, action: str, name: str, known: KnownPlayers,
                 java_lookup) -> bool:
    """Applies an action editing the server's files. False if it can't (the player's id is unknown):
    then it stays pending. `java_lookup(name)` gives (name, UUID) or None."""
    if action in ("whitelist_on", "whitelist_off"):
        on = action == "whitelist_on"
        if game_id == "hytale":
            path = server_dir / "config.json"
            config = _load(path, {})
            if not config:
                return False  # created on the first start
            config["RequireJoinPermission"] = on
            _save(path, config)
        else:
            key = "allow-list" if game_id == "bedrock" else "white-list"
            write_properties(server_dir / "server.properties", {key: str(on).lower()})
        return True
    if action == "kick":
        return False
    if game_id == "hytale":
        return _edit_hytale(server_dir, action, name, known)
    if game_id == "bedrock":
        return _edit_bedrock(server_dir, action, name, known)
    return _edit_java(server_dir, action, name, java_lookup)


def _edit_java(server_dir: Path, action: str, name: str, java_lookup) -> bool:
    files = {"whitelist_add": "whitelist.json", "whitelist_remove": "whitelist.json", "op": "ops.json",
             "deop": "ops.json", "ban": "banned-players.json", "pardon": "banned-players.json"}
    path = server_dir / files[action]
    entries = _load(path, [])
    if action in ("whitelist_remove", "deop", "pardon"):
        _save(path, _drop(entries, name))
        return True
    profile = java_lookup(name)
    if not profile:
        return False
    real, uuid = profile
    entry = {"uuid": uuid, "name": real}
    if action == "op":
        entry |= {"level": 4, "bypassesPlayerLimit": False}
    elif action == "ban":
        entry |= {"created": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"), "source": "Server",
                  "expires": "forever", "reason": "Banned by an operator."}
    entries = [e for e in _drop(entries, real) if not (isinstance(e, dict) and e.get("uuid") == uuid)]
    _save(path, entries + [entry])
    return True


def _edit_bedrock(server_dir: Path, action: str, name: str, known: KnownPlayers) -> bool:
    if action in ("whitelist_add", "whitelist_remove"):
        path = server_dir / "allowlist.json"
        entries = _drop(_load(path, []), name)
        if action == "whitelist_add":
            # Bedrock fills in the XUID by itself the first time the player joins.
            entries.append({"ignoresPlayerLimit": False, "name": name})
        _save(path, entries)
        return True
    if action not in ("op", "deop"):
        return False
    xuid = known.id_of(name)
    if not xuid:
        return False
    path = server_dir / "permissions.json"
    entries = [e for e in _load(path, []) if not (isinstance(e, dict) and e.get("xuid") == xuid)]
    if action == "op":
        entries.append({"permission": "operator", "xuid": xuid})
    _save(path, entries)
    return True


def _edit_hytale(server_dir: Path, action: str, name: str, known: KnownPlayers) -> bool:
    player = known.id_of(name)
    if not player:
        return False
    if action in ("ban", "pardon"):
        path = server_dir / "bans.json"
        data = _load(path, {}) or {"Version": 1}
        bans = [b for b in data.get("Bans") or [] if not (isinstance(b, dict) and b.get("Target") == player)]
        if action == "ban":
            bans.append({"Target": player, "By": "00000000-0000-0000-0000-000000000000",
                         "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                         "Reason": "No reason."})
        data["Bans"] = bans
        _save(path, data)
        return True
    path = server_dir / "permissions.json"
    data = _load(path, {})
    users = data.setdefault("users", {})
    user = users.setdefault(player, {})
    field, value = ("permissions", HYTALE_JOIN) if action.startswith("whitelist") else ("groups", HYTALE_OP)
    values = [v for v in user.get(field) or [] if v != value]
    if action in ("whitelist_add", "op"):
        values.append(value)
    if values:
        user[field] = values
    else:
        user.pop(field, None)
    if not user:
        users.pop(player, None)
    _save(path, data)
    return True
