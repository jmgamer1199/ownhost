"""Multiplataforma con Geyser: jugadores de Bedrock (móvil, consola, Windows) en servidores Java.

Geyser traduce el protocolo de Bedrock y escucha en un puerto UDP propio (19132 por defecto).
Floodgate permite entrar a los jugadores de Bedrock sin tener cuenta de Java.
"""

import json
import re
from pathlib import Path

from ownhost.agent import mods
from ownhost.agent.downloads import Log, download, get_json
from ownhost.agent.errors import UserError
from ownhost.agent.mods import ModTarget

GEYSER = "wKkoqHrH"       # proyectos en Modrinth
FLOODGATE = "bWrNNfkb"
VIAVERSION = "P1OZGk5p"
FLOODGATE_SPIGOT = "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot"
DEFAULT_BEDROCK_PORT = 19132
SUPPORTED = ("paper", "fabric", "neoforge")

# Dónde guarda Geyser su configuración en cada plataforma.
CONFIG_PATHS = {
    "paper": Path("plugins") / "Geyser-Spigot" / "config.yml",
    "fabric": Path("config") / "Geyser-Fabric" / "config.yml",
    "neoforge": Path("config") / "Geyser-NeoForge" / "config.yml",
}


def check_supported(flavor: str) -> None:
    if flavor not in SUPPORTED:
        raise UserError("Geyser solo funciona con servidores Paper, Fabric o NeoForge. "
                        "Crea uno de esos tipos para tener multiplataforma.")


def install(flavor: str, target: ModTarget, game_version: str, latest_release: str, folder: Path,
            floodgate: bool, log: Log) -> list[str]:
    """Instala Geyser (y Floodgate/ViaVersion si hacen falta). Devuelve los archivos añadidos."""
    check_supported(flavor)
    log("Instalando Geyser para jugadores de Bedrock...")
    try:
        added = mods.install("modrinth", GEYSER, target, game_version, folder, None, log)
    except UserError:
        raise UserError(f"Geyser no tiene versión para {flavor} {game_version}. "
                        "Prueba con un servidor Paper o con una versión más reciente.") from None
    if flavor == "paper" and game_version != latest_release:
        # Geyser habla el protocolo de la última versión de Java; ViaVersion hace de puente.
        log("El servidor no es de la última versión: instalando ViaVersion para Geyser...")
        added += mods.install("modrinth", VIAVERSION, target, game_version, folder, None, log)
    if floodgate:
        log("Instalando Floodgate (entrar sin cuenta de Java)...")
        if flavor == "paper":
            added.append(_install_floodgate_spigot(folder, log))
        else:
            added += mods.install("modrinth", FLOODGATE, target, game_version, folder, None, log)
    return added


def _install_floodgate_spigot(folder: Path, log: Log) -> str:
    # Floodgate para Paper no está en Modrinth: se usa la descarga oficial de GeyserMC.
    name = "floodgate-spigot.jar"
    download(FLOODGATE_SPIGOT, folder / name, log)
    meta = mods.load_metadata(folder)
    meta[name] = {"source": "geysermc", "project_id": "floodgate", "title": "Floodgate", "version": "latest"}
    (folder / mods.METADATA_FILE).write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return name


