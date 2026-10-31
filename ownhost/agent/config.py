import json
import secrets
import socket
from dataclasses import asdict, dataclass
from pathlib import Path

from ownhost.agent import DEFAULT_PORT


@dataclass
class AgentConfig:
    name: str
    token: str
    port: int = DEFAULT_PORT
    bind: str = "0.0.0.0"
    # Dispositivos de Tailscale de la misma cuenta pueden gestionar este equipo sin token.
    trust_tailscale: bool = True
    # Language of the console lines and notices ("es" or "en"); None = the system's.
    language: str | None = None

    @staticmethod
    def path(data_dir: Path) -> Path:
        return data_dir / "agent.json"

    @classmethod
    def load_or_create(cls, data_dir: Path) -> "AgentConfig":
        path = cls.path(data_dir)
        if path.exists():
            return cls(**json.loads(path.read_text(encoding="utf-8")))
        cfg = cls(name=socket.gethostname(), token=secrets.token_urlsafe(24))
        cfg.save(data_dir)
        return cfg

    def save(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path(data_dir).write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
