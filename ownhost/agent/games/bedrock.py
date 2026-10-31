"""Mojang's official Minecraft Bedrock Dedicated Server (BDS).

It does not use Java: it ships its own executable. Bedrock players (phone, console, Windows) connect
over UDP. The Bedrock client updates itself, so the server must always be on the latest version:
that is why automatic updates are on.
"""

import re
import sys
import time
import zipfile
from pathlib import Path

from ownhost.agent.downloads import download, get_json
from ownhost.agent.games.base import Flavor, GameAdapter, InstallContext, read_properties, write_properties
from ownhost.agent.models import ServerMeta
from ownhost.i18n import tr

LINKS_API = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
# User files an update must not overwrite.
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
        Flavor("release", "Oficial (Bedrock Dedicated Server)"),  # translated in describe()
        Flavor("preview", "Preview (versión de pruebas)"),
    ]
    ready_pattern = re.compile(r"Server started\.")
    properties_file = "server.properties"
    # "save hold" leaves the world files ready to copy without stopping the server.
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
            raise RuntimeError(tr("Mojang no ofrece el servidor de Bedrock para este sistema"))
        return url

    @staticmethod
    def _version_of(url: str) -> str:
        m = re.search(r"bedrock-server-([\d.]+)\.zip", url)
        return m.group(1) if m else "latest"

    def versions(self, flavor: str) -> list[str]:
        # Mojang only publishes the latest: Bedrock clients cannot join old versions.
        return [self._version_of(self._url(flavor))]

    def java_major(self, flavor: str, version: str) -> int | None:
        return None

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        latest = self.versions(meta.flavor)[0]
        return latest if latest != meta.version else None

    def install(self, ctx: InstallContext) -> None:
        url = self._url(ctx.meta.flavor)
        ctx.meta.version = self._version_of(url)
        # minecraft.net stalls downloads that do not present themselves as a browser.
        archive = download(url, ctx.server_dir / "bedrock-server.zip", ctx.log, user_agent=BROWSER_UA)
        ctx.log(tr("Extrayendo el servidor de Bedrock..."))
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                # On an update the user's configuration and permissions are kept.
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
        # On Linux the server looks for its libraries in its own folder.
        return None if sys.platform == "win32" else {"LD_LIBRARY_PATH": "."}

    def command(self, meta: ServerMeta, server_dir: Path, java: Path | None) -> list[str]:
        exe = server_dir / ("bedrock_server.exe" if sys.platform == "win32" else "bedrock_server")
        if not exe.exists():
            raise RuntimeError(tr("No se encuentra el ejecutable del servidor; prueba a actualizarlo"))
        return [str(exe)]
