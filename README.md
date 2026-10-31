# Ownhost

Monta tus propios servidores de **Minecraft Java** (Vanilla, Paper, Fabric, Forge, NeoForge), **Minecraft Bedrock** y **Hytale** en tus propios equipos: tu PC, un portátil viejo o un homelab. Con la app (Windows y Linux) los creas, enciendes, apagas, actualizas y haces copias de seguridad desde cualquier PC de tu red local o de tu Tailscale. Sin alquilar nada ni depender de servicios de terceros.

## Cómo funciona

```
 ┌──────────────┐        HTTP + WebSocket (puerto 8765)       ┌─────────────────────┐
 │  App (GUI)   │ ──────────────────────────────────────────▶ │ Agente  (este PC)   │──▶ java (Minecraft)
 │  PySide6     │ ──────────────────────────────────────────▶ │ Agente  (homelab)   │──▶ java (Hytale)
 └──────────────┘                                             └─────────────────────┘
```

- **Agente** (`ownhost/agent`): un pequeño servicio que corre en cada equipo que hospeda servidores. Descarga los juegos y la versión de Java que necesita cada uno, arranca y para los procesos y guarda las copias de seguridad. Si cierras la app, los servidores siguen encendidos.
- **App** (`ownhost/app`): la ventana desde la que gestionas todos los agentes de la red.

Cada agente genera un **token** la primera vez que arranca. La app lo necesita para conectarse a él.

## Instalación

### Windows: `Ownhost.exe`

Todo va en un solo archivo, `dist\Ownhost.exe`, que no necesita Python. Cópialo donde quieras y ábrelo:

- **Para hospedar servidores en ese PC**, pulsa **«Usar este PC como servidor»**. El mismo exe arranca en segundo plano como agente (`Ownhost.exe --agent`).
- **Para gestionar otro equipo**, pulsa **«Conectar a un equipo por IP»** e introduce su IP, puerto y token. En el otro PC, el botón **«Copiar token»** de la ficha «Este PC» te da el token.

