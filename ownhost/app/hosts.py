"""Equipos (agentes) que gestiona la app, y arranque del agente local."""

import json
import os
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ownhost.agent import DEFAULT_PORT
from ownhost.paths import app_config_dir, default_data_dir
from ownhost.sysenv import clean_env

LOCAL_ADDRESSES = {"127.0.0.1", "localhost", "::1"}


@dataclass
class Host:
    name: str
    address: str
    token: str
    port: int = DEFAULT_PORT
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    @property
    def is_local(self) -> bool:
        return self.address in LOCAL_ADDRESSES


def _hosts_file() -> Path:
    return app_config_dir() / "hosts.json"


def load_hosts() -> list[Host]:
    path = _hosts_file()
    if not path.exists():
        return []
    return [Host(**h) for h in json.loads(path.read_text(encoding="utf-8"))]


def save_hosts(hosts: list[Host]) -> None:
    path = _hosts_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(h) for h in hosts], indent=2), encoding="utf-8")


def local_agent_config() -> dict | None:
    path = default_data_dir() / "agent.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def kill_local_agents(port: int) -> int:
    """Cierra el agente de este PC que escucha en `port` (para sustituirlo por una versión nueva).

    Solo ese proceso y su lanzador (el exe de un solo archivo arranca un proceso hijo), nunca otros.
    Se usa después de apagar los servidores, para no dejar ningún juego huérfano.
    """
    import psutil

    me = {os.getpid(), os.getppid()}
    victims = []
    for conn in psutil.net_connections(kind="tcp"):
        if conn.status == psutil.CONN_LISTEN and conn.laddr and conn.laddr.port == port and conn.pid:
            try:
                proc = psutil.Process(conn.pid)
            except psutil.Error:
                continue
            if proc.pid in me:
                continue
            victims.append(proc)
            parent = proc.parent()
            if parent and parent.pid not in me and "--agent" in (parent.cmdline() or []):
                victims.append(parent)
    for proc in victims:
        try:
            proc.kill()
        except psutil.Error:
            pass
    psutil.wait_procs(victims, timeout=10)
    return len(victims)


def launch_local_agent() -> None:
    """Arranca el agente de este PC en segundo plano, independiente de la app.

    Así los servidores siguen encendidos aunque cierres la ventana.
    """
    data_dir = default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    log = open(data_dir / "agent.log", "ab")
    if os.environ.get("APPIMAGE"):
        # Dentro de un AppImage: se relanza el propio .AppImage, porque la carpeta montada de esta
        # ventana desaparece al cerrarla y el agente se quedaría sin sus archivos.
        cmd = [os.environ["APPIMAGE"], "--agent"]
    elif getattr(sys, "frozen", False):
        # Empaquetado como .exe: el propio ejecutable hace de agente.
        cmd = [sys.executable, "--agent"]
    else:
        python = Path(sys.executable)
        # Con pythonw.exe no aparece ninguna ventana de consola en Windows.
        if sys.platform == "win32" and python.name.lower() == "python.exe":
            pythonw = python.with_name("pythonw.exe")
            if pythonw.exists():
                python = pythonw
        cmd = [str(python), "-m", "ownhost.agent"]
    # Sin esto, el agente reutilizaría la carpeta temporal de la app empaquetada (onefile), que se
    # borra al cerrar la ventana: el agente seguiría vivo pero sin sus archivos internos.
    # Además, entorno del sistema sin las bibliotecas de esta app (en Linux, /bin/sh fallaría).
    kwargs = {"env": clean_env({"PYINSTALLER_RESET_ENVIRONMENT": "1"})}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                     stderr=subprocess.STDOUT, close_fds=True, **kwargs)
