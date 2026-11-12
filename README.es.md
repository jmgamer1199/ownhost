[English](README.md) · **Español**

# Ownhost

Monta tus propios servidores de **Minecraft Java** (Vanilla, Paper, Fabric, Forge, NeoForge), **Minecraft Bedrock** y **Hytale** en tus propios equipos: tu PC, un portátil que ya no uses o un servidor casero. Con la app (Windows y Linux) los creas, enciendes, apagas, actualizas y haces copias de seguridad desde cualquier PC de tu red local o de tu Tailscale. Sin alquilar nada ni depender de alojamientos de terceros.

## Índice

- [Capturas de pantalla](#capturas-de-pantalla)
- [Inicio rápido](#inicio-rápido)
- [Requisitos del equipo](#requisitos-del-equipo)
- [Cómo funciona](#cómo-funciona)
- [Instalación](#instalación)
- [Equipos detectados automáticamente](#equipos-detectados-automáticamente)
- [Tailscale](#tailscale)
- [Puertos y cortafuegos](#puertos-y-cortafuegos)
- [Multiplataforma (Bedrock)](#multiplataforma-bedrock)
- [Mover un servidor a otro equipo](#mover-un-servidor-a-otro-equipo)
- [Mundos](#mundos)
- [Mods y plugins](#mods-y-plugins)
- [Jugadores](#jugadores)
- [Rendimiento](#rendimiento)
- [Clonar e icono](#clonar-e-icono)
- [Tareas automáticas](#tareas-automáticas)
- [Memoria recomendada](#memoria-recomendada)
- [Mapa y mundo](#mapa-y-mundo)
- [Archivos](#archivos)
- [Copias en otro equipo](#copias-en-otro-equipo)
- [Modpacks](#modpacks)
- [Accesos para amigos](#accesos-para-amigos)
- [Panel web](#panel-web)
- [Actualizaciones](#actualizaciones)
- [Actualizar Ownhost](#actualizar-ownhost)
- [Notas por juego](#notas-por-juego)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad](#seguridad)
- [Desarrollo](#desarrollo)
- [Ideas pendientes](#ideas-pendientes)
- [Licencia](#licencia)

## Capturas de pantalla

Pronto se añadirán capturas.

<!--
Capturas que faltan (añade los archivos y luego sustituye este comentario por los enlaces a las imágenes):
  1. Ventana principal, con la lista de equipos y servidores:
     docs/screenshots/main-window.png
  2. Un servidor en marcha (su ficha con la pestaña Consola y las direcciones de «Conectar a»):
     docs/screenshots/server-running.png
  3. El panel web en el móvil (vale una ventana de navegador estrecha):
     docs/screenshots/web-panel-phone.png
Antes de publicarlas, tapa tokens, códigos de acceso, IPs reales y nombres de jugadores.
El README en inglés usa los mismos archivos.
-->

## Inicio rápido

Descárgalo todo desde la página de [Releases](https://github.com/jmgamer1199/ownhost/releases) del proyecto. No hace falta instalar Python. Más detalles en [Instalación](#instalación).

### En Windows

1. Descarga `Ownhost.exe` y ábrelo. Si Windows muestra un aviso, lee antes [Avisos de SmartScreen o del antivirus](#avisos-de-smartscreen-o-del-antivirus).
2. Pulsa **«Usar este PC como servidor»**. La primera vez puede tardar un poco en arrancar el agente de este PC.
3. Si Windows pregunta por el cortafuegos, permite el acceso solo en **redes privadas**.
4. Pulsa **«＋ Nuevo servidor»**, elige **Juego**, **Tipo** y **Versión**, cuántos **Jugadores a la vez** y la **Memoria máxima** (la app propone un valor). En Minecraft, marca **«Acepto el EULA de Minecraft»**. Pulsa **Crear**.
5. Cuando termine de instalarse, selecciona el servidor en la lista y pulsa **Encender**. La ficha muestra en «Conectar a» las direcciones para entrar.

### En Linux con escritorio

1. Descarga `Ownhost-x86_64.AppImage` y, si quieres, `install-app-linux.sh` en la misma carpeta.
2. Ejecuta `chmod +x Ownhost-x86_64.AppImage` y ábrelo con doble clic, o ejecuta `bash install-app-linux.sh` para añadirlo al menú de aplicaciones.
3. Sigue como en Windows desde el paso 2. Si el equipo tiene `ufw` o `firewalld` activo, la app se ofrece a permitir los puertos (solo para la red de casa y Tailscale, ver [Puertos y cortafuegos](#puertos-y-cortafuegos)).

### En Linux sin escritorio (solo el agente)

1. Descarga `Ownhost` e `install-agent-service.sh` en una misma carpeta.
2. Ejecuta `sudo bash install-agent-service.sh`. Al final muestra la IP y el token.
3. En otro equipo con la app, pulsa **«Conectar a un equipo»**, elígelo en «Detectados» (o escribe su IP), pega el token en **«Token o código»** y acepta.
4. Crea el primer servidor con **«＋ Nuevo servidor»**, eligiendo ese equipo en **Equipo**.

## Requisitos del equipo

Son orientaciones, no mediciones. Ownhost no tiene mediciones publicadas de rendimiento ni de consumo: el uso real depende del juego, la versión, los mods, el número de jugadores y cuánto mundo exploran.

**Ownhost (app y agente)**

- Windows 10 u 11 (64 bits), o Linux x86_64 con glibc 2.28 o posterior (Debian 10+, Ubuntu 20.04+, Fedora, Arch, openSUSE, RHEL/Rocky/Alma 8+ y derivadas; no las que usan musl, como Alpine). No hay versiones para ARM.
- Las descargas ocupan unos 55 MB (Windows) y 70 MB (AppImage). Los servidores, las versiones de Java y las copias ocupan mucho más, según cada mundo.
- Conexión a internet para descargar los juegos, Java, mods y actualizaciones.

**Servidores de juegos**

- **Minecraft Java:** la versión de Java correcta (Temurin) se descarga sola. La memoria que propone la app es un punto de partida (ver [Memoria recomendada](#memoria-recomendada)).
- **Minecraft Bedrock:** el servidor oficial de Mojang, sin Java; gestiona su memoria solo. Funciona en los sistemas para los que Mojang lo publica.
- **Hytale:** necesita una cuenta de Hytale y Java 25 (se descarga solo). La app propone 4 GB de memoria como punto de partida. Consulta la documentación oficial del servidor de Hytale para ver sus requisitos actuales.

**Varios servidores a la vez**

Cada servidor encendido usa su propia memoria. Al crear uno, la app avisa si pides más de la que el equipo tiene libre, y sus propuestas dejan unos 2 GB para el sistema. Es una orientación: no tiene en cuenta otros programas ni el uso de CPU y disco. Usa la pestaña [Rendimiento](#rendimiento) para ver el uso real en tu equipo.

Queda por comprobar: mediciones reales de memoria, CPU y disco con distintos juegos, mods y números de jugadores.

## Cómo funciona

```
 ┌──────────────┐        HTTP + WebSocket (puerto 8765)       ┌─────────────────────┐
 │  App (GUI)   │ ──────────────────────────────────────────▶ │ Agente  (equipo A)  │──▶ servidores
 │  PySide6     │ ──────────────────────────────────────────▶ │ Agente  (equipo B)  │──▶ servidores
 └──────────────┘                                             └─────────────────────┘
```

- **Agente** (`ownhost/agent`): un pequeño servicio que corre en cada equipo que hospeda servidores. Descarga los juegos y la versión de Java que necesita cada uno, arranca y para los procesos y guarda las copias de seguridad. Si cierras la app, los servidores siguen encendidos.
- **App** (`ownhost/app`): la ventana desde la que gestionas todos los agentes de la red.

Cada agente genera un **token** la primera vez que arranca. La app lo necesita para conectarse a él (ver [Seguridad](#seguridad)).

## Instalación

Descarga la última versión desde [Releases](https://github.com/jmgamer1199/ownhost/releases). No hace falta instalar Python ni nada más.

La app se puede usar en español o en inglés (**Ajustes → Idioma**), y el panel web también tiene un selector de idioma.

### Windows

Descarga `Ownhost.exe`, guárdalo donde quieras y ábrelo:

- **Para hospedar servidores en ese PC**, pulsa **«Usar este PC como servidor»**. El mismo programa se queda en segundo plano como agente.
- **Para gestionar otro equipo**, pulsa **«Conectar a un equipo por IP...»** e introduce su IP, puerto y token. En el otro equipo, el botón **«Copiar token»** de su ficha te da el token.

Si Windows pregunta por el cortafuegos, permite el acceso solo en redes privadas (nunca en públicas) para que los demás equipos y los jugadores puedan conectarse. Ownhost nunca necesita abrir puertos en el router: para jugar desde fuera de casa, usa Tailscale.

### Linux con escritorio

Descarga `Ownhost-x86_64.AppImage`, dale permiso de ejecución (`chmod +x Ownhost-x86_64.AppImage`) y ábrelo con doble clic. Con `install-app-linux.sh` (en la misma página) se copia a `~/Applications` y se añade al menú con su icono.

Si la ventana no se abre, faltan bibliotecas gráficas; en Debian/Ubuntu: `sudo apt install libgl1 libegl1 libxcb-cursor0`.

### Linux sin escritorio (solo el agente)

Para un equipo que solo hospeda servidores, descarga `Ownhost` e `install-agent-service.sh` en una misma carpeta y ejecuta:

```bash
sudo bash install-agent-service.sh
```

El script instala el agente como servicio `systemd` (arranca solo con el equipo, aunque nadie inicie sesión), permite los puertos en `ufw` o `firewalld` si hay uno activo (solo para la red de casa y Tailscale: desde internet siguen cerrados) y al final muestra la IP y el token. En la app de otro equipo, pulsa **«Conectar a un equipo»**, elígelo en «Detectados» y pega el token.

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
- Si quitas un equipo de la lista, no se vuelve a añadir solo; sigue apareciendo en «Detectados en tu red».
- Para desactivar el acceso sin token por Tailscale en un equipo, pon `"trust_tailscale": false` en su `agent.json`.

## Tailscale

Si un equipo tiene Tailscale activo, la app lo detecta:

- **Al conectar a un equipo**, el diálogo muestra una lista con los ordenadores de tu red Tailscale. Al elegir uno se rellenan su nombre y su IP.
- **En la ficha de cada servidor**, «Conectar a» muestra la IP de la red local y la de Tailscale. Los amigos que estén en tu tailnet pueden entrar desde fuera de casa sin abrir puertos en el router.
- **Minecraft Bedrock es la excepción, de momento.** Desde fuera de casa, por Tailscale, la app de Minecraft (26.60) se rinde antes de pedir al servidor que la deje entrar: solo lee el nombre y los jugadores y luego muestra una pantalla vacía con un botón «Atrás». Es un fallo de Minecraft, no de Ownhost. Por eso los servidores de Bedrock solo muestran la IP de la red de casa, y la app y el panel web lo avisan. En casa funciona con la IP y el puerto que aparecen, o desde la lista de mundos LAN. Java y Hytale sí funcionan por Tailscale.
- **En la ficha de cada equipo** aparece también su IP de Tailscale, para gestionarlo desde fuera de casa.

## Puertos y cortafuegos

| Para qué | Puerto |
|---|---|
| Agente (app ↔ agente, y encontrar equipos en la red) | 8765/TCP y 8765/UDP |
| Minecraft Java | 25565/TCP (el siguiente libre si ya está ocupado) |
| Minecraft Bedrock (servidor oficial) | 19132/TCP para conectar (el siguiente libre si está ocupado); los jugadores juegan por UDP, en un bloque de 10 puertos por servidor entre el 19200 y el 19299; 7551/UDP para aparecer como partida LAN |
| Hytale | 5520/UDP |
| Bedrock con Geyser (multiplataforma) | 19132/TCP y UDP, más 19133/UDP (los siguientes libres si hay varios servidores) |
| Mapa web (BlueMap) | 8100/TCP (8101, 8102... si hay varios servidores) |

**Cortafuegos de Linux:** si `ufw` o `firewalld` está activo, el botón **«Abrir puertos del cortafuegos»** de la ficha del equipo pide tu contraseña y permite estos rangos: 8765 (TCP y UDP), 25565-25575/TCP, 19132-19140 (TCP y UDP), 5520-5530/UDP, 8100-8110/TCP, 19200-19299/UDP y 7551/UDP. Se permiten **solo** desde redes privadas (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `fc00::/7`, `fe80::/10`) y desde el rango de Tailscale (`100.64.0.0/10`). Las reglas de versiones anteriores, abiertas a cualquier dirección, se quitan. La app lo pregunta la primera vez, y otra vez cuando una versión nueva necesita más puertos.

**Cortafuegos de Windows:** Windows pregunta cuando cada programa empieza a escuchar (Ownhost, y el servidor de Java o de Bedrock). Permite solo las redes privadas.

**Router:** Ownhost nunca abre puertos en tu router ni usa UPnP. Para jugar o gestionar desde fuera de casa, usa Tailscale.

## Multiplataforma (Bedrock)

Los servidores **Paper, Fabric y NeoForge** pueden admitir también jugadores de **Minecraft Bedrock** (móvil, consolas, Windows) gracias a [Geyser](https://geysermc.org/). Puedes activarlo al crear el servidor o después, en **Ajustes → Multiplataforma**.

- Geyser se instala solo. En Paper también se añade ViaVersion si el servidor no es de la última versión de Minecraft, y en Fabric también Fabric API.
- **Floodgate** (activado por defecto) deja entrar a los jugadores de Bedrock sin cuenta de Java.
- Cada servidor recibe su propio puerto para Bedrock, que se muestra en «Conectar a», más el siguiente para NetherNet. Por ejemplo: 19132 en TCP y UDP, y 19133 en UDP.
- Lo que ven los jugadores de Bedrock: el **nombre** del servidor es el de la app; Geyser lo recibe en cada arranque, porque si no mostraría «Geyser». La **descripción** y el **límite de jugadores** son los mismos que en Java. Se editan en **Ajustes** («Descripción» y «Jugadores máximos», que corresponden a `motd` y `max-players` de `server.properties`), y Geyser los copia.
- Geyser se configura con `transport: both`, es decir, NetherNet (Bedrock 26.60+) y RakNet a la vez. Con solo NetherNet, las consolas de la misma red no veían el servidor en la pestaña de Amigos como partida LAN.
- Los jugadores de Bedrock solo pueden entrar desde la red de casa por ahora, igual que en los servidores de Bedrock: consulta [Tailscale](#tailscale).
- Vanilla y Forge no son compatibles: Geyser no tiene versión para ellos.
- **Extras** (en Ajustes → Multiplataforma, una vez activada):
  - **Consolas en la pestaña Amigos (MCXboxBroadcast):** Switch, Xbox y PlayStation no pueden añadir servidores por IP. Geyser tampoco anuncia el servidor en la red local con NetherNet (puerto 7551), así que no aparece como partida LAN. Con esta extensión, el servidor inicia sesión con una cuenta de Microsoft **secundaria** y aparece como partida de un amigo. La app abre una ventana para iniciar sesión y luego muestra a qué cuenta hay que añadir como amigo.
  - **ThirdPartyCosmetics:** los jugadores de Bedrock ven las capas y orejas de los de Java.
  - **EmoteOffhand:** cambiar el objeto de la mano secundaria con un gesto.
  - El paquete que iguala Bedrock a Java (GeyserIntegratedPack, antes GeyserOptionalPack) ya viene incluido en Geyser.
- Floodgate pregunta al servicio de GeyserMC (`api.geysermc.org`) si un jugador de Bedrock ha vinculado su cuenta de Java. Si no se puede contactar con ese servicio, entra sin su cuenta vinculada y la consola lo avisa.
- En consolas (Switch, Xbox, PlayStation) no se puede añadir un servidor por IP directamente. Hace falta un truco como [BedrockConnect](https://github.com/Pugmatt/BedrockConnect). En móvil y Windows sí se añade por IP y puerto.

## Mover un servidor a otro equipo

En la ficha del servidor, pulsa **Clonar o mover → Mover a otro equipo...** y elige el destino. La app hace lo siguiente:

1. Apaga el servidor.
2. Crea una copia de seguridad.
3. La envía por la red al otro agente.
4. Allí instala la misma versión del juego y restaura el mundo, la configuración y los mods.

El original se conserva apagado, salvo que marques «Borrar el servidor de este equipo».

## Mundos

En la ficha del servidor, el botón **Mundo** tiene dos opciones:

- **Importar un mundo...**: eliges la carpeta del mundo (en `.minecraft\saves`, o en la carpeta `saves` de tu instancia de CurseForge, Prism o Modrinth) o un `.zip`.
  - Antes de sustituir el mundo actual se hace una copia de seguridad.
  - Si el mundo viene de una instancia con mods, la app ofrece copiar también sus mods y su carpeta `config`. Los mods de Fabric marcados como «solo cliente» (shaders, minimapas...) se descartan.
  - El servidor tiene que ser de la misma versión de Minecraft y del mismo loader que la instancia.
- **Descargar una copia...**: lleva a la pestaña «Copias», donde «Descargar...» guarda la copia en tu PC. Así puedes editar el mundo con programas como [Amulet](https://www.amuletmc.com/) aunque el servidor esté en otro equipo, y volver a subirlo con «Importar un mundo...».

El botón **Abrir carpeta**, al lado, abre la carpeta del servidor para editar archivos a mano. Solo funciona si el servidor está en el mismo PC que la app.

## Mods y plugins

La pestaña **Plugins** (en servidores Paper) o **Mods** (en servidores Fabric, Forge y NeoForge) busca en **Modrinth** y **CurseForge**. Solo muestra lo que es compatible con la versión del servidor e instala solas las dependencias obligatorias. Desde la misma pestaña puedes activar, desactivar o eliminar lo instalado.

- Modrinth no necesita configuración.
- CurseForge necesita una clave de API gratuita: consíguela en [console.curseforge.com](https://console.curseforge.com/) y ponla en **Ajustes** de la app.
- Algunos autores de CurseForge bloquean las descargas desde apps externas. En ese caso, la app te da el enlace para descargarlo desde la web.
- Los servidores Vanilla no admiten mods.

## Jugadores

En la pestaña **Jugadores** (Minecraft Java, Bedrock y Hytale) ves quién está conectado y puedes hacer operador, echar o banear sin escribir comandos. También gestionas los operadores, la lista blanca (y si está activada) y los baneados.

- Con la multiplataforma, las listas muestran «Nombre (Bedrock)» o «Nombre (Java)». Los jugadores de Bedrock que entran por Geyser llevan un «.» delante de su nombre real: escríbelo con el punto.
- **Con el servidor apagado**, los cambios se escriben directamente en los archivos del servidor y se ven en la lista al momento. Si todavía no se puede identificar la cuenta del jugador (por ejemplo, un jugador de Bedrock por Geyser cuando el servicio de GeyserMC no responde, o un jugador de Hytale que nunca ha entrado), el nombre aparece como **«pendiente»** y se aplica en cuanto se enciende el servidor.
- Bedrock nativo no tiene baneos: usa la lista blanca.
- Minecraft 26 crea los servidores con la lista blanca activada. Ownhost la deja desactivada salvo que marques «Solo pueden entrar los jugadores que añadas» al crear el servidor; así tus amigos pueden entrar a la primera.
- **Estadísticas:** cuánto tiempo ha jugado cada uno, cuántas veces ha entrado y cuándo fue la última vez. El agente las apunta aunque la app esté cerrada.

## Rendimiento

La pestaña **Rendimiento** muestra gráficas de CPU, memoria RAM y jugadores conectados de la última hora, 6 horas o 24 horas, además de cuánto ocupan el servidor y sus copias y el espacio libre del disco. Avisa si el disco pasa del 90 %. El agente toma una muestra por minuto mientras el servidor está encendido y guarda las últimas 24 horas, aunque la app esté cerrada.

## Clonar e icono

- **Clonar o mover → Clonar en este equipo...** crea otro servidor igual (mundo, mods, ajustes e icono) con otro puerto. Se puede clonar con el servidor encendido.
- **Ajustes → Icono** (Minecraft Java): elige cualquier imagen y la app la recorta y la deja en 64x64, que es lo que pide Minecraft. Se ve en la lista de servidores del juego tras reiniciar y también en la lista de la app.

## Tareas automáticas

En **Ajustes** de cada servidor:

- **Volver a encenderlo si se cae** (activado por defecto): si el servidor se cierra por un error, se enciende de nuevo a los 10 segundos. Si se cae más de 3 veces en 10 minutos se queda apagado, para no entrar en un bucle. La app avisa en los dos casos.
- **Copia de seguridad cada N horas** (24 por defecto): solo se hace si el servidor se ha usado desde la última copia. Las copias automáticas acaban en `-auto.zip` y se guardan las últimas N; las que haces a mano no se borran nunca.
- **Reiniciar cada día a una hora**: avisa a los jugadores 1 minuto y 10 segundos antes.
- **Apagar si nadie juega durante N minutos** (Minecraft Java, Bedrock y Hytale; desactivado por defecto): ahorra luz y memoria cuando el servidor se queda vacío.

Las tareas las hace el agente, así que funcionan aunque la app esté cerrada.

## Memoria recomendada

Al crear un servidor (o importar un modpack) dices cuántos vais a jugar a la vez y la app propone la memoria según el tipo de servidor, los mods del modpack y la memoria del equipo, y avisa si pides más de la que tiene libre. Bedrock gestiona su memoria solo, así que no lo pregunta.

Las propuestas son valores de partida fijos, no mediciones: 2 GB para Vanilla y Paper, 3 GB para Fabric y 4 GB para Forge, NeoForge y Hytale (para unos 5 jugadores), más 128 MB por cada jugador de más; para modpacks, 4, 6 u 8 GB según el número de mods. Nunca pasan de la memoria del equipo menos unos 2 GB para el sistema. Ajústalas mirando la pestaña [Rendimiento](#rendimiento).

## Mapa y mundo

En **Ajustes → Mapa y mundo** (servidores Paper, Fabric, Forge y NeoForge):

- **Mapa del mundo en el navegador (BlueMap):** se instala con un clic y la app muestra el enlace (`http://IP:8100/`). Es un mapa en 3D que se ve también desde el móvil y se dibuja poco a poco mientras el servidor está encendido. En Linux, el puerto tiene que estar permitido en el cortafuegos (ver [Puertos y cortafuegos](#puertos-y-cortafuegos)).
- **Generar el mundo por adelantado (Chunky):** eliges un radio en bloques y pulsas **Generar**. Crea el terreno de antemano para que no haya tirones cuando los jugadores exploran; la app muestra el progreso. Se puede seguir jugando mientras tanto.

## Archivos

La pestaña **Archivos** abre y edita la configuración de mods y plugins (`.yml`, `.json`, `.toml`, `.properties`...) sin buscar la carpeta del servidor, también si está en otro equipo. Solo se ven archivos de configuración: nunca el mundo, los programas ni los archivos de inicio de sesión. Los `.json` se comprueban antes de guardar.

## Copias en otro equipo

Por si se estropea un disco: en **Ajustes → Copia en otro equipo** eliges otro equipo tuyo y cada copia de seguridad se envía también allí (guarda las 3 últimas). El otro equipo da un código que solo sirve para recibir copias. Si el primero falla, en la ficha del otro equipo, **Copias de otros equipos...** → **Restaurar aquí** crea el servidor con su mundo, sus mods y su configuración.

## Modpacks

En la ventana **Nuevo servidor**, **Desde un modpack...** te deja elegir un modpack descargado y Ownhost monta el servidor:

- **Modrinth**: el archivo `.mrpack` (botón «Download» de la página del modpack).
- **CurseForge**: el `.zip` normal del modpack, no el «Server Pack». Necesita tu clave de API de CurseForge en Ajustes.

Se instala la versión de Minecraft y la versión exacta de Fabric, Forge o NeoForge que pide el modpack, se descargan los mods (comprobando que no estén dañados) y se copia su configuración. Los mods que solo sirven en el juego (shaders, minimapas...) se descartan solos. Si algún autor de CurseForge no permite descargar su mod desde otras apps, la consola dice cuál falta y dónde descargarlo.

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

**Da «Moderar» y «Gestionar» solo a gente de confianza:** «Moderar» incluye la consola sin filtros, que equivale a ser operador de ese servidor (puede ejecutar cualquier comando del juego). «Gestionar» permite instalar mods e importar mundos, y eso son programas que se ejecutan en tu equipo. «Encender y apagar» es el permiso seguro para dárselo a cualquiera.

Nadie con un código puede crear ni borrar servidores, clonarlos o moverlos, descargar copias ni ver la carpeta del equipo. Tu amigo entra con «Conectar a un equipo» poniendo el código en «Token o código», o desde el navegador (abajo). El código solo se ve al crearlo (ver [Seguridad](#seguridad)). Para quitarle el acceso, pulsa **Quitar acceso**; deja de funcionar al momento.

Tu amigo tiene que estar en tu red local o en tu Tailscale (desde Tailscale puedes compartirle solo ese equipo con «Share»). No se abre nada a internet.

## Panel web

Cada agente sirve un panel en `http://IP-del-equipo:8765/` (la ficha de cada equipo en la app muestra los enlaces, para la red de casa y para Tailscale). Desde el navegador del móvil o de cualquier PC, con el token o un código de amigo, se gestiona cada servidor: encender y apagar, quién juega, jugadores y estadísticas, consola, copias de seguridad y ajustes, según el permiso de cada uno. Si entras desde un dispositivo de tu misma cuenta de Tailscale no hace falta código. Mods, archivos, multiplataforma y mapa se gestionan desde la app. El panel tiene su propio selector de idioma (español/inglés).

El botón **Abrir en el móvil...** de la ficha del equipo muestra un código QR: lo escaneas con la cámara del móvil y el panel se abre ya con tu acceso, en casa o, por Tailscale, desde cualquier sitio. Ese QR contiene **tu código de acceso completo** a ese equipo: no se lo enseñes a nadie ni publiques capturas de él. El navegador del móvil recuerda el código hasta que pulsas **Salir** en el panel.

## Actualizaciones

Cada servidor tiene la opción **«Actualizar automáticamente al encender»** en Ajustes, activada por defecto. Antes de encender, la app comprueba si hay una versión nueva compatible. Si la hay, hace una copia de seguridad y la instala.

- **Minecraft Java:** se actualizan las builds de Paper y los loaders de Fabric, Forge y NeoForge, pero **no se cambia la versión de Minecraft**, para no romper mundos ni mods. Para pasar a otra versión (por ejemplo, de la 1.21.1 a la 26.3) usa «Actualizar...».
- **Minecraft Bedrock:** se instala siempre la última versión, porque los clientes de Bedrock se actualizan solos y no pueden entrar en servidores antiguos.
- **Hytale:** antes de encender, el *Hytale Downloader* comprueba si hay una versión nueva en tu canal (Release o Pre-release) y, si la hay, la instala tras hacer una copia.

## Actualizar Ownhost

Al abrirse, la app mira si hay una versión nueva en las [Releases](https://github.com/jmgamer1199/ownhost/releases) del proyecto (se puede desactivar en **Ajustes**, donde también está **Buscar ahora**). Si la hay, la descarga, se cierra y se abre ya actualizada; los servidores siguen encendidos y el agente del mismo PC se actualiza solo. Los agentes de otros equipos se actualizan desde su ficha con **Actualizar agente**: apagan los servidores guardando el mundo, se reinician con la versión nueva y los vuelven a encender. Antes de reemplazarse, el programa comprueba que lo descargado tiene la huella SHA-256 que GitHub publica para ese archivo, y lo descarta si no coincide. Solo se actualizan solos el `.exe` y el AppImage o binario de Linux; si instalaste el agente con pip, actualízalo con pip. Un agente instalado como servicio de Linux con `install-agent-service.sh` no puede reemplazar su propio archivo (es de `root` a propósito): para actualizarlo, descarga el nuevo `Ownhost` y `install-agent-service.sh` y vuelve a ejecutar el script.

Para publicar versiones, ver [Publicar una versión](#publicar-una-versión).

## Notas por juego

**Minecraft**: al crear el servidor tienes que aceptar el [EULA](https://aka.ms/MinecraftEULA). La versión de Java correcta (Temurin) se descarga sola. Las copias de seguridad en caliente usan `save-off` / `save-all` para no corromper el mundo.

**Minecraft Bedrock**: usa el servidor oficial de Mojang (Bedrock Dedicated Server), que no necesita Java. Desde la versión 1.26.50 se conecta con NetherNet: el puerto del servidor (19132 por defecto, por TCP) inicia la conexión y luego cada jugador juega por un puerto UDP. Ownhost da a cada servidor de Bedrock su propio bloque de 10 puertos UDP entre el 19200 y el 19299 (`server-udp-ports`), para que no choque con Geyser. En móvil y Windows, añade el servidor con la IP y el puerto que aparecen en «Conectar a», o entra desde la lista de mundos LAN. De momento solo funciona desde la red de casa: consulta [Tailscale](#tailscale).

**Forge / NeoForge**: la app descarga y ejecuta el instalador oficial en modo servidor, y elige la versión recomendada del loader para la versión de Minecraft que escojas.

**Hytale**: necesitas una cuenta de Hytale. La app abre una ventana de **inicio de sesión** con un código en dos momentos:
1. Al crear el servidor, para que el *Hytale Downloader* oficial pueda descargar los archivos. Solo la primera vez en cada equipo, porque las credenciales se guardan.
2. Al encenderlo por primera vez, para autenticar el servidor. El agente lanza `/auth login device` por su cuenta y, cuando inicias sesión, guarda las credenciales con `/auth persistence Encrypted`.

Si algo falla, el botón «Iniciar sesión...» de la ficha del servidor vuelve a pedirlo.

En la pestaña **Propiedades** se edita el `config.json` de Hytale (nombre, contraseña, jugadores máximos, modo de juego...) sin tocar el archivo; cada valor conserva su tipo (número, true/false o texto). El nombre del servidor en la app se pasa a `ServerName`, y en **Ajustes** se editan la descripción (`MOTD`) y el límite de jugadores (`MaxPlayers`) cuando el servidor ya se ha encendido una vez. La pestaña **Mods** busca e instala mods de Hytale de CurseForge (necesita tu clave de API) en la carpeta `mods` del servidor, y también busca sus actualizaciones.

## Solución de problemas

### El cortafuegos de Windows bloquea la conexión

Síntoma: desde otro equipo, la app dice que el equipo «está encendido y responde al ping, pero el Ownhost no contesta... Casi seguro es su cortafuegos», o los jugadores no pueden entrar. La app distingue las causas: si dice que el equipo «responde, pero no te deja entrar sin el token», no es el cortafuegos (escribe el token en «Token o código»); si dice que «el Ownhost no responde en el puerto 8765: el agente no está en marcha», el equipo está encendido pero el agente no (en un servidor Linux, `sudo systemctl status ownhost-agent` y `journalctl -u ownhost-agent -n 50`). Los consejos que muestra dependen del sistema del equipo (Windows, Linux con o sin pantalla).

1. Comprueba que la red está como **Privada**: **Configuración → Red e Internet → (tu red) → Tipo de perfil de red**. En una red pública (cafeterías, hoteles...) es mejor no aceptar conexiones.
2. En **Seguridad de Windows → Firewall y protección de red → Permitir una aplicación a través del firewall**, comprueba que Ownhost (y, para los jugadores, Java o `bedrock_server.exe`) está permitido solo en **Privada**.
3. Desde el otro equipo con Windows, comprueba el puerto con PowerShell: `Test-NetConnection 192.168.1.20 -Port 8765` (con la IP correcta). `TcpTestSucceeded : True` significa que se llega al agente.
4. Si prefieres una regla explícita, limítala a tu red y a Tailscale: `New-NetFirewallRule -DisplayName 'Ownhost' -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -RemoteAddress LocalSubnet,100.64.0.0/10`.

No desactives el cortafuegos ni permitas las redes públicas para arreglarlo. En Linux, usa el botón **«Abrir puertos del cortafuegos»** (ver [Puertos y cortafuegos](#puertos-y-cortafuegos)).

### El puerto 8765 ya está en uso

Síntoma: la app dice «El agente de este PC no ha arrancado» y remite a `agent.log`, donde pone «El puerto 8765 está ocupado; esperando a que se libere...».

1. Averigua qué lo usa. Windows: `netstat -ano | findstr :8765` y luego `tasklist /FI "PID eq 1234"` con el número de la última columna. Linux: `ss -ltnp | grep 8765`.
2. Muchas veces es otro agente de Ownhost que ya está en marcha (por ejemplo, el servicio instalado con `install-agent-service.sh` y el AppImage a la vez). En ese caso, usa ese en lugar de arrancar otro.
3. Si es otro programa, ciérralo o cambia el puerto de Ownhost: con el agente parado, edita `"port"` en `agent.json` (`%LOCALAPPDATA%\Ownhost\agent\` en Windows, `~/.local/share/ownhost/` en Linux), vuelve a arrancarlo y actualiza el puerto en la app con **Editar equipo**.

En un equipo con el servicio `systemd`, el puerto se fija en `/etc/systemd/system/ownhost-agent.service` (`--port 8765`) y manda sobre `agent.json`: cámbialo ahí y ejecuta `sudo systemctl daemon-reload` y `sudo systemctl restart ownhost-agent`. Si el cortafuegos está activo, solo permite el 8765: permite el puerto nuevo solo para la red de casa y Tailscale.

### No se detecta Tailscale

La app considera que Tailscale está activo cuando el equipo tiene una IP del rango `100.64.0.0/10` en una interfaz encendida. Para listar tus equipos y reconocer los dispositivos de tu misma cuenta usa el comando `tailscale`.

1. Comprueba que Tailscale está conectado: `tailscale status` y `tailscale ip -4` (en Windows, el icono de Tailscale debe decir «Connected»).
2. Comprueba que el comando `tailscale` funciona en una terminal. En Windows, la app también lo busca en `C:\Program Files\Tailscale\tailscale.exe`.
3. Los dos equipos tienen que estar en la misma tailnet (o el equipo debe estar compartido con «Share»). El acceso sin token solo funciona con dispositivos de **tu misma cuenta**, y solo si `trust_tailscale` no está en `false` en `agent.json`.
4. La detección se hace cada 30 segundos. También puedes añadir el equipo a mano con **«Conectar a un equipo por IP...»** y su IP de Tailscale.

### Avisos de SmartScreen o del antivirus

Los binarios no están firmados digitalmente, así que SmartScreen de Windows puede decir que la app es de un editor desconocido. Un aviso no debe darse por falso positivo sin comprobarlo:

1. Descarga solo desde la página de [Releases](https://github.com/jmgamer1199/ownhost/releases) de este proyecto.
2. Comprueba el SHA-256 del archivo con `Get-FileHash .\Ownhost.exe -Algorithm SHA256` (Windows) o `sha256sum Ownhost-x86_64.AppImage` (Linux), y compáralo con la suma que aparece junto al archivo en la página de Releases, si la hay.
3. Si tu antivirus marca el archivo, no lo ejecutes. Avisa en las incidencias (issues) del proyecto con el nombre del antivirus y el de la detección. También puedes pedir una segunda opinión a un analizador en línea.
4. Si prefieres no fiarte de los binarios, puedes ejecutar Ownhost desde el código fuente (ver [Desarrollo](#desarrollo)).

No desactives el antivirus ni añadas exclusiones como solución por defecto.

## Seguridad

Ownhost está pensado para tu red de casa y Tailscale. No promete seguridad absoluta, y el acceso remoto solo es tan seguro como las condiciones de abajo:

- **HTTP sin cifrar:** la app, el panel web y el agente se comunican por HTTP normal. En la red local, alguien que pueda ver el tráfico podría ver el token. Por Tailscale, el tráfico va cifrado por Tailscale. **No abras nunca el puerto 8765 a internet** ni lo redirijas en el router.
- **El token de `agent.json`:** cada agente guarda su token en `agent.json`, en su carpeta de datos (`%LOCALAPPDATA%\Ownhost\agent\` en Windows, `~/.local/share/ownhost/` en Linux, `/var/lib/ownhost/` con el servicio `systemd`). Quien lo tenga puede hacerlo todo en ese equipo: no lo compartas, no subas ese archivo a ningún sitio y no publiques capturas del token ni del QR de **Abrir en el móvil...**. Si se filtra: para el agente, cambia el nombre de `agent.json` (por ejemplo, a `agent.json.old`) y vuelve a arrancarlo. Se crea un `agent.json` nuevo con otro token; el nombre del equipo, el puerto y las demás opciones vuelven a sus valores por defecto, y los servidores no se tocan. Después actualiza el token en la app con **Editar equipo** y borra el archivo antiguo. No edites el token a mano. Ownhost todavía no tiene un botón para cambiar el token.
- **Códigos de amigos:** solo dan los permisos y servidores elegidos. El agente no guarda el código: guarda su huella SHA-256 y, cuando alguien se conecta, compara la huella del código que envía. Por eso un código no se puede volver a ver después de crearlo: si un amigo lo pierde, quítale el acceso y crea otro. **Quitar acceso** lo invalida al momento.
- **Tailscale:** los dispositivos de **tu misma cuenta de Tailscale** entran sin token. Cualquiera que pueda usar uno de esos dispositivos puede gestionar tus servidores. Se puede desactivar con `"trust_tailscale": false` en `agent.json`.
- **El agente escucha en todas las redes del equipo** (`--bind 0.0.0.0` por defecto). En un portátil que se conecta a otras redes, cualquier dispositivo de esa red podría llegar al puerto 8765 (aunque seguiría necesitando el token). En Windows, deja esas redes como públicas; en Linux, las reglas del cortafuegos solo permiten rangos privados y Tailscale. También puedes usar `--bind` con una IP concreta.
- **Las reglas del cortafuegos de Linux** también permiten `100.64.0.0/10`, que es el rango de Tailscale pero también lo usan algunos proveedores de internet (CGNAT). Detrás de un router de casa que no redirige puertos, esas direcciones no pueden llegar a tu equipo.

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

### Traducciones

Los textos de la interfaz se escriben en español con `tr("Texto en español")`, y su traducción al inglés va en `ownhost/locale/en_*.py`. `scripts/check_translations.py` comprueba que todos los textos de `tr()` tienen traducción al inglés con los mismos `{marcadores}`, y lista las entradas del catálogo que ya no se usan. Ejecútalo antes de publicar:

```bash
python scripts/check_translations.py
```

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

Otros scripts: `scripts\install-windows.ps1` instala el entorno para ejecutar desde el código en Windows, `scripts/install-agent-linux.sh` instala el agente como servicio en Linux usando Python, `scripts/generate_icon.py` vuelve a dibujar el icono y los gráficos del tema, `scripts/generate_ascii.py` vuelve a dibujar el paisaje ASCII de la ficha del equipo, y `scripts/check_translations.py` comprueba las traducciones (ver [Traducciones](#traducciones)).

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
│   ├── firewall.py         reglas del cortafuegos de Linux (ufw / firewalld)
│   ├── phone.py            código QR de «Abrir en el móvil»
│   ├── app_update.py       actualizarse sola
│   ├── client.py           cliente HTTP de la API del agente
│   └── theme.py            el aspecto (QSS y dibujos)
├── locale/                 traducciones al inglés (en_*.py)
├── updates.py              Releases de GitHub: comprobar, descargar y sustituir el ejecutable
├── discovery.py            encontrar agentes en la red local (UDP)
└── net.py                  IPs locales y de Tailscale
```

La app nunca toca los archivos de los servidores directamente: todo pasa por la API del agente, también cuando el agente está en el mismo PC. Por eso cualquier equipo de la red puede gestionar cualquier otro.

### Añadir otro juego

Crea una clase en `ownhost/agent/games/` que herede de `GameAdapter`, implementando `versions`, `java_major`, `install` y `command`, y regístrala en `games/__init__.py`. Opcionalmente: `available_update` (actualización automática), `mod_target` (mods), `read_config`/`write_config` (pestaña Propiedades), `tracks_players` y `setting_keys` (pestaña Jugadores y ajustes comunes). La app la detecta sola.

## Ideas pendientes

- HTTPS entre app y agente si alguna vez sale de la red local.

## Licencia

Ownhost es software libre bajo la [GPL-3.0](LICENSE): puedes usarlo, estudiarlo, modificarlo y compartirlo. Si publicas una versión modificada, tiene que seguir siendo libre y con la misma licencia.

La app incluye las fuentes Cascadia Mono y Geist, las dos con licencia SIL Open Font License (textos en `ownhost/app/assets/fonts`).
