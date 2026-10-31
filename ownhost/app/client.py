from pathlib import Path
from typing import Callable
from urllib.parse import quote

import httpx

from ownhost.app.hosts import Host


class ApiError(Exception):
    pass


class AgentClient:
    def __init__(self, host: Host):
        self.host = host
        self.base = f"http://{host.address}:{host.port}/api"
        # Conexión corta: si un equipo está apagado no queremos esperar 15 s.
        self.http = httpx.Client(timeout=httpx.Timeout(15, connect=3), headers={"Authorization": f"Bearer {host.token}"})

    def close(self) -> None:
        self.http.close()

    def _req(self, method: str, path: str, **kwargs):
        try:
            r = self.http.request(method, self.base + path, **kwargs)
        except httpx.ConnectError:
            raise ApiError(f"No se puede conectar con {self.host.address}:{self.host.port}") from None
        except httpx.TimeoutException:
            raise ApiError("El agente no responde") from None
        if r.status_code == 401:
            raise ApiError("Token incorrecto")
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail")
            except ValueError:
                detail = r.text
            raise ApiError(str(detail) if detail else f"Error {r.status_code}")
        return r.json() if r.content else None

    def ws_url(self, server_id: str) -> str:
        return f"ws://{self.host.address}:{self.host.port}/api/servers/{server_id}/console?token={quote(self.host.token)}"

    def info(self):
        return self._req("GET", "/info")

    def games(self):
        return self._req("GET", "/games")

    def versions(self, game: str, flavor: str):
        return self._req("GET", f"/games/{game}/{flavor}/versions", timeout=60)

    def servers(self):
        return self._req("GET", "/servers")

    def create(self, **body):
        return self._req("POST", "/servers", json=body, timeout=60)

    def action(self, sid: str, action: str):
        return self._req("POST", f"/servers/{sid}/{action}")

    def command(self, sid: str, command: str):
        return self._req("POST", f"/servers/{sid}/command", json={"command": command})

    def patch(self, sid: str, **changes):
        return self._req("PATCH", f"/servers/{sid}", json=changes)

    def delete(self, sid: str):
        return self._req("DELETE", f"/servers/{sid}")

    def update(self, sid: str, version: str | None):
        return self._req("POST", f"/servers/{sid}/update", json={"version": version}, timeout=60)

    def properties(self, sid: str):
        return self._req("GET", f"/servers/{sid}/properties")

    def set_properties(self, sid: str, props: dict):
        return self._req("PUT", f"/servers/{sid}/properties", json=props)

    def backups(self, sid: str):
        return self._req("GET", f"/servers/{sid}/backups")

    def restore_backup(self, sid: str, name: str):
        return self._req("POST", f"/servers/{sid}/backups/{quote(name)}/restore")

    def delete_backup(self, sid: str, name: str):
        return self._req("DELETE", f"/servers/{sid}/backups/{quote(name)}")

    def enable_crossplay(self, sid: str, floodgate: bool):
        return self._req("POST", f"/servers/{sid}/crossplay", json={"floodgate": floodgate})

    def set_crossplay_extra(self, sid: str, key: str, enabled: bool):
        return self._req("PUT", f"/servers/{sid}/crossplay/extras/{key}", json={"enabled": enabled}, timeout=120)

    def disable_crossplay(self, sid: str):
        return self._req("DELETE", f"/servers/{sid}/crossplay")

    def server(self, sid: str):
        return self._req("GET", f"/servers/{sid}")

    # ---------- transferencias (mover servidores entre equipos) ----------

    def download_backup(self, sid: str, name: str, dest: Path, progress: Callable[[int], None]) -> None:
        url = f"{self.base}/servers/{sid}/backups/{quote(name)}/download"
        try:
            with self.http.stream("GET", url, timeout=httpx.Timeout(None, connect=5)) as r:
                if r.status_code >= 400:
                    raise ApiError(f"No se pudo descargar la copia (error {r.status_code})")
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(1 << 20):
                        f.write(chunk)
                        done += len(chunk)
                        progress(done)
        except httpx.TransportError as e:
            raise ApiError(f"Conexión interrumpida al descargar: {e}") from None

    def _upload(self, path: str, archive: Path, progress: Callable[[int], None], headers: dict | None = None,
                **params):
        def chunks():
            done = 0
            with open(archive, "rb") as f:
                while chunk := f.read(1 << 20):
                    done += len(chunk)
                    progress(done)
                    yield chunk

        headers = {"Content-Type": "application/zip", "Content-Length": str(archive.stat().st_size),
                   **(headers or {})}
        try:
            return self._req("POST", path, params=params or None, content=chunks(),
                             headers=headers, timeout=httpx.Timeout(None, connect=5))
        except httpx.TransportError as e:
            raise ApiError(f"Conexión interrumpida al enviar: {e}") from None

    def import_server(self, archive: Path, name: str, progress: Callable[[int], None]):
        return self._upload("/servers/import", archive, progress, name=name)

    def import_world(self, sid: str, archive: Path, progress: Callable[[int], None]):
        return self._upload(f"/servers/{sid}/world", archive, progress)

    def import_modpack(self, archive: Path, progress: Callable[[int], None], cf_key: str | None, **params):
        return self._upload("/modpacks/import", archive, progress, headers=self._cf_headers(cf_key), **params)

    def mod_updates(self, sid: str, cf_key: str | None):
        # Con CurseForge se consulta mod a mod: puede tardar con muchos mods.
        return self._req("GET", f"/servers/{sid}/mods/updates", headers=self._cf_headers(cf_key), timeout=120)

    def update_mods(self, sid: str, filenames: list[str], cf_key: str | None):
        return self._req("POST", f"/servers/{sid}/mods/update", json={"filenames": filenames},
                         headers=self._cf_headers(cf_key), timeout=120)

    # ---------- mods ----------

    @staticmethod
    def _cf_headers(cf_key: str | None) -> dict:
        return {"X-CurseForge-Key": cf_key} if cf_key else {}

    def metrics(self, sid: str, hours: float):
        # La primera vez el agente mide el tamaño del mundo, que puede tardar en mundos grandes.
        return self._req("GET", f"/servers/{sid}/metrics", params={"hours": hours}, timeout=60)

    def clone(self, sid: str, name: str):
        return self._req("POST", f"/servers/{sid}/clone", json={"name": name})

    def icon(self, sid: str) -> bytes | None:
        try:
            r = self.http.get(f"{self.base}/servers/{sid}/icon")
        except httpx.HTTPError:
            raise ApiError(f"No se puede conectar con {self.host.address}:{self.host.port}") from None
        return r.content if r.status_code == 200 else None

    def set_icon(self, sid: str, png: bytes):
        return self._req("PUT", f"/servers/{sid}/icon", content=png, headers={"Content-Type": "image/png"})

    def delete_icon(self, sid: str):
        return self._req("DELETE", f"/servers/{sid}/icon")

    def guests(self):
        return self._req("GET", "/guests")

    def create_guest(self, name: str, role: str, servers: list[str] | None):
        return self._req("POST", "/guests", json={"name": name, "role": role, "servers": servers})

    def delete_guest(self, guest_id: str):
        return self._req("DELETE", f"/guests/{guest_id}")

    def players(self, sid: str):
        return self._req("GET", f"/servers/{sid}/players")

    def player_action(self, sid: str, action: str, name: str = ""):
        return self._req("POST", f"/servers/{sid}/players", json={"action": action, "name": name})

    def mods(self, sid: str):
        return self._req("GET", f"/servers/{sid}/mods")

    def search_mods(self, sid: str, source: str, query: str, cf_key: str | None):
        return self._req("GET", f"/servers/{sid}/mods/search", params={"source": source, "q": query},
                         headers=self._cf_headers(cf_key), timeout=60)

    def install_mod(self, sid: str, source: str, project_id: str, cf_key: str | None):
        return self._req("POST", f"/servers/{sid}/mods", json={"source": source, "project_id": project_id},
                         headers=self._cf_headers(cf_key), timeout=300)

    def toggle_mod(self, sid: str, filename: str, enabled: bool):
        return self._req("PUT", f"/servers/{sid}/mods/{quote(filename)}", json={"enabled": enabled})

    def remove_mod(self, sid: str, filename: str):
        return self._req("DELETE", f"/servers/{sid}/mods/{quote(filename)}")
