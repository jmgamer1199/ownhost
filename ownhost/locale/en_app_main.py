"""English texts of the main window, the dialogs, friend access and app updates
(ownhost/app/main_window.py, dialogs.py, guests.py, app_update.py)."""

STRINGS = {
    # ---------- main_window.py ----------
    "Este PC": "This PC",
    "＋  Nuevo servidor": "＋  New server",
    "Conectar a un equipo": "Connect to a computer",
    "Ajustes": "Settings",
    "Detectados en tu red": "Found on your network",
    "Equipos y servidores": "Computers and servers",
    "<span style='font-size:26pt'>Bienvenido</span><br>"
    "<span style='font-size:11pt'>Tus servidores de Minecraft y Hytale, en toda tu red.</span>":
        "<span style='font-size:26pt'>Welcome</span><br>"
        "<span style='font-size:11pt'>Your Minecraft and Hytale servers, across your whole network.</span>",
    "Cada equipo que hospeda servidores ejecuta un pequeño <b>agente</b>. "
    "Esta app se conecta a los agentes de tu red para crear, encender, apagar "
    "y actualizar servidores.<br><br>"
    "Empieza usando este PC como servidor, o conéctate por IP a otro equipo "
    "(por ejemplo tu homelab) donde ya esté funcionando.":
        "Each computer that hosts servers runs a small <b>agent</b>. "
        "This app connects to the agents on your network to create, start, stop "
        "and update servers.<br><br>"
        "Start by using this PC as a server, or connect by IP to another computer "
        "(for example your homelab) where it is already running.",
    "Usar este PC como servidor": "Use this PC as a server",
    "Conectar a un equipo por IP...": "Connect to a computer by IP...",
    "Nuevo servidor en este equipo": "New server on this computer",
    "Iniciar agente local": "Start local agent",
    "Copiar token": "Copy token",
    "Abrir puertos del cortafuegos": "Open firewall ports",
    "El cortafuegos ({kind}) bloquea a los demás equipos y a los jugadores. Pide tu contraseña.":
        "The firewall ({kind}) blocks other computers and players. Asks for your password.",
    "Actualizar agente": "Update agent",
    "Instala en ese equipo la última versión de Ownhost. Los servidores encendidos se apagan con «stop» y se "
    "vuelven a encender.":
        "Installs the latest version of Ownhost on that computer. Running servers are stopped with \"stop\" "
        "and started again.",
    "Copias de otros equipos...": "Backups from other computers...",
    "Copias de seguridad que otros equipos tuyos guardan en este":
        "Backups that your other computers store on this one",
    "Accesos para amigos...": "Friend access...",
    "Da a tus amigos un código para encender o gestionar tus servidores":
        "Give your friends an access code to start or manage your servers",
    "Editar equipo": "Edit computer",
    "Quitar de la lista": "Remove from list",
    "{name} (sin conexión)": "{name} (offline)",
    "{name} (conectando...)": "{name} (connecting...)",
    "¿Actualizar Ownhost en «{name}»? Los servidores encendidos se apagan guardando el mundo y se vuelven a "
    "encender al terminar (un par de minutos).":
        "Update Ownhost on \"{name}\"? Running servers are stopped (saving the world) and started again "
        "when it finishes (a couple of minutes).",
    "red local": "local network",
    "<b>{hostname}</b> · {os} · agente v{version}<br>": "<b>{hostname}</b> · {os} · agent v{version}<br>",
    "Dirección: {address}": "Address: {address}",
    "CPU: {threads} hilos, {percent}% en uso<br>": "CPU: {threads} threads, {percent}% in use<br>",
    "RAM: {used} / {total} GB en uso<br>": "RAM: {used} / {total} GB in use<br>",
    "Servidores: {count} ({running} encendidos)<br>": "Servers: {count} ({running} running)<br>",
    "Panel web (también desde el móvil): <a href='{url}'>{url}</a>":
        "Web panel (also from your phone): <a href='{url}'>{url}</a>",
    "<br><br>Entras con el acceso de <b>{name}</b>: <b>{role}</b>.":
        "<br><br>You are signed in with <b>{name}</b>'s access: <b>{role}</b>.",
    "<br><br>Para gestionar este PC desde otro equipo usa la IP <b>{ip}</b> (o <b>{ts}</b> por Tailscale, desde "
    "fuera de casa), puerto <b>{port}</b> y el token (botón «Copiar token»).":
        "<br><br>To manage this PC from another computer use the IP <b>{ip}</b> (or <b>{ts}</b> via Tailscale, "
        "from outside your home), port <b>{port}</b> and the token (\"Copy token\" button).",
    "<br><br>Para gestionar este PC desde otro equipo usa la IP <b>{ip}</b>, puerto <b>{port}</b> y el token "
    "(botón «Copiar token»).":
        "<br><br>To manage this PC from another computer use the IP <b>{ip}</b>, port <b>{port}</b> and the "
        "token (\"Copy token\" button).",
    "Sin conexión con {address}": "No connection to {address}",
    "Nuevo servidor": "New server",
    " (en {name})": " (on {name})",
    "Servidor caído": "Server crashed",
    "\n\nMira la consola del servidor para ver el motivo.": "\n\nCheck the server console to see why.",
    "Actualizando el agente de este PC a la versión nueva...": "Updating this PC's agent to the new version...",
    "El agente nuevo no ha arrancado; abre la app de nuevo": "The new agent didn't start; open the app again",
    "Agente de este PC actualizado a la versión nueva.": "This PC's agent was updated to the new version.",
    "Agente de este PC actualizado a la versión nueva y 1 servidor vuelto a encender.":
        "This PC's agent was updated to the new version and 1 server was started again.",
    "Agente de este PC actualizado a la versión nueva y {count} servidores vueltos a encender.":
        "This PC's agent was updated to the new version and {count} servers were started again.",
    "No se pudo actualizar el agente de este PC: {msg}": "Couldn't update this PC's agent: {msg}",
    "Sesión iniciada correctamente.": "Signed in successfully.",
    "Quitar equipo": "Remove computer",
    "¿Quitar «{name}» de la lista? Sus servidores no se borran.":
        "Remove \"{name}\" from the list? Its servers are not deleted.",
    "Añadido automáticamente por Tailscale: {names}": "Added automatically via Tailscale: {names}",
    "Pulsa para conectarlo (te pedirá el token de ese equipo)":
        "Click to connect it (you'll be asked for that computer's token)",
    "Sin equipos": "No computers",
    "No hay ningún equipo tuyo conectado. Usa este PC o añade otro equipo primero.\n\n(En los equipos de un "
    "amigo solo puedes usar los servidores que te haya dejado.)":
        "None of your computers is connected. Use this PC or add another computer first.\n\n(On a friend's "
        "computers you can only use the servers they have shared with you.)",
    "Arrancando el agente de este PC (la primera vez puede tardar un poco)...":
        "Starting this PC's agent (the first time it may take a while)...",
    "Agente local": "Local agent",
    "El agente de este PC no ha arrancado.\n\nMira qué ha pasado en:\n{path}":
        "This PC's agent didn't start.\n\nSee what happened in:\n{path}",
    "Cortafuegos": "Firewall",
    "Este equipo tiene el cortafuegos «{kind}» activado: bloquea a los demás equipos de la red y a los "
    "jugadores.\n\n¿Abrir ahora los puertos de Ownhost y de los juegos? Te pedirá tu contraseña.":
        "This computer has the \"{kind}\" firewall enabled: it blocks the other computers on the network and "
        "the players.\n\nOpen the Ownhost and game ports now? You'll be asked for your password.",
    "Abriendo puertos del cortafuegos...": "Opening firewall ports...",
    "Token copiado al portapapeles": "Token copied to the clipboard",

    # ---------- dialogs.py ----------
    "Homelab, PC del salón...": "Homelab, living room PC...",
    "Vacío si el equipo está en tu Tailscale con tu misma cuenta":
        "Empty if the computer is on your Tailscale with your same account",
    "En el otro equipo abre Ownhost y pulsa «Usar este PC como servidor»: en la ficha de «Este PC» verás su IP "
    "y su token. En Linux, el instalador del agente los muestra al terminar. Si un amigo te ha dado un código "
    "de acceso, escríbelo como token.":
        "On the other computer open Ownhost and click \"Use this PC as a server\": the \"This PC\" page shows "
        "its IP and token. On Linux, the agent installer shows them when it finishes. If a friend gave you an "
        "access code, enter it as the token.",
    "Buscando equipos...": "Searching for computers...",
    "Detectados": "Found",
    "Nombre": "Name",
    "Dirección IP": "IP address",
    "Puerto": "Port",
    "Token o código": "Token or code",
    "{name}  ({address}, ownhost en la red local)": "{name}  ({address}, ownhost on the local network)",
    "{name}  ({ip}, Tailscale, conectado)": "{name}  ({ip}, Tailscale, online)",
    "{name}  ({ip}, Tailscale, desconectado)": "{name}  ({ip}, Tailscale, offline)",
    "Elegir entre {count} equipos encontrados...": "Choose from {count} computers found...",
    "No se encontró ningún equipo: escribe su IP abajo": "No computers found: enter its IP below",
    "Faltan datos": "Missing information",
    "Indica la dirección del equipo.": "Enter the computer's address.",
    "Probando...": "Testing...",
    "OK": "OK",
    "Token incorrecto": "Wrong token",
    "El equipo {address} está encendido y responde, pero no deja conectar con el Ownhost (puerto {port}). Casi "
    "seguro es su cortafuegos.\n\nEn ese equipo, abre Ownhost y pulsa «Abrir puertos del cortafuegos» en la "
    "ficha «Este PC» (en Linux), o permite Ownhost en el Firewall de Windows.":
        "The computer {address} is on and responding, but it doesn't allow connecting to Ownhost (port "
        "{port}). It is almost certainly its firewall.\n\nOn that computer, open Ownhost and click \"Open "
        "firewall ports\" on the \"This PC\" page (on Linux), or allow Ownhost in Windows Firewall.",
    "No se pudo conectar": "Couldn't connect",
    "Survival con amigos": "Survival with friends",
    "Cuántos vais a jugar a la vez como mucho: sirve para recomendar la memoria":
        "The most people playing at the same time: used to recommend the memory",
    "Automático": "Automatic",
    "Acepto el EULA de Minecraft": "I accept the Minecraft EULA",
    '<a href="https://aka.ms/MinecraftEULA">Leer el EULA</a>':
        '<a href="https://aka.ms/MinecraftEULA">Read the EULA</a>',
    "Equipo": "Computer",
    "Juego": "Game",
    "Tipo": "Type",
    "Versión": "Version",
    "Jugadores a la vez": "Players at once",
    "Memoria máxima": "Maximum memory",
    "Necesitas una cuenta del juego: al crear el servidor se abrirá una ventana para iniciar sesión con ella.":
        "You need a game account: when the server is created, a window will open to sign in with it.",
    "Multiplataforma: que también entren jugadores de Bedrock\n(móvil, consola, Windows) con Geyser":
        "Crossplay: let Bedrock players join too\n(mobile, console, Windows) with Geyser",
    "Sin necesitar cuenta de Java (Floodgate)": "No Java account needed (Floodgate)",
    "Solo pueden entrar los jugadores que añadas (lista blanca)": "Only players you add can join (whitelist)",
    "Si la activas, añade a tus amigos en la pestaña Jugadores. Se puede cambiar cuando quieras.":
        "If you turn it on, add your friends in the Players tab. You can change it any time.",
    "Crear": "Create",
    "Desde un modpack...": "From a modpack...",
    "Importa un modpack de Modrinth (.mrpack) o de CurseForge (.zip)":
        "Import a modpack from Modrinth (.mrpack) or CurseForge (.zip)",
    "Cargando juegos...": "Loading games...",
    "Cargando versiones...": "Loading versions...",
    "EULA": "EULA",
    "Para crear un servidor de Minecraft debes aceptar el EULA.":
        "To create a Minecraft server you must accept the EULA.",
    "Creando...": "Creating...",
    "No se pudo crear": "Couldn't create",
    "Importar un modpack": "Import a modpack",
    "Archivo .mrpack o .zip del modpack": "The modpack's .mrpack or .zip file",
    "Elegir...": "Choose...",
    "El del modpack": "The modpack's name",
    "Descarga el modpack desde Modrinth (botón «Download» → .mrpack) o desde CurseForge (el archivo .zip "
    "normal, no el «Server Pack»). Los mods que solo sirven para el juego (shaders, minimapas...) se descartan "
    "solos. Para los de CurseForge hace falta tu clave de API en Ajustes.":
        "Download the modpack from Modrinth (\"Download\" button → .mrpack) or from CurseForge (the regular "
        ".zip file, not the \"Server Pack\"). Client-only mods (shaders, minimaps...) are left out "
        "automatically. CurseForge modpacks need your API key in Settings.",
    "Modpack": "Modpack",
    "Importar": "Import",
    "Elegir modpack": "Choose modpack",
    "Modpacks (*.mrpack *.zip)": "Modpacks (*.mrpack *.zip)",
    "Elige el archivo del modpack.": "Choose the modpack file.",
    "Enviando el modpack... {sent} / {total} MB": "Sending the modpack... {sent} / {total} MB",
    "No se pudo importar": "Couldn't import",
    "Modrinth funciona sin configurar nada. Para buscar en <b>CurseForge</b> hace falta una clave de API "
    "gratuita: entra en <a href=\"https://console.curseforge.com/\">console.curseforge.com</a>, inicia sesión y "
    "copia la clave de la sección «API keys».":
        "Modrinth works with no setup. To search <b>CurseForge</b> you need a free API key: go to "
        "<a href=\"https://console.curseforge.com/\">console.curseforge.com</a>, sign in and copy the key from "
        "the \"API keys\" section.",
    "Clave de CurseForge": "CurseForge key",
    "Buscar versiones nuevas de Ownhost al abrir la app": "Check for new Ownhost versions when the app opens",
    "Buscar ahora": "Check now",
    "Incluida en la app (opcional: pon aquí la tuya)": "Included in the app (optional: enter your own here)",
    "CurseForge y Modrinth ya funcionan: esta versión de la app incluye una clave de CurseForge. Solo necesitas "
    "rellenar el campo si quieres usar la tuya.":
        "CurseForge and Modrinth already work: this version of the app includes a CurseForge key. You only "
        "need to fill in the field if you want to use your own.",
    "Mover a otro equipo": "Move to another computer",
    "Borrar el servidor de este equipo cuando termine": "Delete the server from this computer when it finishes",
    "Se apagará «{name}», se hará una copia de seguridad y se instalará en el equipo elegido con la misma "
    "versión, el mundo, la configuración y los mods.<br><br>Si no marcas la casilla, el original se queda aquí "
    "apagado por si algo falla.":
        "\"{name}\" will be stopped, backed up and installed on the chosen computer with the same version, "
        "world, configuration and mods.<br><br>If you don't tick the box, the original stays here, stopped, "
        "in case something goes wrong.",
    "Destino": "Destination",
    "Mover": "Move",
    "Importar un mundo": "Import a world",
    "El mundo elegido sustituirá al de <b>{name}</b> (Minecraft {version}). Antes se hará una copia de "
    "seguridad del actual.<br>Usa un mundo de la misma versión de Minecraft o anterior; uno más nuevo no "
    "cargará.":
        "The chosen world will replace the one in <b>{name}</b> (Minecraft {version}). A backup of the current "
        "one is made first.<br>Use a world from the same Minecraft version or older; a newer one won't load.",
    "Ningún mundo elegido": "No world chosen",
    "Carpeta del mundo...": "World folder...",
    "Archivo .zip...": ".zip file...",
    "Carpeta del mundo (la que contiene level.dat)": "World folder (the one that contains level.dat)",
    "Mundo en .zip": "World in .zip",
    "Archivo zip (*.zip)": "Zip file (*.zip)",
    "Analizando...": "Analyzing...",
    "Mundo encontrado: <b>{name}</b>": "World found: <b>{name}</b>",
    "Viene de la instancia «{instance}», que tiene {count} mods.":
        "It comes from the \"{instance}\" instance, which has {count} mods.",
    "Copiar también sus mods y su configuración (sustituyen a los actuales)":
        "Also copy its mods and configuration (they replace the current ones)",
    "El mundo viene de una instancia con mods, pero este servidor no admite mods: crea uno Fabric, Forge o "
    "NeoForge con la misma versión.":
        "The world comes from a modded instance, but this server doesn't support mods: create a Fabric, Forge "
        "or NeoForge one with the same version.",
    "Se omiten {count} mods que solo funcionan en el cliente ({names}).":
        "Skipping {count} client-only mods ({names}).",
    "Iniciar sesión en {game}": "Sign in to {game}",
    "Abrir página de inicio de sesión": "Open sign-in page",
    "Copiar código": "Copy code",
    "Esperando a que inicies sesión... Esta ventana se cerrará sola.":
        "Waiting for you to sign in... This window will close by itself.",
    "Iniciar sesión con Microsoft (amigos de Xbox)": "Sign in with Microsoft (Xbox friends)",
    "El servidor <b>{server}</b> va a aparecer en la pestaña Amigos de las consolas.<br>Para eso necesita una "
    "<b>cuenta de Microsoft secundaria</b> (no uses la tuya).<br><br>1. Pulsa <b>Abrir página de inicio de "
    "sesión</b>.<br>2. Introduce este código y entra con la cuenta secundaria:":
        "The server <b>{server}</b> will show up in the consoles' Friends tab.<br>For that it needs a "
        "<b>secondary Microsoft account</b> (don't use yours).<br><br>1. Click <b>Open sign-in page</b>.<br>"
        "2. Enter this code and sign in with the secondary account:",
    "El servidor <b>{server}</b> necesita tu cuenta de {game} para descargar los archivos del juego.<br><br>":
        "The server <b>{server}</b> needs your {game} account to download the game files.<br><br>",
    "El servidor <b>{server}</b> necesita tu cuenta de {game} para que el servidor pueda aceptar "
    "jugadores.<br><br>":
        "The server <b>{server}</b> needs your {game} account so the server can accept players.<br><br>",
    "1. Pulsa <b>Abrir página de inicio de sesión</b>.<br>2. Entra con tu cuenta e introduce este código si te "
    "lo pide:":
        "1. Click <b>Open sign-in page</b>.<br>2. Sign in with your account and enter this code if asked:",
    "(el código aparece en la página)": "(the code is shown on the page)",
    "Actualizar servidor": "Update server",
    "Versión (elegir la misma descarga la última build de esa versión).\nSe hará una copia de seguridad antes "
    "de actualizar.":
        "Version (choosing the same one downloads the latest build of that version).\nA backup is made "
        "before updating.",

    # ---------- guests.py ----------
    "Encender y apagar": "Start and stop",
    "Ve sus servidores y quién está jugando, y puede encenderlos, apagarlos y reiniciarlos.":
        "Sees their servers and who is playing, and can start, stop and restart them.",
    "Moderar": "Moderate",
    "Lo anterior, y además la consola, los jugadores (operadores, lista blanca, baneos) y hacer copias de "
    "seguridad.":
        "All of the above, plus the console, players (operators, whitelist, bans) and making backups.",
    "Gestionar": "Manage",
    "Lo anterior, y además los ajustes, las propiedades, los mods, actualizar, restaurar copias e importar "
    "mundos. No puede borrar servidores, crear otros ni ver tu carpeta.":
        "All of the above, plus settings, properties, mods, updating, restoring backups and importing worlds. "
        "Can't delete servers, create new ones or see your folder.",
    "Dueño": "Owner",
    "Recibir copias (otro equipo)": "Receive backups (another computer)",
    "Accesos para amigos · {host}": "Friend access · {host}",
    "Dale a cada amigo su propio código para que encienda o gestione tus servidores desde su Ownhost o desde el "
    "navegador del móvil, sin darle tu token. Puedes quitarle el acceso cuando quieras.":
        "Give each friend their own access code so they can start or manage your servers from their Ownhost "
        "or their phone's browser, without giving them your token. You can revoke their access any time.",
    "Permiso": "Permission",
    "Servidores": "Servers",
    "Todavía no has dado acceso a nadie.": "You haven't given access to anyone yet.",
    "Nuevo acceso...": "New access...",
    "Quitar acceso": "Revoke access",
    "Cerrar": "Close",
    "Accesos": "Access",
    "Todos": "All",
    "(borrado)": "(deleted)",
    "Ninguno": "None",
    "Selecciona un acceso de la lista.": "Select an access from the list.",
    "¿Quitar el acceso de {name}? Su código dejará de funcionar al momento.":
        "Revoke {name}'s access? Their code will stop working immediately.",
    "Nuevo acceso": "New access",
    "Nombre de tu amigo": "Your friend's name",
    "Todos los servidores (también los que crees después)": "All servers (including ones you create later)",
    "Crear código": "Create code",
    "<b>Servidores que puede ver</b>": "<b>Servers they can see</b>",
    "Ponle un nombre (el de tu amigo, para reconocerlo luego).":
        "Give it a name (your friend's, to recognize it later).",
    "Elige al menos un servidor, o marca «Todos los servidores».":
        "Choose at least one server, or tick \"All servers\".",
    "Código para {name}": "Code for {name}",
    "Copiar": "Copy",
    "Copiado": "Copied",
    " o ": " or ",
    "Pásale este código a <b>{name}</b> por un canal privado. Con él puede entrar:<br><br>"
    "• <b>Desde Ownhost</b>: «Conectar a un equipo», dirección {where}, puerto <b>{port}</b>, y el código en "
    "«Token o código».<br>"
    "• <b>Desde el navegador del móvil</b>: abre <b>http://{first}:{port}/</b> y escribe el código.<br><br>"
    "Tiene que estar en tu red local, o en tu Tailscale (desde Tailscale puedes compartirle solo este equipo "
    "con «Share»).<br><br>"
    "<b>Guárdalo ahora:</b> no se puede volver a ver. Si se pierde, quita este acceso y crea otro.":
        "Send this access code to <b>{name}</b> over a private channel. With it they can get in:<br><br>"
        "• <b>From Ownhost</b>: \"Connect to a computer\", address {where}, port <b>{port}</b>, and the code "
        "in \"Token or code\".<br>"
        "• <b>From a phone's browser</b>: open <b>http://{first}:{port}/</b> and enter the code.<br><br>"
        "They must be on your local network or your Tailscale (from Tailscale you can share just this "
        "computer with \"Share\").<br><br>"
        "<b>Save it now:</b> it can't be shown again. If it gets lost, revoke this access and create another.",

    # ---------- app_update.py ----------
    "Actualizaciones": "Updates",
    "Ya tienes la última versión.": "You already have the latest version.",
    "Todavía no hay ninguna versión publicada.": "No version has been published yet.",
    "No se pudo comprobar si hay versión nueva:\n{msg}": "Couldn't check for a new version:\n{msg}",
    "Versión nueva": "New version",
    "<b>Hay una versión nueva de Ownhost</b> (del {date}).": "<b>A new version of Ownhost is available</b> ({date}).",
    "Se descarga, la app se cierra y se vuelve a abrir sola. Tus servidores siguen encendidos.":
        "It downloads, then the app closes and opens again by itself. Your servers keep running.",
    "Esta copia no se puede actualizar sola: descárgala desde la página de versiones.":
        "This copy can't update itself: download it from the releases page.",
    "Actualizar ahora": "Update now",
    "Abrir la página": "Open the page",
    "Ahora no": "Not now",
    "Descargando la versión nueva...": "Downloading the new version...",
    "Actualizando": "Updating",
    "No se pudo actualizar:\n{msg}": "Couldn't update:\n{msg}",
}
