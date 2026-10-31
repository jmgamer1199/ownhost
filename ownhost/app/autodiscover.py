"""Busca otros equipos con Ownhost en la red local y en Tailscale.

- Red local: difusión UDP (ver ownhost.discovery).
- Tailscale: no hay difusión, así que se pregunta a cada dispositivo conectado por /api/hello.

Si un equipo de Tailscale deja entrar sin token (es de la misma cuenta que este), se marca como
«de confianza» y la app lo añade sola. El resto se muestra para conectarlo con su token.
"""

from concurrent.futures import ThreadPoolExecutor

import httpx

from ownhost.agent import DEFAULT_PORT
from ownhost.discovery import discover
from ownhost.net import own_ips, tailscale_peers


def _hello(address: str, port: int) -> dict | None:
    try:
        r = httpx.get(f"http://{address}:{port}/api/hello", timeout=2)
        return r.json() if r.status_code == 200 else None
    except (httpx.HTTPError, ValueError):
        return None


def _trusted(address: str, port: int) -> bool:
    """¿Nos deja entrar sin token? (dispositivo de Tailscale de la misma cuenta)."""
    try:
        r = httpx.get(f"http://{address}:{port}/api/info", headers={"Authorization": "Bearer "}, timeout=4)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def scan(port: int = DEFAULT_PORT) -> list[dict]:
    """[{name, hostname, port, lan, tailscale, trusted}] de los equipos encontrados (sin contar este)."""
    own = own_ips()
    found: dict[str, dict] = {}
    for r in discover(port):
        if r["address"] in own:
            continue
        key = r.get("hostname") or r["address"]
        found[key] = {"name": r.get("name") or key, "hostname": key, "port": r.get("port", port),
                      "lan": r["address"], "tailscale": None, "trusted": False}

    peers = [p for p in tailscale_peers() if p["online"] and p["ip"] not in own]
    with ThreadPoolExecutor(max_workers=16) as pool:
        hellos = list(pool.map(lambda p: (p, _hello(p["ip"], port)), peers))
    for peer, hello in hellos:
        if not hello:
            continue
        key = hello.get("hostname") or peer["name"]
        entry = found.setdefault(key, {"name": hello.get("name") or key, "hostname": key,
                                       "port": hello.get("port", port), "lan": None, "trusted": False})
        entry["tailscale"] = peer["ip"]

    with ThreadPoolExecutor(max_workers=16) as pool:
        checks = [(e, pool.submit(_trusted, e["tailscale"], e["port"])) for e in found.values() if e["tailscale"]]
        for entry, future in checks:
            entry["trusted"] = future.result()
    return sorted(found.values(), key=lambda e: e["name"].lower())
