"""Default paths shared by the agent and the app."""

import os
import sys
from pathlib import Path

APP_DIR_NAME = "Ownhost"


def default_data_dir() -> Path:
    """Where the agent stores servers, Java and backups."""
    env = os.environ.get("OWNHOST_DATA_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_DIR_NAME / "agent"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "ownhost"


def app_config_dir() -> Path:
    """Where the app stores the list of computers."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / APP_DIR_NAME
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "ownhost"
