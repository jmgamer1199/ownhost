from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


@dataclass
class ServerMeta:
    id: str
    name: str
    game: str
    flavor: str
    version: str
    memory_mb: int
    port: int
    build: str | None = None
    java_major: int | None = None
    auto_start: bool = False
    # On start, installs new compatible builds (same Minecraft Java version; latest on Bedrock).
    auto_update: bool = True
    # If it crashes, it starts again by itself (at most 3 times in 10 minutes).
    auto_restart: bool = True
    extra: dict = field(default_factory=dict)  # each game's own data
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
