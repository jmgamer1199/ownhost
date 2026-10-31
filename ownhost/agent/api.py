import asyncio
import logging
import os
import sys
import threading
import platform
import secrets
import socket
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import psutil
from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from ownhost import BUILD, __version__, discovery, i18n, updates
from ownhost.agent import files
from ownhost.agent.access import (
    MANAGE, MODERATE, OWNER, OWNER_PRINCIPAL, PLAY, GuestStore, Principal,
)
from ownhost.agent.config import AgentConfig
from ownhost.agent.errors import UserError
from ownhost.agent.games import GAMES
from ownhost.agent.manager import ServerManager
from ownhost.i18n import tr
from ownhost.net import TailscaleOwnerCheck, lan_ip, tailscale_ip
from ownhost.sysenv import clean_env


class CreateServer(BaseModel):
    name: str
    game: str
    flavor: str
    version: str = "latest"
    memory_mb: int = Field(2048, ge=512)
    port: int | None = Field(None, ge=1, le=65535)
    accept_eula: bool = False
    crossplay_enabled: bool = False
    floodgate: bool = True
    whitelist: bool = False


class UpdateSettings(BaseModel):
    name: str | None = None
    auto_restart: bool | None = None
    schedule: dict | None = None
    memory_mb: int | None = Field(None, ge=512)
    port: int | None = Field(None, ge=1, le=65535)
    auto_start: bool | None = None
    auto_update: bool | None = None


class Command(BaseModel):
    command: str


class UpdateRequest(BaseModel):
    version: str | None = None


class InstallMod(BaseModel):
    source: str
    project_id: str


class ToggleMod(BaseModel):
    enabled: bool


class UpdateMods(BaseModel):
    filenames: list[str]


class CloneRequest(BaseModel):
    name: str = ""


class PlayerAction(BaseModel):
    action: str
    name: str = ""


class CrossplayRequest(BaseModel):
    floodgate: bool = True


class FileContent(BaseModel):
    path: str
    content: str


class Pregen(BaseModel):
    action: str
    radius: int = 0


class ReplicaTarget(BaseModel):
    addresses: list[str] = Field(..., min_length=1, max_length=5)
    port: int = Field(..., ge=1, le=65535)
    token: str
    target_name: str
    source_name: str = ""  # what this computer is called in the app (so the other one shows it that way)
    keep: int = Field(3, ge=1, le=30)


class RestoreReplica(BaseModel):
    name: str = ""


class LanguageChoice(BaseModel):
    language: str


class CreateGuest(BaseModel):
    name: str
    role: str = "play"
    servers: list[str] | None = None  # None = all


WEB_PANEL = Path(__file__).resolve().parent / "web" / "panel.html"


