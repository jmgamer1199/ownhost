**English** · [Español](README.es.md)

# Ownhost

Run your own **Minecraft Java** (Vanilla, Paper, Fabric, Forge, NeoForge), **Minecraft Bedrock** and **Hytale** servers on your own computers: your PC, a laptop you no longer use, or a home server. With the app (Windows and Linux) you create, start, stop, update and back them up from any PC on your local network or your Tailscale network. No renting anything, no relying on third-party hosting.

## Contents

- [Screenshots](#screenshots)
- [Quick start](#quick-start)
- [Requirements](#requirements)
- [How it works](#how-it-works)
- [Installation](#installation)
- [Automatically found computers](#automatically-found-computers)
- [Tailscale](#tailscale)
- [Computer settings: starting and switching on](#computer-settings-starting-and-switching-on)
- [Ports and firewall](#ports-and-firewall)
- [Crossplay (Bedrock)](#crossplay-bedrock)
- [Moving a server to another computer](#moving-a-server-to-another-computer)
- [Worlds](#worlds)
- [Mods and plugins](#mods-and-plugins)
- [Players](#players)
- [Performance](#performance)
- [Cloning and icon](#cloning-and-icon)
- [Automatic tasks](#automatic-tasks)
- [Recommended memory](#recommended-memory)
- [Map and world](#map-and-world)
- [Files](#files)
- [Backups on another computer](#backups-on-another-computer)
- [Modpacks](#modpacks)
- [Friend access](#friend-access)
- [Web panel](#web-panel)
- [Updates](#updates)
- [Updating Ownhost](#updating-ownhost)
- [Notes per game](#notes-per-game)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Development](#development)
- [Ideas for later](#ideas-for-later)
- [License](#license)

## Screenshots

Screenshots will be added soon.

<!--
Screenshots still missing (add the files and then replace this comment with the image links):
  1. Main window, with the list of computers and servers:
     docs/screenshots/main-window.png
  2. A server running (its card with the Console tab and the "Connect to" addresses):
     docs/screenshots/server-running.png
  3. The web panel on a phone (a narrow browser window is enough):
     docs/screenshots/web-panel-phone.png
Hide tokens, access codes, real IPs and player names before publishing them.
The Spanish README uses the same files.
-->

## Quick start

Download everything from the project's [Releases](https://github.com/jmgamer1199/ownhost/releases) page. You don't need to install Python. More details in [Installation](#installation).

### On Windows

1. Download `Ownhost.exe` and open it. If Windows shows a warning, read [SmartScreen or antivirus warnings](#smartscreen-or-antivirus-warnings) first.
2. Click **"Use this PC as a server"**. The first time it may take a moment to start this PC's agent.
3. If Windows asks about the firewall, allow access on **private networks** only.
4. Click **"＋ New server"**, choose **Game**, **Type** and **Version**, how many **Players at once** and the **Max memory** (the app suggests a value). For Minecraft, check **"I accept the Minecraft EULA"**. Click **Create**.
5. When it finishes installing, select the server in the list and click **Start**. The card shows the addresses to connect to under "Connect to".

### On Linux with a desktop

1. Download `Ownhost-x86_64.AppImage` and, optionally, `install-app-linux.sh` into the same folder.
2. Either run `chmod +x Ownhost-x86_64.AppImage` and double-click it, or run `bash install-app-linux.sh` to add it to the applications menu.
3. Continue as on Windows from step 2. If the computer has `ufw` or `firewalld` active, the app offers to allow the ports (only for the home network and Tailscale, see [Ports and firewall](#ports-and-firewall)).

### On Linux without a desktop (agent only)

1. Download `Ownhost` and `install-agent-service.sh` into the same folder.
2. Run `sudo bash install-agent-service.sh`. At the end it shows the IP and the token.
3. On another computer with the app, click **"Connect to a computer"**, pick it under "Found" (or type its IP), paste the token in **"Token or code"** and accept.
4. Create the first server with **"＋ New server"**, choosing that computer under **Computer**.

## Requirements

These are guidelines, not measurements. Ownhost has no published performance or consumption measurements: real usage depends on the game, the version, the mods, the number of players and how much of the world they explore.

**Ownhost (app and agent)**

- Windows 10 or 11 (64-bit), or Linux x86_64 with glibc 2.28 or newer (Debian 10+, Ubuntu 20.04+, Fedora, Arch, openSUSE, RHEL/Rocky/Alma 8+ and derivatives; not musl-based ones such as Alpine). There are no ARM builds.
- The downloads take about 55 MB (Windows) and 70 MB (AppImage). Servers, Java versions and backups take much more, depending on each world.
- An internet connection to download the games, Java, mods and updates.

**Game servers**

- **Minecraft Java:** the right Java version (Temurin) is downloaded automatically. The memory the app suggests is a starting point (see [Recommended memory](#recommended-memory)).
- **Minecraft Bedrock:** Mojang's official server, without Java; it manages its own memory. It runs on the systems Mojang publishes it for.
- **Hytale:** needs a Hytale account and Java 25 (downloaded automatically). The app suggests 4 GB of memory as a starting point. Check Hytale's official server documentation for its current requirements.

**Several servers at once**

Each running server uses its own memory. When you create one, the app warns you if you ask for more than the computer has free, and its suggestions leave about 2 GB for the system. That is a guideline: it doesn't account for other programs or for CPU and disk usage. Use the [Performance](#performance) tab to see real usage on your computer.

Still to be checked: real measurements of memory, CPU and disk with different games, mods and numbers of players.

## How it works

```
 ┌──────────────┐        HTTP + WebSocket (port 8765)         ┌─────────────────────┐
 │  App (GUI)   │ ──────────────────────────────────────────▶ │ Agent (computer A)  │──▶ servers
 │  PySide6     │ ──────────────────────────────────────────▶ │ Agent (computer B)  │──▶ servers
 └──────────────┘                                             └─────────────────────┘
```

- **Agent** (`ownhost/agent`): a small service that runs on every computer that hosts servers. It downloads the games and the Java version each one needs, starts and stops the processes, and stores the backups. If you close the app, the servers keep running.
- **App** (`ownhost/app`): the window you use to manage every agent on your network.

Each agent generates a **token** the first time it starts. The app needs it to connect (see [Security](#security)).

## Installation

Download the latest version from [Releases](https://github.com/jmgamer1199/ownhost/releases). You don't need to install Python or anything else.

The app can be used in English or Spanish (**Settings → Language**), and the web panel has a language switch too.

### Windows

Download `Ownhost.exe`, save it wherever you like and open it:

- **To host servers on that PC**, click **"Use this PC as a server"**. The same program stays in the background as the agent.
- **To manage another computer**, click **"Connect to a computer by IP..."** and enter its IP, port and token. On the other computer, the **"Copy token"** button on its card gives you the token.

If Windows asks about the firewall, allow access on private networks only (never public ones) so other computers and players can connect. Ownhost never needs ports opened on your router: to play from outside your home, use Tailscale.

### Linux with a desktop

Download `Ownhost-x86_64.AppImage`, make it executable (`chmod +x Ownhost-x86_64.AppImage`) and double-click it. `install-app-linux.sh` (on the same page) copies it to `~/Applications` and adds it to the menu with its icon.

If the window doesn't open, some graphics libraries are missing; on Debian/Ubuntu: `sudo apt install libgl1 libegl1 libxcb-cursor0`.

### Linux without a desktop (agent only)

For a computer that only hosts servers, download `Ownhost` and `install-agent-service.sh` into the same folder and run:

```bash
sudo bash install-agent-service.sh
```

The script installs the agent as a `systemd` service (it starts with the computer, even if nobody logs in), allows the ports in `ufw` or `firewalld` if one is active (only for the home network and Tailscale: from the internet they stay closed), and finally shows the IP and token. In the app on another computer, click **"Connect to a computer"**, pick it under "Found" and paste the token.

If it's a laptop and you want the servers to keep running with the lid closed **while it's plugged in**:

```bash
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitchExternalPower=ignore\nHandleLidSwitchDocked=ignore\n' | sudo tee /etc/systemd/logind.conf.d/10-lid-closed.conf
sudo systemctl kill -s HUP systemd-logind   # applies the change without logging you out
```

To keep it from suspending on battery as well, also add `HandleLidSwitch=ignore`; this isn't recommended if you carry it closed in a backpack (it heats up and drains the battery). Don't use `systemctl restart systemd-logind`: on many desktops it ends your session.

## Automatically found computers

Every 30 seconds the app looks for other computers running Ownhost, on the local network (via UDP broadcast) and on Tailscale (by asking each connected device).

- **Tailscale, same account:** if the other computer is on your Tailscale network under your own account, the app **adds it by itself, with no token**. You manage it like any other computer of yours, even from outside your home. The agent asks Tailscale who owns each connection (`tailscale whois`) and only lets in devices from its own account that arrive through the Tailscale interface.
- **Other computers** (local network only, or someone else's Tailscale): they appear under **"Found on your network"**. When you click one, the app asks for its token **once**.
- If you remove a computer from the list, it isn't added back automatically; it still shows up under "Found on your network".
- To turn off token-free access over Tailscale on a computer, set `"trust_tailscale": false` in its `agent.json`.

## Computer settings: starting and switching on

On the page of each computer that is on (only for you, its owner), the **"Computer settings..."** button has two options. Both are off by default.

- **Start Ownhost when the computer starts.** It is each system's own way, with no administrator needed:
  - **Windows:** the agent starts when you sign in (a value in your user's "Run" key). If the PC signs in to your account by itself, that is as soon as it's switched on.
  - **Linux with a desktop:** an autostart entry in your user's folder, which also runs when you sign in.
  - **Linux server installed with `install-agent-service.sh`:** the `ownhost-agent` systemd service already starts with the computer, even if nobody signs in. The app shows the box checked and can't change it (it belongs to `root`); to remove it, on that computer: `sudo systemctl disable --now ownhost-agent`.
- **Allow this computer to be switched on from other computers of my network (Wake-on-LAN).** Only if you turn it on, the agent tells the apps that manage it the physical (MAC) address of its network card, and they save it. From then on, when that computer is off, its page shows **"Switch on computer"**, which sends the standard Wake-on-LAN packet (no port is opened). Keep in mind:
  - It **only works inside your home network**: the packet doesn't cross routers or Tailscale.
  - The computer needs Wake-on-LAN turned on in its BIOS/UEFI and in its network card (on Linux, for example, `sudo ethtool -s <card> wol g`; on Windows, in Device Manager → the network card → Power Management). The app can't do that for you.
  - Turning the option off makes the apps forget the address.

If you press **"New server"** and none of your computers is on, the app doesn't just say so: it offers to start this PC's agent ("Use this PC as a server") or to switch on a computer that has Wake-on-LAN, and opens the window to create the server as soon as it's ready (it waits up to 4 minutes).

## Tailscale

If a computer has Tailscale running, the app detects it:

- **When connecting to a computer**, the dialog shows a list of the machines on your Tailscale network. Picking one fills in its name and IP.
- **On each server's card**, "Connect to" shows the local network IP and the Tailscale IP. Friends on your tailnet can join from outside your home without opening ports on the router.
- **Minecraft Bedrock is the exception, for now.** From outside your home, over Tailscale, the Minecraft app (26.60) gives up before asking the server to let it in: it only reads the name and the number of players and then shows an empty screen with a "Back" button. It's a Minecraft bug, not an Ownhost one. That's why Bedrock servers only show the home network IP, and the app and the web panel say so. At home it works with the IP and port shown, or from the LAN worlds list. Java and Hytale do work over Tailscale.
- **On each computer's card** its Tailscale IP is shown too, so you can manage it from outside your home.

## Ports and firewall

| Purpose | Port |
|---|---|
| Agent (app ↔ agent, and finding computers on the network) | 8765/TCP and 8765/UDP |
| Minecraft Java | 25565/TCP (the next free one if it's already taken) |
| Minecraft Bedrock (official server) | 19132/TCP to connect (the next free one if it's taken); players play over UDP, on a block of 10 ports per server between 19200 and 19299; 7551/UDP to appear as a LAN game |
| Hytale | 5520/UDP |
| Bedrock via Geyser (crossplay) | 19132/TCP and UDP, plus 19133/UDP (the next free ones if there are several servers) |
| Web map (BlueMap) | 8100/TCP (8101, 8102... if there are several servers) |

**Linux firewall:** if `ufw` or `firewalld` is active, the **"Open firewall ports"** button on the computer's card asks for your password and allows these ranges: 8765 (TCP and UDP), 25565-25575/TCP, 19132-19140 (TCP and UDP), 5520-5530/UDP, 8100-8110/TCP, 19200-19299/UDP and 7551/UDP. They are allowed **only** from private networks (`192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`, `fc00::/7`, `fe80::/10`) and from Tailscale's range (`100.64.0.0/10`). Rules from older versions that were open to any address are removed. The app asks the first time, and again when a new version needs more ports.

**Windows firewall:** Windows asks when each program starts listening (Ownhost, and the Java or Bedrock server). Allow private networks only.

**Router:** Ownhost never opens ports on your router and doesn't use UPnP. To play or manage from outside your home, use Tailscale.

## Crossplay (Bedrock)

**Paper, Fabric and NeoForge** servers can also accept **Minecraft Bedrock** players (mobile, consoles, Windows) thanks to [Geyser](https://geysermc.org/). You can turn it on when creating the server or later, under **Settings → Crossplay**.

- Geyser installs itself. On Paper, ViaVersion is also added if the server isn't on the latest Minecraft version, and on Fabric, Fabric API is added too.
- **Floodgate** (on by default) lets Bedrock players join without a Java account.
- Each server gets its own Bedrock port, shown under "Connect to", plus the next one for NetherNet. For example: 19132 on TCP and UDP, and 19133 on UDP.
- What Bedrock players see: the server **name** is the one in the app; Geyser receives it on every start, because otherwise it would show "Geyser". The **description** and **player limit** are the same as on Java. You edit them in **Settings** ("Description" and "Max players", which map to `motd` and `max-players` in `server.properties`), and Geyser copies them.
- Geyser is configured with `transport: both`, meaning NetherNet (Bedrock 26.60+) and RakNet at the same time. With NetherNet alone, consoles on the same network didn't see the server in the Friends tab as a LAN game.
- Bedrock players can only join from the home network for now, as with Bedrock servers: see [Tailscale](#tailscale).
- Vanilla and Forge aren't supported: Geyser has no version for them.
- **Extras** (under Settings → Crossplay, once enabled):
  - **Consoles in the Friends tab (MCXboxBroadcast):** Switch, Xbox and PlayStation can't add servers by IP. Geyser doesn't announce the server on the local network over NetherNet (port 7551) either, so it doesn't show up as a LAN game. With this extension, the server signs in with a **secondary** Microsoft account and appears as a friend's game. The app opens a sign-in window and then shows which account to add as a friend.
  - **ThirdPartyCosmetics:** Bedrock players see Java players' capes and ears.
  - **EmoteOffhand:** swap the item in the offhand with an emote.
  - The pack that makes Bedrock match Java (GeyserIntegratedPack, formerly GeyserOptionalPack) is already included in Geyser.
- Floodgate asks GeyserMC's service (`api.geysermc.org`) whether a Bedrock player has linked their Java account. If that service can't be reached, they join without their linked account, and the console says so.
- On consoles (Switch, Xbox, PlayStation) you can't add a server by IP directly. You need a workaround such as [BedrockConnect](https://github.com/Pugmatt/BedrockConnect). On mobile and Windows you can add it by IP and port.

## Moving a server to another computer

On the server's card, click **Clone or move → Move to another computer...** and pick the destination. The app does the following:

1. Stops the server.
2. Creates a backup.
3. Sends it over the network to the other agent.
4. Installs the same game version there and restores the world, settings and mods.

The original is kept, stopped, unless you check "Delete the server from this computer".

## Worlds

On the server's card, the **World** button has two options:

- **Import a world...**: pick the world folder (in `.minecraft\saves`, or in the `saves` folder of your CurseForge, Prism or Modrinth instance) or a `.zip`.
  - A backup is made before the current world is replaced.
  - If the world comes from a modded instance, the app offers to copy its mods and `config` folder too. Fabric mods marked as "client only" (shaders, minimaps...) are skipped.
  - The server must be on the same Minecraft version and the same loader as the instance.
- **Download a backup...**: takes you to the "Backups" tab, where "Download..." saves the backup to your PC. That way you can edit the world with tools such as [Amulet](https://www.amuletmc.com/) even if the server is on another computer, and upload it again with "Import a world...".

The **Open folder** button, next to it, opens the server folder to edit files by hand. It only works if the server is on the same PC as the app.

## Mods and plugins

The **Plugins** tab (on Paper servers) or **Mods** tab (on Fabric, Forge and NeoForge servers) searches **Modrinth** and **CurseForge**. It only shows what's compatible with the server version and installs required dependencies automatically. From the same tab you can enable, disable or remove what's installed.

- Modrinth needs no setup.
- CurseForge needs a free API key: get one at [console.curseforge.com](https://console.curseforge.com/) and enter it in the app's **Settings**.
- Some CurseForge authors block downloads from external apps. In that case, the app gives you the link to download it from the website.
- Vanilla servers don't support mods.

## Players

In the **Players** tab (Minecraft Java, Bedrock and Hytale) you see who's online and can op, kick or ban them without typing commands. You also manage operators, the whitelist (and whether it's on) and banned players.

- With crossplay, the lists show "Name (Bedrock)" or "Name (Java)". Bedrock players joining through Geyser have a "." in front of their real name: type it with the dot.
- **With the server stopped**, the changes are written straight to the server's files and show up in the list at once. If the player's account can't be identified yet (for example, a Bedrock player through Geyser when GeyserMC's service doesn't answer, or a Hytale player who has never joined), the name shows as **"pending"** and is applied as soon as the server starts.
- Native Bedrock has no bans: use the whitelist.
- Minecraft 26 creates servers with the whitelist turned on. Ownhost leaves it off unless you check "Only players you add can join" when creating the server, so your friends can join right away.
- **Statistics:** how long each player has played, how many times they've joined, and when they were last on. The agent records them even when the app is closed.

## Performance

The **Performance** tab shows graphs of CPU, RAM and online players for the last hour, 6 hours or 24 hours, plus how much space the server and its backups take up and the free disk space. It warns you if the disk goes over 90 %. The agent takes one sample per minute while the server is running and keeps the last 24 hours, even when the app is closed.

## Cloning and icon

- **Clone or move → Clone on this computer...** creates an identical server (world, mods, settings and icon) on a different port. You can clone while the server is running.
- **Settings → Icon** (Minecraft Java): pick any image and the app crops it and scales it to 64x64, which is what Minecraft requires. It shows up in the game's server list after a restart, and in the app's list too.

## Automatic tasks

In each server's **Settings**:

- **Restart it if it crashes** (on by default): if the server closes because of an error, it starts again after 10 seconds. If it crashes more than 3 times in 10 minutes it stays stopped, to avoid a loop. The app notifies you in both cases.
- **Backup every N hours** (24 by default): only made if the server has been used since the last backup. Automatic backups end in `-auto.zip` and the last N are kept; the ones you make by hand are never deleted.
- **Restart every day at a set time**: warns players 1 minute and 10 seconds before.
- **Stop if nobody plays for N minutes** (Minecraft Java, Bedrock and Hytale; off by default): saves power and memory when the server is empty.

The agent runs these tasks, so they work even when the app is closed.

## Recommended memory

When you create a server (or import a modpack) you say how many people will play at once, and the app suggests the memory based on the server type, the modpack's mods and the computer's memory, and warns you if you ask for more than is free. Bedrock manages its own memory, so it doesn't ask.

The suggestions are fixed starting values, not measurements: 2 GB for Vanilla and Paper, 3 GB for Fabric, 4 GB for Forge, NeoForge and Hytale (for about 5 players), plus 128 MB for each extra player; for modpacks, 4, 6 or 8 GB depending on the number of mods. They never go beyond the computer's memory minus about 2 GB for the system. Adjust them by watching the [Performance](#performance) tab.

## Map and world

Under **Settings → Map & world** (Paper, Fabric, Forge and NeoForge servers):

- **World map in the browser (BlueMap):** installs with one click and the app shows the link (`http://IP:8100/`). It's a 3D map you can also view on your phone, and it renders bit by bit while the server is running. On Linux the port must be allowed in the firewall (see [Ports and firewall](#ports-and-firewall)).
- **Pre-generate the world (Chunky):** choose a radius in blocks and click **Generate**. It creates the terrain ahead of time so there's no lag when players explore; the app shows the progress. You can keep playing in the meantime.

## Files

The **Files** tab opens and edits mod and plugin configuration (`.yml`, `.json`, `.toml`, `.properties`...) without hunting for the server folder, even if it's on another computer. Only configuration files are shown: never the world, the programs or the login files. `.json` files are validated before saving.

## Backups on another computer

In case a disk fails: under **Settings → Backup on another computer** you choose another computer of yours and every backup is also sent there (it keeps the last 3). The other computer provides a code that can only be used to receive backups. If the first one fails, on the other computer's card, **Backups from other computers...** → **Restore here** creates the server with its world, mods and configuration.

## Modpacks

In the **New server** window, **From a modpack...** lets you pick a downloaded modpack and Ownhost sets up the server:

- **Modrinth**: the `.mrpack` file ("Download" button on the modpack's page).
- **CurseForge**: the regular `.zip` of the modpack, not the "Server Pack". Requires your CurseForge API key in Settings.

It installs the Minecraft version and the exact Fabric, Forge or NeoForge version the modpack requires, downloads the mods (checking they aren't corrupted) and copies their configuration. Mods that only matter in the game client (shaders, minimaps...) are skipped automatically. If a CurseForge author doesn't allow their mod to be downloaded from other apps, the console says which one is missing and where to get it.

Modpack servers don't change loader when they update themselves, so the modpack doesn't break.

### Updating mods

In the **Mods** tab, **Check for updates** shows the mods with a new version for your Minecraft version and lets you choose which ones to update. A backup is made before anything changes. Modrinth mods are recognized even if you didn't install them from Ownhost (for example, those from a modpack or copied by hand); CurseForge ones, if you installed them from Ownhost and have the API key.

## Friend access

On the card of one of your computers, **Friend access...** creates a code for each friend, without giving them your token. You choose which servers they can see and with what permission:

| Permission | What they can do |
|---|---|
| Start and stop | See the status and who's playing; start, stop and restart |
| Moderate | All of the above, plus the console, players (operators, whitelist, bans) and making backups |
| Manage | All of the above, plus settings, properties, mods, updating, restoring backups and importing worlds |

**Give "Moderate" and "Manage" only to people you trust:** "Moderate" includes the raw console, which is the same as being an operator of that server (they can run any game command). "Manage" lets them install mods and import worlds, and those are programs that run on your computer. "Start and stop" is the safe one to share widely.

Nobody with a code can create or delete servers, clone or move them, download backups or see the computer's folder. Your friend connects with "Connect to a computer" by entering the code in "Token or code", or from the browser (below). The code is only shown when it's created (see [Security](#security)). To revoke access, click **Revoke access**; it stops working immediately.

Your friend has to be on your local network or your Tailscale network (in Tailscale you can share just that computer with "Share"). Nothing is opened to the internet.

## Web panel

Each agent serves a panel at `http://computer-IP:8765/` (each computer's card in the app shows the links, for the home network and for Tailscale). From the browser on your phone or any PC, with the token or a friend code, you manage each server: start and stop, who's playing, players and statistics, console, backups and settings, depending on each person's permission. If you connect from a device on your own Tailscale account, no code is needed. Mods, files, crossplay and the map are managed from the app. The panel has its own language switch (English/Spanish).

The **Open on phone...** button on the computer's card shows a QR code: scan it with your phone's camera and the panel opens already signed in, at home or, through Tailscale, from anywhere. That QR code contains **your full access code** to that computer: don't show it to anyone or post screenshots of it. The phone's browser remembers the code until you tap **Sign out** in the panel.

## Updates

Each server has the **"Update automatically on start"** option in Settings, on by default. Before starting, the app checks whether there's a new compatible version. If there is, it makes a backup and installs it.

- **Minecraft Java:** Paper builds and the Fabric, Forge and NeoForge loaders are updated, but **the Minecraft version is not changed**, so worlds and mods don't break. To move to another version (for example, from 1.21.1 to 26.3) use "Update...".
- **Minecraft Bedrock:** the latest version is always installed, because Bedrock clients update themselves and can't join older servers.
- **Hytale:** before starting, the *Hytale Downloader* checks whether there's a new version on your channel (Release or Pre-release) and, if so, installs it after making a backup.

## Updating Ownhost

When it opens, the app checks whether there's a new version in the project's [Releases](https://github.com/jmgamer1199/ownhost/releases) (this can be turned off in **Settings**, which also has **Check now**). If there is, it downloads it, closes and reopens already updated; the servers keep running and the agent on the same PC updates itself. Agents on other computers are updated from their card with **Update agent**: they stop the servers saving the world, restart with the new version and start them again. Before replacing itself, the program checks that what it downloaded has the SHA-256 checksum GitHub publishes for that file, and discards it if it doesn't match. Only the `.exe` and the Linux AppImage or binary update themselves; if you installed the agent with pip, update it with pip. An agent installed as a Linux service with `install-agent-service.sh` can't replace its own file (it belongs to `root` on purpose): to update it, download the new `Ownhost` and `install-agent-service.sh` and run the script again.

To publish releases, see [Publishing a release](#publishing-a-release).

## Notes per game

**Minecraft**: when creating the server you have to accept the [EULA](https://aka.ms/MinecraftEULA). The right Java version (Temurin) is downloaded automatically. Hot backups use `save-off` / `save-all` so the world doesn't get corrupted.

**Minecraft Bedrock**: uses Mojang's official server (Bedrock Dedicated Server), which doesn't need Java. Since version 1.26.50 it connects with NetherNet: the server port (19132 by default, over TCP) starts the connection and each player then plays over a UDP port. Ownhost gives each Bedrock server its own block of 10 UDP ports between 19200 and 19299 (`server-udp-ports`), so it doesn't clash with Geyser. On mobile and Windows, add the server with the IP and port shown under "Connect to", or join it from the LAN worlds list. For now it only works from the home network: see [Tailscale](#tailscale).

**Forge / NeoForge**: the app downloads and runs the official installer in server mode, and picks the recommended loader version for the Minecraft version you choose.

**Hytale**: you need a Hytale account. The app opens a **sign-in** window with a code at two points:
1. When creating the server, so the official *Hytale Downloader* can download the files. Only the first time on each computer, because the credentials are saved.
2. When starting it for the first time, to authenticate the server. The agent runs `/auth login device` by itself and, once you sign in, saves the credentials with `/auth persistence Encrypted`.

If something goes wrong, the "Sign in..." button on the server's card asks again.

The **Properties** tab edits Hytale's `config.json` (name, password, max players, game mode...) without touching the file; each value keeps its type (number, true/false or text). The server name in the app is passed to `ServerName`, and **Settings** edits the description (`MOTD`) and the player limit (`MaxPlayers`) once the server has started for the first time. The **Mods** tab searches for and installs Hytale mods from CurseForge (requires your API key) into the server's `mods` folder, and also checks for their updates.

## Troubleshooting

### Windows Firewall blocks the connection

Symptom: from another computer the app says the computer "is on and answers ping, but Ownhost doesn't answer... It is almost certainly its firewall", or players can't join. The app tells the causes apart: if it says the computer "answers, but won't let you in without the token", it isn't the firewall (type the token in "Token or code"); if it says "Ownhost doesn't answer on port 8765: the agent isn't running", the computer is on but the agent isn't (on a Linux server, `sudo systemctl status ownhost-agent` and `journalctl -u ownhost-agent -n 50`). The advice it shows depends on the computer's system (Windows, Linux with or without a screen).

1. Check that the network is set as **Private**: **Settings → Network & internet → (your network) → Network profile type**. On a public network (cafés, hotels...) it's better not to accept connections.
2. In **Windows Security → Firewall & network protection → Allow an app through firewall**, check that Ownhost (and, for players, Java or `bedrock_server.exe`) is allowed only on **Private**.
3. From the other Windows computer, check the port with PowerShell: `Test-NetConnection 192.168.1.20 -Port 8765` (with the right IP). `TcpTestSucceeded : True` means the agent is reachable.
4. If you prefer an explicit rule, limit it to your network and Tailscale: `New-NetFirewallRule -DisplayName 'Ownhost' -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow -RemoteAddress LocalSubnet,100.64.0.0/10`.

Don't turn the firewall off or allow public networks to fix it. On Linux, use the **"Open firewall ports"** button (see [Ports and firewall](#ports-and-firewall)).

### Port 8765 is already in use

Symptom: the app says "This PC's agent didn't start" and points to `agent.log`, where it says "Port 8765 is in use; waiting for it to be free...".

1. Find out what is using it. Windows: `netstat -ano | findstr :8765`, then `tasklist /FI "PID eq 1234"` with the number from the last column. Linux: `ss -ltnp | grep 8765`.
2. It's often another Ownhost agent that's already running (for example, the service installed with `install-agent-service.sh` and the AppImage at the same time). In that case, use that one instead of starting another.
3. If it's another program, close it, or change Ownhost's port: with the agent stopped, edit `"port"` in `agent.json` (`%LOCALAPPDATA%\Ownhost\agent\` on Windows, `~/.local/share/ownhost/` on Linux), start it again and update the port in the app with **Edit computer**.

On a computer with the `systemd` service, the port is set in `/etc/systemd/system/ownhost-agent.service` (`--port 8765`) and overrides `agent.json`: change it there, then run `sudo systemctl daemon-reload` and `sudo systemctl restart ownhost-agent`. If the firewall is active, it only allows 8765: allow the new port only for the home network and Tailscale.

### Tailscale isn't detected

The app considers Tailscale active when the computer has an IP in the `100.64.0.0/10` range on an interface that is up. To list your machines and recognize devices on your own account, it uses the `tailscale` command.

1. Check that Tailscale is connected: `tailscale status` and `tailscale ip -4` (on Windows, the Tailscale icon should say "Connected").
2. Check that the `tailscale` command works in a terminal. On Windows the app also looks for it in `C:\Program Files\Tailscale\tailscale.exe`.
3. Both computers must be on the same tailnet (or the computer must be shared with "Share"). Token-free access only works with devices on **your own account**, and only if `trust_tailscale` isn't set to `false` in `agent.json`.
4. Detection runs every 30 seconds. You can also add the computer by hand with **"Connect to a computer by IP..."** and its Tailscale IP.

### SmartScreen or antivirus warnings

The binaries aren't digitally signed, so Windows SmartScreen may say the app is from an unknown publisher. A warning shouldn't be assumed to be a false positive without checking:

1. Download only from this project's [Releases](https://github.com/jmgamer1199/ownhost/releases) page.
2. Check the file's SHA-256 with `Get-FileHash .\Ownhost.exe -Algorithm SHA256` (Windows) or `sha256sum Ownhost-x86_64.AppImage` (Linux), and compare it with the checksum shown next to the file on the Releases page, if there is one.
3. If your antivirus flags the file, don't run it. Report it in the project's issues with the antivirus name and the detection name. You can also get a second opinion from an online scanner.
4. If you'd rather not trust the binaries, you can run Ownhost from the source code (see [Development](#development)).

Don't turn off the antivirus or add exclusions as the default fix.

## Security

Ownhost is meant for your home network and Tailscale. It doesn't promise absolute security, and remote access is only as safe as the conditions below:

- **Unencrypted HTTP:** the app, the web panel and the agent talk over plain HTTP. On the local network, anyone who can watch the traffic could see the token. Through Tailscale the traffic is encrypted by Tailscale. **Never open port 8765 to the internet** or forward it on your router.
- **The token in `agent.json`:** each agent stores its token in `agent.json`, in its data folder (`%LOCALAPPDATA%\Ownhost\agent\` on Windows, `~/.local/share/ownhost/` on Linux, `/var/lib/ownhost/` with the `systemd` service). Whoever has it can do anything on that computer: don't share it, don't upload that file anywhere, and don't post screenshots of the token or of the **Open on phone...** QR code. If it leaks: stop the agent, rename `agent.json` (for example to `agent.json.old`) and start it again. A new `agent.json` with a new token is created; the computer's name, port and other options go back to their defaults, and the servers aren't touched. Then update the token in the app with **Edit computer** and delete the old file. Don't edit the token by hand. Ownhost has no button to change the token yet.
- **Friend codes:** they only grant the chosen permissions and servers. The agent doesn't store the code: it stores its SHA-256 fingerprint and, when someone connects, compares the fingerprint of the code they send. That's why a code can't be shown again after it's created: if a friend loses it, revoke it and create another. **Revoke access** stops it working immediately.
- **Tailscale:** devices on **your own Tailscale account** get in without a token. Anyone who can use one of those devices can manage your servers. It can be turned off with `"trust_tailscale": false` in `agent.json`.
- **The agent listens on every network of the computer** (`--bind 0.0.0.0` by default). On a laptop that connects to other networks, any device on that network could reach port 8765 (it would still need the token). On Windows, keep those networks as public; on Linux, the firewall rules only allow private ranges and Tailscale. You can also use `--bind` with a specific IP.
- **The Linux firewall rules** also allow `100.64.0.0/10`, which is Tailscale's range but is also used by some internet providers (CGNAT). Behind a home router that doesn't forward ports, those addresses can't reach your computer.

## Development

### Running from source

You need Python 3.11 or later.

```bash
python -m venv ~/.venvs/ownhost
~/.venvs/ownhost/bin/pip install -e ".[app]"   # on Windows: %USERPROFILE%\.venvs\ownhost\Scripts\pip
python -m ownhost.agent        # the agent (shows the token on startup)
python -m ownhost.app          # the app
```

To only host servers (no window), `pip install -e .` is enough: the interface (PySide6) is optional.

Agent options:
- `--data-dir`, or the `OWNHOST_DATA_DIR` variable: data folder. By default, `%LOCALAPPDATA%\Ownhost\agent` on Windows and `~/.local/share/ownhost` on Linux.
- `--port 8765`, `--bind 0.0.0.0`, `--name "Server"`, `--show-token`.

The agent's API documents itself at `http://<ip>:8765/docs`.

### Translations

UI texts are written in Spanish with `tr("Spanish text")`, and their English translation goes in `ownhost/locale/en_*.py`. `scripts/check_translations.py` checks that every `tr()` text has an English translation with the same `{placeholders}`, and lists catalog entries that are no longer used. Run it before publishing:

```bash
python scripts/check_translations.py
```

### Building

A single command, on Windows, generates everything in `dist/`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

| File | Purpose |
|---|---|
| `dist/Ownhost.exe` | Windows: app and agent in a single file, no Python needed |
| `dist/linux/Ownhost-x86_64.AppImage` | Linux with a desktop (double-click) |
| `dist/linux/Ownhost` | Linux without a desktop: the same program as a single binary; with `--agent` it's the agent |
| `dist/linux/install-*.sh` | Installers for the app and for the agent as a service on Linux |

What the script does:
1. Creates the Python environment if it doesn't exist, installs the dependencies and PyInstaller.
2. Picks the **build** number (UTC date and time, `YYYYMMDDhhmmss`). It's the same for Windows and Linux and is the release tag when publishing.
3. Builds the `.exe` with PyInstaller (intermediate files go to the system temp folder).
4. Builds Linux inside **Docker** with AlmaLinux 8 (`scripts/build-linux.sh`). Using an old glibc makes it work on almost any current distribution. Requires Docker Desktop; without it, only the `.exe` is generated.
5. Runs `scripts/check_privacy.py`, which opens the binaries and looks for your username, computer name, home folder and IPs. If it finds anything, it warns you: don't share those files.

If Ownhost is open, the `.exe` in use is moved aside as `.old` and deleted on the next build.

**CurseForge key (optional):** if you put your key in a `curseforge.key` file at the root (or in the `CURSEFORGE_API_KEY` variable), it's embedded, obfuscated, in the binaries so users don't need to get their own. It's obfuscation, not encryption: someone with time could extract it, so don't include it in binaries you're going to publish. That file is in `.gitignore`: never commit it.

Other scripts: `scripts\install-windows.ps1` sets up the environment to run from source on Windows, `scripts/install-agent-linux.sh` installs the agent as a service on Linux using Python, `scripts/generate_icon.py` redraws the icon and the theme graphics, `scripts/generate_ascii.py` redraws the ASCII landscape of the computer page, and `scripts/check_translations.py` checks the translations (see [Translations](#translations)).

### Publishing a release

1. Build with `scripts\build.ps1`. At the start it shows the tag, for example `v20261031143350`.
2. Push the code (`git push`).
3. Create the Release with that tag, the three binaries and the two Linux installers:

```bash
gh release create v20261031143350 dist/Ownhost.exe dist/linux/Ownhost-x86_64.AppImage dist/linux/Ownhost dist/linux/install-app-linux.sh dist/linux/install-agent-service.sh --title "Ownhost mm/dd/yyyy" --notes "What's new..."
```

Apps and agents compare their build with the latest Release's and offer to update (see [Updating Ownhost](#updating-ownhost)). To test updates without publishing anything, the `OWNHOST_RELEASES_API` variable points the check at another address with the same format as the GitHub API.

### How the code is organized

```
ownhost/
├── agent/                  the agent (FastAPI + uvicorn)
│   ├── api.py              HTTP routes and the console WebSocket; permissions for each route
│   ├── manager.py          servers: create, start, stop, backups, import, clone, mods...
│   ├── access.py           friend access (codes, permission levels)
│   ├── games/              one file per game: minecraft.py, bedrock.py, hytale.py (base.py: the interface)
│   ├── java.py             downloads the Java version each server needs
│   ├── mods.py, modpacks.py  Modrinth, CurseForge and modpacks
│   ├── crossplay.py        Geyser, Floodgate and their extras
│   ├── players.py          players (operators, whitelist, bans)
│   ├── stats.py            player statistics (time played, last seen)
│   ├── addons.py           web map (BlueMap) and pre-generation (Chunky)
│   ├── files.py            Files tab: what can be read and saved
│   ├── replicas.py         backups on another computer
│   ├── scheduler.py        backups, scheduled restarts and stopping when empty
│   ├── metrics.py          CPU, RAM and player samples for the graphs
│   └── web/panel.html      the web panel for phones
├── app/                    the app (PySide6)
│   ├── main_window.py      main window, computer list, agent polling
│   ├── server_panel.py     a server's card and its tabs
│   ├── *_tab.py            players, performance, mods and files tabs
│   ├── memory.py           recommended memory when creating a server
│   ├── replicas.py         backups on another computer (send and restore)
│   ├── dialogs.py          create server, connect computer, settings...
│   ├── guests.py           friend access
│   ├── firewall.py         Linux firewall rules (ufw / firewalld)
│   ├── phone.py            "Open on phone" QR code
│   ├── app_update.py       self-update
│   ├── client.py           HTTP client for the agent API
│   └── theme.py            the look (QSS and drawings)
├── locale/                 English translations (en_*.py)
├── updates.py              GitHub Releases: check, download and replace the executable
├── discovery.py            find agents on the local network (UDP)
└── net.py                  local and Tailscale IPs
```

The app never touches server files directly: everything goes through the agent's API, even when the agent is on the same PC. That's why any computer on the network can manage any other.

### Adding another game

Create a class in `ownhost/agent/games/` that inherits from `GameAdapter`, implementing `versions`, `java_major`, `install` and `command`, and register it in `games/__init__.py`. Optionally: `available_update` (automatic updates), `mod_target` (mods), `read_config`/`write_config` (Properties tab), `tracks_players` and `setting_keys` (Players tab and common settings). The app picks it up automatically.

## Ideas for later

- HTTPS between app and agent if it ever leaves the local network.

## License

Ownhost is free software under the [GPL-3.0](LICENSE): you can use, study, modify and share it. If you publish a modified version, it must remain free and under the same license.

The app includes the Cascadia Mono and Geist fonts, both under the SIL Open Font License (texts in `ownhost/app/assets/fonts`).
