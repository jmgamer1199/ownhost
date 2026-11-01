"""English texts of the agent's server manager (ownhost/agent/manager.py): console lines, notices and errors."""

STRINGS = {
    # Server
    "La cuenta de Microsoft aún no tiene perfil de Xbox. Entra en https://www.xbox.com/ "
    "con ella, crea el perfil (elige un gamertag) y reinicia el servidor.":
        "The Microsoft account doesn't have an Xbox profile yet. Sign in at https://www.xbox.com/ "
        "with it, create the profile (choose a gamertag) and restart the server.",
    "Sesión iniciada; credenciales guardadas para próximos arranques.":
        "Signed in; credentials saved for future starts.",
    "El servidor no está encendido": "The server isn't running",
    "No se pudo enviar el comando: {error}": "Couldn't send the command: {error}",
    "equipo": "computer",

    # Utilities
    "El servidor está ocupado ({task})": "The server is busy ({task})",
    "Apaga el servidor primero": "Stop the server first",
    "ERROR: {error}": "ERROR: {error}",

    # Create
    "Juego desconocido: {game}": "Unknown game: {game}",
    "Tipo desconocido: {flavor}": "Unknown type: {flavor}",
    "Debes aceptar el EULA de Minecraft para crear el servidor":
        "You must accept the Minecraft EULA to create the server",
    "Servidor": "Server",

    # Crossplay
    "Multiplataforma activada: los jugadores de Bedrock entran por el puerto {port} (UDP).":
        "Crossplay enabled: Bedrock players join on port {port} (UDP).",
    "Multiplataforma desactivada (Geyser eliminado).": "Crossplay disabled (Geyser removed).",
    "Activa primero la multiplataforma": "Enable crossplay first",
    "Extra «{key}» instalado. Se activará al encender el servidor.":
        "Extra \"{key}\" installed. It will be enabled when the server starts.",
    "Extra «{key}» quitado.": "Extra \"{key}\" removed.",

    # Install
    "Instalando {game} {flavor} {version}...": "Installing {game} {flavor} {version}...",
    "Instalación completada.": "Installation complete.",

    # Clone
    "{name} (copia)": "{name} (copy)",
    "Clonado como «{name}» (puerto {port}).": "Cloned as \"{name}\" (port {port}).",

    # Icon
    "Solo los servidores de Minecraft Java tienen icono": "Only Minecraft Java servers have an icon",
    "El icono tiene que ser un PNG de 64x64 píxeles": "The icon must be a 64x64 pixel PNG",
    "Icono cambiado. Se verá en la lista de servidores tras reiniciar.":
        "Icon changed. It will show in the server list after a restart.",

    # Start / stop
    "El servidor ya está encendido": "The server is already running",
    "ERROR al arrancar: {error}": "ERROR while starting: {error}",
    "No se pudo comprobar si hay actualizaciones ({error}); se arranca la versión actual.":
        "Couldn't check for updates ({error}); starting the current version.",
    "El servidor de actualizaciones no responde; se arranca la versión actual y se volverá a "
    "comprobar la próxima vez.":
        "The update server isn't responding; starting the current version, it will check again next time.",
    "Hay una versión nueva ({version}). Actualizando antes de encender...":
        "There's a new version ({version}). Updating before starting...",
    "Arrancando: {command}": "Starting: {command}",
    "Iniciando sesión del servidor con tu cuenta...": "Signing the server in with your account...",
    "Este juego no necesita iniciar sesión": "This game doesn't need to sign in",
    "Enciende el servidor primero": "Start the server first",
    "Servidor listo.": "Server ready.",
    "El servidor se cerró al arrancar. Mira la consola para ver el motivo.":
        "The server closed while starting. Check the console to see why.",
    "«{name}» no ha podido arrancar.": "\"{name}\" couldn't start.",
    "Servidor apagado (código {code}).": "Server stopped (code {code}).",
    "El proceso terminó inesperadamente (código {code})": "The process ended unexpectedly (code {code})",
    "El proceso terminó inesperadamente (lo cerró el sistema)":
        "The process ended unexpectedly (closed by the system)",

    # Crashes
    "«{name}» se ha caído.": "\"{name}\" has crashed.",
    "Se ha caído demasiadas veces seguidas: no se vuelve a encender solo. Mira la consola.":
        "It crashed too many times in a row: it won't restart by itself. Check the console.",
    "«{name}» se ha caído varias veces seguidas y se ha quedado apagado.":
        "\"{name}\" crashed several times in a row and has been left stopped.",
    "Se ha caído: se vuelve a encender en 10 segundos (intento {attempt} de 3).":
        "It crashed: restarting in 10 seconds (attempt {attempt} of 3).",
    "«{name}» se ha caído y se está volviendo a encender.": "\"{name}\" crashed and is restarting.",

    # Scheduled tasks
    "El servidor se reiniciará en 1 minuto.": "The server will restart in 1 minute.",
    "El servidor se reinicia en 10 segundos.": "The server restarts in 10 seconds.",
    "Reinicio programado.": "Scheduled restart.",

    # Add-ons
    "Complemento desconocido: {key}": "Unknown add-on: {key}",
    "Mapa web (BlueMap) instalado.": "Web map (BlueMap) installed.",
    "Chunky instalado.": "Chunky installed.",
    "Reinicia el servidor para activarlo.": "Restart the server to enable it.",
    "Mapa web quitado.": "Web map removed.",
    "Chunky quitado.": "Chunky removed.",
    "Instala primero Chunky": "Install Chunky first",
    "Enciende el servidor para generar el mundo": "Start the server to generate the world",
    "El radio tiene que estar entre 100 y 100.000 bloques": "The radius must be between 100 and 100,000 blocks",
    "Acción desconocida: {action}": "Unknown action: {action}",

    # Players
    "La gestión de jugadores está disponible en Minecraft Java y Bedrock":
        "Player management is available on Minecraft Java and Bedrock",
    "Nombre de jugador no válido": "Invalid player name",
    "El servidor está apagado: no hay nadie a quien echar": "The server is stopped: there's no one to kick",
    "Apagando...": "Stopping...",
    "No respondió en {seconds}s; forzando cierre.": "No response in {seconds}s; forcing it to close.",
    "Forzando cierre del proceso.": "Forcing the process to close.",

    # Settings
    "Apaga el servidor para cambiar el puerto": "Stop the server to change the port",
    "Este juego no usa archivo de propiedades": "This game doesn't use a properties file",

    # Update
    "Haciendo copia de seguridad antes de actualizar...": "Making a backup before updating...",
    "Actualizado: {old} -> {new}": "Updated: {old} -> {new}",

    # Backups
    "Creando copia {name}...": "Creating backup {name}...",
    "omitido {path}: {error}": "skipped {path}: {error}",
    "Copia creada ({size} MB).": "Backup created ({size} MB).",
    "Enviando la copia a «{target}»...": "Sending the backup to \"{target}\"...",
    "Copia guardada también en «{target}».": "Backup also saved on \"{target}\".",
    "No se pudo enviar la copia a «{target}»: {error}": "Couldn't send the backup to \"{target}\": {error}",
    "«{name}»: no se pudo enviar la copia a «{target}».": "\"{name}\": couldn't send the backup to \"{target}\".",
    "Las copias de seguridad se guardarán también en «{target}».": "Backups will also be saved on \"{target}\".",
    "Restaurando {name}...": "Restoring {name}...",
    "Copia restaurada (versión {version}).": "Backup restored (version {version}).",
    "Copia de seguridad no encontrada": "Backup not found",

    # Import world
    "Este juego no admite importar mundos": "This game doesn't support importing worlds",
    "El archivo no es un .zip válido": "The file isn't a valid .zip",
    "No se encontró level.dat: elige la carpeta de un mundo de Minecraft":
        "level.dat not found: choose a Minecraft world folder",
    "Copia de seguridad del mundo actual antes de importar...": "Backing up the current world before importing...",
    "Mundo importado en «{level}» con {count} mods. Enciende el servidor para cargarlo.":
        "World imported into \"{level}\" with {count} mods. Start the server to load it.",
    "Mundo importado en «{level}». Enciende el servidor para cargarlo.":
        "World imported into \"{level}\". Start the server to load it.",

    # Import server
    "El archivo no es una copia de seguridad de Ownhost": "The file isn't an Ownhost backup",
    "Restaurando el mundo y la configuración...": "Restoring the world and settings...",
    "Servidor importado (puerto {port}).": "Server imported (port {port}).",

    # Modpacks
    "Modpack «{name}» {version}: Minecraft {minecraft}, {loader}, {count} archivo.":
        "Modpack \"{name}\" {version}: Minecraft {minecraft}, {loader}, {count} file.",
    "Modpack «{name}» {version}: Minecraft {minecraft}, {loader}, {count} archivos.":
        "Modpack \"{name}\" {version}: Minecraft {minecraft}, {loader}, {count} files.",
    "Faltan {count} mods que sus autores no dejan descargar desde otras apps. Mira la consola.":
        "{count} mods are missing because their authors don't allow downloading them from other apps. "
        "Check the console.",
    "AVISO: estos mods hay que descargarlos a mano y ponerlos en la carpeta mods:":
        "WARNING: these mods must be downloaded manually and put in the mods folder:",
    "Modpack instalado. Enciende el servidor para generar el mundo.":
        "Modpack installed. Start the server to generate the world.",

    # Mods
    "No hay actualizaciones para esos mods": "There are no updates for those mods",
    "Haciendo copia de seguridad antes de actualizar los mods...": "Making a backup before updating the mods...",
    "Actualizando {title}: {current} -> {latest}": "Updating {title}: {current} -> {latest}",
    "Mod actualizado.": "Mod updated.",
    "{count} mods actualizados.": "{count} mods updated.",
    "Este tipo de servidor no admite mods ni plugins": "This server type doesn't support mods or plugins",
    "Instalado: {files}. Reinicia el servidor para cargarlo.": "Installed: {files}. Restart the server to load it.",
}
