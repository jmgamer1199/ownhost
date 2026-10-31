"""English texts of the server panel (ownhost/app/server_panel.py), the Files tab (files_tab.py) and the
Performance tab (metrics_tab.py)."""

STRINGS = {
    # --- server_panel.py: Geyser extras (EXTRAS table) ---
    "Que aparezca en la pestaña Amigos de las consolas (MCXboxBroadcast)":
        "Show it in the consoles' Friends tab (MCXboxBroadcast)",
    "Switch, Xbox y PlayStation no pueden añadir servidores por IP. Con esto, el servidor aparece como partida de un amigo a través de Xbox Live, también desde fuera de casa.":
        "Switch, Xbox and PlayStation can't add servers by IP. With this, the server shows up as a friend's game through Xbox Live, also from outside your home.",
    "Mostrar capas y orejas de los jugadores de Java (ThirdPartyCosmetics)":
        "Show Java players' capes and ears (ThirdPartyCosmetics)",
    "Los jugadores de Bedrock verán las capas y orejas de servicios de terceros que llevan los de Java.":
        "Bedrock players will see the third-party capes and ears that Java players wear.",
    "Cambiar el objeto de la mano secundaria con un gesto (EmoteOffhand)":
        "Swap the off-hand item with an emote (EmoteOffhand)",
    "Bedrock no tiene la tecla de cambiar de mano: con esta extensión se hace con un gesto.":
        "Bedrock has no swap-hands key: with this extension it is done with an emote.",

    # --- server_panel.py: buttons, menus and tabs ---
    "Encender": "Start",
    "Apagar": "Stop",
    "Reiniciar": "Restart",
    "Forzar cierre": "Force stop",
    "Iniciar sesión...": "Sign in...",
    "Vuelve a pedir el inicio de sesión con tu cuenta del juego": "Asks again to sign in with your game account",
    "Actualizar...": "Update...",
    "Copia de seguridad": "Backup",
    "Clonar o mover": "Clone or move",
    "Clonar en este equipo...": "Clone on this computer...",
    "Crea otro servidor igual (mundo, mods y ajustes) con otro puerto":
        "Creates an identical server (world, mods and settings) on another port",
    "Mover a otro equipo...": "Move to another computer...",
    "Abrir carpeta": "Open folder",
    "Mundo": "World",
    "Importar un mundo...": "Import a world...",
    "Descargar una copia...": "Download a backup...",
    "Eliminar": "Delete",
    "Consola": "Console",
    "Jugadores": "Players",
    "Rendimiento": "Performance",
    "Mods": "Mods",
    "Ajustes": "Settings",
    "Propiedades": "Properties",
    "Archivos": "Files",
    "Copias": "Backups",

    # --- server_panel.py: console and settings ---
    "Escribe un comando (p. ej. say hola, op TuNombre) y pulsa Enter":
        "Type a command (e.g. say hello, op YourName) and press Enter",
    "Encender automáticamente cuando arranque el agente": "Start automatically when the agent starts",
    "Actualizar automáticamente al encender": "Update automatically on start",
    "Antes de encender, instala la última build compatible y hace una copia de seguridad.\nEn Minecraft Java no cambia la versión de Minecraft (para no romper mundos ni mods);\nen Bedrock instala siempre la última, porque los jugadores la necesitan.":
        "Before starting, installs the latest compatible build and makes a backup.\nIn Minecraft Java it doesn't change the Minecraft version (so worlds and mods don't break);\nin Bedrock it always installs the latest, because players need it.",
    "Lo que se ve debajo del nombre en la lista de servidores": "What shows under the name in the server list",
    "Guardar": "Save",
    "Cambiar icono...": "Change icon...",
    "Quitar": "Remove",
    "Se ve en la lista de servidores de Minecraft. Cualquier imagen vale: se recorta y se ajusta a 64x64. Se aplica al reiniciar.":
        "Shown in the Minecraft server list. Any image works: it is cropped and resized to 64x64. Applied on restart.",
    "Icono": "Icon",
    "Nombre": "Name",
    "Descripción": "Description",
    "Jugadores máximos": "Max players",
    "Memoria máxima": "Maximum memory",
    "Puerto": "Port",
    "Volver a encenderlo si se cae": "Start it again if it crashes",
    "Si el servidor se cierra por un error, se vuelve a encender a los 10 segundos.\nSi se cae más de 3 veces en 10 minutos, se queda apagado.":
        "If the server closes because of an error, it starts again after 10 seconds.\nIf it crashes more than 3 times in 10 minutes, it stays stopped.",
    "Nunca": "Never",
    "Solo se hace la copia si el servidor se ha usado desde la anterior.":
        "The backup is only made if the server has been used since the previous one.",
    "Reiniciar cada día a las": "Restart every day at",
    "Si no hay ningún jugador conectado durante ese tiempo, el servidor se apaga solo (ahorra luz y memoria). Solo en Minecraft.":
        "If no player is online for that long, the server stops by itself (saves power and memory). Minecraft only.",
    "<br><b>Tareas automáticas</b>": "<br><b>Automatic tasks</b>",
    "Copia de seguridad cada": "Backup every",
    "Copias automáticas a guardar": "Automatic backups to keep",
    "Apagar si nadie juega durante": "Stop if nobody plays for",
    "Los jugadores reciben un aviso 1 minuto antes del reinicio. Los cambios de memoria se aplican la próxima vez que se encienda el servidor.":
        "Players get a warning 1 minute before the restart. Memory changes apply the next time the server starts.",
    "<br><b>Copia en otro equipo</b>": "<br><b>Backup on another computer</b>",
    "Por si se estropea el disco: cada copia de seguridad se envía también a otro equipo tuyo, y desde allí se puede restaurar el servidor.":
        "In case the disk fails: every backup is also sent to another computer of yours, and the server can be restored from there.",
    "<br><b>Mapa y mundo</b>": "<br><b>Map &amp; world</b>",
    "Solo en servidores Paper, Fabric, Forge o NeoForge.": "Only on Paper, Fabric, Forge or NeoForge servers.",
    "Mapa del mundo en el navegador (BlueMap)": "World map in the browser (BlueMap)",
    "Un mapa en 3D del mundo que se abre en el navegador, también desde el móvil.\nSe dibuja poco a poco mientras el servidor está encendido.":
        "A 3D map of the world that opens in the browser, also on your phone.\nIt is drawn little by little while the server is running.",
    "Generar el mundo por adelantado (Chunky)": "Generate the world in advance (Chunky)",
    "Crea de antemano el terreno alrededor del centro del mundo: así no hay tirones cuando los jugadores exploran zonas nuevas.":
        "Creates the terrain around the world center beforehand, so there is no lag when players explore new areas.",
    "bloques": "blocks",
    "Distancia desde el centro (0, 0). 3000 bloques tarda unos minutos; 10 000 puede tardar horas y ocupar varios GB.":
        "Distance from the center (0, 0). 3000 blocks takes a few minutes; 10,000 can take hours and use several GB.",
    "Generar": "Generate",
    "Cancelar": "Cancel",
    "Radio": "Radius",
    "<br><b>Multiplataforma (Geyser)</b>": "<br><b>Crossplay (Geyser)</b>",
    "Sin necesitar cuenta de Java (Floodgate)": "No Java account needed (Floodgate)",
    "<br><b>Extras para los jugadores de Bedrock</b>": "<br><b>Extras for Bedrock players</b>",
    "El paquete que acerca Bedrock a Java (posturas de soportes de armadura, partículas, flechas espectrales...) ya viene incluido en Geyser.":
        "The pack that brings Bedrock closer to Java (armor stand poses, particles, spectral arrows...) is already included in Geyser.",

    # --- server_panel.py: Properties and Backups tabs ---
    "Propiedad": "Property",
    "Valor": "Value",
    "Recargar": "Reload",
    "El servidor crea este archivo en su primer arranque. Reinicia el servidor para aplicar los cambios.":
        "The server creates this file the first time it starts. Restart the server to apply the changes.",
    "Archivo": "File",
    "Tamaño": "Size",
    "Fecha": "Date",
    "Crear copia ahora": "Back up now",
    "Descargar...": "Download...",
    "Guarda la copia en este PC (para editar el mundo o guardarla aparte)":
        "Saves the backup on this PC (to edit the world or keep it separately)",
    "Restaurar": "Restore",

    # --- server_panel.py: header and status texts ---
    "Conectar a: {addresses}": "Connect to: {addresses}",
    "Bedrock: <b>{ip}</b> puerto <b>{port}</b>": "Bedrock: <b>{ip}</b> port <b>{port}</b>",
    "La carpeta está en el otro equipo: ábrela desde Ownhost en ese equipo":
        "The folder is on the other computer: open it from Ownhost on that computer",
    "Dejar de enviar": "Stop sending",
    "Enviar las copias aquí": "Send the backups here",
    "Para enviarlas a otro equipo, conéctalo antes en la app (tiene que ser tuyo, no de un amigo).":
        "To send them to another computer, connect it in the app first (it has to be yours, not a friend's).",
    "Abrir el mapa: <a href='{url}'>{url}</a>": "Open the map: <a href='{url}'>{url}</a>",
    "El mapa estará en <b>{url}</b> cuando el servidor esté encendido.":
        "The map will be at <b>{url}</b> when the server is running.",
    "Generando: {percent} % ({chunks} chunks, quedan {eta})": "Generating: {percent}% ({chunks} chunks, {eta} left)",
    "Generando: {percent} % ({chunks} chunks)": "Generating: {percent}% ({chunks} chunks)",
    "Mundo generado: {chunks} chunks.": "World generated: {chunks} chunks.",
    "Enciende el servidor para generar el mundo (si acabas de instalar Chunky, reinícialo).":
        "Start the server to generate the world (if you just installed Chunky, restart it).",
    "Pulsa «Generar». Los jugadores pueden seguir jugando mientras tanto.":
        "Press \"Generate\". Players can keep playing meanwhile.",
    "Descargando {name}...": "Downloading {name}...",
    "Reinicia el servidor": "Restart the server",
    "Instalado. Reinicia el servidor para que empiece a funcionar.":
        "Installed. Restart the server for it to start working.",
    "Solo disponible en servidores Paper, Fabric o NeoForge.": "Only available on Paper, Fabric or NeoForge servers.",
    "Activada. Los jugadores de Bedrock entran por el puerto <b>{port}</b>, sin cuenta de Java.":
        "Enabled. Bedrock players join on port <b>{port}</b>, without a Java account.",
    "Activada. Los jugadores de Bedrock entran por el puerto <b>{port}</b>.":
        "Enabled. Bedrock players join on port <b>{port}</b>.",
    "Para jugar desde fuera de casa, abre en el router el {port} (TCP y UDP) y el {next_port} (UDP), o usad Tailscale.":
        "To play from outside your home, open {port} (TCP and UDP) and {next_port} (UDP) on the router, or use Tailscale.",
    "Los jugadores de Bedrock ven el nombre <b>{name}</b> y la misma descripción y límite de jugadores que en Java (los de arriba).":
        "Bedrock players see the name <b>{name}</b> and the same description and player limit as in Java (the ones above).",
    "Desactivar multiplataforma": "Disable crossplay",
    "Permite que jugadores de Bedrock (móvil, consola, Windows) entren a este servidor de Java.":
        "Lets Bedrock players (phone, console, Windows) join this Java server.",
    "Activar multiplataforma": "Enable crossplay",
    "Apaga el servidor primero": "Stop the server first",
    "<span style='color:{color}'>La cuenta de Microsoft aún no tiene <b>perfil de Xbox</b>.</span> Entra en <a href='https://www.xbox.com/'>xbox.com</a> con la cuenta secundaria, crea el perfil (eligiendo un gamertag) y después reinicia el servidor.":
        "<span style='color:{color}'>The Microsoft account doesn't have an <b>Xbox profile</b> yet.</span> Sign in to <a href='https://www.xbox.com/'>xbox.com</a> with the secondary account, create the profile (choosing a gamertag) and then restart the server.",
    "En la consola (Switch, Xbox, PlayStation), añade como amigo a <b>{gamertag}</b>. El servidor aparecerá en la pestaña <b>Amigos</b> cuando esté encendido.":
        "On the console (Switch, Xbox, PlayStation), add <b>{gamertag}</b> as a friend. The server will show up in the <b>Friends</b> tab when it is running.",
    "Al encender el servidor se abrirá una ventana para iniciar sesión con una <b>cuenta de Microsoft secundaria</b> (créala solo para esto, no uses la tuya). Después te diré a quién añadir como amigo.":
        "When the server starts, a window will open to sign in with a <b>secondary Microsoft account</b> (create one just for this, don't use yours). Then I'll tell you who to add as a friend.",
    "Amigos de Xbox": "Xbox friends",
    "Para que el servidor salga en la pestaña Amigos de las consolas, hace falta iniciar sesión con una cuenta de Microsoft.\n\nUsa una cuenta SECUNDARIA creada solo para esto, sin datos personales ni de pago: la extensión imita a un cliente de Xbox y Microsoft podría bloquear esa cuenta. Tu cuenta principal no corre ningún riesgo.\n\n¿Continuar?":
        "For the server to show up in the consoles' Friends tab, you need to sign in with a Microsoft account.\n\nUse a SECONDARY account created just for this, with no personal or payment details: the extension imitates an Xbox client and Microsoft could block that account. Your main account is not at any risk.\n\nContinue?",
    "Multiplataforma": "Crossplay",
    "¿Quitar Geyser? Los jugadores de Bedrock no podrán entrar.": "Remove Geyser? Bedrock players won't be able to join.",
    "Error": "Error",

    # --- server_panel.py: actions ---
    "Se cerrará el proceso sin guardar. ¿Continuar?": "The process will be closed without saving. Continue?",
    "Mover servidor": "Move server",
    "No hay otro equipo conectado. Añade el destino con «Conectar a un equipo (IP)» primero.":
        "No other computer is connected. Add the destination with \"Connect to a computer (IP)\" first.",
    "Preparando...": "Preparing...",
    "Moviendo «{name}» a {computer}": "Moving \"{name}\" to {computer}",
    "Servidor movido": "Server moved",
    "«{name}» ya está en {computer}, puerto {port}.\nLos jugadores deben conectarse a {address}:{port}.":
        "\"{name}\" is now on {computer}, port {port}.\nPlayers must connect to {address}:{port}.",
    "Clonar servidor": "Clone server",
    "Nombre del servidor nuevo (tendrá otro puerto):": "Name of the new server (it will use another port):",
    "{name} (copia)": "{name} (copy)",
    "Clonando «{name}»: el servidor nuevo aparecerá en la lista en unos momentos.":
        "Cloning \"{name}\": the new server will appear in the list in a few moments.",
    "Sin icono": "No icon",
    "Elegir icono": "Choose icon",
    "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.webp)": "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)",
    "No se pudo abrir la imagen.": "The image could not be opened.",
    "Eliminar servidor": "Delete server",
    "¿Eliminar «{name}»? Se borrarán el mundo y todas sus copias de seguridad. Esto no se puede deshacer.":
        "Delete \"{name}\"? The world and all its backups will be erased. This can't be undone.",
    "Guardado. Reinicia el servidor para aplicar los cambios.": "Saved. Restart the server to apply the changes.",
    "Guardado": "Saved",
    "Propiedades guardadas.": "Properties saved.",
    "Importando mundo en «{name}»": "Importing world into \"{name}\"",
    "Mundo importado": "World imported",
    "Mundo importado. Enciende el servidor para cargarlo.\nEl mundo anterior está en la pestaña «Copias».":
        "World imported. Start the server to load it.\nThe previous world is in the \"Backups\" tab.",
    "Descargar copia": "Download backup",
    "Selecciona una copia de la lista (o crea una con «Crear copia ahora»).":
        "Select a backup from the list (or create one with \"Back up now\").",
    "Guardar copia": "Save backup",
    "Archivo zip (*.zip)": "Zip file (*.zip)",
    "Descargada": "Downloaded",
    "Copia guardada en:\n{path}": "Backup saved to:\n{path}",
    "Restaurar copia": "Restore backup",
    "Se sustituirá el mundo actual por la copia {name}. ¿Continuar?":
        "The current world will be replaced by the backup {name}. Continue?",
    "Eliminar copia": "Delete backup",
    "¿Eliminar {name}?": "Delete {name}?",

    # --- files_tab.py ---
    "Elige un archivo de la izquierda": "Choose a file on the left",
    "Configuración de mods, plugins y del servidor. Reinicia el servidor para aplicar los cambios.":
        "Mod, plugin and server configuration. Restart the server to apply the changes.",
    "Hay cambios sin guardar. ¿Descartarlos?": "There are unsaved changes. Discard them?",
    "Este servidor aún no tiene archivos de configuración (se crean al encenderlo).":
        "This server has no configuration files yet (they are created when it starts).",
    "sin guardar": "unsaved",
    "Guardado {path}. Reinicia el servidor para aplicarlo.": "Saved {path}. Restart the server to apply it.",
    "No se pudo guardar": "Could not save",

    # --- metrics_tab.py ---
    "Sin datos en este periodo. Se guarda una muestra por minuto mientras el servidor está encendido.":
        "No data for this period. One sample per minute is stored while the server is running.",
    "Servidor (mundo, mods y ajustes)": "Server (world, mods and settings)",
    "Copias de seguridad": "Backups",
    "Espacio libre en el disco": "Free disk space",
    "<b>CPU</b> <span>· % del procesador del equipo</span>": "<b>CPU</b> <span>· % of the computer's processor</span>",
    "<b>Memoria RAM</b>": "<b>RAM</b>",
    "<b>Jugadores conectados</b>": "<b>Players online</b>",
    "<b>Jugadores conectados</b> · máximo {max}": "<b>Players online</b> · max {max}",
    "<b>Memoria RAM</b> · la que usa el proceso (Java usa algo más que la asignada)":
        "<b>RAM</b> · used by the process (Java uses a bit more than the allocated amount)",
    "Asignada: {size} GB": "Allocated: {size} GB",
    "Ninguna": "None",
    "⚠ Queda poco espacio": "⚠ Low on space",
    "de {total} ({percent} usado)": "of {total} ({percent} used)",
    "Actualizado a las {time}": "Updated at {time}",
}
