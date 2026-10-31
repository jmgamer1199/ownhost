Español: [README.es.md](README.es.md)

# Ownhost

Run your own **Minecraft Java** (Vanilla, Paper, Fabric, Forge, NeoForge), **Minecraft Bedrock** and **Hytale** servers on your own computers: your PC, a laptop you no longer use, or a home server. With the app (Windows and Linux) you create, start, stop, update and back them up from any PC on your local network or your Tailscale network. No renting anything, no relying on third-party services.

## How it works

```
 ┌──────────────┐        HTTP + WebSocket (port 8765)         ┌─────────────────────┐
 │  App (GUI)   │ ──────────────────────────────────────────▶ │ Agent (computer A)  │──▶ servers
 │  PySide6     │ ──────────────────────────────────────────▶ │ Agent (computer B)  │──▶ servers
 └──────────────┘                                             └─────────────────────┘
```

- **Agent** (`ownhost/agent`): a small service that runs on every computer that hosts servers. It downloads the games and the Java version each one needs, starts and stops the processes, and stores the backups. If you close the app, the servers keep running.
- **App** (`ownhost/app`): the window you use to manage every agent on your network.

Each agent generates a **token** the first time it starts. The app needs it to connect.

## Installation

Download the latest version from [Releases](https://github.com/jmgamer1199/ownhost/releases). You don't need to install Python or anything else.

The app can be used in English or Spanish (**Settings → Language**), and the web panel has a language switch too.

### Windows

Download `Ownhost.exe`, save it wherever you like and open it:

- **To host servers on that PC**, click **"Use this PC as a server"**. The same program stays in the background as the agent.
- **To manage another computer**, click **"Connect to a computer by IP"** and enter its IP, port and token. On the other computer, the **"Copy token"** button on its card gives you the token.

If Windows asks about the firewall, allow access on private networks so other computers and players can connect.

### Linux with a desktop

Download `Ownhost-x86_64.AppImage`, make it executable (`chmod +x Ownhost-x86_64.AppImage`) and double-click it. `install-app-linux.sh` (on the same page) copies it to `~/Applications` and adds it to the menu with its icon.

It works on almost any current distribution: Debian 10+, Ubuntu 20.04+, Fedora, Arch, openSUSE, RHEL/Rocky/Alma 8+ and their derivatives (not on musl-based ones such as Alpine). If the window doesn't open, some graphics libraries are missing; on Debian/Ubuntu: `sudo apt install libgl1 libegl1 libxcb-cursor0`.

### Linux without a desktop (agent only)

For a computer that only hosts servers, download `Ownhost` and `install-agent-service.sh` into the same folder and run:

```bash
sudo bash install-agent-service.sh
```

The script installs the agent as a `systemd` service (it starts with the computer, even if nobody logs in), opens the ports in `ufw` if it is active, and finally shows the IP and token. In the app on another computer, click **"Connect to a computer"**, pick it under "Found on your network" and paste the token.

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

## Tailscale

If a computer has Tailscale running, the app detects it:

- **When connecting to a computer**, the dialog shows a list of the machines on your Tailscale network. Picking one fills in its name and IP.
- **On each server's card**, "Connect to" shows the local network IP and the Tailscale IP. Friends on your tailnet can join from outside your home without opening ports on the router.
- **On each computer's card** its Tailscale IP is shown too, so you can manage it from outside your home.

## Ports

| Purpose | Port |
|---|---|
| Agent (app ↔ agent) | 8765/TCP |
| Minecraft | 25565/TCP (the next free one if it's already taken) |
| Minecraft Bedrock | 19132/UDP and 19133/UDP (the next free ones if there are several) |
| Hytale | 5520/UDP |
| Bedrock via Geyser (crossplay) | 19132/UDP (19133, 19134... if there are several servers) |
| Web map (BlueMap) | 8100/TCP (8101, 8102... if there are several servers) |

## Crossplay (Bedrock)

**Paper, Fabric and NeoForge** servers can also accept **Minecraft Bedrock** players (mobile, consoles, Windows) thanks to [Geyser](https://geysermc.org/). You can turn it on when creating the server or later, under **Settings → Crossplay**.

- Geyser installs itself. On Paper, ViaVersion is also added if the server isn't on the latest Minecraft version, and on Fabric, Fabric API is added too.
- **Floodgate** (on by default) lets Bedrock players join without a Java account.
- Each server gets its own Bedrock port, shown under "Connect to", plus the next one for NetherNet. For example: 19132 on TCP and UDP, and 19133 on UDP.
- What Bedrock players see: the server **name** is the one in the app; Geyser receives it on every start, because otherwise it would show "Geyser". The **description** and **player limit** are the same as on Java. You edit them in **Settings** ("Description" and "Max players", which map to `motd` and `max-players` in `server.properties`), and Geyser copies them.
- Geyser is configured with `transport: both`, meaning NetherNet (Bedrock 26.60+) and RakNet at the same time. With NetherNet alone, consoles on the same network didn't see the server in the Friends tab as a LAN game.
- Vanilla and Forge aren't supported: Geyser has no version for them.
- **Extras** (under Settings → Crossplay, once enabled):
  - **Consoles in the Friends tab (MCXboxBroadcast):** Switch, Xbox and PlayStation can't add servers by IP. Geyser doesn't announce the server on the local network over NetherNet (port 7551) either, so it doesn't show up as a LAN game. With this extension, the server signs in with a **secondary** Microsoft account and appears as a friend's game. The app opens a sign-in window and then shows which account to add as a friend.
  - **ThirdPartyCosmetics:** Bedrock players see Java players' capes and ears.
  - **EmoteOffhand:** swap the item in the offhand with an emote.
  - The pack that makes Bedrock match Java (GeyserIntegratedPack, formerly GeyserOptionalPack) is already included in Geyser.
- On consoles (Switch, Xbox, PlayStation) you can't add a server by IP directly. You need a workaround such as [BedrockConnect](https://github.com/Pugmatt/BedrockConnect). On mobile and Windows you can add it by IP and port.

## Moving a server to another computer

On the server's card, click **"Move to another computer..."** and pick the destination. The app does the following:

1. Stops the server.
2. Creates a backup.
3. Sends it over the network to the other agent.
4. Installs the same game version there and restores the world, settings and mods.

The original is kept, stopped, unless you check "Delete the server from this computer".

## Worlds

On the server's card, the **World** button has three options:

- **Import a world...**: pick the world folder (in `.minecraft\saves`, or in the `saves` folder of your CurseForge, Prism or Modrinth instance) or a `.zip`.
  - A backup is made before the current world is replaced.
  - If the world comes from a modded instance, the app offers to copy its mods and `config` folder too. Fabric mods marked as "client only" (shaders, minimaps...) are skipped.
  - The server must be on the same Minecraft version and the same loader as the instance.
- **Open server folder**: only if the server is on the same PC as the app. Use it to edit files by hand.
- **Download a backup...**: takes you to the "Backups" tab, where "Download..." saves the backup to your PC. That way you can edit the world with tools such as [Amulet](https://www.amuletmc.com/) even if the server is on another computer, and upload it again with "Import a world".

## Mods and plugins

The **Plugins** tab (on Paper servers) or **Mods** tab (on Fabric, Forge and NeoForge servers) searches **Modrinth** and **CurseForge**. It only shows what's compatible with the server version and installs required dependencies automatically. From the same tab you can enable, disable or remove what's installed.

- Modrinth needs no setup.
- CurseForge needs a free API key: get one at [console.curseforge.com](https://console.curseforge.com/) and enter it in the app's **Settings**.
- Some CurseForge authors block downloads from external apps. In that case, the app gives you the link to download it from the website.
- Vanilla servers don't support mods.

## Players

In the **Players** tab (Minecraft Java and Bedrock) you see who's online and can op, kick or ban them without typing commands. You also manage operators, the whitelist (and whether it's on) and banned players.

- Bedrock players joining through Geyser have a "." in front of their name.
- If the server is stopped, changes are queued and applied as soon as it starts.
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
- **Stop if nobody plays for N minutes** (Minecraft; off by default): saves power and memory when the server is empty.

The agent runs these tasks, so they work even when the app is closed.

## Recommended memory

When you create a server (or import a modpack) you say how many people will play at once, and the app recommends the memory based on the server type, the modpack's mods and the computer's memory, and warns you if you ask for more than is free. Bedrock manages its own memory, so it doesn't ask.

## Map & world

Under **Settings → Map & world** (Paper, Fabric, Forge and NeoForge servers):

- **World map in the browser (BlueMap):** installs with one click and the app shows the link (`http://IP:8100/`). It's a 3D map you can also view on your phone, and it renders bit by bit while the server is running.
- **Pre-generate the world (Chunky):** choose a radius in blocks and click **Generate**. It creates the terrain ahead of time so there's no lag when players explore; the app shows the progress. You can keep playing in the meantime.

## Files

The **Files** tab opens and edits mod and plugin configuration (`.yml`, `.json`, `.toml`, `.properties`...) without hunting for the server folder, even if it's on another computer. Only configuration files are shown: never the world, the programs or the login files. `.json` files are validated before saving.

## Backups on another computer

In case a disk fails: under **Settings → Backup on another computer** you choose another computer of yours and every backup is also sent there (it keeps the last 3). The other computer provides a code that can only be used to receive backups. If the first one fails, on the other computer's card, **Backups from other computers...** → **Restore here** creates the server with its world, mods and configuration.

## Modpacks

Under **New server → From a modpack...** you pick a downloaded modpack and Ownhost sets up the server:

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

Nobody with a code can create or delete servers, clone or move them, download backups or see the computer's folder. Your friend connects with "Connect to a computer" by entering the code in "Token or code", or from the browser (below). The code is only shown when it's created: the agent stores its fingerprint, not the code. To revoke access, click **Remove access**; it stops working immediately.

Your friend has to be on your local network or your Tailscale network (in Tailscale you can share just that computer with "Share"). Nothing is opened to the internet.

## Web panel

Each agent serves a panel at `http://computer-IP:8765/` (each computer's card in the app shows the link). From the browser on your phone or any PC, with the token or a friend code, you manage each server: start and stop, who's playing, players and statistics, console, backups and settings, depending on each person's permission. If you connect from a device on your own Tailscale account, no code is needed. Mods, files, crossplay and the map are managed from the app. The panel has its own language switch (English/Spanish).

## Updates

Each server has the **"Update automatically on start"** option in Settings, on by default. Before starting, the app checks whether there's a new compatible version. If there is, it makes a backup and installs it.

- **Minecraft Java:** Paper builds and the Fabric, Forge and NeoForge loaders are updated, but **the Minecraft version is not changed**, so worlds and mods don't break. To move to another version (for example, from 1.21.1 to 26.3) use "Update...".
- **Minecraft Bedrock:** the latest version is always installed, because Bedrock clients update themselves and can't join older servers.
- **Hytale:** before starting, the *Hytale Downloader* checks whether there's a new version on your channel (Release or Pre-release) and, if so, installs it after making a backup.

## Updating Ownhost

When it opens, the app checks whether there's a new version in the project's [Releases](https://github.com/jmgamer1199/ownhost/releases) (this can be turned off in **Settings**, which also has **Check now**). If there is, it downloads it, closes and reopens already updated; the servers keep running and the agent on the same PC updates itself. Agents on other computers are updated from their card with **Update agent**: they stop the servers saving the world, restart with the new version and start them again. Only the `.exe` and the Linux AppImage or binary update themselves; if you installed the agent with pip, update it with pip.

To publish releases, see [Publishing a release](#publishing-a-release).

## Notes per game

**Minecraft**: when creating the server you have to accept the [EULA](https://aka.ms/MinecraftEULA). The right Java version (Temurin) is downloaded automatically. Hot backups use `save-off` / `save-all` so the world doesn't get corrupted.

**Minecraft Bedrock**: uses Mojang's official server (Bedrock Dedicated Server), which doesn't need Java. It listens over UDP on port 19132 (IPv4) and 19133 (IPv6). If you create several servers, the app assigns ports so they don't clash with each other or with Geyser.

**Forge / NeoForge**: the app downloads and runs the official installer in server mode, and picks the recommended loader version for the Minecraft version you choose.

**Hytale**: you need a Hytale account. The app opens a **sign-in** window with a code at two points:
1. When creating the server, so the official *Hytale Downloader* can download the files. Only the first time on each computer, because the credentials are saved.
2. When starting it for the first time, to authenticate the server. The agent runs `/auth login device` by itself and, once you sign in, saves the credentials with `/auth persistence Encrypted`.

If something goes wrong, the "Sign in..." button on the server's card asks again.

The **Properties** tab edits Hytale's `config.json` (name, password, max players, game mode...) without touching the file; each value keeps its type (number, true/false or text). The server name in the app is passed to `ServerName`. The **Mods** tab searches for and installs Hytale mods from CurseForge (requires your API key) into the server's `mods` folder, and also checks for their updates.

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

UI texts are written in Spanish with `tr("Spanish text")`, and their English translation goes in `ownhost/locale/en_*.py`. `scripts/check_translations.py` checks that every `tr()` text has an English translation with the same `{placeholders}`, and lists catalog entries that are no longer used:

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

Other scripts: `scripts\install-windows.ps1` sets up the environment to run from source on Windows, `scripts/install-agent-linux.sh` installs the agent as a service on Linux using Python, `scripts/generate_icon.py` redraws the icon and the theme graphics, and `scripts/check_translations.py` checks the translations (see [Translations](#translations)).

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
│   ├── app_update.py       self-update
│   ├── client.py           HTTP client for the agent API
│   └── theme.py            the look (QSS and drawings)
├── locale/                 English translations (en_*.py)
├── updates.py              GitHub Releases: check, download and replace the executable
├── discovery.py            find agents on the local network (UDP)
└── net.py                  local and Tailscale IPs
```

The app never touches server files directly: everything goes through the agent's API, even when the agent is on the same PC. That's why any computer on the network can manage any other.

### Security

- Each agent has a **token** (in `agent.json`, in its data folder). Whoever has it can do anything on that computer.
- Devices on **your own Tailscale account** get in without a token (can be turned off with `trust_tailscale: false` in `agent.json`).
- **Friend codes** only grant the chosen permissions. The agent stores their fingerprint (SHA-256), not the code.
- Communication is unencrypted HTTP: it's meant for the local network and Tailscale (which already encrypts). Don't open port 8765 to the internet.

### Adding another game

Create a class in `ownhost/agent/games/` that inherits from `GameAdapter`, implementing `versions`, `java_major`, `install` and `command`, and register it in `games/__init__.py`. Optionally: `available_update` (automatic updates), `mod_target` (mods), `read_config`/`write_config` (Properties tab). The app picks it up automatically.

## Ideas for later

- HTTPS between app and agent if it ever leaves the local network.

## License

Ownhost is free software under the [GPL-3.0](LICENSE): you can use, study, modify and share it. If you publish a modified version, it must remain free and under the same license.
