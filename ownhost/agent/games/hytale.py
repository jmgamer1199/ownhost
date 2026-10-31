"""Servidor dedicado de Hytale.

Los archivos se obtienen con el Hytale Downloader oficial, que pide iniciar
sesión con tu cuenta de Hytale la primera vez (muestra una URL y un código).
El servidor también necesita autenticarse tras el primer arranque con
`/auth login device`; el agente lo lanza solo y la app muestra la ventana de
inicio de sesión (ver device_auth.py).
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
    # config.json se edita en la pestaña «Propiedades» (el servidor lo crea al primer arranque)
    properties_file = CONFIG_FILE

    def versions(self, flavor: str) -> list[str]:
        # El downloader siempre descarga la última versión del canal elegido.
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
            raise RuntimeError("No se encontró el ejecutable del Hytale Downloader para este sistema")
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
        # Preferimos el binario de nuestra arquitectura si hay varios.
        candidates.sort(key=lambda p: ("arm64" in p.name.lower() or "aarch64" in p.name.lower()) != arm)
        return candidates[0] if candidates else None

    @staticmethod
    def _patchline(meta: ServerMeta) -> list[str]:
        return ["-patchline", "pre-release"] if meta.flavor == "pre-release" else []

    def _latest_version(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        """Versión que descargaría ahora el downloader (sin descargar nada)."""
        exe = self._find_downloader(tools_dir / "hytale-downloader")
        if not exe:
            return None
        # Si las credenciales del downloader han caducado pediría iniciar sesión: con el límite de
        # tiempo no se queda colgado y el servidor arranca con la versión que tiene.
        out = subprocess.run([str(exe), "-print-version", *self._patchline(meta)], cwd=exe.parent,
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
                             stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, env=clean_env())
        if out.returncode != 0:
            raise RuntimeError(f"el downloader terminó con código {out.returncode}")
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
        ctx.log("Ejecutando Hytale Downloader. Si es la primera vez, la app mostrará una ventana "
                "para iniciar sesión con tu cuenta de Hytale.")
        cmd = [str(exe), "-download-path", str(game_zip), *self._patchline(ctx.meta)]
        # Se ejecuta en la carpeta de herramientas para que las credenciales
        # del downloader se reutilicen entre servidores.
        run_logged(cmd, exe.parent, ctx.log)
        ctx.log("Extrayendo archivos del juego...")
        extract(game_zip, ctx.server_dir)
        game_zip.unlink()
        # Se apunta la versión para saber luego si hay una más nueva.
        try:
            ctx.meta.build = self._latest_version(ctx.meta, ctx.tools_dir)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            ctx.meta.build = None
        if ctx.first_install:
            ctx.log("Instalado. Al encenderlo por primera vez se pedirá iniciar sesión para el servidor.")

    def command(self, meta: ServerMeta, server_dir: Path, java: Path) -> list[str]:
        jar = next(server_dir.rglob("HytaleServer.jar"), None)
        if not jar:
            raise RuntimeError("No se encuentra HytaleServer.jar; prueba a actualizar el servidor")
        return [str(java), f"-Xms{min(2048, meta.memory_mb)}M", f"-Xmx{meta.memory_mb}M",
                "-jar", str(jar.relative_to(server_dir)), "--assets", "Assets.zip",
                "--bind", f"0.0.0.0:{meta.port}"]

    # ---------- configuración (config.json) ----------

    def read_config(self, server_dir: Path) -> dict[str, str]:
        """config.json aplanado: {"Defaults.GameMode": "Adventure", ...}. Las listas no se editan aquí."""
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
                    raise UserError(f"No se puede cambiar {key}")
            old = node.get(parts[-1])
            node[parts[-1]] = self._typed(text, old, key)
        (server_dir / CONFIG_FILE).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _typed(text: str, old, key: str):
        """El valor nuevo con el mismo tipo que tenía (número, sí/no o texto)."""
        text = text.strip()
        if isinstance(old, bool):
            if text.lower() not in ("true", "false"):
                raise UserError(f"{key} tiene que ser true o false")
            return text.lower() == "true"
        if isinstance(old, int):
            try:
                return int(text)
            except ValueError:
                raise UserError(f"{key} tiene que ser un número entero") from None
        if isinstance(old, float):
            try:
                return float(text.replace(",", "."))
            except ValueError:
                raise UserError(f"{key} tiene que ser un número") from None
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
            raise UserError(f"{CONFIG_FILE} no es un JSON válido; corrígelo a mano o restaura una copia") from None
        return data if isinstance(data, dict) else {}

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        # El nombre de la app es el que ven los jugadores (si el servidor ya creó su config.json).
        if (server_dir / CONFIG_FILE).exists() and "ServerName" in self._load_config(server_dir):
            self.write_config(server_dir, {"ServerName": meta.name})

    # ---------- mods (CurseForge) ----------

    def mod_target(self, meta: ServerMeta) -> ModTarget | None:
        # El servidor de Hytale carga los mods de la carpeta «mods» (.jar o .zip). En Modrinth no hay
        # mods de Hytale: solo CurseForge.
        return ModTarget(folder="mods", label="Mods", modrinth_type="", modrinth_loaders=[], cf_class="mods",
                         cf_game="hytale", match_version=False, sources=("curseforge",),
                         extensions=(".jar", ".zip"))
