"""Servidor dedicado de Minecraft Bedrock (BDS) oficial de Mojang.

No usa Java: trae su propio ejecutable. Los jugadores de Bedrock (móvil, consola, Windows) se
conectan por UDP. El cliente de Bedrock se actualiza solo, así que el servidor tiene que ir siempre
a la última versión: por eso la actualización automática viene activada.
"""

import re
import sys
import time
import zipfile
from pathlib import Path

from ownhost.agent.downloads import download, get_json
from ownhost.agent.games.base import Flavor, GameAdapter, InstallContext, read_properties, write_properties
from ownhost.agent.models import ServerMeta

LINKS_API = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
# Archivos del usuario que una actualización no debe sobrescribir.
KEEP_ON_UPDATE = {"server.properties", "permissions.json", "allowlist.json", "whitelist.json"}
CACHE_SECONDS = 600
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


class BedrockAdapter(GameAdapter):
    id = "bedrock"
    name = "Minecraft Bedrock"
    default_port = 19132
    needs_eula = True
    uses_java = False
    flavors = [
        Flavor("release", "Oficial (Bedrock Dedicated Server)"),
        Flavor("preview", "Preview (versión de pruebas)"),
    ]
    ready_pattern = re.compile(r"Server started\.")
    properties_file = "server.properties"
    # "save hold" deja los archivos del mundo listos para copiar sin apagar el servidor.
    backup_pre_commands = ["save hold"]
    backup_post_commands = ["save resume"]

    def __init__(self):
        self._cache: tuple[float, dict] | None = None

    def _links(self) -> dict[str, str]:
        if self._cache and time.time() - self._cache[0] < CACHE_SECONDS:
            return self._cache[1]
        data = get_json(LINKS_API)
        links = {l["downloadType"]: l["downloadUrl"] for l in data["result"]["links"]}
        self._cache = (time.time(), links)
        return links

    def _url(self, flavor: str) -> str:
        system = "Windows" if sys.platform == "win32" else "Linux"
        key = f"serverBedrock{'Preview' if flavor == 'preview' else ''}{system}"
        url = self._links().get(key)
        if not url:
            raise RuntimeError("Mojang no ofrece el servidor de Bedrock para este sistema")
        return url

    @staticmethod
    def _version_of(url: str) -> str:
        m = re.search(r"bedrock-server-([\d.]+)\.zip", url)
        return m.group(1) if m else "latest"

    def versions(self, flavor: str) -> list[str]:
        # Mojang solo publica la última: los clientes de Bedrock no pueden entrar en versiones viejas.
        return [self._version_of(self._url(flavor))]

    def java_major(self, flavor: str, version: str) -> int | None:
        return None

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        latest = self.versions(meta.flavor)[0]
        return latest if latest != meta.version else None

    def install(self, ctx: InstallContext) -> None:
        url = self._url(ctx.meta.flavor)
        ctx.meta.version = self._version_of(url)
        # minecraft.net deja colgadas las descargas que no se presentan como un navegador.
        archive = download(url, ctx.server_dir / "bedrock-server.zip", ctx.log, user_agent=BROWSER_UA)
        ctx.log("Extrayendo el servidor de Bedrock...")
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                # En una actualización se conservan la configuración y los permisos del usuario.
                if not ctx.first_install and member.filename in KEEP_ON_UPDATE \
                        and (ctx.server_dir / member.filename).exists():
                    continue
                z.extract(member, ctx.server_dir)
        archive.unlink()
        exe = ctx.server_dir / "bedrock_server"
        if exe.exists():
            exe.chmod(0o755)
        self.apply_settings(ctx.meta, ctx.server_dir)

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        path = server_dir / self.properties_file
        updates = {"server-port": str(meta.port), "server-portv6": str(meta.port + 1)}
        if read_properties(path).get("server-name") in (None, "Dedicated Server"):
            updates["server-name"] = meta.name
        write_properties(path, updates)

    def extra_ports(self, meta: ServerMeta) -> list[int]:
        return [meta.port + 1]  # IPv6

    def env(self, meta: ServerMeta, server_dir: Path) -> dict[str, str] | None:
        # En Linux el servidor busca sus bibliotecas en su propia carpeta.
        return None if sys.platform == "win32" else {"LD_LIBRARY_PATH": "."}

    def command(self, meta: ServerMeta, server_dir: Path, java: Path | None) -> list[str]:
        exe = server_dir / ("bedrock_server.exe" if sys.platform == "win32" else "bedrock_server")
        if not exe.exists():
            raise RuntimeError("No se encuentra el ejecutable del servidor; prueba a actualizarlo")
        return [str(exe)]
