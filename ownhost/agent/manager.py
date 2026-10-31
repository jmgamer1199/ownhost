import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import zipfile
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Callable

import psutil

from ownhost.agent import addons, crossplay, modpacks, mods, players, replicas
from ownhost.agent.metrics import Metrics
from ownhost.agent.scheduler import Scheduler, schedule_of
from ownhost.agent.stats import PlayerStats
from ownhost.agent.device_auth import DeviceAuthWatcher
from ownhost.sysenv import clean_env
from ownhost.agent.errors import UserError
from ownhost.agent.games import GAMES
from ownhost.agent.games.base import NO_WINDOW, GameAdapter, InstallContext, read_properties, write_properties
from ownhost.agent.java import JavaManager
from ownhost.agent.models import ServerMeta

log = logging.getLogger("ownhost.agent")

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
STOP_TIMEOUT = 60
CONSOLE_LINES = 2000

# Archivos que no merece la pena copiar: se vuelven a descargar al actualizar,
# o están bloqueados por el juego mientras se ejecuta.
BACKUP_EXCLUDE = {"Assets.zip", "Server", "libraries", "versions", "cache", "session.lock",
                  "bedrock_server", "bedrock_server.exe", "bedrock_server.pdb"}
BACKUP_META = "_ownhost_server.json"
# Señales de que el servidor ya acepta comandos (para lanzar el inicio de sesión de Hytale).
BOOT_RE = re.compile(r"\b(booted|server started|started server|ready|listening on|done \()", re.IGNORECASE)
BOOT_WAIT = 60
XBOX_LOGIN_RE = re.compile(r"Successfully authenticated as (.+?) \(\d+\)")
# Icono de la lista de servidores de Minecraft Java: PNG de 64x64 junto a server.properties.
ICON_FILE = "server-icon.png"
RESUME_FILE = "resume-after-update.json"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class Server:
    _event_seq = 0  # numeración de avisos compartida por todos los servidores
    def __init__(self, meta: ServerMeta, root: Path, loop: asyncio.AbstractEventLoop):
        self.meta = meta
        self.root = root
        self.server_dir = root / "server"
        self.loop = loop
        self.state = "stopped"  # stopped | starting | running | stopping | crashed
        self.task: str | None = None  # tarea en segundo plano: installing, updating...
        self.error: str | None = None
        self.proc: subprocess.Popen | None = None
        self.ps: psutil.Process | None = None
        self.started_at: float | None = None
        self.stopping = False
        self.console: deque[str] = deque(maxlen=CONSOLE_LINES)
        self.subscribers: set[asyncio.Queue] = set()
        self.lock = threading.RLock()
        # Inicio de sesión pendiente (Hytale): {"url", "code", "source": "downloader" | "server"}
        self.auth: dict | None = None
        self.auth_watcher = DeviceAuthWatcher()
        self.booted = threading.Event()
        self.online: set[str] = set()  # jugadores conectados ahora mismo
        self.player_stats = PlayerStats(root / "player-stats.json")
        self.empty_since: float | None = None  # para apagarlo si se queda vacío (ver scheduler)
        self.pregen: dict | None = None  # progreso de Chunky (último mensaje)
        self.events: deque[dict] = deque(maxlen=30)  # avisos para la app (caídas, copias...)
        self.crash_times: deque[float] = deque(maxlen=5)

    @property
    def game(self) -> GameAdapter:
        return GAMES[self.meta.game]

    @property
    def running(self) -> bool:
        return self.proc is not None

    def save(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "instance.json").write_text(json.dumps(self.meta.to_dict(), indent=2), encoding="utf-8")

    def event(self, kind: str, text: str) -> None:
        """Aviso que la app enseña al usuario (se numeran para no repetirlos)."""
        Server._event_seq += 1
        self.events.append({"id": Server._event_seq, "time": datetime.now().isoformat(timespec="seconds"),
                            "kind": kind, "text": text})

    def emit(self, line: str) -> None:
        self.console.append(line)
        before = set(self.online)
        if players.track(self.online, line):
            for name in self.online - before:
                self.player_stats.joined(name)
            for name in before - self.online:
                self.player_stats.left(name)
        if "Processed:" in line and (progress := addons.parse_chunky(line)):
            self.pregen = progress
        for q in list(self.subscribers):
            self.loop.call_soon_threadsafe(q.put_nowait, line)
        if self.auth_watcher:
            self._watch_auth(line)

    def _watch_auth(self, line: str) -> None:
        event = self.auth_watcher.feed(line)
        if gamertag := XBOX_LOGIN_RE.search(line):
            # MCXboxBroadcast: la cuenta que los jugadores de consola deben añadir como amigo
            self.meta.extra["xbox_gamertag"] = gamertag.group(1)
            self.meta.extra.pop("xbox_problem", None)
            self.save()
        elif "XO_E_ACCOUNT_CREATION_REQUIRED" in line and "xbox_problem" not in self.meta.extra:
            # Cuenta de Microsoft recién creada: aún no tiene perfil de Xbox (gamertag).
            self.meta.extra["xbox_problem"] = "no_profile"
            self.save()
            self.log("La cuenta de Microsoft aún no tiene perfil de Xbox. Entra en https://www.xbox.com/ "
                     "con ella, crea el perfil (elige un gamertag) y reinicia el servidor.")
        if event == "pending":
            source = "server" if self.running else "downloader"
            kind = "xbox" if "microsoft.com" in self.auth_watcher.pending["url"] else "game"
            self.auth = {**self.auth_watcher.pending, "source": source, "kind": kind}
        elif event in ("success", "failed"):
            was = self.auth
            self.auth = None
            if (event == "success" and self.game.device_auth and self.running
                    and (was or not self.meta.extra.get("auth_done"))):
                # Guardamos las credenciales para no tener que iniciar sesión en cada arranque.
                self.meta.extra["auth_done"] = True
                self.save()
                if self.game.auth_persist_command:
                    threading.Timer(1, self._persist_auth).start()

    def _persist_auth(self) -> None:
        try:
            self.send(self.game.auth_persist_command)
            self.log("Sesión iniciada; credenciales guardadas para próximos arranques.")
        except UserError:
            pass

    def clear_auth(self) -> None:
        self.auth = None
        if self.auth_watcher:
            self.auth_watcher.reset()

    def log(self, msg: str) -> None:
        self.emit(f"[Ownhost {datetime.now():%H:%M:%S}] {msg}")

    def send(self, command: str) -> None:
        proc = self.proc
        if not proc or not proc.stdin:
            raise UserError("El servidor no está encendido")
        try:
            proc.stdin.write(command + "\n")
            proc.stdin.flush()
        except OSError as e:
            raise UserError(f"No se pudo enviar el comando: {e}") from e

    def stats(self) -> dict:
        ps = self.ps
        if not ps:
            return {}
        try:
            with ps.oneshot():
                mem = ps.memory_info().rss
                cpu = ps.cpu_percent(None) / psutil.cpu_count()
            return {"cpu_percent": round(cpu, 1), "memory_mb": mem // (1 << 20),
                    "uptime_s": int(time.time() - (self.started_at or time.time()))}
        except psutil.Error:
            return {}

    def to_dict(self) -> dict:
        return {
            **self.meta.to_dict(),
            "status": self.task or self.state,
            "task": self.task,
            "state": self.state,
            "error": self.error,
            "game_name": self.game.name,
            "flavor_name": next((f.name for f in self.game.flavors if f.id == self.meta.flavor), self.meta.flavor),
            "has_properties": bool(self.game.properties_file),
            "mods_label": (target.label if (target := self.game.mod_target(self.meta)) else None),
            "mod_sources": list(target.sources) if target else [],
            "device_auth": self.game.device_auth,
            "world_import": self.game.supports_world_import,
            "crossplay": self.meta.extra.get("crossplay"),
            "xbox_gamertag": self.meta.extra.get("xbox_gamertag"),
            "xbox_problem": self.meta.extra.get("xbox_problem"),
            "crossplay_supported": self.meta.flavor in crossplay.SUPPORTED,
            "auth": self.auth,
            "stats": self.stats(),
            "players_online": sorted(self.online, key=str.lower),
            "schedule": schedule_of(self.meta),
            "events": list(self.events)[-10:],
            "map": self.meta.extra.get("map"),
            "replica": ({k: v for k, v in rep.items() if k != "token"}
                        if (rep := self.meta.extra.get("replica")) else None),
            "pregen_installed": bool(self.meta.extra.get("pregen")),
            "pregen": self.pregen,
            "addons_supported": self.meta.flavor in addons.SUPPORTED,
            "icon_supported": self.meta.game == "minecraft",
            "icon_version": self.icon_version(),
        }

    def icon_version(self) -> int | None:
        """Fecha del icono (la app lo vuelve a descargar solo si cambia), o None si no hay."""
        try:
            return int((self.server_dir / ICON_FILE).stat().st_mtime)
        except OSError:
            return None


