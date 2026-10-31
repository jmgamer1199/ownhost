"""Crossplay with Geyser: Bedrock players (phone, console, Windows) on Java servers.

Geyser translates the Bedrock protocol and listens on its own UDP port (19132 by default).
Floodgate lets Bedrock players join without a Java account.
"""

import json
import re
from pathlib import Path

from ownhost.agent import mods
from ownhost.agent.downloads import Log, download, get_json
from ownhost.agent.errors import UserError
from ownhost.agent.mods import ModTarget
from ownhost.i18n import tr

GEYSER = "wKkoqHrH"       # projects on Modrinth
FLOODGATE = "bWrNNfkb"
VIAVERSION = "P1OZGk5p"
FLOODGATE_SPIGOT = "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot"
DEFAULT_BEDROCK_PORT = 19132
SUPPORTED = ("paper", "fabric", "neoforge")

# Where Geyser stores its configuration on each platform.
CONFIG_PATHS = {
    "paper": Path("plugins") / "Geyser-Spigot" / "config.yml",
    "fabric": Path("config") / "Geyser-Fabric" / "config.yml",
    "neoforge": Path("config") / "Geyser-NeoForge" / "config.yml",
}


def check_supported(flavor: str) -> None:
    if flavor not in SUPPORTED:
        raise UserError(tr("Geyser solo funciona con servidores Paper, Fabric o NeoForge. "
                           "Crea uno de esos tipos para tener multiplataforma."))


def install(flavor: str, target: ModTarget, game_version: str, latest_release: str, folder: Path,
            floodgate: bool, log: Log) -> list[str]:
    """Installs Geyser (and Floodgate/ViaVersion if needed). Returns the files added."""
    check_supported(flavor)
    log(tr("Instalando Geyser para jugadores de Bedrock..."))
    try:
        added = mods.install("modrinth", GEYSER, target, game_version, folder, None, log)
    except UserError:
        raise UserError(tr("Geyser no tiene versión para {flavor} {version}. "
                           "Prueba con un servidor Paper o con una versión más reciente.",
                           flavor=flavor, version=game_version)) from None
    if flavor == "paper" and game_version != latest_release:
        # Geyser speaks the latest Java version's protocol; ViaVersion acts as a bridge.
        log(tr("El servidor no es de la última versión: instalando ViaVersion para Geyser..."))
        added += mods.install("modrinth", VIAVERSION, target, game_version, folder, None, log)
    if floodgate:
        log(tr("Instalando Floodgate (entrar sin cuenta de Java)..."))
        if flavor == "paper":
            added.append(_install_floodgate_spigot(folder, log))
        else:
            added += mods.install("modrinth", FLOODGATE, target, game_version, folder, None, log)
    return added


