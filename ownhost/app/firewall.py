"""Abrir los puertos de Ownhost en el cortafuegos de Linux (ufw o firewalld).

Cada distribución trae uno distinto y suele estar activo (CachyOS, Fedora, openSUSE...): sin abrir
los puertos, los demás equipos no pueden conectar con el agente ni los jugadores con los servidores.
Se usa `pkexec`, que pide la contraseña con la ventana normal del sistema.
"""

import shutil
import subprocess
import sys

from ownhost.sysenv import clean_env

# Agente (TCP + UDP para que lo encuentren), Minecraft Java, Bedrock/Geyser, Hytale y el mapa web (BlueMap).
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
    """'ufw', 'firewalld' o None (sin cortafuegos conocido activo, o no es Linux)."""
    if not sys.platform.startswith("linux"):
        return None
    if _active("ufw") and shutil.which("ufw"):
        return "ufw"
    if _active("firewalld") and shutil.which("firewall-cmd"):
        return "firewalld"
    return None


def commands(kind: str) -> str:
    """Comando para pegar en una terminal (también lo que se ejecuta con pkexec)."""
    if kind == "ufw":
        return " && ".join(f"ufw allow {rule}" for rule in UFW_RULES)
    ports = " ".join(f"--add-port={p}" for p in FIREWALLD_PORTS)
    return f"firewall-cmd --permanent {ports} && firewall-cmd --reload"


def open_ports(kind: str) -> tuple[bool, str]:
    """Abre los puertos pidiendo la contraseña con pkexec. Devuelve (ok, mensaje)."""
    if not shutil.which("pkexec"):
        return False, "No se encontró pkexec. Ejecuta en una terminal:\nsudo sh -c '" + commands(kind) + "'"
    try:
        out = subprocess.run(["pkexec", "sh", "-c", commands(kind)], capture_output=True, text=True,
                             timeout=300, env=clean_env())
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)
    if out.returncode == 0:
        return True, "Puertos abiertos en el cortafuegos."
    if out.returncode in (126, 127):
        return False, "Cancelado (no se introdujo la contraseña)."
    return False, (out.stderr or out.stdout).strip() or f"Error {out.returncode}"
