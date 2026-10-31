"""Discovery of agents on the local network via UDP broadcast.

The app sends a broadcast message to the agent's port (UDP) and each agent answers with its
name and port. The token is not shared: it must be entered to connect.
"""

import asyncio
import ipaddress
import json
import socket
import time

import psutil

from ownhost.net import lan_ip

QUERY = b"OWNHOST_DISCOVER_V1"
TIMEOUT = 1.5


class _Responder(asyncio.DatagramProtocol):
    def __init__(self, info: dict):
        self.info = info
        self.transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if data.strip() == QUERY and self.transport:
            self.transport.sendto(json.dumps(self.info).encode(), addr)


async def start_responder(bind: str, port: int, info: dict) -> asyncio.DatagramTransport | None:
    """Starts the responder inside the agent. If the UDP port is taken, it is skipped."""
    loop = asyncio.get_running_loop()
    try:
        transport, _ = await loop.create_datagram_endpoint(lambda: _Responder(info), local_addr=(bind, port))
        return transport
    except OSError:
        return None


def _broadcast_addresses() -> set[str]:
    """Broadcast address of each local network (192.168.1.255...), plus the generic one."""
    targets = {"255.255.255.255"}
    for addrs in psutil.net_if_addrs().values():
        for a in addrs:
            if a.family != socket.AF_INET or not a.netmask or a.address.startswith("127."):
                continue
            try:
                net = ipaddress.ip_network(f"{a.address}/{a.netmask}", strict=False)
            except ValueError:
                continue
            if net.prefixlen < 31 and not net.is_link_local:
                targets.add(str(net.broadcast_address))
    return targets


def discover(port: int, timeout: float = TIMEOUT) -> list[dict]:
    """Looks for agents on the local networks: [{name, hostname, address, port, version}]."""
    found: dict[tuple[str, int], dict] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.2)
        for target in _broadcast_addresses():
            try:
                s.sendto(QUERY, (target, port))
            except OSError:
                pass
        end = time.time() + timeout
        while time.time() < end:
            try:
                data, (address, _) = s.recvfrom(4096)
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                break
            try:
                info = json.loads(data)
            except ValueError:
                continue
            info["address"] = address
            # The same computer may answer through several networks (Wi-Fi, VPN, WSL...): one per computer,
            # keeping the main local network address if there is one.
            key = (info.get("hostname") or address, info.get("port", port))
            if key not in found or _same_lan(address):
                found[key] = info
    return sorted(found.values(), key=lambda i: i.get("name", "").lower())


def _same_lan(address: str) -> bool:
    return address.rsplit(".", 1)[0] == lan_ip().rsplit(".", 1)[0]
