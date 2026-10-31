"""Accesos para amigos: cada uno con su código, un nivel de permisos y los servidores que puede ver.

El dueño del equipo usa el token del agente (o entra por Tailscale desde su cuenta) y puede hacerlo todo.
Los códigos de los amigos no se guardan tal cual, solo su hash: si alguien copia la carpeta del agente
no puede entrar con ellos.
"""

import hashlib
import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ownhost.agent.errors import UserError

# Niveles: cada uno incluye lo de los anteriores. BACKUP_ONLY no ve nada: solo puede enviar copias.
BACKUP_ONLY, PLAY, MODERATE, MANAGE, OWNER = 0, 1, 2, 3, 9
ROLES = {
    "backup": BACKUP_ONLY,  # otro equipo tuyo que guarda aquí sus copias de seguridad
    "play": PLAY,          # ver el estado, encender, apagar y reiniciar
    "moderate": MODERATE,  # + consola, jugadores (operador, lista blanca, baneos) y copias
    "manage": MANAGE,      # + ajustes, propiedades, mods, actualizar, restaurar copias e importar mundos
}


@dataclass
class Guest:
    id: str
    name: str
    role: str
    servers: list[str] | None  # None = todos, también los que se creen después
    token_hash: str
    created: float = field(default_factory=time.time)

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "role": self.role, "servers": self.servers,
                "created": self.created}


@dataclass
class Principal:
    """Quién hace la petición."""
    level: int
    name: str = ""
    role: str = "owner"
    servers: list[str] | None = None

    @property
    def owner(self) -> bool:
        return self.level >= OWNER

    def can_see(self, sid: str) -> bool:
        return self.level > BACKUP_ONLY and (self.servers is None or sid in self.servers)

    def describe(self) -> dict:
        return {"role": self.role, "level": self.level, "name": self.name}


OWNER_PRINCIPAL = Principal(OWNER)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class GuestStore:
    def __init__(self, data_dir: Path):
        self.path = data_dir / "guests.json"
        self.lock = threading.Lock()
        self.guests: list[Guest] = []
        if self.path.exists():
            self.guests = [Guest(**g) for g in json.loads(self.path.read_text(encoding="utf-8"))]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps([asdict(g) for g in self.guests], indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def public(self) -> list[dict]:
        return [g.public() for g in self.guests]

    def create(self, name: str, role: str, servers: list[str] | None) -> tuple[Guest, str]:
        name = name.strip()
        if not name:
            raise UserError("Ponle un nombre al acceso (p. ej. el de tu amigo)")
        if role not in ROLES:
            raise UserError(f"Permiso desconocido: {role}")
        if servers is not None and not servers:
            raise UserError("Elige al menos un servidor")
        token = "oh-" + secrets.token_urlsafe(18)
        guest = Guest(id=secrets.token_hex(4), name=name[:60], role=role, servers=servers, token_hash=_hash(token))
        with self.lock:
            self.guests.append(guest)
            self._save()
        return guest, token

    def delete(self, guest_id: str) -> None:
        with self.lock:
            before = len(self.guests)
            self.guests = [g for g in self.guests if g.id != guest_id]
            if len(self.guests) == before:
                raise UserError("Ese acceso ya no existe")
            self._save()

    def forget_server(self, sid: str) -> None:
        """Al borrar un servidor se quita de los accesos (un acceso sin servidores no sirve de nada)."""
        with self.lock:
            changed = False
            for g in self.guests:
                if g.servers and sid in g.servers:
                    g.servers.remove(sid)
                    changed = True
            if changed:
                self._save()

    def find(self, token: str) -> Principal | None:
        if not token:
            return None
        digest = _hash(token)
        for g in self.guests:
            if secrets.compare_digest(digest, g.token_hash):
                return Principal(ROLES[g.role], g.name, g.role, g.servers)
        return None