def create_app(config: AgentConfig, manager: ServerManager) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        manager.load(asyncio.get_running_loop())
        # Answers the app when it looks for agents on the network (same port number, over UDP).
        responder = await discovery.start_responder(
            config.bind, config.port,
            {"name": config.name, "hostname": socket.gethostname(), "port": config.port, "version": __version__})
        yield
        if responder:
            responder.close()
        await asyncio.to_thread(manager.shutdown)

    app = FastAPI(title="Ownhost - agente", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def request_language(request: Request, call_next):
        # Errors are returned in the language of the app that asks (the header it sends with every request).
        token = i18n.use_language(request.headers.get(i18n.HEADER))
        try:
            return await call_next(request)
        finally:
            i18n.reset_language(token)

    owner_check = TailscaleOwnerCheck()
    guests = GuestStore(manager.data_dir)

    def identify(token: str, client, server) -> Principal | None:
        """The owner (agent token, or Tailscale from a device of their account) or a friend with their code."""
        if token and secrets.compare_digest(token.encode(), config.token.encode()):
            return OWNER_PRINCIPAL
        if guest := guests.find(token):
            return guest
        if config.trust_tailscale and client and owner_check.is_owner(client[0], server[0] if server else None):
            return OWNER_PRINCIPAL
        return None

    def principal(request: Request, authorization: str = Header("")) -> Principal:
        token = authorization.removeprefix("Bearer ").strip()
        who = identify(token, request.scope.get("client"), request.scope.get("server"))
        if not who:
            raise HTTPException(401, tr("Token incorrecto"))
        return who

    def need(level: int) -> list:
        def check(who: Principal = Depends(principal)) -> None:
            if who.level < level:
                raise HTTPException(403, tr("No tienes permiso para hacer esto en este equipo"))
        return [Depends(check)]

    def need_server(level: int) -> list:
        """Same, and the server must also be one of those they can see."""
        def check(sid: str, who: Principal = Depends(principal)) -> None:
            if not who.can_see(sid):
                raise HTTPException(404, tr("Servidor no encontrado"))
            if who.level < level:
                raise HTTPException(403, tr("No tienes permiso para hacer esto en este servidor"))
        return [Depends(check)]

    @app.exception_handler(UserError)
    async def user_error(_: Request, exc: UserError):
        return JSONResponse({"detail": str(exc)}, status_code=400)

    @app.exception_handler(httpx.HTTPError)
    async def upstream_error(_: Request, exc: httpx.HTTPError):
        return JSONResponse({"detail": tr("Error al contactar con un servicio externo: {error}", error=exc)}, status_code=502)

    @app.exception_handler(KeyError)
    async def not_found(_: Request, exc: KeyError):
        return JSONResponse({"detail": tr("Servidor no encontrado: {server}", server=exc)}, status_code=404)

    owner = need(OWNER)
    manager.agent_name = config.name

    def backup_sender(who: Principal = Depends(principal)) -> None:
        """The "receive backups" code of another computer, or the owner."""
        if not (who.owner or who.role == "backup"):
            raise HTTPException(403, tr("No tienes permiso para hacer esto en este equipo"))

    def shown(server, who: Principal) -> dict:
        # Only the owner sees the folder (the path contains their user name).
        data = server.to_dict()
        if who.owner:
            data["path"] = str(server.server_dir)
        return data

    async def _receive_upload(request: Request) -> Path:
        # The .zip arrives as the request body, streamed, so it is not loaded whole into memory.
        tmp_dir = manager.data_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        archive = tmp_dir / f"upload-{secrets.token_hex(6)}.zip"
        with open(archive, "wb") as f:
            async for chunk in request.stream():
                f.write(chunk)
        return archive

    @app.get("/api/hello")
    def hello():
        """No token: only identifies the computer so the app can find it on the network."""
        return {"name": config.name, "hostname": socket.gethostname(), "version": __version__,
                "build": BUILD, "port": config.port, "trust_tailscale": config.trust_tailscale}

    @app.get("/api/info", dependencies=need(PLAY))
    def info(who: Principal = Depends(principal)):
        mem = psutil.virtual_memory()
        return {
            "access": who.describe(),
            "language": i18n.normalize(config.language) or i18n.system_language(),
            "name": config.name,
            "hostname": socket.gethostname(),
            "version": __version__,
            "build": BUILD,
            "os": f"{platform.system()} {platform.release()}",
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(None),
            "memory_total_mb": mem.total // (1 << 20),
            "memory_available_mb": mem.available // (1 << 20),
            "lan_ip": lan_ip(),
            "tailscale_ip": tailscale_ip(),
        }

    @app.post("/api/shutdown", dependencies=owner, status_code=202)
    def shutdown():
        """Closes the agent (the app uses it to replace it with a new version).

        First it stops the servers with "stop" so they save the world.
        """
        def stop():
            manager.shutdown()
            os._exit(0)

        threading.Thread(target=stop, daemon=True).start()
        return {"detail": tr("Cerrando el agente")}

    @app.put("/api/agent/language", dependencies=owner, status_code=204)
    def set_agent_language(body: LanguageChoice):
        """Language of the console lines and notices of this agent (the app sends its own)."""
        config.language = i18n.normalize(body.language)
        config.save(manager.data_dir)
        i18n.set_language(config.language)

    @app.post("/api/agent/update", dependencies=owner, status_code=202)
    def update_agent():
        """Downloads the latest published version and restarts with it (agents on other computers).

        Running servers are stopped with "stop" and started again when it comes back.
        """
        release = updates.latest_release()
        if not release or not updates.is_newer(release["build"]):
            raise UserError(tr("Este agente ya tiene la última versión"))
        url = updates.download_url(release)
        if not url:
            raise UserError(tr("Este agente no se puede actualizar solo (se instaló desde el código o con pip, "
                               "o no hay versión para este sistema). Actualízalo a mano."))

        def run():
            try:
                binary = updates.install(url)
            except Exception:  # noqa: BLE001 - keeps the current version
                logging.getLogger(__name__).exception("Could not update the agent")
                return
            manager.shutdown(resume=True)
            args = sys.argv[1:]
            if sys.platform == "win32":
                updates.relaunch(binary, args)
                os._exit(0)
            # Same process (and same PID): systemd does not consider it dead.
            os.execve(str(binary), [str(binary), *args], clean_env({"PYINSTALLER_RESET_ENVIRONMENT": "1"}))

        threading.Thread(target=run, daemon=True).start()
        return {"detail": tr("Actualizando a la versión del {date}", date=updates.build_date(release["build"]))}

    @app.get("/api/games", dependencies=need(MANAGE))
    def games():
        return [g.describe() for g in GAMES.values()]

    @app.get("/api/games/{game}/{flavor}/versions", dependencies=need(MANAGE))
    def versions(game: str, flavor: str):
        if game not in GAMES:
            raise HTTPException(404, tr("Juego desconocido"))
        return GAMES[game].versions(flavor)

    @app.get("/api/servers", dependencies=need(PLAY))
    def list_servers(who: Principal = Depends(principal)):
        return [shown(s, who) for sid, s in manager.servers.items() if who.can_see(sid)]

    @app.post("/api/servers", dependencies=owner, status_code=201)
    def create_server(body: CreateServer):
        return manager.create(**body.model_dump()).to_dict()

    @app.get("/api/servers/{sid}", dependencies=need_server(PLAY))
    def get_server(sid: str, who: Principal = Depends(principal)):
        return shown(manager.get(sid), who)

    @app.patch("/api/servers/{sid}", dependencies=need_server(MANAGE))
    def patch_server(sid: str, body: UpdateSettings):
        return manager.update_settings(sid, body.model_dump(exclude_none=True)).to_dict()

    @app.delete("/api/servers/{sid}", dependencies=owner, status_code=204)
    def delete_server(sid: str):
        manager.delete(sid)
        guests.forget_server(sid)

    # ---------- access for friends ----------

    @app.get("/api/guests", dependencies=owner)
    def list_guests():
        return guests.public()

    @app.post("/api/guests", dependencies=owner, status_code=201)
    def create_guest(body: CreateGuest):
        for sid in body.servers or []:
            manager.get(sid)
        guest, token = guests.create(body.name, body.role, body.servers)
        # The code is only shown now: the agent stores its hash.
        return {**guest.public(), "token": token}

    @app.delete("/api/guests/{guest_id}", dependencies=owner, status_code=204)
    def delete_guest(guest_id: str):
        guests.delete(guest_id)

    # ---------- backups from other computers ----------

    @app.get("/api/replicas/check", dependencies=[Depends(backup_sender)])
    def replicas_check():
        return {"name": config.name}

    @app.put("/api/replicas/{source}/{sid}/{name}", dependencies=[Depends(backup_sender)], status_code=204)
    async def receive_replica(source: str, sid: str, name: str, request: Request, server_name: str = "",
                              game: str = "", keep: int = 3):
        upload = await _receive_upload(request)
        await asyncio.to_thread(manager.replicas.store, source, sid, name, server_name or sid, game, upload,
                                min(max(keep, 1), 30))

    @app.get("/api/replicas", dependencies=owner)
    def list_replicas():
        return manager.replicas.listing()

    @app.post("/api/replicas/{key}/{name}/restore", dependencies=owner, status_code=201)
    def restore_replica(key: str, name: str, body: RestoreReplica):
        return manager.restore_replica(key, name, body.name.strip() or None).to_dict()

    @app.delete("/api/replicas/{key}", dependencies=owner, status_code=204)
    def delete_replicas(key: str):
        manager.replicas.delete(key)

    @app.put("/api/servers/{sid}/replica", dependencies=owner)
    def set_replica(sid: str, body: ReplicaTarget):
        manager.set_replica(sid, body.model_dump())
        return manager.get(sid).to_dict()

    @app.delete("/api/servers/{sid}/replica", dependencies=owner)
    def remove_replica(sid: str):
        manager.set_replica(sid, None)
        return manager.get(sid).to_dict()

    # ---------- web panel (for the phone) ----------

    @app.get("/", include_in_schema=False)
    def web_panel():
        return HTMLResponse(WEB_PANEL.read_text(encoding="utf-8"), headers={"Cache-Control": "no-cache"})

    actions = {"start": PLAY, "stop": PLAY, "restart": PLAY, "kill": MODERATE, "backup": MODERATE, "login": MANAGE}
    for action, level in actions.items():
        def make(action=action):
            def handler(sid: str):
                getattr(manager, action)(sid)
                return manager.get(sid).to_dict()
            return handler
        app.post(f"/api/servers/{{sid}}/{action}", dependencies=need_server(level))(make())

    @app.post("/api/servers/{sid}/command", dependencies=need_server(MODERATE), status_code=204)
    def send_command(sid: str, body: Command):
        manager.command(sid, body.command)

    @app.post("/api/servers/{sid}/update", dependencies=need_server(MANAGE))
    def update_server(sid: str, body: UpdateRequest):
        manager.update(sid, body.version)
        return manager.get(sid).to_dict()

    @app.get("/api/servers/{sid}/properties", dependencies=need_server(MANAGE))
    def get_properties(sid: str):
        return manager.get_properties(sid)

    @app.put("/api/servers/{sid}/properties", dependencies=need_server(MANAGE), status_code=204)
    def put_properties(sid: str, body: dict[str, str]):
        manager.set_properties(sid, body)

    @app.get("/api/servers/{sid}/backups", dependencies=need_server(MODERATE))
    def list_backups(sid: str):
        return manager.list_backups(sid)

    @app.post("/api/servers/{sid}/backups/{name}/restore", dependencies=need_server(MANAGE), status_code=204)
    def restore_backup(sid: str, name: str):
        manager.restore_backup(sid, name)

    @app.delete("/api/servers/{sid}/backups/{name}", dependencies=need_server(MANAGE), status_code=204)
    def delete_backup(sid: str, name: str):
        manager.delete_backup(sid, name)

    @app.get("/api/servers/{sid}/backups/{name}/download", dependencies=owner)
    def download_backup(sid: str, name: str):
        return FileResponse(manager.backup_file(sid, name), media_type="application/zip", filename=name)

    @app.post("/api/servers/import", dependencies=owner, status_code=201)
    async def import_server(request: Request, name: str | None = None):
        archive = await _receive_upload(request)
        server = await asyncio.to_thread(manager.import_server, archive, name)
        return server.to_dict()

    @app.post("/api/modpacks/import", dependencies=owner, status_code=201)
    async def import_modpack(request: Request, name: str | None = None, memory_mb: int = 4096,
                             accept_eula: bool = False, whitelist: bool = False,
                             x_curseforge_key: str | None = Header(None)):
        archive = await _receive_upload(request)
        server = await asyncio.to_thread(manager.import_modpack, archive, name, max(memory_mb, 512),
                                         x_curseforge_key, accept_eula, whitelist)
        return server.to_dict()

    @app.post("/api/servers/{sid}/world", dependencies=need_server(MANAGE))
    async def import_world(sid: str, request: Request):
        manager.get(sid)
        archive = await _receive_upload(request)
        await asyncio.to_thread(manager.import_world, sid, archive)
        return manager.get(sid).to_dict()

    @app.post("/api/servers/{sid}/crossplay", dependencies=need_server(MANAGE))
    def enable_crossplay(sid: str, body: CrossplayRequest):
        manager.enable_crossplay(sid, body.floodgate)
        return manager.get(sid).to_dict()

    @app.put("/api/servers/{sid}/crossplay/extras/{key}", dependencies=need_server(MANAGE))
    def set_crossplay_extra(sid: str, key: str, body: ToggleMod):
        manager.set_crossplay_extra(sid, key, body.enabled)
        return manager.get(sid).to_dict()

    @app.delete("/api/servers/{sid}/crossplay", dependencies=need_server(MANAGE))
    def disable_crossplay(sid: str):
        manager.disable_crossplay(sid)
        return manager.get(sid).to_dict()

    @app.get("/api/servers/{sid}/files", dependencies=need_server(MANAGE))
    def list_files(sid: str, path: str = ""):
        return files.listing(manager.get(sid).server_dir, path)

    @app.get("/api/servers/{sid}/file", dependencies=need_server(MANAGE))
    def read_file(sid: str, path: str):
        return {"path": path, "content": files.read(manager.get(sid).server_dir, path)}

    @app.put("/api/servers/{sid}/file", dependencies=need_server(MANAGE), status_code=204)
    def write_file(sid: str, body: FileContent):
        files.write(manager.get(sid).server_dir, body.path, body.content)

    @app.put("/api/servers/{sid}/addons/{key}", dependencies=need_server(MANAGE))
    def set_addon(sid: str, key: str, body: ToggleMod):
        manager.set_addon(sid, key, body.enabled)
        return manager.get(sid).to_dict()

    @app.post("/api/servers/{sid}/pregen", dependencies=need_server(MANAGE))
    def pregenerate(sid: str, body: Pregen):
        manager.pregenerate(sid, body.action, body.radius)
        return manager.get(sid).to_dict()

    @app.get("/api/servers/{sid}/metrics", dependencies=need_server(PLAY))
    def get_metrics(sid: str, hours: float = 1):
        return manager.get_metrics(sid, min(max(hours, 0.1), 24))

    @app.post("/api/servers/{sid}/clone", dependencies=owner, status_code=202)
    def clone_server(sid: str, body: CloneRequest):
        manager.clone(sid, body.name)
        return {"ok": True}

    @app.get("/api/servers/{sid}/icon", dependencies=need_server(PLAY))
    def get_icon(sid: str):
        return FileResponse(manager.icon_path(sid), media_type="image/png")

    @app.put("/api/servers/{sid}/icon", dependencies=need_server(MANAGE))
    async def put_icon(sid: str, request: Request):
        manager.set_icon(sid, await request.body())
        return manager.get(sid).to_dict()

    @app.delete("/api/servers/{sid}/icon", dependencies=need_server(MANAGE))
    def delete_icon(sid: str):
        manager.set_icon(sid, None)
        return manager.get(sid).to_dict()

    @app.get("/api/servers/{sid}/stats", dependencies=need_server(PLAY))
    def player_stats(sid: str):
        return manager.get(sid).player_stats.summary()

    @app.get("/api/servers/{sid}/players", dependencies=need_server(PLAY))
    def get_players(sid: str):
        return manager.get_players(sid)

    @app.post("/api/servers/{sid}/players", dependencies=need_server(MODERATE))
    def player_action(sid: str, body: PlayerAction):
        return {"result": manager.player_action(sid, body.action, body.name)}

    @app.get("/api/servers/{sid}/mods", dependencies=need_server(MANAGE))
    def list_mods(sid: str):
        return manager.list_mods(sid)

    @app.get("/api/servers/{sid}/mods/search", dependencies=need_server(MANAGE))
    def search_mods(sid: str, source: str = "modrinth", q: str = "", offset: int = 0,
                    x_curseforge_key: str | None = Header(None)):
        return manager.search_mods(sid, source, q, x_curseforge_key, offset)

    @app.get("/api/servers/{sid}/mods/updates", dependencies=need_server(MANAGE))
    def mod_updates(sid: str, x_curseforge_key: str | None = Header(None)):
        return manager.mod_updates(sid, x_curseforge_key)

    @app.post("/api/servers/{sid}/mods/update", dependencies=need_server(MANAGE), status_code=202)
    def update_mods(sid: str, body: UpdateMods, x_curseforge_key: str | None = Header(None)):
        manager.update_mods(sid, body.filenames, x_curseforge_key)
        return manager.get(sid).to_dict()

    @app.post("/api/servers/{sid}/mods", dependencies=need_server(MANAGE))
    def install_mod(sid: str, body: InstallMod, x_curseforge_key: str | None = Header(None)):
        return manager.install_mod(sid, body.source, body.project_id, x_curseforge_key)

    @app.put("/api/servers/{sid}/mods/{filename}", dependencies=need_server(MANAGE), status_code=204)
    def toggle_mod(sid: str, filename: str, body: ToggleMod):
        manager.set_mod_enabled(sid, filename, body.enabled)

    @app.delete("/api/servers/{sid}/mods/{filename}", dependencies=need_server(MANAGE), status_code=204)
    def remove_mod(sid: str, filename: str):
        manager.remove_mod(sid, filename)

    @app.websocket("/api/servers/{sid}/console")
    async def console(ws: WebSocket, sid: str, token: str = ""):
        # Browsers/WebSocket clients cannot easily send headers: token in the query.
        who = identify(token, ws.scope.get("client"), ws.scope.get("server"))
        if not who or who.level < MODERATE or not who.can_see(sid) or sid not in manager.servers:
            await ws.close(code=4401)
            return
        await ws.accept()
        server = manager.servers[sid]
        queue: asyncio.Queue[str] = asyncio.Queue()
        server.subscribers.add(queue)
        try:
            await ws.send_text("\n".join(server.console))

            async def receive_commands():
                while True:
                    text = await ws.receive_text()
                    try:
                        manager.command(sid, text)
                    except UserError as e:
                        server.log(str(e))

            receiver = asyncio.create_task(receive_commands())
            try:
                while True:
                    line = await queue.get()
                    lines = [line]
                    while not queue.empty() and len(lines) < 200:
                        lines.append(queue.get_nowait())
                    await ws.send_text("\n".join(lines))
            finally:
                receiver.cancel()
        except WebSocketDisconnect:
            pass
        finally:
            server.subscribers.discard(queue)

    return app