Para regenerar el exe después de cambiar el código:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\crear-exe.ps1
```

`scripts\instalar-windows.ps1` sigue disponible si prefieres ejecutarlo con Python (modo desarrollo).

### Linux: `dist/linux/`

`scripts\crear-exe.ps1` también genera la versión para Linux. La compila dentro de un contenedor Ubuntu 22.04 con Docker; si Docker Desktop está cerrado, lo arranca. Genera dos archivos:

- **`Ownhost-x86_64.AppImage`**: para escritorio. Dale permiso de ejecución y ábrelo con doble clic. También puedes ejecutar `bash instalar-app-linux.sh` para copiarlo a `~/Applications` y añadirlo al menú con su icono.
- **`Ownhost`**: binario simple, útil en servidores sin escritorio como agente (`Ownhost --agent`).

Al terminar, `scripts\comprobar_privacidad.py` revisa el exe y el binario de Linux. Si encuentra datos de quien compila (usuario, nombre del equipo, carpeta personal o IPs), avisa y el script termina con error. Toda la información de cada usuario (IPs, Tailscale, equipos de la red, carpetas de Minecraft, Java) la detecta la app en su propio equipo.

Funcionan en Ubuntu 22.04 o posterior, Debian 12 o posterior, Proxmox 8 o posterior y derivadas. Si la ventana no abre, instala `sudo apt install libgl1 libegl1 libxcb-cursor0`. El icono de la app se genera con `scripts/generar_icono.py`.

### En un portátil, el homelab u otro equipo Linux (solo el agente)

Copia `dist/linux/Ownhost` y `dist/linux/instalar-agente-servicio.sh` a ese equipo y ejecuta en la misma carpeta:

```bash
sudo bash instalar-agente-servicio.sh
```

El script instala el agente como servicio `systemd` (arranca solo con el equipo, aunque nadie inicie sesión), abre los puertos en `ufw` si está activo y al final muestra la IP y el token. En la app del otro PC, pulsa **«Conectar a un equipo»**, elige el equipo en «Detectados» y pega el token.

En un portátil, para que los servidores sigan funcionando con la tapa cerrada, pon `HandleLidSwitch=ignore` (y `HandleLidSwitchExternalPower=ignore`) en `/etc/systemd/logind.conf` y ejecuta `sudo systemctl restart systemd-logind`.

(`scripts/instalar-agente-linux.sh` hace lo mismo desde el código fuente, con Python.)

### Otro PC con Windows que solo hospeda

Instálalo igual que en este PC y ejecuta `python -m ownhost.agent` (o abre la app y pulsa «Usar este PC»). Abre el puerto 8765/TCP en el firewall.

## Equipos detectados automáticamente

Cada 30 segundos la app busca otros equipos con Ownhost, en la red local (por difusión UDP) y en Tailscale (preguntando a cada dispositivo conectado).

- **Tailscale, misma cuenta:** si el otro equipo está en tu Tailscale con tu misma cuenta, la app **lo añade sola y sin token**. Lo gestionas igual que «Este PC», también desde fuera de casa. El agente pregunta a Tailscale de quién es cada conexión (`tailscale whois`) y solo deja pasar dispositivos de su misma cuenta que lleguen por la interfaz de Tailscale.
- **Resto de equipos** (solo red local, o Tailscale de otra persona): aparecen en **«Detectados en tu red»**. Al pulsar uno, la app pide su token **una vez**.
- Si quitas un equipo de la lista, no se vuelve a añadir solo; sigue apareciendo en «Detectados».
- Para desactivar el acceso sin token por Tailscale en un equipo, pon `"trust_tailscale": false` en su `agent.json`.

## Tailscale

Si un equipo tiene Tailscale activo, la app lo detecta:

- **Al conectar a un equipo**, el diálogo muestra una lista con los ordenadores de tu red Tailscale. Al elegir uno se rellenan su nombre y su IP.
- **En la ficha de cada servidor**, «Conectar a» muestra la IP de la red local y la de Tailscale. Los amigos que estén en tu tailnet pueden entrar desde fuera de casa sin abrir puertos en el router.
- **En la ficha «Este PC»**, aparece también su IP de Tailscale, para gestionarlo desde fuera de casa.

## Puertos

| Para qué | Puerto |
|---|---|
| Agente (app ↔ agente) | 8765/TCP |
| Minecraft | 25565/TCP (el siguiente libre si ya está ocupado) |
| Minecraft Bedrock | 19132/UDP y 19133/UDP (los siguientes libres si hay varios) |
| Hytale | 5520/UDP |
| Bedrock con Geyser (multiplataforma) | 19132/UDP (19133, 19134... si hay varios servidores) |

## Multiplataforma (Bedrock)

Los servidores **Paper, Fabric y NeoForge** pueden admitir también jugadores de **Minecraft Bedrock** (móvil, consolas, Windows) gracias a [Geyser](https://geysermc.org/). Puedes activarlo al crear el servidor o después, en **Ajustes → Multiplataforma**.

- Geyser se instala solo. En Paper también se añade ViaVersion si el servidor no es de la última versión de Minecraft, y en Fabric también Fabric API.
- **Floodgate** (activado por defecto) deja entrar a los jugadores de Bedrock sin cuenta de Java.
- Cada servidor recibe su propio puerto para Bedrock, que se muestra en «Conectar a», más el siguiente para NetherNet. Por ejemplo: 19132 en TCP y UDP, y 19133 en UDP.
- Lo que ven los jugadores de Bedrock: el **nombre** del servidor es el de la app; Geyser lo recibe en cada arranque, porque si no enseñaría «Geyser». La **descripción** y el **límite de jugadores** son los mismos que en Java. Se editan en **Ajustes** («Descripción» y «Jugadores máximos», que corresponden a `motd` y `max-players` de `server.properties`), y Geyser los copia.
- Geyser se configura con `transport: both`, es decir, NetherNet (Bedrock 26.60+) y RakNet a la vez. Con solo NetherNet, las consolas de la misma red no veían el servidor en la pestaña de Amigos como partida LAN.
- Vanilla y Forge no son compatibles: Geyser no tiene versión para ellos.
- **Extras** (en Ajustes → Multiplataforma, una vez activada):
  - **Consolas en la pestaña Amigos (MCXboxBroadcast):** Switch, Xbox y PlayStation no pueden añadir servidores por IP. Geyser tampoco anuncia el servidor en la red local con NetherNet (puerto 7551), así que no aparece como partida LAN. Con esta extensión, el servidor inicia sesión con una cuenta de Microsoft **secundaria** y aparece como partida de un amigo. La app abre una ventana para iniciar sesión y luego muestra a qué cuenta hay que añadir como amigo.
  - **ThirdPartyCosmetics:** los jugadores de Bedrock ven las capas y orejas de los de Java.
  - **EmoteOffhand:** cambiar el objeto de la mano secundaria con un gesto.
  - El paquete que iguala Bedrock a Java (GeyserIntegratedPack, antes GeyserOptionalPack) ya viene incluido en Geyser.
- En consolas (Switch, Xbox, PlayStation) no se puede añadir un servidor por IP directamente. Hace falta un truco como [BedrockConnect](https://github.com/Pugmatt/BedrockConnect). En móvil y Windows sí se añade por IP y puerto.

## Mover un servidor a otro equipo

En la ficha del servidor, pulsa **«Mover a otro equipo...»** y elige el destino. La app hace lo siguiente:

1. Apaga el servidor.
2. Crea una copia de seguridad.
3. La envía por la red al otro agente.
4. Allí instala la misma versión del juego y restaura el mundo, la configuración y los mods.

El original se conserva apagado, salvo que marques «Borrar el servidor de este equipo».

## Mundos

En la ficha del servidor, el botón **Mundo** tiene tres opciones:

- **Importar un mundo...**: eliges la carpeta del mundo (en `.minecraft\saves`, o en la carpeta `saves` de tu instancia de CurseForge, Prism o Modrinth) o un `.zip`.
  - Antes de sustituir el mundo actual se hace una copia de seguridad.
  - Si el mundo viene de una instancia con mods, la app ofrece copiar también sus mods y su carpeta `config`. Los mods de Fabric marcados como «solo cliente» (shaders, minimapas...) se descartan.
  - El servidor tiene que ser de la misma versión de Minecraft y del mismo loader que la instancia.
- **Abrir carpeta del servidor**: solo si el servidor está en este PC. Sirve para editar archivos a mano.
- **Descargar una copia...**: lleva a «Copias de seguridad», donde «Descargar...» guarda la copia en este PC. Así puedes editar el mundo con programas como [Amulet](https://www.amuletmc.com/) aunque el servidor esté en el homelab, y volver a subirlo con «Importar un mundo».

## Mods y plugins

La pestaña **Plugins** (en servidores Paper) o **Mods** (en servidores Fabric, Forge y NeoForge) busca en **Modrinth** y **CurseForge**. Solo muestra lo que es compatible con la versión del servidor e instala solas las dependencias obligatorias. Desde la misma pestaña puedes activar, desactivar o eliminar lo instalado.

- Modrinth no necesita configuración.
- CurseForge necesita una clave de API gratuita de [console.curseforge.com](https://console.curseforge.com/). Hay dos formas de usarla:
  - **Incluida en el exe:** guárdala en un archivo `curseforge.key` en la raíz del proyecto (o en la variable `CURSEFORGE_API_KEY`) y ejecuta `scripts\crear-exe.ps1`. Se mete ofuscada solo al compilar, no queda en el código fuente y está en `.gitignore`. Es ofuscación, no cifrado: alguien con tiempo podría sacarla del exe, así que no repartas el exe públicamente.
  - **Por usuario:** se pone en **Ajustes** de la app y tiene prioridad sobre la incluida.
- Algunos autores de CurseForge bloquean las descargas desde apps externas. En ese caso, la app te da el enlace para descargarlo desde la web.
- Los servidores Vanilla no admiten mods.

## Jugadores

En la pestaña **Jugadores** (Minecraft Java y Bedrock) ves quién está conectado y puedes hacer operador, echar o banear sin escribir comandos. También gestionas los operadores, la lista blanca (y activarla o no) y los baneados.

- Los jugadores de Bedrock que entran por Geyser llevan un «.» delante del nombre.
- Si el servidor está apagado, los cambios quedan pendientes y se aplican en cuanto se enciende.
- Bedrock nativo no tiene baneos: usa la lista blanca.
- Minecraft 26 crea los servidores con la lista blanca activada. Ownhost la deja desactivada salvo que marques «Solo pueden entrar los jugadores que añadas» al crear el servidor; así tus amigos pueden entrar a la primera.

## Rendimiento

La pestaña **Rendimiento** muestra gráficas de CPU, memoria RAM y jugadores conectados de la última hora, 6 horas o 24 horas, y cuánto ocupan el servidor y sus copias, y el espacio libre del disco. Si el disco pasa del 90 % avisa. El agente toma una muestra por minuto mientras el servidor está encendido y guarda las últimas 24 horas, aunque la app esté cerrada.

## Clonar e icono

- **Clonar o mover → Clonar en este equipo...** crea otro servidor igual (mundo, mods, ajustes e icono) con otro puerto. Se puede clonar con el servidor encendido.
- **Ajustes → Icono** (Minecraft Java): elige cualquier imagen y la app la recorta y la deja en 64x64, que es lo que pide Minecraft. Se ve en la lista de servidores del juego tras reiniciar y también en la lista de la app.

## Tareas automáticas

En **Ajustes** de cada servidor:

- **Volver a encenderlo si se cae** (activado por defecto): si el servidor se cierra por un error, se enciende de nuevo a los 10 segundos. Si se cae más de 3 veces en 10 minutos se queda apagado, para no entrar en un bucle. La app avisa en los dos casos.
- **Copia de seguridad cada N horas** (24 por defecto): solo se hace si el servidor se ha usado desde la última copia. Las copias automáticas acaban en `-auto.zip` y se guardan las últimas N; las que haces a mano no se borran nunca.
- **Reiniciar cada día a una hora**: avisa a los jugadores 1 minuto y 10 segundos antes.

Las tareas las hace el agente, así que funcionan aunque la app esté cerrada.

## Modpacks

En **Nuevo servidor → Desde un modpack...** eliges un modpack descargado y Ownhost monta el servidor:

- **Modrinth**: el archivo `.mrpack` (botón «Download» de la página del modpack).
- **CurseForge**: el `.zip` normal del modpack, no el «Server Pack». Necesita tu clave de API de CurseForge en Ajustes.

Se instala la versión de Minecraft y la versión exacta de Fabric, Forge o NeoForge que pide el modpack, se descargan los mods (comprobando que no estén corruptos) y se copia su configuración. Los mods que solo sirven en el juego (shaders, minimapas...) se descartan solos. Si algún autor de CurseForge no permite descargar su mod desde otras apps, la consola dice cuál falta y dónde bajarlo.

Los servidores de modpack no cambian de loader al actualizarse solos, para no romper el modpack.

### Actualizar mods

En la pestaña **Mods**, **Buscar actualizaciones** muestra los mods con versión nueva para tu versión de Minecraft y te deja elegir cuáles actualizar. Antes de cambiar nada se hace una copia de seguridad. Los mods de Modrinth se reconocen aunque no los instalaras desde Ownhost (por ejemplo, los de un modpack o copiados a mano); los de CurseForge, si los instalaste desde Ownhost y tienes la clave de API.

## Accesos para amigos

En la ficha de un equipo tuyo, **Accesos para amigos...** crea un código para cada amigo, sin darle tu token. Eliges qué servidores puede ver y con qué permiso:

| Permiso | Qué puede hacer |
|---|---|
| Encender y apagar | Ver el estado y quién juega; encender, apagar y reiniciar |
| Moderar | Lo anterior, la consola, los jugadores (operadores, lista blanca, baneos) y hacer copias |
| Gestionar | Lo anterior, ajustes, propiedades, mods, actualizar, restaurar copias e importar mundos |

Nadie con un código puede crear ni borrar servidores, clonarlos o moverlos, descargar copias ni ver la carpeta del equipo. Tu amigo entra con «Conectar a un equipo» poniendo el código en «Token o código», o desde el navegador (abajo). El código solo se ve al crearlo: el agente guarda su huella, no el código. Para quitarle el acceso, **Quitar acceso**; deja de funcionar al momento.

Tu amigo tiene que estar en tu red local o en tu Tailscale (desde Tailscale puedes compartirle solo ese equipo con «Share»). Nada se abre a internet.

## Panel web para el móvil

Cada agente sirve un panel sencillo en `http://IP-del-equipo:8765/`. Desde el navegador del móvil, con el token o un código de amigo, se ven los servidores, quién juega, se encienden y apagan y, con permiso de Moderar, se usa la consola. Si entras desde un dispositivo de tu misma cuenta de Tailscale no hace falta código.

