"""Computers (agents) managed by the app, and starting the local agent."""

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
    """Closes this PC's agent listening on `port` (to replace it with a new version).

    Only that process and its launcher (the one-file exe starts a child process), never others.
    Used after stopping the servers, so no game is left orphaned.
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
    """Starts this PC's agent in the background, independent of the app.

    That way the servers keep running even if you close the window.
    """
    data_dir = default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    log = open(data_dir / "agent.log", "ab")
    if os.environ.get("APPIMAGE"):
        # Inside an AppImage: relaunch the .AppImage itself, because this window's mounted folder
        # disappears when it closes and the agent would be left without its files.
        cmd = [os.environ["APPIMAGE"], "--agent"]
    elif getattr(sys, "frozen", False):
        # Packaged as an .exe: the executable itself acts as the agent.
        cmd = [sys.executable, "--agent"]
    else:
        python = Path(sys.executable)
        # With pythonw.exe no console window appears on Windows.
        if sys.platform == "win32" and python.name.lower() == "python.exe":
            pythonw = python.with_name("pythonw.exe")
            if pythonw.exists():
                python = pythonw
        cmd = [str(python), "-m", "ownhost.agent"]
    # Without this, the agent would reuse the packaged (onefile) app's temp folder, which is
    # deleted when the window closes: the agent would stay alive but without its internal files.
    # Also, the system environment without this app's libraries (on Linux, /bin/sh would fail).
    kwargs = {"env": clean_env({"PYINSTALLER_RESET_ENVIRONMENT": "1"})}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log,
                     stderr=subprocess.STDOUT, close_fds=True, **kwargs)
