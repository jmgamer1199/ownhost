"""App settings (for now, the CurseForge API key)."""

import json

from ownhost.paths import app_config_dir


def _path():
    return app_config_dir() / "settings.json"


def load_settings() -> dict:
    path = _path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_settings(settings: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def embedded_curseforge_key() -> str | None:
    """Key embedded when building the exe (see scripts/embed_key.py), if any."""
    try:
        from ownhost._embedded import curseforge_key as embedded
    except ImportError:
        return None
    return embedded()


def curseforge_key() -> str | None:
    # The user's own key (Settings) takes priority over the one embedded in the exe.
    return load_settings().get("curseforge_key") or embedded_curseforge_key()