def _install_floodgate_spigot(folder: Path, log: Log) -> str:
    # Floodgate for Paper is not on Modrinth: GeyserMC's official download is used.
    name = "floodgate-spigot.jar"
    download(FLOODGATE_SPIGOT, folder / name, log)
    meta = mods.load_metadata(folder)
    meta[name] = {"source": "geysermc", "project_id": "floodgate", "title": "Floodgate", "version": "latest"}
    (folder / mods.METADATA_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return name


def set_bedrock_port(server_dir: Path, flavor: str, port: int) -> None:
    """Configures the Bedrock ports and transport in Geyser.

    - `port`: RakNet (UDP) and NetherNet signaling (TCP).
    - `webrtc-port` = port + 1: the game over NetherNet (UDP).
    - `transport: both`: speaks NetherNet (Bedrock 26.60+) and RakNet at the same time. With NetherNet
      only, Geyser does not answer the classic LAN game discovery and consoles (Switch...) do not see
      the server in the Friends tab.

    If Geyser has never started yet, a minimal configuration is created: Geyser fills in the
    remaining options with their defaults the first time it loads.
    """
    path = server_dir / CONFIG_PATHS[flavor]
    wanted = {"port": str(port), "webrtc-port": str(port + 1), "transport": "both"}
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("bedrock:\n" + "".join(f"  {k}: {v}\n" for k, v in wanted.items()), encoding="utf-8")
        return
    text = path.read_text(encoding="utf-8")
    original = text
    for key, value in wanted.items():
        text = _set_bedrock_key(text, key, value)
    if text != original:
        path.write_text(text, encoding="utf-8")


def _set_bedrock_key(text: str, key: str, value: str) -> str:
    """Changes (or adds) a top-level key inside the `bedrock:` section of the YAML."""
    return _set_key(text, "bedrock", key, value)


def _section(text: str, section: str) -> re.Match | None:
    return re.search(rf"^{re.escape(section)}:[ \t]*\n((?:[ \t]+.*\n|[ \t]*\n)*)", text, flags=re.MULTILINE)


def _indent(body: str) -> str:
    """Indentation of a section's keys (that of its first non-empty line)."""
    for line in body.splitlines():
        if line.strip():
            return re.match(r"[ \t]*", line).group(0) or "  "
    return "  "


def _key_re(indent: str, key: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(indent)}{re.escape(key)}:[ \t]*(.*)$", flags=re.MULTILINE)


def _get_key(text: str, section: str | None, key: str) -> str | None:
    """Reads a top-level key (section=None) or a section key. Returns the text without quotes."""
    if section is None:
        found = _key_re("", key).search(text)
    else:
        sec = _section(text, section)
        found = _key_re(_indent(sec.group(1)), key).search(sec.group(1)) if sec else None
    return _unquote(found.group(1)) if found else None


def _set_key(text: str, section: str | None, key: str, value: str) -> str:
    """Changes (or adds) a top-level key (section=None) or one inside a section of the YAML."""
    if text and not text.endswith("\n"):
        text += "\n"
    if section is None:
        line = _key_re("", key)
        return line.sub(lambda _: f"{key}: {value}", text, count=1) if line.search(text) \
            else text + f"{key}: {value}\n"
    sec = _section(text, section)
    if not sec:
        return text + f"{section}:\n  {key}: {value}\n"
    body = sec.group(1)
    indent = _indent(body)
    line = _key_re(indent, key)
    new_body = line.sub(lambda _: f"{indent}{key}: {value}", body, count=1) if line.search(body) \
        else f"{indent}{key}: {value}\n" + body
    return text[:sec.start(1)] + new_body + text[sec.end(1):]


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    return re.sub(r"\s+#.*$", "", raw)  # comment at the end of the line


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------- what Bedrock players see (description, name, players...) ----------
#
# Geyser changed its configuration format in version 5 (`config-version`): options that used to be
# top-level or inside `bedrock:` moved to the `motd:` and `gameplay:` sections.
# If the file does not state its version (Geyser has never started yet) the old format is written:
# old versions read it as is and new ones migrate it by themselves on start.

# Ownhost key -> (section and key in the new format, section and key in the old one, type)
APPEARANCE = {
    "server_name": (("gameplay", "server-name"), ("bedrock", "server-name"), str),
    "motd1": (("motd", "primary-motd"), ("bedrock", "motd1"), str),
    "motd2": (("motd", "secondary-motd"), ("bedrock", "motd2"), str),
    "passthrough_motd": (("motd", "passthrough-motd"), (None, "passthrough-motd"), bool),
    "max_players": (("motd", "max-players"), (None, "max-players"), int),
    "passthrough_player_counts": (("motd", "passthrough-player-counts"), (None, "passthrough-player-counts"), bool),
    "show_coordinates": (("gameplay", "show-coordinates"), (None, "show-coordinates"), bool),
    "command_suggestions": (("gameplay", "command-suggestions"), (None, "command-suggestions"), bool),
    "emotes_enabled": (("gameplay", "emotes-enabled"), (None, "emotes-enabled"), bool),  # new format only
}
APPEARANCE_DEFAULTS = {
    "server_name": "Geyser", "motd1": "Geyser", "motd2": "Another Geyser server.",
    "passthrough_motd": True, "max_players": 100, "passthrough_player_counts": True,
    "show_coordinates": True, "command_suggestions": True, "emotes_enabled": True,
}


def _new_format(text: str) -> bool:
    version = _get_key(text, None, "config-version")
    return bool(version and version.isdigit() and int(version) >= 5)


def get_appearance(server_dir: Path, flavor: str) -> dict:
    """What Geyser shows Bedrock players, with Geyser's defaults."""
    path = server_dir / CONFIG_PATHS[flavor]
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    new = _new_format(text)
    result = dict(APPEARANCE_DEFAULTS)
    for name, (new_loc, old_loc, kind) in APPEARANCE.items():
        if name == "emotes_enabled" and not new:
            continue  # does not exist in the old format: the default is kept
        raw = _get_key(text, *(new_loc if new else old_loc))
        if raw is None or raw == "":
            continue
        if kind is bool:
            result[name] = raw.lower() == "true"
        elif kind is int:
            result[name] = int(raw) if raw.lstrip("-").isdigit() else result[name]
        else:
            result[name] = raw
    return result


def set_appearance(server_dir: Path, flavor: str, values: dict) -> None:
    """Saves the received options (only known ones) in the Geyser configuration."""
    path = server_dir / CONFIG_PATHS[flavor]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    new = _new_format(text)
    for name, value in values.items():
        if name not in APPEARANCE or (name == "emotes_enabled" and not new):
            continue
        new_loc, old_loc, kind = APPEARANCE[name]
        if kind is bool:
            raw = "true" if value else "false"
        elif kind is int:
            raw = str(max(1, int(value)))
        else:
            raw = _quote(str(value).replace("\n", " ").strip())
        text = _set_key(text, *(new_loc if new else old_loc), raw)
    path.write_text(text, encoding="utf-8")


def sync_appearance(server_dir: Path, flavor: str, name: str, java_motd: str, java_max_players: int) -> None:
    """What Bedrock players see, same as on Java. Called on every start.

    Geyser's "automatic" copy (passthrough) does not work with Paper 26.x: the integrated one copies
    nothing and the network one leaves the description in quotes. So the description and player limit
    are copied here from server.properties, and Geyser only asks the Java server (over the network,
    the method that works) how many players are online.
    """
    first_line = java_motd.split("\n")[0].strip() or name
    set_appearance(server_dir, flavor, {
        "server_name": name,
        "motd1": first_line,
        "motd2": name,  # second line: on Bedrock's LAN list it shows as the game name
        "max_players": java_max_players,
        "passthrough_motd": False,
        "passthrough_player_counts": True,
    })
    path = server_dir / CONFIG_PATHS[flavor]
    text = path.read_text(encoding="utf-8")
    if _new_format(text):
        text = _set_key(text, "motd", "integrated-ping-passthrough", "false")
    else:
        text = _set_key(text, None, "legacy-ping-passthrough", "true")  # old name of the same thing
    path.write_text(text, encoding="utf-8")


def decode_motd(raw: str) -> str:
    """The server.properties motd as Java stores it (\\uXXXX, \\n, \\:, \\=)."""
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    return raw.replace("\\n", "\n").replace("\\:", ":").replace("\\=", "=").replace("\\\\", "\\")


def remove(folder: Path, files: list[str]) -> None:
    for name in files:
        mods.remove(folder, name)


# ---------- Geyser extras (extensions in Geyser's `extensions` folder) ----------
#
# The pack that brings Bedrock closer to Java (GeyserIntegratedPack, formerly GeyserOptionalPack) is
# already included in Geyser: no need to install it.

GEYSERMC_API = "https://download.geysermc.org/v2/projects"
EXTRAS = {
    # Makes the server appear in the consoles' Friends tab through Xbox Live.
    "xbox": {"source": "github", "repo": "MCXboxBroadcast/Broadcaster", "asset": "MCXboxBroadcastExtension.jar"},
    # Shows Bedrock players the capes and ears of Java players.
    "cosmetics": {"source": "geysermc", "project": "thirdpartycosmetics"},
    # Bedrock players swap the off-hand item with an emote.
    "emote_offhand": {"source": "geysermc", "project": "emoteoffhand"},
}


def extensions_dir(server_dir: Path, flavor: str) -> Path:
    return server_dir / CONFIG_PATHS[flavor].parent / "extensions"


def _latest_geysermc(project: str) -> tuple[str, str]:
    versions = [v for v in get_json(f"{GEYSERMC_API}/{project}")["versions"] if v]
    version = versions[-1]
    build = get_json(f"{GEYSERMC_API}/{project}/versions/{version}/builds")["builds"][-1]
    key, info = next(iter(build["downloads"].items()))
    return f"{GEYSERMC_API}/{project}/versions/{version}/builds/{build['build']}/downloads/{key}", info["name"]


def _latest_github(repo: str, asset: str) -> tuple[str, str]:
    release = get_json(f"https://api.github.com/repos/{repo}/releases/latest")
    url = next(a["browser_download_url"] for a in release["assets"] if a["name"] == asset)
    return url, asset


def install_extra(key: str, server_dir: Path, flavor: str, log: Log) -> str:
    """Downloads the latest version of an extra into the extensions folder. Returns the file name."""
    spec = EXTRAS.get(key)
    if not spec:
        raise UserError(tr("Extra desconocido: {key}", key=key))
    check_supported(flavor)
    if spec["source"] == "github":
        url, name = _latest_github(spec["repo"], spec["asset"])
    else:
        url, name = _latest_geysermc(spec["project"])
    download(url, extensions_dir(server_dir, flavor) / name, log)
    return name


def remove_extra(server_dir: Path, flavor: str, filename: str) -> None:
    (extensions_dir(server_dir, flavor) / Path(filename).name).unlink(missing_ok=True)
