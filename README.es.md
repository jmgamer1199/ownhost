English: [README.md](README.md)

# Ownhost

Monta tus propios servidores de **Minecraft Java** (Vanilla, Paper, Fabric, Forge, NeoForge), **Minecraft Bedrock** y **Hytale** en tus propios equipos: tu PC, un portátil que no uses o un servidor casero. Con la app (Windows y Linux) los creas, enciendes, apagas, actualizas y haces copias de seguridad desde cualquier PC de tu red local o de tu Tailscale. Sin alquilar nada ni depender de servicios de terceros.

## Cómo funciona

```
 ┌──────────────┐        HTTP + WebSocket (puerto 8765)       ┌─────────────────────┐
 │  App (GUI)   │ ──────────────────────────────────────────▶ │ Agente  (equipo A)  │──▶ servidores
 │  PySide6     │ ──────────────────────────────────────────▶ │ Agente  (equipo B)  │──▶ servidores
 └──────────────┘                                             └─────────────────────┘
```

- **Agente** (`ownhost/agent`): un pequeño servicio que corre en cada equipo que hospeda servidores. Descarga los juegos y la versión de Java que necesita cada uno, arranca y para los procesos y guarda las copias de seguridad. Si cierras la app, los servidores siguen encendidos.
- **App** (`ownhost/app`): la ventana desde la que gestionas todos los agentes de la red.

Cada agente genera un **token** la primera vez que arranca. La app lo necesita para conectarse a él.

## Instalación

