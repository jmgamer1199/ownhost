import json
import os
import secrets
import socket
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ownhost.agent import DEFAULT_PORT


@dataclass
class AgentConfig:
    name: str
    token: str
    port: int = DEFAULT_PORT
    bind: str = "0.0.0.0"
    # Tailscale devices of the same account can manage this computer without a token.
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
            known = {f.name for f in fields(cls)}  # a file from another version may have more or fewer keys
            return cls(**{k: v for k, v in json.loads(path.read_text(encoding="utf-8")).items() if k in known})
        cfg = cls(name=socket.gethostname(), token=secrets.token_urlsafe(24))
        cfg.save(data_dir)
        return cfg

    def save(self, data_dir: Path) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        path = self.path(data_dir)
        # It holds the token: only its owner can read it (on Linux), and it is replaced in one go so a crash
        # halfway can't leave it empty.
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(path)
