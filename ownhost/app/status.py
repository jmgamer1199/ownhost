from ownhost.i18n import tr

# Spanish labels (the catalog keys): show them with tr(label). Colours as in theme.py.
STATUS = {
    "stopped": ("Apagado", "#ff5c5c"),
    "starting": ("Arrancando", "#f5a524"),
    "running": ("Encendido", "#4ade80"),
    "stopping": ("Apagando", "#f5a524"),
    "crashed": ("Caído", "#ff5c5c"),
    "installing": ("Instalando", "#22d3ee"),
    "updating": ("Actualizando", "#22d3ee"),
    "backing-up": ("Haciendo copia", "#22d3ee"),
    "restoring": ("Restaurando", "#22d3ee"),
    "importing": ("Importando", "#22d3ee"),
    "installing-mod": ("Instalando mods", "#22d3ee"),
    "cloning": ("Clonando", "#22d3ee"),
}


def format_uptime(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    return tr("encendido {hours} h {minutes} min", hours=h, minutes=m) if h else tr("encendido {minutes} min", minutes=m)


# What each game supports. Agents older than this version don't say it: what they supported is assumed.
OLD_SETTING_KEYS = {"minecraft": {"motd": "motd", "max_players": "max-players"},
                    "bedrock": {"max_players": "max-players"}}


def players_supported(server: dict) -> bool:
    """Whether the agent knows who plays on this server ("Players" tab, stats, stop if nobody plays)."""
    return server.get("players_supported", server.get("game") in ("minecraft", "bedrock"))


def setting_keys(server: dict) -> dict[str, str]:
    """Where the description ("motd") and the player limit ("max_players") are in its configuration."""
    keys = server.get("setting_keys")
    return keys if keys is not None else OLD_SETTING_KEYS.get(server.get("game"), {})