Descarga la última versión desde [Releases](https://github.com/jmgamer1199/ownhost/releases). No hace falta instalar Python ni nada más.

La app se puede usar en español o en inglés (**Ajustes → Idioma**), y el panel web también tiene un selector de idioma.

### Windows

Descarga `Ownhost.exe`, guárdalo donde quieras y ábrelo:

- **Para hospedar servidores en ese PC**, pulsa **«Usar este PC como servidor»**. El mismo programa se queda en segundo plano como agente.
- **Para gestionar otro equipo**, pulsa **«Conectar a un equipo por IP»** e introduce su IP, puerto y token. En el otro equipo, el botón **«Copiar token»** de su ficha te da el token.

Si Windows pregunta por el cortafuegos, permite el acceso en redes privadas para que los demás equipos y los jugadores puedan conectarse.

### Linux con escritorio

Descarga `Ownhost-x86_64.AppImage`, dale permiso de ejecución (`chmod +x Ownhost-x86_64.AppImage`) y ábrelo con doble clic. Con `install-app-linux.sh` (en la misma página) se copia a `~/Applications` y se añade al menú con su icono.

Funciona en casi cualquier distribución actual: Debian 10+, Ubuntu 20.04+, Fedora, Arch, openSUSE, RHEL/Rocky/Alma 8+ y derivadas (no en las que usan musl, como Alpine). Si la ventana no abre, faltan bibliotecas gráficas; en Debian/Ubuntu: `sudo apt install libgl1 libegl1 libxcb-cursor0`.

### Linux sin escritorio (solo el agente)

Para un equipo que solo hospeda servidores, descarga `Ownhost` e `install-agent-service.sh` en una misma carpeta y ejecuta:

```bash
sudo bash install-agent-service.sh
```

El script instala el agente como servicio `systemd` (arranca solo con el equipo, aunque nadie inicie sesión), abre los puertos en `ufw` si está activo y al final muestra la IP y el token. En la app de otro equipo, pulsa **«Conectar a un equipo»**, elígelo en «Detectados» y pega el token.

Si es un portátil y quieres que los servidores sigan funcionando con la tapa cerrada **mientras está enchufado**:

```bash
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' | sudo tee /etc/systemd/logind.conf.d/10-tapa-cerrada.conf
sudo systemctl kill -s HUP systemd-logind   # aplica el cambio sin cerrar tu sesión
```

Para que tampoco se suspenda con batería, añade también `HandleLidSwitch=ignore`; no es recomendable si lo guardas cerrado en una mochila (se calienta y se descarga). No uses `systemctl restart systemd-logind`: en muchos escritorios cierra la sesión.

## Equipos detectados automáticamente

Cada 30 segundos la app busca otros equipos con Ownhost, en la red local (por difusión UDP) y en Tailscale (preguntando a cada dispositivo conectado).

- **Tailscale, misma cuenta:** si el otro equipo está en tu Tailscale con tu misma cuenta, la app **lo añade sola y sin token**. Lo gestionas como cualquier otro equipo tuyo, también desde fuera de casa. El agente pregunta a Tailscale de quién es cada conexión (`tailscale whois`) y solo deja pasar dispositivos de su misma cuenta que lleguen por la interfaz de Tailscale.
- **Resto de equipos** (solo red local, o Tailscale de otra persona): aparecen en **«Detectados en tu red»**. Al pulsar uno, la app pide su token **una vez**.
- Si quitas un equipo de la lista, no se vuelve a añadir solo; sigue apareciendo en «Detectados».
- Para desactivar el acceso sin token por Tailscale en un equipo, pon `"trust_tailscale": false` en su `agent.json`.

## Tailscale

Si un equipo tiene Tailscale activo, la app lo detecta:

- **Al conectar a un equipo**, el diálogo muestra una lista con los ordenadores de tu red Tailscale. Al elegir uno se rellenan su nombre y su IP.
- **En la ficha de cada servidor**, «Conectar a» muestra la IP de la red local y la de Tailscale. Los amigos que estén en tu tailnet pueden entrar desde fuera de casa sin abrir puertos en el router.
- **En la ficha de cada equipo** aparece también su IP de Tailscale, para gestionarlo desde fuera de casa.

## Puertos

| Para qué | Puerto |
|---|---|
| Agente (app ↔ agente) | 8765/TCP |
| Minecraft | 25565/TCP (el siguiente libre si ya está ocupado) |
| Minecraft Bedrock | 19132/UDP y 19133/UDP (los siguientes libres si hay varios) |
| Hytale | 5520/UDP |
| Bedrock con Geyser (multiplataforma) | 19132/UDP (19133, 19134... si hay varios servidores) |
| Mapa web (BlueMap) | 8100/TCP (8101, 8102... si hay varios servidores) |

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
- **Abrir carpeta del servidor**: solo si el servidor está en el mismo PC que la app. Sirve para editar archivos a mano.
- **Descargar una copia...**: lleva a la pestaña «Copias», donde «Descargar...» guarda la copia en tu PC. Así puedes editar el mundo con programas como [Amulet](https://www.amuletmc.com/) aunque el servidor esté en otro equipo, y volver a subirlo con «Importar un mundo».

## Mods y plugins

La pestaña **Plugins** (en servidores Paper) o **Mods** (en servidores Fabric, Forge y NeoForge) busca en **Modrinth** y **CurseForge**. Solo muestra lo que es compatible con la versión del servidor e instala solas las dependencias obligatorias. Desde la misma pestaña puedes activar, desactivar o eliminar lo instalado.

- Modrinth no necesita configuración.
- CurseForge necesita una clave de API gratuita: consíguela en [console.curseforge.com](https://console.curseforge.com/) y ponla en **Ajustes** de la app.
- Algunos autores de CurseForge bloquean las descargas desde apps externas. En ese caso, la app te da el enlace para descargarlo desde la web.
- Los servidores Vanilla no admiten mods.

## Jugadores

En la pestaña **Jugadores** (Minecraft Java y Bedrock) ves quién está conectado y puedes hacer operador, echar o banear sin escribir comandos. También gestionas los operadores, la lista blanca (y activarla o no) y los baneados.

- Los jugadores de Bedrock que entran por Geyser llevan un «.» delante del nombre.
- Si el servidor está apagado, los cambios quedan pendientes y se aplican en cuanto se enciende.
- Bedrock nativo no tiene baneos: usa la lista blanca.
- Minecraft 26 crea los servidores con la lista blanca activada. Ownhost la deja desactivada salvo que marques «Solo pueden entrar los jugadores que añadas» al crear el servidor; así tus amigos pueden entrar a la primera.
- **Estadísticas:** cuánto tiempo ha jugado cada uno, cuántas veces ha entrado y cuándo fue la última vez. El agente las apunta aunque la app esté cerrada.

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
- **Apagar si nadie juega durante N minutos** (Minecraft; desactivado por defecto): ahorra luz y memoria cuando el servidor se queda vacío.

Las tareas las hace el agente, así que funcionan aunque la app esté cerrada.

## Memoria recomendada

Al crear un servidor (o importar un modpack) dices cuántos vais a jugar a la vez y la app recomienda la memoria según el tipo de servidor, los mods del modpack y la memoria del equipo, y avisa si pides más de la que tiene libre. Bedrock gestiona su memoria solo, así que no lo pregunta.

## Mapa y mundo

En **Ajustes → Mapa y mundo** (servidores Paper, Fabric, Forge y NeoForge):

- **Mapa del mundo en el navegador (BlueMap):** se instala con un clic y la app enseña el enlace (`http://IP:8100/`). Es un mapa en 3D que se ve también desde el móvil y se dibuja poco a poco mientras el servidor está encendido.
- **Generar el mundo por adelantado (Chunky):** eliges un radio en bloques y pulsas **Generar**. Crea el terreno de antemano para que no haya tirones cuando los jugadores exploran; la app enseña el progreso. Se puede seguir jugando mientras tanto.

## Archivos

La pestaña **Archivos** abre y edita la configuración de mods y plugins (`.yml`, `.json`, `.toml`, `.properties`...) sin buscar la carpeta del servidor, también si está en otro equipo. Solo se ven archivos de configuración: nunca el mundo, los programas ni los archivos de inicio de sesión. Los `.json` se comprueban antes de guardar.

## Copias en otro equipo

Por si se estropea un disco: en **Ajustes → Copia en otro equipo** eliges otro equipo tuyo y cada copia de seguridad se envía también allí (guarda las 3 últimas). El otro equipo da un código que solo sirve para recibir copias. Si el primero falla, en la ficha del otro equipo, **Copias de otros equipos...** → **Restaurar aquí** crea el servidor con su mundo, sus mods y su configuración.

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

## Panel web

Cada agente sirve un panel en `http://IP-del-equipo:8765/` (la ficha de cada equipo en la app enseña los enlaces, para la red de casa y para Tailscale). El botón **Abrir en el móvil...** de esa ficha enseña un código QR: lo escaneas con la cámara del móvil y el panel se abre ya con tu acceso, en casa o, por Tailscale, desde cualquier sitio. Desde el navegador del móvil o de cualquier PC, con el token o un código de amigo, se gestiona cada servidor: encender y apagar, quién juega, jugadores y estadísticas, consola, copias de seguridad y ajustes, según el permiso de cada uno. Si entras desde un dispositivo de tu misma cuenta de Tailscale no hace falta código. Mods, archivos, multiplataforma y mapa se gestionan desde la app.

## Actualizaciones

Cada servidor tiene la opción **«Actualizar automáticamente al encender»** en Ajustes, activada por defecto. Antes de encender, la app comprueba si hay una versión nueva compatible. Si la hay, hace una copia de seguridad y la instala.

- **Minecraft Java:** se actualizan las builds de Paper y los loaders de Fabric, Forge y NeoForge, pero **no se cambia la versión de Minecraft**, para no romper mundos ni mods. Para pasar a otra versión (por ejemplo, de la 1.21.1 a la 26.3) usa «Actualizar...».
- **Minecraft Bedrock:** se instala siempre la última versión, porque los clientes de Bedrock se actualizan solos y no pueden entrar en servidores antiguos.
- **Hytale:** antes de encender, el *Hytale Downloader* comprueba si hay una versión nueva en tu canal (Release o Pre-release) y, si la hay, la instala tras hacer una copia.

## Actualizar Ownhost

Al abrirse, la app mira si hay una versión nueva en las [Releases](https://github.com/jmgamer1199/ownhost/releases) del proyecto (se puede desactivar en **Ajustes**, donde también está **Buscar ahora**). Si la hay, la descarga, se cierra y se abre ya actualizada; los servidores siguen encendidos y el agente del mismo PC se actualiza solo. Los agentes de otros equipos se actualizan desde su ficha con **Actualizar agente**: apagan los servidores guardando el mundo, se reinician con la versión nueva y los vuelven a encender. Solo se actualizan solos el `.exe` y el AppImage o binario de Linux; si instalaste el agente con pip, actualízalo con pip.

Para publicar versiones, ver [Publicar una versión](#publicar-una-versión).

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

### Ejecutar desde el código

Hace falta Python 3.11 o superior.

```bash
python -m venv ~/.venvs/ownhost
~/.venvs/ownhost/bin/pip install -e ".[app]"   # en Windows: %USERPROFILE%\.venvs\ownhost\Scripts\pip
python -m ownhost.agent        # el agente (muestra el token al arrancar)
python -m ownhost.app          # la app
```

Solo para hospedar servidores (sin ventana) basta con `pip install -e .`: la interfaz (PySide6) es opcional.

Opciones del agente:
- `--data-dir`, o la variable `OWNHOST_DATA_DIR`: carpeta de datos. Por defecto, `%LOCALAPPDATA%\Ownhost\agent` en Windows y `~/.local/share/ownhost` en Linux.
- `--port 8765`, `--bind 0.0.0.0`, `--name "Servidor"`, `--show-token`.

La API del agente se documenta sola en `http://<ip>:8765/docs`.

### Compilar

Un solo comando, en Windows, genera todo en `dist/`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

| Archivo | Para qué |
|---|---|
| `dist/Ownhost.exe` | Windows: app y agente en un solo archivo, sin instalar Python |
| `dist/linux/Ownhost-x86_64.AppImage` | Linux con escritorio (doble clic) |
| `dist/linux/Ownhost` | Linux sin escritorio: el mismo programa en un binario; con `--agent` es el agente |
| `dist/linux/install-*.sh` | Instaladores de la app y del agente como servicio en Linux |

Qué hace el script:
1. Crea el entorno de Python si no existe, instala las dependencias y PyInstaller.
2. Decide el número de **compilación** (fecha y hora UTC, `AAAAMMDDhhmmss`). Es el mismo para Windows y Linux y es la etiqueta de la versión al publicarla.
3. Compila el `.exe` con PyInstaller (los archivos intermedios van a la carpeta temporal del sistema).
4. Compila Linux dentro de **Docker** con AlmaLinux 8 (`scripts/build-linux.sh`). Usar una glibc antigua hace que funcione en casi cualquier distribución actual. Hace falta Docker Desktop; si no está, solo se genera el `.exe`.
5. Ejecuta `scripts/check_privacy.py`, que abre los binarios y busca tu usuario, el nombre del equipo, tu carpeta personal y tus IPs. Si encuentra algo, avisa: no compartas esos archivos.

Si Ownhost está abierto, el `.exe` en uso se aparta como `.old` y se borra en la siguiente compilación.

**Clave de CurseForge (opcional):** si pones tu clave en un archivo `curseforge.key` en la raíz (o en la variable `CURSEFORGE_API_KEY`), se incluye ofuscada en los binarios y los usuarios no tienen que conseguir la suya. Es ofuscación, no cifrado: alguien con tiempo podría sacarla, así que no la incluyas en binarios que vayas a publicar. Ese archivo está en `.gitignore`: no lo subas nunca.

Otros scripts: `scripts\install-windows.ps1` instala el entorno para ejecutar desde el código en Windows, `scripts/install-agent-linux.sh` instala el agente como servicio en Linux usando Python, `scripts/generate_icon.py` vuelve a dibujar el icono y los gráficos del tema, y `scripts/check_translations.py` comprueba que todos los textos de `tr()` tienen traducción al inglés.

**Textos de la interfaz:** se escriben en español con `tr("Texto en español")` y su traducción al inglés va en `ownhost/locale/en_*.py`. Ejecuta `python scripts/check_translations.py` antes de publicar: avisa de los textos sin traducir.

### Publicar una versión

1. Compila con `scripts\build.ps1`. Al principio muestra la etiqueta, por ejemplo `v20261031143350`.
2. Sube el código (`git push`).
3. Crea la Release con esa etiqueta, los tres binarios y los dos instaladores de Linux:

```bash
gh release create v20261031143350 dist/Ownhost.exe dist/linux/Ownhost-x86_64.AppImage dist/linux/Ownhost dist/linux/install-app-linux.sh dist/linux/install-agent-service.sh --title "Ownhost dd/mm/aaaa" --notes "Novedades..."
```

Las apps y los agentes comparan su compilación con la de la última Release y se ofrecen a actualizarse (ver [Actualizar Ownhost](#actualizar-ownhost)). Para probar las actualizaciones sin publicar nada, la variable `OWNHOST_RELEASES_API` apunta la comprobación a otra dirección con el mismo formato que la API de GitHub.

### Cómo está organizado el código

```
ownhost/
├── agent/                  el agente (FastAPI + uvicorn)
│   ├── api.py              rutas HTTP y WebSocket de la consola; permisos de cada ruta
│   ├── manager.py          servidores: crear, encender, apagar, copias, importar, clonar, mods...
│   ├── access.py           accesos para amigos (códigos, niveles de permiso)
│   ├── games/              un archivo por juego: minecraft.py, bedrock.py, hytale.py (base.py: la interfaz)
│   ├── java.py             descarga la versión de Java que necesita cada servidor
│   ├── mods.py, modpacks.py  Modrinth, CurseForge y modpacks
│   ├── crossplay.py        Geyser, Floodgate y sus extras
│   ├── players.py          jugadores (operadores, lista blanca, baneos)
│   ├── stats.py            estadísticas de jugadores (tiempo jugado, última vez)
│   ├── addons.py           mapa web (BlueMap) y pregeneración (Chunky)
│   ├── files.py            pestaña Archivos: qué se puede leer y guardar
│   ├── replicas.py         copias de seguridad en otro equipo
│   ├── scheduler.py        copias, reinicios programados y apagar si está vacío
│   ├── metrics.py          muestras de CPU, RAM y jugadores para las gráficas
│   └── web/panel.html      el panel web para el móvil
├── app/                    la app (PySide6)
│   ├── main_window.py      ventana principal, lista de equipos, sondeo de los agentes
│   ├── server_panel.py     la ficha de un servidor y sus pestañas
│   ├── *_tab.py            pestañas de jugadores, rendimiento, mods y archivos
│   ├── memory.py           memoria recomendada al crear un servidor
│   ├── replicas.py         copias en otro equipo (enviar y restaurar)
│   ├── dialogs.py          crear servidor, conectar equipo, ajustes...
│   ├── guests.py           accesos para amigos
│   ├── app_update.py       actualizarse sola
│   ├── client.py           cliente HTTP de la API del agente
│   └── theme.py            el aspecto (QSS y dibujos)
├── locale/                 traducciones al inglés (en_*.py)
├── updates.py              Releases de GitHub: comprobar, descargar y sustituir el ejecutable
├── discovery.py            encontrar agentes en la red local (UDP)
└── net.py                  IPs locales y de Tailscale
```

La app nunca toca los archivos de los servidores directamente: todo pasa por la API del agente, también cuando el agente está en el mismo PC. Por eso cualquier equipo de la red puede gestionar cualquier otro.

### Seguridad

- Cada agente tiene un **token** (en `agent.json`, en su carpeta de datos). Quien lo tiene puede hacerlo todo en ese equipo.
- Los dispositivos de **tu misma cuenta de Tailscale** entran sin token (se puede desactivar con `trust_tailscale: false` en `agent.json`).
- Los **códigos de amigos** solo dan los permisos elegidos. El agente guarda su huella (SHA-256), no el código.
- La comunicación va por HTTP sin cifrar: está pensado para la red local y Tailscale (que ya cifra). No abras el puerto 8765 a internet.

### Añadir otro juego

Crea una clase en `ownhost/agent/games/` que herede de `GameAdapter`, implementando `versions`, `java_major`, `install` y `command`, y regístrala en `games/__init__.py`. Opcionalmente: `available_update` (actualización automática), `mod_target` (mods), `read_config`/`write_config` (pestaña Propiedades). La app la detecta sola.

## Ideas pendientes

- HTTPS entre app y agente si alguna vez sale de la red local.

## Licencia

Ownhost es software libre bajo la [GPL-3.0](LICENSE): puedes usarlo, estudiarlo, modificarlo y compartirlo. Si publicas una versión modificada, tiene que seguir siendo libre y con la misma licencia.