def set_bedrock_port(server_dir: Path, flavor: str, port: int) -> None:
    """Configura los puertos y el transporte de Bedrock en Geyser.

    - `port`: RakNet (UDP) y señalización de NetherNet (TCP).
    - `webrtc-port` = port + 1: el juego por NetherNet (UDP).
    - `transport: both`: habla NetherNet (Bedrock 26.60+) y RakNet a la vez. Con solo NetherNet,
      Geyser no responde a la búsqueda clásica de partidas en red local y las consolas (Switch...)
      no ven el servidor en la pestaña de Amigos.

    Si Geyser aún no ha arrancado nunca, se crea una configuración mínima: Geyser completa
    el resto de opciones con sus valores por defecto la primera vez que se carga.
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
    """Cambia (o añade) una clave de primer nivel dentro de la sección `bedrock:` del YAML."""
    return _set_key(text, "bedrock", key, value)


def _section(text: str, section: str) -> re.Match | None:
    return re.search(rf"^{re.escape(section)}:[ \t]*\n((?:[ \t]+.*\n|[ \t]*\n)*)", text, flags=re.MULTILINE)


def _indent(body: str) -> str:
    """Sangría de las claves de una sección (la de su primera línea con contenido)."""
    for line in body.splitlines():
        if line.strip():
            return re.match(r"[ \t]*", line).group(0) or "  "
    return "  "


def _key_re(indent: str, key: str) -> re.Pattern:
    return re.compile(rf"^{re.escape(indent)}{re.escape(key)}:[ \t]*(.*)$", flags=re.MULTILINE)


def _get_key(text: str, section: str | None, key: str) -> str | None:
    """Lee una clave de primer nivel (section=None) o de una sección. Devuelve el texto sin comillas."""
    if section is None:
        found = _key_re("", key).search(text)
    else:
        sec = _section(text, section)
        found = _key_re(_indent(sec.group(1)), key).search(sec.group(1)) if sec else None
    return _unquote(found.group(1)) if found else None


def _set_key(text: str, section: str | None, key: str, value: str) -> str:
    """Cambia (o añade) una clave de primer nivel (section=None) o dentro de una sección del YAML."""
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
    return re.sub(r"\s+#.*$", "", raw)  # comentario al final de la línea


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------- lo que ven los jugadores de Bedrock (descripción, nombre, jugadores...) ----------
#
# Geyser cambió el formato de su configuración en la versión 5 (`config-version`): las opciones que
# antes estaban sueltas o dentro de `bedrock:` pasaron a las secciones `motd:` y `gameplay:`.
# Si el archivo no dice su versión (Geyser aún no ha arrancado nunca) se escribe en el formato
# antiguo: las versiones antiguas lo leen tal cual y las nuevas lo migran solas al arrancar.

# clave de Ownhost -> (sección y clave en el formato nuevo, sección y clave en el antiguo, tipo)
APPEARANCE = {
    "server_name": (("gameplay", "server-name"), ("bedrock", "server-name"), str),
    "motd1": (("motd", "primary-motd"), ("bedrock", "motd1"), str),
    "motd2": (("motd", "secondary-motd"), ("bedrock", "motd2"), str),
    "passthrough_motd": (("motd", "passthrough-motd"), (None, "passthrough-motd"), bool),
    "max_players": (("motd", "max-players"), (None, "max-players"), int),
    "passthrough_player_counts": (("motd", "passthrough-player-counts"), (None, "passthrough-player-counts"), bool),
    "show_coordinates": (("gameplay", "show-coordinates"), (None, "show-coordinates"), bool),
    "command_suggestions": (("gameplay", "command-suggestions"), (None, "command-suggestions"), bool),
    "emotes_enabled": (("gameplay", "emotes-enabled"), (None, "emotes-enabled"), bool),  # solo formato nuevo
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
    """Lo que Geyser enseña a los jugadores de Bedrock, con los valores por defecto de Geyser."""
    path = server_dir / CONFIG_PATHS[flavor]
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    new = _new_format(text)
    result = dict(APPEARANCE_DEFAULTS)
    for name, (new_loc, old_loc, kind) in APPEARANCE.items():
        if name == "emotes_enabled" and not new:
            continue  # en el formato antiguo no existe: se deja el valor por defecto
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
    """Guarda en la configuración de Geyser las opciones recibidas (solo las conocidas)."""
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
    """Lo que ven los jugadores de Bedrock, igual que en Java. Se llama en cada arranque.

    La copia «automática» de Geyser (passthrough) no sirve con Paper 26.x: la integrada no copia
    nada y la de red deja la descripción entre comillas. Por eso la descripción y el límite de
    jugadores se copian aquí desde server.properties, y Geyser solo pregunta al servidor de Java
    (por la red, el método que funciona) cuántos jugadores hay conectados.
    """
    first_line = java_motd.split("\n")[0].strip() or name
    set_appearance(server_dir, flavor, {
        "server_name": name,
        "motd1": first_line,
        "motd2": name,  # segunda línea: en la red local de Bedrock se ve como nombre de la partida
        "max_players": java_max_players,
        "passthrough_motd": False,
        "passthrough_player_counts": True,
    })
    path = server_dir / CONFIG_PATHS[flavor]
    text = path.read_text(encoding="utf-8")
    if _new_format(text):
        text = _set_key(text, "motd", "integrated-ping-passthrough", "false")
    else:
        text = _set_key(text, None, "legacy-ping-passthrough", "true")  # nombre antiguo de lo mismo
    path.write_text(text, encoding="utf-8")


def decode_motd(raw: str) -> str:
    """El motd de server.properties tal cual lo guarda Java (\\uXXXX, \\n, \\:, \\=)."""
    raw = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    return raw.replace("\\n", "\n").replace("\\:", ":").replace("\\=", "=").replace("\\\\", "\\")


def remove(folder: Path, files: list[str]) -> None:
    for name in files:
        mods.remove(folder, name)


# ---------- extras de Geyser (extensiones en la carpeta `extensions` de Geyser) ----------
#
# El paquete que acerca Bedrock a Java (GeyserIntegratedPack, antes GeyserOptionalPack) ya viene
# dentro de Geyser: no hace falta instalarlo.

GEYSERMC_API = "https://download.geysermc.org/v2/projects"
EXTRAS = {
    # Hace que el servidor aparezca en la pestaña Amigos de las consolas a través de Xbox Live.
    "xbox": {"source": "github", "repo": "MCXboxBroadcast/Broadcaster", "asset": "MCXboxBroadcastExtension.jar"},
    # Muestra a los jugadores de Bedrock las capas y orejas de los jugadores de Java.
    "cosmetics": {"source": "geysermc", "project": "thirdpartycosmetics"},
    # Los jugadores de Bedrock cambian el objeto de la mano secundaria haciendo un gesto.
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
    """Descarga la última versión de un extra en la carpeta de extensiones. Devuelve el nombre del archivo."""
    spec = EXTRAS.get(key)
    if not spec:
        raise UserError(f"Extra desconocido: {key}")
    check_supported(flavor)
    if spec["source"] == "github":
        url, name = _latest_github(spec["repo"], spec["asset"])
    else:
        url, name = _latest_geysermc(spec["project"])
    download(url, extensions_dir(server_dir, flavor) / name, log)
    return name


def remove_extra(server_dir: Path, flavor: str, filename: str) -> None:
    (extensions_dir(server_dir, flavor) / Path(filename).name).unlink(missing_ok=True)
