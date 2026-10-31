import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ownhost.agent.downloads import Log
from ownhost.agent.models import ServerMeta
from ownhost.agent.mods import ModTarget
from ownhost.i18n import tr
from ownhost.sysenv import clean_env

# Prevents a console window from opening for every process on Windows.
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


@dataclass
class Flavor:
    id: str
    name: str


@dataclass
class InstallContext:
    meta: ServerMeta
    server_dir: Path
    tools_dir: Path
    log: Log
    first_install: bool
    java: Path


class GameAdapter(ABC):
    id: str
    name: str
    default_port: int
    flavors: list[Flavor]
    needs_eula: bool = False
    stop_command = "stop"
    # Console line that tells the server now accepts players.
    ready_pattern: re.Pattern | None = None
    properties_file: str | None = None
    backup_pre_commands: list[str] = []
    backup_post_commands: list[str] = []
    # Games whose server needs to log in with an account (code in the browser).
    device_auth = False
    # Bedrock ships its own executable: it does not need Java.
    uses_java = True
    # World folders inside the server (to import a world); None if not supported.
    supports_world_import = False

    def world_dirs(self, server_dir: Path) -> list[str]:
        """Folders that make up the current world (the first one is the main one)."""
        return []
    auth_login_command: str | None = None
    auth_persist_command: str | None = None

    def describe(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "default_port": self.default_port,
            "needs_eula": self.needs_eula,
            "device_auth": self.device_auth,
            # Flavor names are translated here, not in the class table (that is built at import time).
            "flavors": [{**f.__dict__, "name": tr(f.name)} for f in self.flavors],
        }

    @abstractmethod
    def versions(self, flavor: str) -> list[str]:
        """Available versions, newest first."""

    @abstractmethod
    def java_major(self, flavor: str, version: str) -> int: ...

    @abstractmethod
    def install(self, ctx: InstallContext) -> None:
        """Downloads/updates the server files. May adjust ctx.meta (e.g. build)."""

    @abstractmethod
    def command(self, meta: ServerMeta, server_dir: Path, java: Path) -> list[str]: ...

    def read_config(self, server_dir: Path) -> dict[str, str]:
        """Settings of the game's configuration file, as text ("Properties" tab)."""
        return read_properties(server_dir / self.properties_file)

    def write_config(self, server_dir: Path, updates: dict[str, str]) -> None:
        write_properties(server_dir / self.properties_file, updates)

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        """Applies name/port to the game's configuration files."""

    def mod_target(self, meta: ServerMeta) -> ModTarget | None:
        """Kind of mods/plugins the server supports, or None if it supports none."""
        return None

    def env(self, meta: ServerMeta, server_dir: Path) -> dict[str, str] | None:
        """Extra environment variables for the server process."""
        return None

    def extra_ports(self, meta: ServerMeta) -> list[int]:
        """Additional ports the server uses (besides meta.port)."""
        return []

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        """If there is a newer *compatible* version (not breaking worlds or mods), its description.

        Nothing is checked by default. For Minecraft Java only builds of the same version are
        updated; changing the Minecraft version is still manual.
        """
        return None


def run_logged(cmd: list[str], cwd: Path, log: Log) -> None:
    """Runs a command, writing its output to the log; raises an error if it fails."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, env=clean_env(),
    )
    assert proc.stdout
    for line in proc.stdout:
        log(line.rstrip())
    if proc.wait() != 0:
        raise RuntimeError(tr("{program} terminó con código {code}", program=Path(cmd[0]).name, code=proc.returncode))


def read_properties(path: Path) -> dict[str, str]:
    props: dict[str, str] = {}
    if not path.exists():
        return props
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value
    return props


def write_properties(path: Path, updates: dict[str, str]) -> None:
    """Updates keys keeping the order and comments of the file."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    pending = dict(updates)
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in pending:
                lines[i] = f"{key}={pending.pop(key)}"
    lines += [f"{k}={v}" for k, v in pending.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
