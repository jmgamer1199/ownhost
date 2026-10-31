from ownhost.agent.games.base import GameAdapter
from ownhost.agent.games.bedrock import BedrockAdapter
from ownhost.agent.games.hytale import HytaleAdapter
from ownhost.agent.games.minecraft import MinecraftAdapter

GAMES: dict[str, GameAdapter] = {g.id: g for g in (MinecraftAdapter(), BedrockAdapter(), HytaleAdapter())}
