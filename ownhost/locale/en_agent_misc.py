"""English texts of the agent (everything under ownhost/agent/ except manager.py, and ownhost/agent/games/)
and of ownhost/updates.py."""

STRINGS = {
    # access.py
    "Ponle un nombre al acceso (p. ej. el de tu amigo)": "Give the access a name (e.g. your friend's)",
    "Permiso desconocido: {role}": "Unknown permission: {role}",
    "Elige al menos un servidor": "Choose at least one server",
    "Ese acceso ya no existe": "That access no longer exists",

    # addons.py
    "Solo está disponible en servidores Paper, Fabric, Forge o NeoForge":
        "Only available on Paper, Fabric, Forge or NeoForge servers",

    # api.py
    "Cerrando el agente": "Closing the agent",
    "Actualizando a la versión del {date}": "Updating to the version from {date}",
    "Token incorrecto": "Wrong token",
    "Error al contactar con un servicio externo: {error}": "Error contacting an external service: {error}",
    "Servidor no encontrado: {server}": "Server not found: {server}",
    "No tienes permiso para hacer esto en este equipo": "You don't have permission to do this on this computer",
    "Este agente ya tiene la última versión": "This agent already has the latest version",
    "Este agente no se puede actualizar solo (se instaló desde el código o con pip, o no hay versión para este sistema). Actualízalo a mano.":
        "This agent can't update itself (it was installed from source or with pip, or there is no version for "
        "this system). Update it manually.",
    "Juego desconocido": "Unknown game",
    "Servidor no encontrado": "Server not found",
    "No tienes permiso para hacer esto en este servidor": "You don't have permission to do this on this server",

    # crossplay.py
    "Instalando Geyser para jugadores de Bedrock...": "Installing Geyser for Bedrock players...",
    "Geyser solo funciona con servidores Paper, Fabric o NeoForge. Crea uno de esos tipos para tener multiplataforma.":
        "Geyser only works with Paper, Fabric or NeoForge servers. Create one of those types to get crossplay.",
    "El servidor no es de la última versión: instalando ViaVersion para Geyser...":
        "The server is not on the latest version: installing ViaVersion for Geyser...",
    "Instalando Floodgate (entrar sin cuenta de Java)...": "Installing Floodgate (join without a Java account)...",
    "Extra desconocido: {key}": "Unknown extra: {key}",
    "Geyser no tiene versión para {flavor} {version}. Prueba con un servidor Paper o con una versión más reciente.":
        "Geyser has no version for {flavor} {version}. Try a Paper server or a newer version.",

    # downloads.py
    "Descargando {url}": "Downloading {url}",

    # files.py
    "Ruta no válida": "Invalid path",
    "Ese archivo no se puede abrir desde la app": "That file can't be opened from the app",
    "La carpeta no existe": "The folder doesn't exist",
    "Solo se pueden abrir archivos de configuración de texto": "Only text configuration files can be opened",
    "El archivo es demasiado grande para editarlo aquí": "The file is too large to edit here",
    "Solo se pueden guardar archivos de configuración que ya existan":
        "Only configuration files that already exist can be saved",
    "El archivo es demasiado grande": "The file is too large",
    "El JSON no es válido (línea {line}): revísalo antes de guardar":
        "The JSON is not valid (line {line}): check it before saving",

    # java.py
    "Java {major} no está instalado; descargándolo...": "Java {major} is not installed; downloading it...",
    "Java {major} instalado.": "Java {major} installed.",
    "Adoptium no ofrece Java {major} para {system}": "Adoptium doesn't offer Java {major} for {system}",
    "Java descargado pero no se encontró el ejecutable": "Java downloaded but the executable was not found",

    # modpacks.py
    "No encuentro la descripción del modpack (modrinth.index.json o manifest.json). Si es de CurseForge, descarga el modpack completo, no solo el servidor.":
        "Can't find the modpack description (modrinth.index.json or manifest.json). If it's from CurseForge, "
        "download the full modpack, not just the server.",
    "Copiando la configuración del modpack...": "Copying the modpack configuration...",
    "Consultando {count} mods en CurseForge...": "Looking up {count} mods on CurseForge...",
    "El modpack tiene una ruta no válida: {path}": "The modpack has an invalid path: {path}",
    "El modpack no es de Minecraft": "The modpack is not for Minecraft",
    "El modpack no indica Fabric, Forge ni NeoForge": "The modpack doesn't specify Fabric, Forge or NeoForge",
    "Loader no soportado en el modpack: {loader}": "Unsupported loader in the modpack: {loader}",
    "ninguno": "none",
    "El archivo no es un modpack (.mrpack o .zip de CurseForge)":
        "The file is not a modpack (.mrpack or CurseForge .zip)",
    "Los modpacks de Quilt no están soportados (solo Fabric, Forge y NeoForge)":
        "Quilt modpacks are not supported (only Fabric, Forge and NeoForge)",
    "El archivo {path} no coincide con el del modpack (descarga corrupta). Vuelve a intentarlo.":
        "The file {path} doesn't match the modpack's (corrupt download). Try again.",

    # mods.py
    "CurseForge ha rechazado la clave de API. Revísala en Ajustes.":
        "CurseForge rejected the API key. Check it in Settings.",
    "Origen desconocido: {source}": "Unknown source: {source}",
    "Para usar CurseForge necesitas una clave de API gratuita. Consíguela en console.curseforge.com y ponla en Ajustes.":
        "To use CurseForge you need a free API key. Get it at console.curseforge.com and enter it in Settings.",
    "Este servidor no admite mods de {source}": "This server doesn't support mods from {source}",
    "No hay una versión de este proyecto para {version}": "There is no version of this project for {version}",
    "El autor de «{name}» no permite descargarlo desde otras apps. Descárgalo desde su página: {url}":
        "The author of \"{name}\" doesn't allow downloading it from other apps. Download it from its page: {url}",
    "Nombre de archivo no válido": "Invalid file name",
    "CurseForge no tiene mods de {game} para tu clave de API": "CurseForge has no {game} mods for your API key",
    "Instalando dependencia de {title}...": "Installing dependency of {title}...",
    "Este proyecto no tiene archivos para descargar": "This project has no files to download",
    "AVISO: no se pudo instalar una dependencia: {error}": "WARNING: could not install a dependency: {error}",

    # replicas.py
    "Este equipo no llega al otro por {addresses} (puerto {port}). ¿Está encendido, en la misma red o en tu Tailscale, y con el cortafuegos abierto?":
        "This computer can't reach the other one at {addresses} (port {port}). Is it on, on the same network or "
        "your Tailscale, and with the firewall open?",
    "El otro equipo no ha aceptado el código de copias": "The other computer did not accept the backup code",
    "El otro equipo tiene una versión de Ownhost sin copias remotas: actualízalo":
        "The other computer has a version of Ownhost without remote backups: update it",
    "Servidor no válido": "Invalid server",
    "Nombre de copia no válido": "Invalid backup name",
    "Copia no válida": "Invalid backup",
    "Esa copia ya no existe": "That backup no longer exists",
    "No existe": "It doesn't exist",
    "No se puede conectar con {address}:{port}. ¿Está encendido y en la red?":
        "Can't connect to {address}:{port}. Is it on and on the network?",
    "error {status}": "error {status}",

    # scheduler.py
    "Nadie ha jugado en {minutes} minutos: se apaga el servidor.":
        "Nobody has played for {minutes} minutes: stopping the server.",
    "«{name}» se ha apagado porque nadie jugaba.": "\"{name}\" was stopped because nobody was playing.",

    # __main__.py
    "Agente '{name}' escuchando en {bind}:{port}": "Agent '{name}' listening on {bind}:{port}",
    "Datos en: {folder}": "Data in: {folder}",
    "El puerto {port} está ocupado; esperando a que se libere...": "Port {port} is in use; waiting for it to be free...",
    "Token para añadir este equipo en la app: {token}": "Token to add this computer in the app: {token}",
    "Agente de Ownhost": "Ownhost agent",
    "carpeta donde se guardan servidores, Java y copias": "folder where servers, Java and backups are stored",
    "puerto de la API (por defecto 8765)": "API port (default 8765)",
    "interfaz de red (por defecto 0.0.0.0 = toda la red local)":
        "network interface (default 0.0.0.0 = the whole local network)",
    "nombre de este equipo en la app": "name of this computer in the app",
    "muestra el token y sale": "show the token and exit",

    # games/base.py
    "{program} terminó con código {code}": "{program} exited with code {code}",

    # games/bedrock.py (flavor names are translated in GameAdapter.describe())
    "Oficial (Bedrock Dedicated Server)": "Official (Bedrock Dedicated Server)",
    "Preview (versión de pruebas)": "Preview (test version)",
    "Extrayendo el servidor de Bedrock...": "Extracting the Bedrock server...",
    "Mojang no ofrece el servidor de Bedrock para este sistema": "Mojang doesn't offer the Bedrock server for this system",
    "No se encuentra el ejecutable del servidor; prueba a actualizarlo":
        "The server executable can't be found; try updating it",

    # games/hytale.py
    "Ejecutando Hytale Downloader. Si es la primera vez, la app mostrará una ventana para iniciar sesión con tu cuenta de Hytale.":
        "Running Hytale Downloader. If this is the first time, the app will show a window to log in with your "
        "Hytale account.",
    "Extrayendo archivos del juego...": "Extracting game files...",
    "No se encontró el ejecutable del Hytale Downloader para este sistema":
        "The Hytale Downloader executable for this system was not found",
    "el downloader terminó con código {code}": "the downloader exited with code {code}",
    "Instalado. Al encenderlo por primera vez se pedirá iniciar sesión para el servidor.":
        "Installed. When you start it for the first time you'll be asked to log in for the server.",
    "No se encuentra HytaleServer.jar; prueba a actualizar el servidor":
        "HytaleServer.jar can't be found; try updating the server",
    "{key} tiene que ser true o false": "{key} must be true or false",
    "{file} no es un JSON válido; corrígelo a mano o restaura una copia":
        "{file} is not valid JSON; fix it by hand or restore a backup",
    "No se puede cambiar {key}": "{key} can't be changed",
    "{key} tiene que ser un número entero": "{key} must be a whole number",
    "{key} tiene que ser un número": "{key} must be a number",

    # games/minecraft.py
    "Tipo desconocido: {flavor}": "Unknown type: {flavor}",
    "Ejecutando el instalador de {flavor} {loader} (puede tardar unos minutos)...":
        "Running the {flavor} {loader} installer (this may take a few minutes)...",
    "No se encuentran los archivos de arranque de Forge/NeoForge; prueba a actualizar el servidor":
        "The Forge/NeoForge startup files can't be found; try updating the server",
    "Versión de Minecraft desconocida: {version}": "Unknown Minecraft version: {version}",
    "No hay NeoForge para Minecraft {version}": "There is no NeoForge for Minecraft {version}",
    "No hay Forge para Minecraft {version}": "There is no Forge for Minecraft {version}",

    # updates.py
    "Esta copia de Ownhost no se puede actualizar sola": "This copy of Ownhost can't update itself",
    "La descarga ha llegado incompleta; vuelve a intentarlo": "The download arrived incomplete; try again",
}
