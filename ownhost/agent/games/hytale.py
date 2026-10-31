"""Hytale dedicated server.

The files are obtained with the official Hytale Downloader, which asks you to log
in with your Hytale account the first time (it shows a URL and a code).
The server also needs to authenticate after the first start with
`/auth login device`; the agent runs it by itself and the app shows the login
window (see device_auth.py).
"""

import json
import platform
import re
import subprocess
import sys
from pathlib import Path

from ownhost.agent.downloads import download, extract
from ownhost.agent.errors import UserError
from ownhost.agent.games.base import NO_WINDOW, Flavor, GameAdapter, InstallContext, run_logged
from ownhost.agent.models import ServerMeta
from ownhost.agent.mods import ModTarget
from ownhost.i18n import tr
from ownhost.sysenv import clean_env

DOWNLOADER_URL = "https://downloader.hytale.com/hytale-downloader.zip"
CONFIG_FILE = "config.json"
VERSION_RE = re.compile(r"\d{4}\.\d{2}\.\d{2}[-\w.]*|\d+\.\d+[.\w-]*")


class HytaleAdapter(GameAdapter):
    id = "hytale"
    name = "Hytale"
    default_port = 5520
    flavors = [
        Flavor("release", "Release"),
        Flavor("pre-release", "Pre-release"),
    ]
    device_auth = True
    auth_login_command = "/auth login device"
    auth_persist_command = "/auth persistence Encrypted"
    # config.json is edited in the "Properties" tab (the server creates it on first start)
    properties_file = CONFIG_FILE

    def versions(self, flavor: str) -> list[str]:
        # The downloader always downloads the latest version of the chosen channel.
        return ["latest"]

    def java_major(self, flavor: str, version: str) -> int:
        return 25

    def _downloader(self, tools_dir: Path, log) -> Path:
        base = tools_dir / "hytale-downloader"
        exe = self._find_downloader(base)
        if exe:
            return exe
        archive = download(DOWNLOADER_URL, tools_dir / "hytale-downloader.zip", log)
        extract(archive, base)
        archive.unlink()
        exe = self._find_downloader(base)
        if not exe:
            raise RuntimeError(tr("No se encontró el ejecutable del Hytale Downloader para este sistema"))
        exe.chmod(0o755)
        return exe

    @staticmethod
    def _find_downloader(base: Path) -> Path | None:
        if not base.exists():
            return None
        is_windows = sys.platform == "win32"
        arm = platform.machine().lower() in ("arm64", "aarch64")
        candidates = []
        for p in base.rglob("hytale-downloader*"):
            if not p.is_file() or p.suffix in (".zip", ".md", ".txt"):
                continue
            name = p.name.lower()
            if is_windows != (p.suffix == ".exe"):
                continue
            if not is_windows and "windows" in name:
                continue
            candidates.append(p)
        # Prefer the binary for our architecture if there are several.
        candidates.sort(key=lambda p: ("arm64" in p.name.lower() or "aarch64" in p.name.lower()) != arm)
        return candidates[0] if candidates else None

    @staticmethod
    def _patchline(meta: ServerMeta) -> list[str]:
        return ["-patchline", "pre-release"] if meta.flavor == "pre-release" else []

    def _latest_version(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        """Version the downloader would download now (without downloading anything)."""
        exe = self._find_downloader(tools_dir / "hytale-downloader")
        if not exe:
            return None
        # If the downloader's credentials have expired it would ask to log in: with the time limit
        # it does not hang and the server starts with the version it has.
        out = subprocess.run([str(exe), "-print-version", *self._patchline(meta)], cwd=exe.parent,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                             stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, env=clean_env())
        if out.returncode != 0:
            raise RuntimeError(tr("el downloader terminó con código {code}", code=out.returncode))
        for line in reversed(out.stdout.splitlines()):
            if match := VERSION_RE.search(line):
                return match.group(0)
        return None

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        latest = self._latest_version(meta, tools_dir)
        return f"Hytale {latest}" if latest and latest != meta.build else None

    def install(self, ctx: InstallContext) -> None:
        exe = self._downloader(ctx.tools_dir, ctx.log)
        game_zip = ctx.server_dir / "hytale-game.zip"
        ctx.log(tr("Ejecutando Hytale Downloader. Si es la primera vez, la app mostrará una ventana "
                   "para iniciar sesión con tu cuenta de Hytale."))
        cmd = [str(exe), "-download-path", str(game_zip), *self._patchline(ctx.meta)]
        # It runs in the tools folder so the downloader's credentials
        # are reused between servers.
        run_logged(cmd, exe.parent, ctx.log)
        ctx.log(tr("Extrayendo archivos del juego..."))
        extract(game_zip, ctx.server_dir)
        game_zip.unlink()
        # The version is recorded to know later whether there is a newer one.
        try:
            ctx.meta.build = self._latest_version(ctx.meta, ctx.tools_dir)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            ctx.meta.build = None
        if ctx.first_install:
            ctx.log(tr("Instalado. Al encenderlo por primera vez se pedirá iniciar sesión para el servidor."))

    def command(self, meta: ServerMeta, server_dir: Path, java: Path) -> list[str]:
        jar = next(server_dir.rglob("HytaleServer.jar"), None)
        if not jar:
            raise RuntimeError(tr("No se encuentra HytaleServer.jar; prueba a actualizar el servidor"))
        return [str(java), f"-Xms{min(2048, meta.memory_mb)}M", f"-Xmx{meta.memory_mb}M",
                "-jar", str(jar.relative_to(server_dir)), "--assets", "Assets.zip",
                "--bind", f"0.0.0.0:{meta.port}"]

    # ---------- configuration (config.json) ----------

    def read_config(self, server_dir: Path) -> dict[str, str]:
        """Flattened config.json: {"Defaults.GameMode": "Adventure", ...}. Lists are not edited here."""
        data = self._load_config(server_dir)
        flat: dict[str, str] = {}

        def walk(prefix: str, value) -> None:
            if isinstance(value, dict):
                for k, v in value.items():
                    walk(f"{prefix}.{k}" if prefix else k, v)
            elif not isinstance(value, list):
                flat[prefix] = "" if value is None else json.dumps(value) if isinstance(value, bool) else str(value)

        walk("", data)
        return flat

    def write_config(self, server_dir: Path, updates: dict[str, str]) -> None:
        data = self._load_config(server_dir)
        for key, text in updates.items():
            node, parts = data, key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
                if not isinstance(node, dict):
                    raise UserError(tr("No se puede cambiar {key}", key=key))
            old = node.get(parts[-1])
            node[parts[-1]] = self._typed(text, old, key)
        (server_dir / CONFIG_FILE).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _typed(text: str, old, key: str):
        """The new value with the same type it had (number, yes/no or text)."""
        text = text.strip()
        if isinstance(old, bool):
            if text.lower() not in ("true", "false"):
                raise UserError(tr("{key} tiene que ser true o false", key=key))
            return text.lower() == "true"
        if isinstance(old, int):
            try:
                return int(text)
            except ValueError:
                raise UserError(tr("{key} tiene que ser un número entero", key=key)) from None
        if isinstance(old, float):
            try:
                return float(text.replace(",", "."))
            except ValueError:
                raise UserError(tr("{key} tiene que ser un número", key=key)) from None
        if old is None and text == "":
            return None
        return text

    @staticmethod
    def _load_config(server_dir: Path) -> dict:
        path = server_dir / CONFIG_FILE
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            raise UserError(tr("{file} no es un JSON válido; corrígelo a mano o restaura una copia", file=CONFIG_FILE)) from None
        return data if isinstance(data, dict) else {}

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        # The app's name is what players see (if the server already created its config.json).
        if (server_dir / CONFIG_FILE).exists() and "ServerName" in self._load_config(server_dir):
            self.write_config(server_dir, {"ServerName": meta.name})

    # ---------- mods (CurseForge) ----------

    def mod_target(self, meta: ServerMeta) -> ModTarget | None:
        # The Hytale server loads mods from the "mods" folder (.jar or .zip). Modrinth has no
        # Hytale mods: CurseForge only.
        return ModTarget(folder="mods", label="Mods", modrinth_type="", modrinth_loaders=[], cf_class="mods",
                         cf_game="hytale", match_version=False, sources=("curseforge",),
                         extensions=(".jar", ".zip"))
