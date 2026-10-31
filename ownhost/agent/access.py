"""Access for friends: each with their own code, a permission level and the servers they can see.

The computer's owner uses the agent token (or comes in through Tailscale from their account) and can do
everything. Friends' codes are not stored as is, only their hash: if someone copies the agent's folder
they cannot log in with them.
"""

import hashlib
import json
import secrets
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ownhost.agent.errors import UserError
from ownhost.i18n import tr

# Levels: each includes the previous ones. BACKUP_ONLY sees nothing: it can only send backups.
BACKUP_ONLY, PLAY, MODERATE, MANAGE, OWNER = 0, 1, 2, 3, 9
ROLES = {
    "backup": BACKUP_ONLY,  # another computer of yours that stores its backups here
    "play": PLAY,          # see the status, start, stop and restart
    "moderate": MODERATE,  # + console, players (operator, whitelist, bans) and backups
    "manage": MANAGE,      # + settings, properties, mods, updating, restoring backups and importing worlds
}


@dataclass
class Guest:
    id: str
    name: str
    role: str
    servers: list[str] | None  # None = all, including those created later
    token_hash: str
    created: float = field(default_factory=time.time)

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "role": self.role, "servers": self.servers,
                "created": self.created}


@dataclass
class Principal:
    """Who makes the request."""
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
            raise UserError(tr("Ponle un nombre al acceso (p. ej. el de tu amigo)"))
        if role not in ROLES:
            raise UserError(tr("Permiso desconocido: {role}", role=role))
        if servers is not None and not servers:
            raise UserError(tr("Elige al menos un servidor"))
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
                raise UserError(tr("Ese acceso ya no existe"))
            self._save()

    def forget_server(self, sid: str) -> None:
        """When a server is deleted it is removed from the accesses (an access without servers is useless)."""
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