## Actualizaciones

Cada servidor tiene la opción **«Actualizar automáticamente al encender»** en Ajustes, activada por defecto. Antes de encender, la app comprueba si hay una versión nueva compatible. Si la hay, hace una copia de seguridad y la instala.

- **Minecraft Java:** se actualizan las builds de Paper y los loaders de Fabric, Forge y NeoForge, pero **no se cambia la versión de Minecraft**, para no romper mundos ni mods. Para pasar a otra versión (por ejemplo, de la 1.21.1 a la 26.3) usa «Actualizar...».
- **Minecraft Bedrock:** se instala siempre la última versión, porque los clientes de Bedrock se actualizan solos y no pueden entrar en servidores antiguos.
- **Hytale:** antes de encender, el *Hytale Downloader* comprueba si hay una versión nueva en tu canal (Release o Pre-release) y, si la hay, la instala tras hacer una copia.

## Actualizar Ownhost

Al abrirse, la app mira si hay una versión nueva en las [Releases](https://github.com/jmgamer1199/ownhost/releases) del proyecto (se puede desactivar en **Ajustes**, donde también está **Buscar ahora**). Si la hay, la descarga, se cierra y se abre ya actualizada; los servidores siguen encendidos y el agente de este PC se actualiza solo. Los agentes de otros equipos (un portátil, el homelab) se actualizan desde su ficha con **Actualizar agente**: apagan los servidores guardando el mundo, se reinician con la versión nueva y los vuelven a encender. Solo se actualizan solos el `.exe` y el AppImage o binario de Linux; si instalaste el agente con pip, actualízalo con pip.

Para publicar una versión: compila con `scripts\crear-exe.ps1` y crea una Release con la etiqueta `v` + la compilación (la que muestra la app, p. ej. `v20261031150000`) adjuntando `Ownhost.exe`, `Ownhost-x86_64.AppImage` y `Ownhost` de `dist/`.

## Notas por juego

**Minecraft**: al crear el servidor tienes que aceptar el [EULA](https://aka.ms/MinecraftEULA). La versión de Java correcta (Temurin) se descarga sola. Las copias de seguridad en caliente usan `save-off` / `save-all` para no corromper el mundo.

**Minecraft Bedrock**: usa el servidor oficial de Mojang (Bedrock Dedicated Server), que no necesita Java. Escucha por UDP en el puerto 19132 (IPv4) y 19133 (IPv6). Si creas varios servidores, la app reparte los puertos para que no choquen entre sí ni con Geyser.

**Forge / NeoForge**: la app descarga y ejecuta el instalador oficial en modo servidor, y elige la versión recomendada del loader para la versión de Minecraft que escojas.

**Hytale**: necesitas una cuenta de Hytale. La app abre una ventana de **inicio de sesión** con un código en dos momentos:
1. Al crear el servidor, para que el *Hytale Downloader* oficial pueda descargar los archivos. Solo la primera vez en cada equipo, porque las credenciales se guardan.
2. Al encenderlo por primera vez, para autenticar el servidor. El agente lanza `/auth login device` solo y, cuando inicias sesión, guarda las credenciales con `/auth persistence Encrypted`.

Si algo falla, el botón «Iniciar sesión...» de la ficha del servidor vuelve a pedirlo.

En la pestaña **Propiedades** se edita el `config.json` de Hytale (nombre, contraseña, jugadores máximos, modo de juego...) sin tocar el archivo; cada valor conserva su tipo (número, true/false o texto). El nombre del servidor en la app se pasa a `ServerName`. La pestaña **Mods** busca e instala mods de Hytale de CurseForge (necesita tu clave de API) en la carpeta `mods` del servidor, y también busca sus actualizaciones.

## Desarrollo

```bash
python -m venv ~/.venvs/ownhost
~/.venvs/ownhost/bin/pip install -e ".[app]"
python -m ownhost.agent        # agente (muestra el token)
python -m ownhost.app          # app
```

Variables y opciones útiles:
- `OWNHOST_DATA_DIR`: carpeta de datos del agente. Por defecto es `%LOCALAPPDATA%\Ownhost\agent` en Windows y `~/.local/share/ownhost` en Linux.
- `python -m ownhost.agent --port 8765 --bind 0.0.0.0 --name "Homelab" --show-token`

La API del agente está documentada automáticamente en `http://<ip>:8765/docs`.

### Añadir otro juego

Crea una clase en `ownhost/agent/games/` que herede de `GameAdapter`, implementando `versions`, `java_major`, `install` y `command`, y regístrala en `games/__init__.py`. La app la detecta sola.

## Ideas pendientes

- HTTPS entre app y agente si alguna vez sale de la red local.

## Licencia

Ownhost es software libre bajo la [GPL-3.0](LICENSE): puedes usarlo, estudiarlo, modificarlo y compartirlo. Si publicas una versión modificada, tiene que seguir siendo libre y con la misma licencia.
