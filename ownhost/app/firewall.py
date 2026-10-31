"""Opens Ownhost's ports in the Linux firewall (ufw or firewalld).

Each distribution ships a different one and it is usually active (CachyOS, Fedora, openSUSE...): without
opening the ports, other computers cannot reach the agent and players cannot reach the servers.
It uses `pkexec`, which asks for the password with the system's usual window.
"""

import shutil
import subprocess
import sys

from ownhost.i18n import tr
from ownhost.sysenv import clean_env

# Agent (TCP + UDP so it can be found), Minecraft Java, Bedrock/Geyser, Hytale and the web map (BlueMap).
UFW_RULES = ["8765", "25565:25575/tcp", "19132:19140/udp", "19132:19140/tcp", "5520:5530/udp", "8100:8110/tcp"]
FIREWALLD_PORTS = ["8765/tcp", "8765/udp", "25565-25575/tcp", "19132-19140/udp", "19132-19140/tcp",
                   "5520-5530/udp", "8100-8110/tcp"]


def _active(service: str) -> bool:
    try:
        out = subprocess.run(["systemctl", "is-active", service], capture_output=True, text=True,
                             timeout=5, env=clean_env())
        return out.stdout.strip() == "active"
    except (OSError, subprocess.SubprocessError):
        return False


def detect() -> str | None:
    """'ufw', 'firewalld' or None (no known firewall active, or not Linux)."""
    if not sys.platform.startswith("linux"):
        return None
    if _active("ufw") and shutil.which("ufw"):
        return "ufw"
    if _active("firewalld") and shutil.which("firewall-cmd"):
        return "firewalld"
    return None


def commands(kind: str) -> str:
    """Command to paste into a terminal (also what runs with pkexec)."""
    if kind == "ufw":
        return " && ".join(f"ufw allow {rule}" for rule in UFW_RULES)
    ports = " ".join(f"--add-port={p}" for p in FIREWALLD_PORTS)
    return f"firewall-cmd --permanent {ports} && firewall-cmd --reload"


def open_ports(kind: str) -> tuple[bool, str]:
    """Opens the ports, asking for the password with pkexec. Returns (ok, message)."""
    if not shutil.which("pkexec"):
        return False, tr("No se encontró pkexec. Ejecuta en una terminal:") + "\nsudo sh -c '" + commands(kind) + "'"
    try:
        out = subprocess.run(["pkexec", "sh", "-c", commands(kind)], capture_output=True, text=True,
                             timeout=300, env=clean_env())
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if out.returncode == 0:
        return True, tr("Puertos abiertos en el cortafuegos.")
    if out.returncode in (126, 127):
        return False, tr("Cancelado (no se introdujo la contraseña).")
    return False, (out.stderr or out.stdout).strip() or tr("Error {code}", code=out.returncode)
