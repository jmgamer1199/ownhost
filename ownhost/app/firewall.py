"""Opens Ownhost's ports in the Linux firewall (ufw or firewalld), only for the home network and Tailscale.

Each distribution ships a different one and it is usually active (CachyOS, Fedora, openSUSE...): without
opening the ports, other computers cannot reach the agent and players cannot reach the servers.
The ports are allowed only from private addresses (the home network) and Tailscale's: from the internet
they stay closed even if a router forwarded them by mistake. The rules of older versions, open to any
address, are removed.
It uses `pkexec`, which asks for the password with the system's usual window.
"""

import shutil
import subprocess
import sys

from ownhost.i18n import tr
from ownhost.sysenv import clean_env

# Home networks (192.168.x.x, 10.x.x.x, 172.16-31.x.x), Tailscale (100.64.0.0/10 and its IPv6 fd7a:..., inside
# fc00::/7) and IPv6 link-local (fe80::/10).
SOURCES = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12", "100.64.0.0/10", "fc00::/7", "fe80::/10"]
# Agent (TCP for the app, UDP so it can be found), Minecraft Java, Bedrock/Geyser, Hytale, the web map
# (BlueMap), Bedrock's players' ports since NetherNet and its LAN discovery.
PORTS = [("8765", "tcp"), ("8765", "udp"), ("25565:25575", "tcp"), ("19132:19140", "udp"), ("19132:19140", "tcp"),
         ("5520:5530", "udp"), ("8100:8110", "tcp"), ("19200:19299", "udp"), ("7551", "udp")]
# Rules of older versions (and of the old install instructions), open to any address.
OLD_UFW_RULES = ["8765", "8765/tcp", "8765/udp", "25565/tcp", "25565:25575/tcp", "19132/udp", "19132:19140/udp",
                 "19132:19140/tcp", "5520/udp", "5520:5530/udp", "8100:8110/tcp", "19200:19299/udp", "7551/udp"]
OLD_FIREWALLD_PORTS = ["8765/tcp", "8765/udp", "25565-25575/tcp", "19132-19140/udp", "19132-19140/tcp",
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
        remove = "; ".join(f"ufw delete allow {rule} >/dev/null 2>&1" for rule in OLD_UFW_RULES)
        add = " && ".join(f"ufw allow from {source} to any port {port} proto {proto} comment Ownhost >/dev/null"
                          for source in SOURCES for port, proto in PORTS)
        return f"{remove}; {add}"
    remove = " ".join(f"--remove-port={p}" for p in OLD_FIREWALLD_PORTS)
    rules = " ".join(
        f"--add-rich-rule='rule family=\"{'ipv6' if ':' in source else 'ipv4'}\" source address=\"{source}\" "
        f"port port=\"{port.replace(':', '-')}\" protocol=\"{proto}\" accept'"
        for source in SOURCES for port, proto in PORTS)
    return (f"firewall-cmd --permanent {remove} >/dev/null 2>&1; "
            f"firewall-cmd --permanent {rules} >/dev/null && firewall-cmd --reload >/dev/null")


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
        return True, tr("Puertos permitidos solo para tu red de casa y Tailscale.")
    if out.returncode in (126, 127):
        return False, tr("Cancelado (no se introdujo la contraseña).")
    return False, (out.stderr or out.stdout).strip() or tr("Error {code}", code=out.returncode)
