"""Start the agent when the computer starts, if the user wants: each system in its own way.

- Windows: a value in the user's "Run" key (no administrator needed): it starts when the user signs in
  (when the PC signs in by itself, that is as soon as it is switched on).
- Linux with a desktop: an XDG autostart entry in the user's folder (starts when the user signs in).
- Linux server installed with `install-agent-service.sh`: the `ownhost-agent` systemd service, which already
  starts with the computer, even if nobody signs in. It belongs to root, so it is only reported here.
"""

import os
import subprocess
import sys
from pathlib import Path

from ownhost.sysenv import clean_env

ENTRY = "Ownhost agent"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
SERVICE = "ownhost-agent"


def agent_command() -> list[str]:
    """The command that starts this installation's agent."""
    if os.environ.get("APPIMAGE"):
        # Inside an AppImage: the .AppImage itself, because this window's mounted folder disappears when it closes.
        return [os.environ["APPIMAGE"], "--agent"]
    if getattr(sys, "frozen", False):
        return [sys.executable, "--agent"]
    python = Path(sys.executable)
    # With pythonw.exe no console window appears on Windows.
    if sys.platform == "win32" and python.name.lower() == "python.exe":
        pythonw = python.with_name("pythonw.exe")
        if pythonw.exists():
            python = pythonw
    return [str(python), "-m", "ownhost.agent"]


def _desktop_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "autostart" / "ownhost-agent.desktop"


def _desktop_quote(arg: str) -> str:
    """One argument of an `Exec=` line (the Desktop Entry rules: double quotes, escaped specials)."""
    if arg and not any(c in arg for c in ' \t\n"\'\\><~|&;$*?#()`'):
        return arg
    return '"' + "".join("\\" + c if c in '"`$\\' else c for c in arg).replace("%", "%%") + '"'


def _service_enabled() -> bool:
    """Whether the systemd service installed by `install-agent-service.sh` starts with the computer."""
    try:
        out = subprocess.run(["systemctl", "is-enabled", SERVICE], capture_output=True, text=True, timeout=5,
                             env=clean_env())
        return out.stdout.strip() == "enabled"
    except (OSError, subprocess.SubprocessError):
        return False


def status() -> dict:
    """{"kind": "registry" | "desktop" | "service" | "none", "enabled": bool, "changeable": bool}"""
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                winreg.QueryValueEx(key, ENTRY)
            enabled = True
        except OSError:
            enabled = False
        return {"kind": "registry", "enabled": enabled, "changeable": True}
    if sys.platform.startswith("linux"):
        if _service_enabled():
            return {"kind": "service", "enabled": True, "changeable": False}
        return {"kind": "desktop", "enabled": _desktop_file().exists(), "changeable": True}
    return {"kind": "none", "enabled": False, "changeable": False}


def set_enabled(enabled: bool) -> dict:
    """Turns the autostart on or off (only where the user can change it). Returns the new status."""
    now = status()
    if not now["changeable"]:
        raise RuntimeError("This computer's autostart can't be changed from here")
    if sys.platform == "win32":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            if enabled:
                winreg.SetValueEx(key, ENTRY, 0, winreg.REG_SZ, subprocess.list2cmdline(agent_command()))
            else:
                try:
                    winreg.DeleteValue(key, ENTRY)
                except OSError:
                    pass
    else:
        path = _desktop_file()
        if enabled:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "[Desktop Entry]\nType=Application\nName=" + ENTRY + "\n"
                "Exec=" + " ".join(_desktop_quote(a) for a in agent_command()) + "\n"
                "Terminal=false\nNoDisplay=true\nX-GNOME-Autostart-enabled=true\n", encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
    return status()
