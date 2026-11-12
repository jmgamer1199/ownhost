"""Wake-on-LAN: switch on a computer of the local network by sending it its "magic packet".

It only works inside the home network (broadcast packets don't cross routers or Tailscale), and the computer
needs Wake-on-LAN turned on in its BIOS/UEFI and in its network card.
"""

import ipaddress
import re
import socket

import psutil

PORTS = (9, 7)


def clean_mac(mac: str) -> bytes:
    """The 6 bytes of a MAC address ("aa:bb:cc:dd:ee:ff", with - or :), or ValueError."""
    text = re.sub(r"[:\-.]", "", mac.strip().lower())
    if not re.fullmatch(r"[0-9a-f]{12}", text):
        raise ValueError(f"Not a MAC address: {mac!r}")
    return bytes.fromhex(text)


def magic_packet(mac: str) -> bytes:
    return b"\xff" * 6 + clean_mac(mac) * 16


def broadcast_targets() -> list[tuple[str, str]]:
    """[(this computer's address on a network, that network's broadcast address)] for each IPv4 network."""
    found = []
    for addrs in psutil.net_if_addrs().values():
        for a in addrs:
            if a.family != socket.AF_INET or a.address.startswith(("127.", "169.254.")) or not a.netmask:
                continue
            try:  # from the netmask: psutil gives no broadcast address on Windows
                broadcast = str(ipaddress.ip_network(f"{a.address}/{a.netmask}", strict=False).broadcast_address)
            except ValueError:
                continue
            found.append((a.address, broadcast))
    return found


def send(mac: str) -> int:
    """Sends the magic packet through every network of this computer. Returns how many packets went out."""
    packet = magic_packet(mac)
    sent = 0
    for source, broadcast in [*broadcast_targets(), ("0.0.0.0", "255.255.255.255")]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.bind((source, 0))  # out of that network's card
                for port in PORTS:
                    s.sendto(packet, (broadcast, port))
                    sent += 1
        except OSError:
            continue
    return sent
