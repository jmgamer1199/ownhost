"""Network addresses: local network and Tailscale IPs."""

import ipaddress
import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import psutil

from ownhost.sysenv import clean_env

TAILSCALE_NET = ipaddress.ip_network("100.64.0.0/10")
# Systems that can run the agent; rules out phones, VR headsets, etc.
COMPUTER_OS = {"windows", "linux", "macos", "freebsd", "openbsd"}
NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def lan_ip() -> str:
    """IP of this computer on the local network (the one players at home should use)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def is_reachable(address: str) -> bool:
    """Does the computer answer ping? (to tell "off" from "firewall")."""
    count = ["-n", "1", "-w", "1500"] if sys.platform == "win32" else ["-c", "1", "-W", "2"]
    try:
        out = subprocess.run(["ping", *count, address], capture_output=True, timeout=5,
                             creationflags=NO_WINDOW, env=clean_env())
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def own_ips() -> set[str]:
    """All IPv4 addresses of this computer (so it does not offer itself as a remote computer)."""
    return {a.address for addrs in psutil.net_if_addrs().values() for a in addrs if a.family == socket.AF_INET}


def tailscale_ip() -> str | None:
    """Tailscale IP (100.x.y.z) of this computer, or None if Tailscale is not active."""
    candidates = []
    for name, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if a.family == socket.AF_INET and ipaddress.ip_address(a.address) in TAILSCALE_NET:
                candidates.append((name, a.address))
    # Some carriers use the same range (CGNAT): prefer the interface named "Tailscale".
    candidates.sort(key=lambda c: "tailscale" not in c[0].lower())
    stats = psutil.net_if_stats()
    for name, address in candidates:
        if stats.get(name) and stats[name].isup:
            return address
    return None


def _tailscale_cli() -> str | None:
    found = shutil.which("tailscale")
    if found:
        return found
    for path in (r"C:\Program Files\Tailscale\tailscale.exe",
                 "/Applications/Tailscale.app/Contents/MacOS/Tailscale"):
        if Path(path).exists():
            return path
    return None


def _tailscale_json(*args: str) -> dict | None:
    cli = _tailscale_cli()
    if not cli:
        return None
    try:
        # --json goes right after the subcommand: after an argument (the whois IP) options are no longer read.
        out = subprocess.run([cli, args[0], "--json", *args[1:]], capture_output=True, text=True, timeout=4,
                             encoding="utf-8", creationflags=NO_WINDOW, env=clean_env())
        return json.loads(out.stdout) if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


class TailscaleOwnerCheck:
    """Does a connection come from a Tailscale device of the same account as this computer?

    Tailscale authenticates every device, so someone with your account is you: the agent can let them
    in without a token. Results are cached for a few minutes so it does not ask on every request.
    """

    TTL = 300

    def __init__(self):
        self._owner: tuple[float, int | None] = (0.0, None)
        self._cache: dict[str, tuple[float, bool]] = {}

    def _owner_id(self) -> int | None:
        stamp, owner = self._owner
        if time.time() - stamp > 60:
            status = _tailscale_json("status") or {}
            owner = (status.get("Self") or {}).get("UserID") or None
            self._owner = (time.time(), owner)
        return owner

    def is_owner(self, remote_ip: str, local_ip: str | None) -> bool:
        remote_ip = remote_ip.removeprefix("::ffff:")
        try:
            if ipaddress.ip_address(remote_ip) not in TAILSCALE_NET:
                return False
        except ValueError:
            return False
        # The connection must have arrived through this computer's Tailscale interface.
        if local_ip is not None and local_ip.removeprefix("::ffff:") != tailscale_ip():
            return False
        hit = self._cache.get(remote_ip)
        if hit and time.time() - hit[0] < self.TTL:
            return hit[1]
        owner = self._owner_id()
        who = _tailscale_json("whois", remote_ip) or {}
        result = bool(owner) and (who.get("UserProfile") or {}).get("ID") == owner
        self._cache[remote_ip] = (time.time(), result)
        return result


def tailscale_peers() -> list[dict]:
    """Other computers on your Tailscale network: [{name, ip, online, os}], online ones first."""
    cli = _tailscale_cli()
    if not cli:
        return []
    try:
        out = subprocess.run([cli, "status", "--json"], capture_output=True, text=True, timeout=5,
                             encoding="utf-8", creationflags=NO_WINDOW, env=clean_env())
        data = json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    peers = []
    for peer in (data.get("Peer") or {}).values():
        ipv4 = next((ip for ip in peer.get("TailscaleIPs") or [] if ":" not in ip), None)
        if not ipv4 or (peer.get("OS") or "").lower() not in COMPUTER_OS:
            continue
        peers.append({"name": peer.get("HostName") or ipv4, "ip": ipv4, "online": bool(peer.get("Online")),
                      "os": peer.get("OS", "")})
    peers.sort(key=lambda p: (not p["online"], p["name"].lower()))
    return peers
