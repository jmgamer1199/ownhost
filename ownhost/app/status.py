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