class ServerManager:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.servers_dir = data_dir / "servers"
        self.backups_dir = data_dir / "backups"
        self.tools_dir = data_dir / "tools"
        self.java = JavaManager(data_dir / "java")
        self.servers: dict[str, Server] = {}
        self.loop: asyncio.AbstractEventLoop | None = None
        self.metrics = Metrics(self)
        self.replicas = replicas.ReplicaStore(data_dir)
        self.agent_name = "equipo"  # lo pone la API con el nombre del agente

    # ---------- ciclo de vida del agente ----------

    def load(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.servers_dir.mkdir(parents=True, exist_ok=True)
        for meta_file in self.servers_dir.glob("*/instance.json"):
            try:
                meta = ServerMeta(**json.loads(meta_file.read_text(encoding="utf-8")))
            except (ValueError, TypeError) as e:
                log.error("No se pudo cargar %s: %s", meta_file, e)
                continue
            if meta.game not in GAMES:
                log.warning("Juego desconocido en %s", meta_file)
                continue
            self.servers[meta.id] = Server(meta, meta_file.parent, loop)
        # Tras actualizar el agente se vuelven a encender los que estaban encendidos.
        resume = self.data_dir / RESUME_FILE
        to_resume = set(json.loads(resume.read_text(encoding="utf-8"))) if resume.exists() else set()
        resume.unlink(missing_ok=True)
        for s in self.servers.values():
            if s.meta.auto_start or s.meta.id in to_resume:
                self.start(s.meta.id)
        Scheduler(self).start()
        self.metrics.start()

    def shutdown(self, resume: bool = False) -> None:
        """Apaga todos los servidores de forma ordenada (al cerrar el agente).

        Con resume, apunta los que estaban encendidos para encenderlos al volver (actualización).
        """
        if resume:
            running = [s.meta.id for s in self.servers.values() if s.running]
            (self.data_dir / RESUME_FILE).write_text(json.dumps(running), encoding="utf-8")
        threads = []
        for s in self.servers.values():
            if s.running:
                t = threading.Thread(target=self._stop_blocking, args=(s,))
                t.start()
                threads.append(t)
        for t in threads:
            t.join(STOP_TIMEOUT + 5)
        self.metrics.save()

    # ---------- utilidades ----------

    def get(self, server_id: str) -> Server:
        s = self.servers.get(server_id)
        if not s:
            raise KeyError(server_id)
        return s

    def _require_idle(self, s: Server, need_stopped: bool = True) -> None:
        if s.task:
            raise UserError(f"El servidor está ocupado ({s.task})")
        if need_stopped and s.running:
            raise UserError("Apaga el servidor primero")

    def _background(self, s: Server, task: str, fn: Callable[[], None]) -> None:
        s.task = task
        s.error = None

        def run():
            try:
                fn()
            except Exception as e:  # noqa: BLE001 - cualquier fallo se muestra en la consola
                log.exception("Error en %s de %s", task, s.meta.name)
                s.error = str(e)
                s.log(f"ERROR: {e}")
            finally:
                s.task = None
                if not s.running:
                    s.clear_auth()  # el downloader ya terminó: no queda nada que autorizar

        threading.Thread(target=run, daemon=True, name=f"{task}-{s.meta.id}").start()

    # ---------- crear / borrar ----------

    def create(self, name: str, game: str, flavor: str, version: str, memory_mb: int,
               port: int | None, accept_eula: bool, crossplay_enabled: bool = False,
               floodgate: bool = True, whitelist: bool = False) -> Server:
        adapter = GAMES.get(game)
        if not adapter:
            raise UserError(f"Juego desconocido: {game}")
        if flavor not in {f.id for f in adapter.flavors}:
            raise UserError(f"Tipo desconocido: {flavor}")
        if adapter.needs_eula and not accept_eula:
            raise UserError("Debes aceptar el EULA de Minecraft para crear el servidor")
        if version == "latest" or not version:
            version = adapter.versions(flavor)[0]
        port = port or self._free_port(adapter.default_port, span=2 if adapter.id == "bedrock" else 1)
        meta = ServerMeta(id=uuid.uuid4().hex[:12], name=name.strip() or "Servidor", game=game,
                          flavor=flavor, version=version, memory_mb=memory_mb, port=port)
        s = Server(meta, self.servers_dir / meta.id, self.loop)
        s.server_dir.mkdir(parents=True, exist_ok=True)
        s.save()
        self.servers[meta.id] = s
        s.state = "stopped"
        if crossplay_enabled:
            crossplay.check_supported(flavor)

        def run():
            self._install(s, first_install=True)
            # Minecraft 26 crea los servidores con la lista blanca activada: aquí se deja como se eligió
            # (si no, los amigos no podrían entrar en un servidor recién creado sin saber por qué).
            key = {"minecraft": "white-list", "bedrock": "allow-list"}.get(game)
            if key:
                write_properties(s.server_dir / adapter.properties_file, {key: str(whitelist).lower()})
            if crossplay_enabled:
                self._enable_crossplay(s, floodgate)

        self._background(s, "installing", run)
        return s

    def _used_ports(self, exclude: str | None = None) -> set[int]:
        """Todos los puertos ocupados: juego, extras (IPv6 de Bedrock) y Bedrock de Geyser."""
        used = set()
        for s in self.servers.values():
            if s.meta.id == exclude:
                continue
            used |= {s.meta.port, *s.game.extra_ports(s.meta)}
            if cp := s.meta.extra.get("crossplay"):
                used |= {cp["bedrock_port"], cp["bedrock_port"] + 1}  # RakNet/señalización + NetherNet
            if web_map := s.meta.extra.get("map"):
                used.add(web_map["port"])
        return used

    def _free_bedrock_port(self, exclude: str | None = None) -> int:
        return self._free_port(crossplay.DEFAULT_BEDROCK_PORT, span=2, exclude=exclude)

    # ---------- multiplataforma (Geyser) ----------

    def enable_crossplay(self, server_id: str, floodgate: bool) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        crossplay.check_supported(s.meta.flavor)
        self._background(s, "installing-mod", lambda: self._enable_crossplay(s, floodgate))

    def _enable_crossplay(self, s: Server, floodgate: bool) -> None:
        target = s.game.mod_target(s.meta)
        latest = s.game.versions("vanilla")[0]
        files = crossplay.install(s.meta.flavor, target, s.meta.version, latest,
                                  s.server_dir / target.folder, floodgate, s.log)
        port = self._free_bedrock_port(exclude=s.meta.id)
        # Al desactivar solo se quitan Geyser y compañía; dependencias como Fabric API se quedan
        # porque otros mods del servidor también suelen necesitarlas.
        own = [f for f in files if re.match(r"(geyser|floodgate|viaversion)", f, re.IGNORECASE)]
        s.meta.extra["crossplay"] = {"bedrock_port": port, "floodgate": floodgate, "files": own}
        s.save()
        crossplay.set_bedrock_port(s.server_dir, s.meta.flavor, port)
        self._sync_geyser(s)
        s.log(f"Multiplataforma activada: los jugadores de Bedrock entran por el puerto {port} (UDP).")

    def disable_crossplay(self, server_id: str) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        cp = s.meta.extra.pop("crossplay", None)
        if cp:
            target = s.game.mod_target(s.meta)
            crossplay.remove(s.server_dir / target.folder, cp.get("files", []))
            for filename in cp.get("extras", {}).values():
                crossplay.remove_extra(s.server_dir, s.meta.flavor, filename)
            s.meta.extra.pop("xbox_gamertag", None)
            s.save()
            s.log("Multiplataforma desactivada (Geyser eliminado).")

    def set_crossplay_extra(self, server_id: str, key: str, enabled: bool) -> None:
        """Instala o quita un extra de Geyser (amigos de Xbox, capas de Java...)."""
        s = self.get(server_id)
        self._require_idle(s)
        cp = s.meta.extra.get("crossplay")
        if not cp:
            raise UserError("Activa primero la multiplataforma")
        extras = cp.setdefault("extras", {})
        if enabled:
            def run():
                extras[key] = crossplay.install_extra(key, s.server_dir, s.meta.flavor, s.log)
                s.save()
                s.log(f"Extra «{key}» instalado. Se activará al encender el servidor.")
            self._background(s, "installing-mod", run)
        elif filename := extras.pop(key, None):
            crossplay.remove_extra(s.server_dir, s.meta.flavor, filename)
            if key == "xbox":
                s.meta.extra.pop("xbox_gamertag", None)
            s.save()
            s.log(f"Extra «{key}» quitado.")

    def _free_port(self, default: int, span: int = 1, exclude: str | None = None) -> int:
        """Primer puerto libre desde `default` con `span` puertos seguidos libres."""
        used = self._used_ports(exclude)
        port = default
        while any(port + i in used for i in range(span)):
            port += 1
        return port

    def _install(self, s: Server, first_install: bool) -> None:
        s.log(f"Instalando {s.game.name} {s.meta.flavor} {s.meta.version}...")
        java = None
        if s.game.uses_java:
            s.meta.java_major = s.game.java_major(s.meta.flavor, s.meta.version)
            java = self.java.ensure(s.meta.java_major, s.log)
        s.game.install(InstallContext(meta=s.meta, server_dir=s.server_dir, tools_dir=self.tools_dir,
                                      log=s.log, first_install=first_install, java=java))
        s.save()
        s.log("Instalación completada.")

    def delete(self, server_id: str) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        del self.servers[server_id]
        shutil.rmtree(s.root, ignore_errors=True)
        shutil.rmtree(self.backups_dir / server_id, ignore_errors=True)
        self.metrics.forget(server_id)

    # ---------- clonar ----------

    def clone(self, server_id: str, name: str) -> None:
        """Copia un servidor (mundo, mods y ajustes) en uno nuevo con otro puerto. Puede estar encendido:
        se usa una copia de seguridad en caliente."""
        s = self.get(server_id)
        self._require_idle(s, need_stopped=False)

        def run():
            tmp = self.data_dir / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            archive = self._backup(s, target=tmp / f"clon-{uuid.uuid4().hex[:8]}.zip")
            new = self.import_server(archive, name.strip() or f"{s.meta.name} (copia)")
            for key in ("auto_update", "auto_restart"):
                setattr(new.meta, key, getattr(s.meta, key))
            if "schedule" in s.meta.extra:
                new.meta.extra["schedule"] = dict(s.meta.extra["schedule"])
            new.save()
            s.log(f"Clonado como «{new.meta.name}» (puerto {new.meta.port}).")

        self._background(s, "cloning", run)

    # ---------- icono ----------

    def icon_path(self, server_id: str) -> Path:
        s = self.get(server_id)
        path = s.server_dir / ICON_FILE
        if not path.exists():
            raise KeyError(server_id)
        return path

    def set_icon(self, server_id: str, data: bytes | None) -> None:
        s = self.get(server_id)
        if s.meta.game != "minecraft":
            raise UserError("Solo los servidores de Minecraft Java tienen icono")
        path = s.server_dir / ICON_FILE
        if data is None:
            path.unlink(missing_ok=True)
            return
        # Minecraft solo acepta PNG de 64x64: la app ya la convierte, aquí solo se comprueba.
        if len(data) > 512 * 1024 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR" \
                or int.from_bytes(data[16:20], "big") != 64 or int.from_bytes(data[20:24], "big") != 64:
            raise UserError("El icono tiene que ser un PNG de 64x64 píxeles")
        path.write_bytes(data)
        s.log("Icono cambiado. Se verá en la lista de servidores tras reiniciar.")

    # ---------- rendimiento ----------

    def get_metrics(self, server_id: str, hours: float) -> dict:
        s = self.get(server_id)
        props = s.server_dir / "server.properties"
        max_players = None
        if props.exists():
            value = read_properties(props).get("max-players", "")
            max_players = int(value) if value.isdigit() else None
        return {"interval": 60, "points": self.metrics.points(server_id, hours),
                "memory_limit_mb": s.meta.memory_mb, "max_players": max_players,
                "disk": self.metrics.disk(s)}

    # ---------- encender / apagar ----------

    def start(self, server_id: str) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        if s.running:
            raise UserError("El servidor ya está encendido")
        s.state = "starting"
        threading.Thread(target=self._launch_safe, args=(s,), daemon=True).start()

    def _launch_safe(self, s: Server) -> None:
        try:
            if s.meta.auto_update:
                self._auto_update(s)
            self._launch(s)
        except Exception as e:  # noqa: BLE001
            s.state = "crashed"
            s.error = str(e)
            s.log(f"ERROR al arrancar: {e}")

    def _auto_update(self, s: Server) -> None:
        """Antes de encender: si hay una versión compatible más nueva, copia de seguridad e instalación."""
        try:
            new = s.game.available_update(s.meta, self.tools_dir)
        except Exception as e:  # noqa: BLE001 - sin internet, API caída...: se arranca igual
            s.log(f"No se pudo comprobar si hay actualizaciones ({e}); se arranca la versión actual.")
            return
        if not new:
            return
        s.task = "updating"
        try:
            s.log(f"Hay una versión nueva ({new}). Actualizando antes de encender...")
            self._backup(s)
            self._install(s, first_install=False)
        finally:
            s.task = None

    def _launch(self, s: Server) -> None:
        s.state = "starting"
        s.error = None
        java = None
        if s.game.uses_java:
            java = self.java.ensure(s.meta.java_major or s.game.java_major(s.meta.flavor, s.meta.version), s.log)
        if cp := s.meta.extra.get("crossplay"):
            crossplay.set_bedrock_port(s.server_dir, s.meta.flavor, cp["bedrock_port"])
            # Nombre del servidor para Bedrock = el de la app (si no, Geyser enseña «Geyser»).
            self._sync_geyser(s)
        if web_map := s.meta.extra.get("map"):
            addons.configure_map(s.server_dir, s.meta.flavor, web_map["port"])
        cmd = s.game.command(s.meta, s.server_dir, java)
        if s.game.uses_java:
            # Fuerza UTF-8 en la salida de Java para que los acentos se vean bien.
            cmd[1:1] = ["-Dstdout.encoding=UTF-8", "-Dstderr.encoding=UTF-8"]
        s.log("Arrancando: " + " ".join(cmd[1:] if s.game.uses_java else cmd))
        # Entorno del sistema (sin las bibliotecas de la app empaquetada) + lo que necesite el juego.
        kwargs = {"env": clean_env(s.game.env(s.meta, s.server_dir))}
        if sys.platform == "win32":
            kwargs["creationflags"] = NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # Así un Ctrl+C en el agente no mata el juego sin guardar.
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(
            cmd, cwd=s.server_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1, **kwargs,
        )
        with s.lock:
            s.proc = proc
            s.stopping = False
            s.started_at = time.time()
            s.ps = psutil.Process(proc.pid)
            s.ps.cpu_percent(None)
            if s.game.ready_pattern is None:
                s.state = "running"
        s.booted.clear()
        threading.Thread(target=self._read_output, args=(s, proc), daemon=True).start()
        if s.game.device_auth and not s.meta.extra.get("auth_done"):
            threading.Thread(target=self._auto_login, args=(s, proc), daemon=True).start()

    def _auto_login(self, s: Server, proc: subprocess.Popen) -> None:
        """Primer arranque de un servidor que necesita cuenta: lanza el inicio de sesión solo."""
        s.booted.wait(BOOT_WAIT)
        if s.proc is proc and not s.auth and not s.meta.extra.get("auth_done"):
            s.log("Iniciando sesión del servidor con tu cuenta...")
            try:
                s.send(s.game.auth_login_command)
            except UserError:
                pass

    def login(self, server_id: str) -> None:
        s = self.get(server_id)
        if not s.game.device_auth:
            raise UserError("Este juego no necesita iniciar sesión")
        if not s.running:
            raise UserError("Enciende el servidor primero")
        s.send(s.game.auth_login_command)

    def _read_output(self, s: Server, proc: subprocess.Popen) -> None:
        assert proc.stdout
        pattern = s.game.ready_pattern
        for raw in proc.stdout:
            line = ANSI.sub("", raw.rstrip("\r\n"))
            s.emit(line)
            if not s.booted.is_set() and BOOT_RE.search(line):
                s.booted.set()
            if s.state == "starting" and pattern and pattern.search(line):
                s.state = "running"
                s.log("Servidor listo.")
                self._apply_pending_players(s)
        code = proc.wait()
        if code > 2**31:  # Windows da los códigos negativos como enteros sin signo (matado = 4294967295)
            code -= 2**32
        s.booted.set()
        with s.lock:
            s.clear_auth()
            s.proc = None
            s.ps = None
            s.started_at = None
            s.player_stats.all_left()
            s.online.clear()
            s.empty_since = None
            s.meta.extra["last_stopped"] = time.time()
            s.save()
            if not s.stopping and s.state == "starting":
                # Se cerró solo antes de estar listo (mundo incompatible, mod roto...): aunque
                # Minecraft salga con código 0, es un fallo.
                s.state = "crashed"
                s.error = "El servidor se cerró al arrancar. Mira la consola para ver el motivo."
                s.log(s.error)
                s.event("crash", f"«{s.meta.name}» no ha podido arrancar.")
            elif s.stopping or code == 0:
                s.state = "stopped"
                s.log(f"Servidor apagado (código {code}).")
            else:
                s.state = "crashed"
                s.error = "El proceso terminó inesperadamente" + (f" (código {code})" if code > 0 else " (lo cerró el sistema)")
                s.log(s.error)
                self._maybe_restart_after_crash(s)

    # ---------- caídas ----------

    def _maybe_restart_after_crash(self, s: Server) -> None:
        if not s.meta.auto_restart:
            s.event("crash", f"«{s.meta.name}» se ha caído.")
            return
        now = time.time()
        s.crash_times.append(now)
        recent = [t for t in s.crash_times if now - t < 600]
        if len(recent) > 3:
            s.log("Se ha caído demasiadas veces seguidas: no se vuelve a encender solo. Mira la consola.")
            s.event("crash", f"«{s.meta.name}» se ha caído varias veces seguidas y se ha quedado apagado.")
            return
        s.log(f"Se ha caído: se vuelve a encender en 10 segundos (intento {len(recent)} de 3).")
        s.event("restart", f"«{s.meta.name}» se ha caído y se está volviendo a encender.")
        threading.Timer(10, lambda: (not s.running and not s.task) and self._launch_safe(s)).start()

    # ---------- tareas programadas ----------

    def last_backup_time(self, server_id: str) -> float | None:
        folder = self.backups_dir / server_id
        times = [f.stat().st_mtime for f in folder.glob("*.zip")] if folder.exists() else []
        return max(times) if times else None

    def auto_backup(self, s: Server, keep: int) -> None:
        def run():
            self._backup(s, auto=True)
            autos = sorted((self.backups_dir / s.meta.id).glob("*-auto.zip"), reverse=True)
            for old in autos[max(1, keep):]:
                old.unlink(missing_ok=True)
        self._background(s, "backing-up", run)

    def scheduled_restart(self, s: Server) -> None:
        def run():
            if s.game.id in ("minecraft", "bedrock"):
                for msg, wait in (("El servidor se reiniciará en 1 minuto.", 50),
                                  ("El servidor se reinicia en 10 segundos.", 10)):
                    try:
                        s.send(f"say {msg}")
                    except UserError:
                        return
                    time.sleep(wait)
            s.log("Reinicio programado.")
            self._stop_blocking(s)
            while s.running:
                time.sleep(0.5)
            self._launch_safe(s)
        threading.Thread(target=run, daemon=True).start()

    # ---------- complementos: mapa web (BlueMap) y pregeneración (Chunky) ----------

    def set_addon(self, server_id: str, key: str, enabled: bool) -> None:
        s = self.get(server_id)
        if key not in ("map", "pregen"):
            raise UserError(f"Complemento desconocido: {key}")
        addons.check_supported(s.meta.flavor)
        self._require_idle(s, need_stopped=False)
        target = s.game.mod_target(s.meta)
        folder = s.server_dir / target.folder
        current = s.meta.extra.get(key)
        if enabled and not current:
            project = addons.MAP_PROJECT if key == "map" else addons.PREGEN_PROJECT
            files = mods.install("modrinth", project, target, s.meta.version, folder, None, s.log)
            info = {"files": files}
            if key == "map":
                info["port"] = self._free_port(addons.DEFAULT_MAP_PORT)
            s.meta.extra[key] = info
            s.save()
            s.log(("Mapa web (BlueMap) instalado." if key == "map" else "Chunky instalado.")
                  + (" Reinicia el servidor para activarlo." if s.running else ""))
        elif not enabled and current:
            for filename in current.get("files", []):
                mods.remove(folder, filename)
            s.meta.extra.pop(key, None)
            s.save()
            s.log("Mapa web quitado." if key == "map" else "Chunky quitado.")

    def pregenerate(self, server_id: str, action: str, radius: int = 0) -> None:
        """Genera el mundo por adelantado con Chunky (menos tirones al explorar)."""
        s = self.get(server_id)
        if not s.meta.extra.get("pregen"):
            raise UserError("Instala primero Chunky")
        if s.state != "running":
            raise UserError("Enciende el servidor para generar el mundo")
        if action == "start":
            if not 100 <= radius <= 100_000:
                raise UserError("El radio tiene que estar entre 100 y 100.000 bloques")
            s.pregen = {"state": "running", "percent": 0.0, "chunks": 0, "eta": None, "world": ""}
            for cmd in ("chunky center 0 0", f"chunky radius {radius}", "chunky start"):
                s.send(cmd)
        elif action == "pause":
            s.send("chunky pause")
        elif action == "continue":
            s.send("chunky continue")
        elif action == "cancel":
            s.send("chunky cancel")
            s.pregen = None
        else:
            raise UserError(f"Acción desconocida: {action}")

    # ---------- jugadores ----------

    def get_players(self, server_id: str) -> dict:
        s = self.get(server_id)
        if s.game.id not in ("minecraft", "bedrock"):
            raise UserError("La gestión de jugadores está disponible en Minecraft Java y Bedrock")
        return {**players.lists(s.game.id, s.server_dir), "online": sorted(s.online, key=str.lower),
                "pending": s.meta.extra.get("pending_players", [])}

    def player_action(self, server_id: str, action: str, name: str = "") -> str:
        s = self.get(server_id)
        try:
            command = players.command(s.game.id, action, name.strip())
        except ValueError:
            raise UserError("Nombre de jugador no válido") from None
        if s.state == "running":
            s.emit(f"> {command}")
            s.send(command)
            return "hecho"
        if action == "kick":
            raise UserError("El servidor está apagado: no hay nadie a quien echar")
        # Apagado: se guarda y se aplica al encender (no hace falta saber el UUID del jugador).
        pending = s.meta.extra.setdefault("pending_players", [])
        pending.append([action, name.strip()])
        s.save()
        return "pendiente"

    def _apply_pending_players(self, s: Server) -> None:
        pending = s.meta.extra.pop("pending_players", None)
        if not pending:
            return
        s.save()
        for action, name in pending:
            try:
                command = players.command(s.game.id, action, name)
                s.emit(f"> {command}")
                s.send(command)
            except (ValueError, UserError):
                pass

    def stop(self, server_id: str) -> None:
        s = self.get(server_id)
        if not s.running:
            raise UserError("El servidor no está encendido")
        threading.Thread(target=self._stop_blocking, args=(s,), daemon=True).start()

    def _stop_blocking(self, s: Server) -> None:
        proc = s.proc
        if not proc:
            return
        s.stopping = True
        s.state = "stopping"
        s.log("Apagando...")
        try:
            s.send(s.game.stop_command)
            proc.wait(STOP_TIMEOUT)
        except (UserError, subprocess.TimeoutExpired):
            s.log(f"No respondió en {STOP_TIMEOUT}s; forzando cierre.")
            self._kill_tree(proc)

    def restart(self, server_id: str) -> None:
        s = self.get(server_id)
        self._require_idle(s, need_stopped=False)

        def run():
            self._stop_blocking(s)
            while s.running:
                time.sleep(0.2)
            self._launch_safe(s)

        s.state = "stopping"
        threading.Thread(target=run, daemon=True).start()

    def kill(self, server_id: str) -> None:
        s = self.get(server_id)
        if not s.proc:
            raise UserError("El servidor no está encendido")
        s.stopping = True
        s.log("Forzando cierre del proceso.")
        self._kill_tree(s.proc)

    @staticmethod
    def _kill_tree(proc: subprocess.Popen) -> None:
        try:
            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                child.kill()
            parent.kill()
        except psutil.Error:
            pass

    def command(self, server_id: str, command: str) -> None:
        s = self.get(server_id)
        s.emit(f"> {command}")
        s.send(command)

    # ---------- ajustes ----------

    def update_settings(self, server_id: str, changes: dict) -> Server:
        s = self.get(server_id)
        if "port" in changes and changes["port"] != s.meta.port and s.running:
            raise UserError("Apaga el servidor para cambiar el puerto")
        if isinstance(changes.get("schedule"), dict):
            s.meta.extra["schedule"] = {**schedule_of(s.meta), **changes["schedule"]}
        for key in ("name", "memory_mb", "port", "auto_start", "auto_update", "auto_restart"):
            if key in changes and changes[key] is not None:
                setattr(s.meta, key, changes[key])
        s.save()
        if not s.task and s.server_dir.exists():
            s.game.apply_settings(s.meta, s.server_dir)
            if s.meta.extra.get("crossplay"):
                self._sync_geyser(s)
        return s

    def get_properties(self, server_id: str) -> dict[str, str]:
        s = self.get(server_id)
        if not s.game.properties_file:
            raise UserError("Este juego no usa archivo de propiedades")
        return s.game.read_config(s.server_dir)

    def _sync_geyser(self, s: Server) -> None:
        """Pasa a Geyser el nombre, la descripción y el límite de jugadores del servidor de Java."""
        props = read_properties(s.server_dir / "server.properties")
        max_players = props.get("max-players", "20").strip()
        crossplay.sync_appearance(s.server_dir, s.meta.flavor, s.meta.name,
                                  crossplay.decode_motd(props.get("motd", "A Minecraft Server")),
                                  int(max_players) if max_players.isdigit() else 20)

    def set_properties(self, server_id: str, props: dict[str, str]) -> None:
        s = self.get(server_id)
        if not s.game.properties_file:
            raise UserError("Este juego no usa archivo de propiedades")
        s.game.write_config(s.server_dir, props)
        if "server-port" in props and props["server-port"].isdigit():
            s.meta.port = int(props["server-port"])
            s.save()
        if s.meta.extra.get("crossplay") and not s.task:
            self._sync_geyser(s)  # descripción y límite nuevos también para Bedrock

    # ---------- actualizar ----------

    def update(self, server_id: str, version: str | None) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        if version in (None, "", "latest"):
            version = s.game.versions(s.meta.flavor)[0]

        def run():
            s.log("Haciendo copia de seguridad antes de actualizar...")
            self._backup(s)
            old = f"{s.meta.version}" + (f" ({s.meta.build})" if s.meta.build else "")
            if version != s.meta.version:
                s.meta.extra.pop("loader_version", None)  # el loader del modpack era para la versión anterior
            s.meta.version = version
            self._install(s, first_install=False)
            new = f"{s.meta.version}" + (f" ({s.meta.build})" if s.meta.build else "")
            s.log(f"Actualizado: {old} -> {new}")

        self._background(s, "updating", run)

    # ---------- copias de seguridad ----------

    def list_backups(self, server_id: str) -> list[dict]:
        self.get(server_id)
        folder = self.backups_dir / server_id
        if not folder.exists():
            return []
        return [{"name": f.name, "size_mb": round(f.stat().st_size / (1 << 20), 1),
                 "created": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")}
                for f in sorted(folder.glob("*.zip"), reverse=True)]

    def backup(self, server_id: str) -> None:
        s = self.get(server_id)
        self._require_idle(s, need_stopped=False)
        self._background(s, "backing-up", lambda: self._backup(s))

    def _backup(self, s: Server, auto: bool = False, target: Path | None = None) -> Path:
        regular = target is None  # las de clonar o mover son temporales: esas no se envían
        if target is None:
            folder = self.backups_dir / s.meta.id
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / f"{datetime.now():%Y%m%d-%H%M%S}{'-auto' if auto else ''}.zip"
        live = s.running
        if live:
            for cmd in s.game.backup_pre_commands:
                s.send(cmd)
            time.sleep(5)
        try:
            s.log(f"Creando copia {target.name}...")
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr(BACKUP_META, json.dumps(s.meta.to_dict()))
                for path in s.server_dir.rglob("*"):
                    rel = path.relative_to(s.server_dir)
                    if rel.parts[0] in BACKUP_EXCLUDE or path.name in BACKUP_EXCLUDE or not path.is_file():
                        continue
                    try:
                        z.write(path, rel)
                    except OSError as e:
                        s.log(f"  omitido {rel}: {e}")
        finally:
            if live and s.running:
                for cmd in s.game.backup_post_commands:
                    s.send(cmd)
        s.log(f"Copia creada ({target.stat().st_size // (1 << 20)} MB).")
        if regular and s.meta.extra.get("replica"):
            threading.Thread(target=self._send_replica, args=(s, target), daemon=True).start()
        return target

    def _send_replica(self, s: Server, archive: Path) -> None:
        cfg = s.meta.extra.get("replica")
        if not cfg:
            return
        s.log(f"Enviando la copia a «{cfg['target_name']}»...")
        try:
            replicas.send(cfg, cfg.get("source_name") or self.agent_name, s.meta.id, s.meta.name, s.meta.game, archive)
            cfg["last"] = {"time": time.time(), "ok": True, "name": archive.name}
            s.log(f"Copia guardada también en «{cfg['target_name']}».")
        except Exception as e:  # noqa: BLE001 - el otro equipo apagado, sin red...: se reintenta en la próxima
            cfg["last"] = {"time": time.time(), "ok": False, "error": str(e)}
            s.log(f"No se pudo enviar la copia a «{cfg['target_name']}»: {e}")
            s.event("replica", f"«{s.meta.name}»: no se pudo enviar la copia a «{cfg['target_name']}».")
        s.save()

    def set_replica(self, server_id: str, cfg: dict | None) -> None:
        s = self.get(server_id)
        if cfg is None:
            s.meta.extra.pop("replica", None)
        else:
            cfg = {**cfg, "address": replicas.reachable(cfg)}
            cfg.pop("addresses", None)
            s.meta.extra["replica"] = {**cfg, "last": None}
            s.log(f"Las copias de seguridad se guardarán también en «{cfg['target_name']}».")
        s.save()

    def restore_replica(self, key: str, name: str, new_name: str | None) -> Server:
        """Crea aquí un servidor a partir de una copia que envió otro equipo."""
        src = self.replicas.path(key, name)
        tmp = self.data_dir / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        copy = tmp / f"replica-{uuid.uuid4().hex[:6]}.zip"
        shutil.copy2(src, copy)  # import_server se queda con el archivo: la copia original no se toca
        return self.import_server(copy, new_name)

    def restore_backup(self, server_id: str, name: str) -> None:
        s = self.get(server_id)
        self._require_idle(s)
        archive = self._backup_path(server_id, name)

        def run():
            s.log(f"Restaurando {name}...")
            for child in s.server_dir.iterdir():
                if child.name in BACKUP_EXCLUDE:
                    continue
                shutil.rmtree(child) if child.is_dir() else child.unlink()
            with zipfile.ZipFile(archive) as z:
                z.extractall(s.server_dir, [m for m in z.namelist() if m != BACKUP_META])
                if BACKUP_META in z.namelist():
                    # Si la copia es de antes de una actualización, volvemos a esa versión.
                    old = json.loads(z.read(BACKUP_META))
                    for key in ("version", "build", "java_major"):
                        setattr(s.meta, key, old.get(key))
                    s.save()
            s.log(f"Copia restaurada (versión {s.meta.version}).")

        self._background(s, "restoring", run)

    def delete_backup(self, server_id: str, name: str) -> None:
        self._backup_path(server_id, name).unlink()

    def backup_file(self, server_id: str, name: str) -> Path:
        return self._backup_path(server_id, name)

    # ---------- importar un mundo existente ----------

    def import_world(self, server_id: str, archive: Path) -> None:
        """Sustituye el mundo por el del .zip (carpeta world/ y, opcionalmente, mods/ y config/).

        Antes se hace una copia de seguridad del servidor, por si hay que volver atrás.
        """
        s = self.get(server_id)
        try:
            self._require_idle(s)
            if not s.game.supports_world_import:
                raise UserError("Este juego no admite importar mundos")
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
        except (UserError, zipfile.BadZipFile) as e:
            archive.unlink(missing_ok=True)
            raise UserError(str(e) if isinstance(e, UserError) else "El archivo no es un .zip válido") from None
        if "world/level.dat" not in names:
            archive.unlink(missing_ok=True)
            raise UserError("No se encontró level.dat: elige la carpeta de un mundo de Minecraft")
        target = s.game.mod_target(s.meta)

        def run():
            try:
                s.log("Copia de seguridad del mundo actual antes de importar...")
                self._backup(s)
                level, *extra_dims = s.game.world_dirs(s.server_dir)
                for d in [level, *extra_dims]:
                    shutil.rmtree(s.server_dir / d, ignore_errors=True)
                mods_added = 0
                with zipfile.ZipFile(archive) as z:
                    if target and any(n.startswith("mods/") for n in z.namelist()):
                        # Los mods de la instancia sustituyen a los actuales (quedan en la copia).
                        shutil.rmtree(s.server_dir / target.folder, ignore_errors=True)
                    for member in z.infolist():
                        top, _, rest = member.filename.partition("/")
                        if not rest or member.is_dir():
                            continue
                        if top == "world":
                            dest = s.server_dir / level / rest
                        elif top == "mods" and target:
                            dest = s.server_dir / target.folder / rest
                            mods_added += 1
                        elif top == "config":
                            dest = s.server_dir / "config" / rest
                        else:
                            continue
                        dest = dest.resolve()
                        if s.server_dir.resolve() not in dest.parents:
                            continue  # rutas raras dentro del zip
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, open(dest, "wb") as out:
                            shutil.copyfileobj(src, out)
                (s.server_dir / level / "session.lock").unlink(missing_ok=True)
                s.log(f"Mundo importado en «{level}»" + (f" con {mods_added} mods" if mods_added else "") +
                      ". Enciende el servidor para cargarlo.")
            finally:
                archive.unlink(missing_ok=True)

        self._background(s, "importing", run)

    # ---------- importar (mover desde otro equipo) ----------

    def import_server(self, archive: Path, name: str | None = None) -> Server:
        """Crea un servidor a partir de una copia de seguridad de otro agente."""
        try:
            with zipfile.ZipFile(archive) as z:
                old = json.loads(z.read(BACKUP_META))
        except (zipfile.BadZipFile, KeyError, ValueError):
            archive.unlink(missing_ok=True)
            raise UserError("El archivo no es una copia de seguridad de Ownhost") from None
        if old.get("game") not in GAMES:
            archive.unlink(missing_ok=True)
            raise UserError(f"Juego desconocido: {old.get('game')}")
        adapter = GAMES[old["game"]]
        port = self._free_port(old.get("port") or adapter.default_port,
                               span=2 if adapter.id == "bedrock" else 1)
        meta = ServerMeta(id=uuid.uuid4().hex[:12], name=name or old["name"], game=old["game"],
                          flavor=old["flavor"], version=old["version"], memory_mb=old["memory_mb"],
                          port=port, auto_start=old.get("auto_start", False))
        if cp := (old.get("extra") or {}).get("crossplay"):
            meta.extra["crossplay"] = {**cp, "bedrock_port": self._free_bedrock_port()}
        s = Server(meta, self.servers_dir / meta.id, self.loop)
        s.server_dir.mkdir(parents=True, exist_ok=True)
        s.save()
        self.servers[meta.id] = s

        def run():
            try:
                # Primero los archivos del juego (no van en la copia) y luego el mundo y la configuración.
                self._install(s, first_install=True)
                s.log("Restaurando el mundo y la configuración...")
                with zipfile.ZipFile(archive) as z:
                    z.extractall(s.server_dir, [m for m in z.namelist() if m != BACKUP_META])
                s.game.apply_settings(s.meta, s.server_dir)
                s.log(f"Servidor importado (puerto {s.meta.port}).")
            finally:
                archive.unlink(missing_ok=True)

        self._background(s, "importing", run)
        return s

    # ---------- modpacks ----------

    def import_modpack(self, archive: Path, name: str | None, memory_mb: int, cf_key: str | None,
                       accept_eula: bool, whitelist: bool = False) -> Server:
        """Crea un servidor a partir de un .mrpack de Modrinth o un .zip de CurseForge."""
        try:
            pack = modpacks.read(archive)
            if pack.kind == "curseforge" and pack.files:
                mods._require_cf_key(cf_key)
            if not accept_eula:
                raise UserError("Debes aceptar el EULA de Minecraft para crear el servidor")
        except UserError:
            archive.unlink(missing_ok=True)
            raise
        adapter = GAMES["minecraft"]
        title = name or (f"{pack.name} {pack.version}".strip())
        meta = ServerMeta(id=uuid.uuid4().hex[:12], name=title, game="minecraft", flavor=pack.flavor,
                          version=pack.minecraft, memory_mb=memory_mb, port=self._free_port(adapter.default_port))
        meta.extra["loader_version"] = pack.loader_version
        meta.extra["modpack"] = {"name": pack.name, "version": pack.version, "source": pack.kind}
        s = Server(meta, self.servers_dir / meta.id, self.loop)
        s.server_dir.mkdir(parents=True, exist_ok=True)
        s.save()
        self.servers[meta.id] = s
        s.state = "stopped"

        def run():
            try:
                s.log(f"Modpack «{pack.name}» {pack.version}: Minecraft {pack.minecraft}, "
                      f"{pack.flavor} {pack.loader_version}, {len(pack.files)} "
                      f"{'archivo' if len(pack.files) == 1 else 'archivos'}.")
                self._install(s, first_install=True)
                manual = modpacks.install(pack, archive, s.server_dir, cf_key, s.log)
                # Después de los overrides, que pueden traer su propio server.properties
                adapter.apply_settings(s.meta, s.server_dir)
                write_properties(s.server_dir / adapter.properties_file, {"white-list": str(whitelist).lower()})
                if manual:
                    s.error = (f"Faltan {len(manual)} mods que sus autores no dejan descargar desde otras apps. "
                               "Mira la consola.")
                    s.log("AVISO: estos mods hay que descargarlos a mano y ponerlos en la carpeta mods:")
                    for m in manual:
                        s.log(f"  - {m}")
                s.log("Modpack instalado. Enciende el servidor para generar el mundo.")
            finally:
                archive.unlink(missing_ok=True)

        self._background(s, "importing", run)
        return s

    def mod_updates(self, server_id: str, cf_key: str | None) -> list[dict]:
        s, target, folder = self._mods(server_id)
        return mods.check_updates(folder, target, s.meta.version, cf_key)

    def update_mods(self, server_id: str, filenames: list[str], cf_key: str | None) -> None:
        s, target, folder = self._mods(server_id)
        self._require_idle(s)
        updates = [u for u in mods.check_updates(folder, target, s.meta.version, cf_key)
                   if u["filename"] in filenames]
        if not updates:
            raise UserError("No hay actualizaciones para esos mods")

        def run():
            s.log("Haciendo copia de seguridad antes de actualizar los mods...")
            self._backup(s)
            for u in updates:
                s.log(f"Actualizando {u['title']}: {u['current'] or u['filename']} -> {u['latest']}")
                mods.apply_update(folder, u)
            s.log("Mod actualizado." if len(updates) == 1 else f"{len(updates)} mods actualizados.")

        self._background(s, "installing-mod", run)

    # ---------- mods y plugins ----------

    def _mods(self, server_id: str) -> tuple[Server, "mods.ModTarget", Path]:
        s = self.get(server_id)
        target = s.game.mod_target(s.meta)
        if not target:
            raise UserError("Este tipo de servidor no admite mods ni plugins")
        return s, target, s.server_dir / target.folder

    def search_mods(self, server_id: str, source: str, query: str, cf_key: str | None, offset: int) -> list[dict]:
        s, target, _ = self._mods(server_id)
        return mods.search(source, target, s.meta.version, query, cf_key, offset)

    def list_mods(self, server_id: str) -> list[dict]:
        _, target, folder = self._mods(server_id)
        return mods.list_installed(folder, target)

    def install_mod(self, server_id: str, source: str, project_id: str, cf_key: str | None) -> list[str]:
        # Síncrono: los mods pesan poco y así los errores llegan directamente a la app.
        s, target, folder = self._mods(server_id)
        added = mods.install(source, project_id, target, s.meta.version, folder, cf_key, s.log)
        if added:
            s.log(f"Instalado: {', '.join(added)}. Reinicia el servidor para cargarlo.")
        return added

    def remove_mod(self, server_id: str, filename: str) -> None:
        mods.remove(self._mods(server_id)[2], filename)

    def set_mod_enabled(self, server_id: str, filename: str, enabled: bool) -> None:
        mods.set_enabled(self._mods(server_id)[2], filename, enabled)

    def _backup_path(self, server_id: str, name: str) -> Path:
        path = (self.backups_dir / server_id / name).resolve()
        if path.parent != (self.backups_dir / server_id).resolve() or not path.exists():
            raise UserError("Copia de seguridad no encontrada")
        return path
