STATUS = {
    "stopped": ("Apagado", "#7f8c8d"),
    "starting": ("Arrancando", "#e67e22"),
    "running": ("Encendido", "#27ae60"),
    "stopping": ("Apagando", "#e67e22"),
    "crashed": ("Caído", "#c0392b"),
    "installing": ("Instalando", "#2980b9"),
    "updating": ("Actualizando", "#2980b9"),
    "backing-up": ("Haciendo copia", "#2980b9"),
    "restoring": ("Restaurando", "#2980b9"),
    "importing": ("Importando", "#2980b9"),
    "installing-mod": ("Instalando mods", "#2980b9"),
    "cloning": ("Clonando", "#2980b9"),
}


def format_uptime(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    return f"encendido {h} h {m} min" if h else f"encendido {m} min"
