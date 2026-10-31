import re
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ownhost.agent.downloads import Log
from ownhost.agent.models import ServerMeta
from ownhost.agent.mods import ModTarget
from ownhost.sysenv import clean_env

# Evita que se abra una ventana de consola por cada proceso en Windows.
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
    # Línea de la consola que indica que el servidor ya acepta jugadores.
    ready_pattern: re.Pattern | None = None
    properties_file: str | None = None
    backup_pre_commands: list[str] = []
    backup_post_commands: list[str] = []
    # Juegos cuyo servidor necesita iniciar sesión con una cuenta (código en el navegador).
    device_auth = False
    # Bedrock trae su propio ejecutable: no necesita Java.
    uses_java = True
    # Carpetas del mundo dentro del servidor (para importar un mundo); None si no se admite.
    supports_world_import = False

    def world_dirs(self, server_dir: Path) -> list[str]:
        """Carpetas que forman el mundo actual (la primera es la principal)."""
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
            "flavors": [f.__dict__ for f in self.flavors],
        }

    @abstractmethod
    def versions(self, flavor: str) -> list[str]:
        """Versiones disponibles, la más reciente primero."""

    @abstractmethod
    def java_major(self, flavor: str, version: str) -> int: ...

    @abstractmethod
    def install(self, ctx: InstallContext) -> None:
        """Descarga/actualiza los archivos del servidor. Puede ajustar ctx.meta (p. ej. build)."""

    @abstractmethod
    def command(self, meta: ServerMeta, server_dir: Path, java: Path) -> list[str]: ...

    def read_config(self, server_dir: Path) -> dict[str, str]:
        """Ajustes del archivo de configuración del juego, como texto (pestaña «Propiedades»)."""
        return read_properties(server_dir / self.properties_file)

    def write_config(self, server_dir: Path, updates: dict[str, str]) -> None:
        write_properties(server_dir / self.properties_file, updates)

    def apply_settings(self, meta: ServerMeta, server_dir: Path) -> None:
        """Aplica nombre/puerto a los archivos de configuración del juego."""

    def mod_target(self, meta: ServerMeta) -> ModTarget | None:
        """Tipo de mods/plugins que admite el servidor, o None si no admite."""
        return None

    def env(self, meta: ServerMeta, server_dir: Path) -> dict[str, str] | None:
        """Variables de entorno extra para el proceso del servidor."""
        return None

    def extra_ports(self, meta: ServerMeta) -> list[int]:
        """Puertos adicionales que ocupa el servidor (además de meta.port)."""
        return []

    def available_update(self, meta: ServerMeta, tools_dir: Path) -> str | None:
        """Si hay una versión más nueva *compatible* (sin romper mundos ni mods), su descripción.

        Por defecto no se comprueba nada. Para Minecraft Java solo se actualizan las builds de la
        misma versión; cambiar de versión de Minecraft sigue siendo manual.
        """
        return None


def run_logged(cmd: list[str], cwd: Path, log: Log) -> None:
    """Ejecuta un comando volcando su salida al log; lanza error si falla."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW, env=clean_env(),
    )
    assert proc.stdout
    for line in proc.stdout:
        log(line.rstrip())
    if proc.wait() != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} terminó con código {proc.returncode}")


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
    """Actualiza claves manteniendo el orden y los comentarios del archivo."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    pending = dict(updates)
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in pending:
                lines[i] = f"{key}={pending.pop(key)}"
    lines += [f"{k}={v}" for k, v in pending.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
