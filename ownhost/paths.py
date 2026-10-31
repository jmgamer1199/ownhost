"""Rutas por defecto compartidas entre el agente y la app."""

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Ownhost"


def default_data_dir() -> Path:
    """Dónde guarda el agente los servidores, Java y las copias de seguridad."""
    env = os.environ.get("OWNHOST_DATA_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_DIR_NAME / "agent"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ownhost"


def app_config_dir() -> Path:
    """Dónde guarda la app la lista de equipos."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ownhost"
