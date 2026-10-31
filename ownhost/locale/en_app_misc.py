"""English texts of the app's helper modules and the Mods and Players tabs (ownhost/app: mods_tab, players_tab,
replicas, memory, world_import, transfer, firewall, status, client)."""

STRINGS = {
    # ---------- status.py (STATUS labels and uptime) ----------
    "Apagado": "Stopped",
    "Arrancando": "Starting",
    "Encendido": "Running",
    "Apagando": "Stopping",
    "Caído": "Crashed",
    "Instalando": "Installing",
    "Actualizando": "Updating",
    "Haciendo copia": "Backing up",
    "Restaurando": "Restoring",
    "Importando": "Importing",
    "Instalando mods": "Installing mods",
    "Clonando": "Cloning",
    "encendido {hours} h {minutes} min": "up {hours} h {minutes} min",
    "encendido {minutes} min": "up {minutes} min",

    # ---------- mods_tab.py ----------
    "Modrinth": "Modrinth",
    "CurseForge": "CurseForge",
    "Modpack": "Modpack",
    "Manual": "Manual",
    "Nombre": "Name",
    "Versión": "Version",
    "Origen": "Source",
    "Estado": "Status",
    "Autor": "Author",
    "Descargas": "Downloads",
    "Descripción": "Description",
    "Activar / desactivar": "Enable / disable",
    "Eliminar": "Delete",
    "Buscar actualizaciones": "Check for updates",
    "Busca versiones nuevas de los mods para esta versión de Minecraft":
        "Looks for new versions of the mods for this Minecraft version",
    "Reinicia el servidor para aplicar los cambios.": "Restart the server to apply the changes.",
    "Buscar (déjalo vacío para ver los más populares)": "Search (leave it empty to see the most popular)",
    "Buscar": "Search",
    "Ver en la web": "View on the web",
    "Instalar": "Install",
    "<b>Buscar e instalar</b>": "<b>Search and install</b>",
    "<b>{label} instalados</b>": "<b>Installed {label}</b>",
    "Error": "Error",
    "Activo": "Enabled",
    "Desactivado": "Disabled",
    "¿Eliminar «{title}»?": "Delete \"{title}\"?",
    "Buscando...": "Searching...",
    "Actualizaciones": "Updates",
    "Para buscar actualizaciones de estos mods hace falta tu clave de API de CurseForge (gratuita). Ponla en Ajustes.":
        "To check for updates to these mods you need your CurseForge API key (free). Enter it in Settings.",
    "Todo está al día.": "Everything is up to date.",
    "(Los mods de CurseForge solo se comprueban si pones tu clave de API en Ajustes.)":
        "(CurseForge mods are only checked if you enter your API key in Settings.)",
    "Actualizando 1 mod: primero se hace una copia de seguridad. Mira la consola.":
        "Updating 1 mod: a backup is made first. Check the console.",
    "Actualizando {count} mods: primero se hace una copia de seguridad. Mira la consola.":
        "Updating {count} mods: a backup is made first. Check the console.",
    "{count} resultados compatibles con {version}. Doble clic para instalar.":
        "{count} results compatible with {version}. Double-click to install.",
    "Nada compatible con {version}.": "Nothing compatible with {version}.",
    "Instalando {title}...": "Installing {title}...",
    "Instalado: {names}": "Installed: {names}",
    "Ya estaba instalado.": "It was already installed.",
    "Actualizaciones de mods": "Mod updates",
    "Antes de actualizar se hace una copia de seguridad del servidor. El servidor tiene que estar apagado.":
        "A backup of the server is made before updating. The server has to be stopped.",
    "Actualizar": "Update",
    "<b>Hay 1 mod con versión nueva</b>": "<b>1 mod has a new version</b>",
    "<b>Hay {count} mods con versión nueva</b>": "<b>{count} mods have a new version</b>",

    # ---------- players_tab.py ----------
    "hacer operador a": "make operator",
    "quitar operador a": "remove operator",
    "añadir a la lista blanca a": "add to whitelist",
    "quitar de la lista blanca a": "remove from whitelist",
    "banear a": "ban",
    "perdonar a": "pardon",
    "activar la lista blanca": "enable the whitelist",
    "desactivar la lista blanca": "disable the whitelist",
    "{hours} h {minutes} min": "{hours} h {minutes} min",
    "{minutes} min": "{minutes} min",
    "Jugando ahora": "Playing now",
    "Hoy, {time}": "Today, {time}",
    "Ayer, {time}": "Yesterday, {time}",
    "Hacer operador": "Make operator",
    "Echar": "Kick",
    "Banear": "Ban",
    "Quitar operador": "Remove operator",
    "Quitar": "Remove",
    "Perdonar": "Pardon",
    "Solo pueden entrar los de la lista blanca": "Only whitelisted players can join",
    "Nombre del jugador": "Player name",
    "Los jugadores de Bedrock que entran por Geyser llevan un «.» delante del nombre":
        "Bedrock players who join through Geyser have a \".\" in front of their name",
    "Añadir a la lista blanca": "Add to whitelist",
    "Jugador": "Player",
    "Tiempo jugado": "Time played",
    "Veces que ha entrado": "Times joined",
    "Última vez": "Last seen",
    "Todavía no ha entrado nadie. Aquí verás quién juega más y cuándo entró por última vez.":
        "Nobody has joined yet. Here you will see who plays the most and when they last joined.",
    "Conectados ahora": "Online now",
    "Operadores": "Operators",
    "Lista blanca": "Whitelist",
    "Baneados": "Banned",
    "<b>Estadísticas</b>": "<b>Stats</b>",
    "Los cambios se aplican al momento.": "Changes apply right away.",
    "El servidor está apagado: los cambios se aplicarán en cuanto se encienda.":
        "The server is stopped: the changes will apply as soon as it starts.",
    "Tu acceso solo deja ver las listas.": "Your access only lets you view the lists.",
    "⚠ La lista blanca está activada pero vacía: no puede entrar nadie. Añade jugadores o desactívala.":
        "⚠ The whitelist is enabled but empty: nobody can join. Add players or disable it.",
    "Pendientes: {actions}.": "Pending: {actions}.",
    "Jugadores": "Players",
    "Selecciona un jugador de la lista.": "Select a player from the list.",
    "¿{action} {name}?": "{action} {name}?",
    "¿Banear a {name}?": "Ban {name}?",

    # ---------- replicas.py ----------
    "Copias de {name}": "Backups from {name}",
    "Las copias solo se guardan en este equipo.": "Backups are only kept on this computer.",
    "Cada copia se guarda también en <b>{target}</b> (las {keep} últimas).":
        "Each backup is also kept on <b>{target}</b> (the last {keep}).",
    "Todavía no se ha enviado ninguna: se enviará con la próxima copia.":
        "None has been sent yet: one will be sent with the next backup.",
    "Última enviada: {when}.": "Last sent: {when}.",
    "⚠ El {when} no se pudo enviar: {error}": "⚠ On {when} it could not be sent: {error}",
    "Copias de otros equipos · {host}": "Backups from other computers · {host}",
    "Copias de seguridad que otros equipos guardan en este. Si uno se estropea, restaura aquí su servidor: se crea uno nuevo con el mundo, los mods y la configuración de esa copia.":
        "Backups that other computers keep on this one. If one breaks, restore its server here: a new one is "
        "created with the world, mods and settings from that backup.",
    "Servidor / copia": "Server / backup",
    "Tamaño": "Size",
    "Fecha": "Date",
    "Ningún equipo guarda copias aquí todavía. Se activa en Ajustes de cada servidor, en «Copia en otro equipo».":
        "No computer keeps backups here yet. Turn it on in each server's Settings, under \"Backup on another "
        "computer\".",
    "Restaurar aquí...": "Restore here...",
    "Borrar las copias de ese servidor": "Delete that server's backups",
    "Copias": "Backups",
    "{server}  (de {source})": "{server}  (from {source})",
    "Elige una copia de la lista.": "Choose a backup from the list.",
    "Restaurar aquí": "Restore here",
    "Nombre del servidor nuevo:": "Name of the new server:",
    "{name} (restaurado)": "{name} (restored)",
    "No se pudo restaurar": "Could not restore",
    "Borrar copias": "Delete backups",
    "¿Borrar de este equipo todas las copias de «{name}»? Las del equipo original no se tocan.":
        "Delete all backups of \"{name}\" from this computer? The ones on the original computer are not touched.",

    # ---------- memory.py ----------
    "1 mod": "1 mod",
    "{count} mods": "{count} mods",
    "{count} jugadores a la vez": "{count} players at once",
    "Recomendado: <b>{memory}</b> ({why}).": "Recommended: <b>{memory}</b> ({why}).",
    "El equipo tiene {free} libres de {total}.": "The computer has {free} free out of {total}.",
    "⚠ Es más de lo que tiene libre ahora: si los demás programas no la sueltan, el equipo irá lento.":
        "⚠ That is more than it has free right now: if other programs don't release it, the computer will be slow.",

    # ---------- world_import.py ----------
    "No se encontró level.dat. Elige la carpeta de un mundo de Minecraft (normalmente está en .minecraft\\saves).":
        "level.dat was not found. Choose a Minecraft world folder (it is usually in .minecraft\\saves).",
    "Preparando archivos... {done} / {total}": "Preparing files... {done} / {total}",

    # ---------- transfer.py ----------
    "Se agotó el tiempo de espera": "Timed out",
    "Enviando... {done} / {total} MB": "Sending... {done} / {total} MB",
    "Copia de seguridad del mundo anterior e instalación del nuevo...":
        "Backing up the previous world and installing the new one...",
    "No se pudo importar el mundo: {error}": "Could not import the world: {error}",
    "Apagando el servidor...": "Stopping the server...",
    "Creando copia de seguridad...": "Creating backup...",
    "Falló la copia de seguridad: {error}": "The backup failed: {error}",
    "No se encontró la copia de seguridad": "The backup was not found",
    "Recibiendo copia... {done} / {total} MB": "Receiving backup... {done} / {total} MB",
    "Enviando al otro equipo... {done} / {total} MB": "Sending to the other computer... {done} / {total} MB",
    "Instalando en el otro equipo (puedes ver el progreso en su consola)...":
        "Installing on the other computer (you can follow the progress in its console)...",
    "Falló la instalación en el otro equipo: {error}. El servidor original sigue intacto.":
        "The installation on the other computer failed: {error}. The original server is untouched.",
    "Borrando el servidor original...": "Deleting the original server...",

    # ---------- firewall.py ----------
    "No se encontró pkexec. Ejecuta en una terminal:": "pkexec was not found. Run in a terminal:",
    "Puertos abiertos en el cortafuegos.": "Ports opened in the firewall.",
    "Cancelado (no se introdujo la contraseña).": "Canceled (the password was not entered).",
    "Error {code}": "Error {code}",

    # ---------- client.py ----------
    "No se puede conectar con {address}:{port}": "Cannot connect to {address}:{port}",
    "El agente no responde": "The agent is not responding",
    "Token incorrecto": "Wrong token",
    "No se pudo descargar la copia (error {code})": "Could not download the backup (error {code})",
    "Conexión interrumpida al descargar: {error}": "Connection lost while downloading: {error}",
    "Conexión interrumpida al enviar: {error}": "Connection lost while sending: {error}",
}
