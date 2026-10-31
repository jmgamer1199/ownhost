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
    # Al encender, instala builds nuevas compatibles (misma versión de Minecraft Java; última en Bedrock).
    auto_update: bool = True
    # Si se cae, se vuelve a encender solo (máximo 3 veces en 10 minutos).
    auto_restart: bool = True
    extra: dict = field(default_factory=dict)  # datos propios de cada juego
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)
