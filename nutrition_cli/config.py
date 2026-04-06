"""Persistent config management at ~/.config/nutrition-cli/config.json."""

import json
from pathlib import Path


def get_config_path() -> Path:
    """Return config file path, creating parent dirs if missing."""
    path = Path.home() / ".config" / "nutrition-cli" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_config() -> dict:
    """Read config JSON. Returns {} if file missing or invalid."""
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    """Write config dict as JSON with indent=2."""
    path = get_config_path()
    path.write_text(json.dumps(data, indent=2) + "\n")


def get(key: str, default=None):
    """Read one key from config."""
    return load_config().get(key, default)


def set(key: str, value: str) -> None:
    """Load config, update one key, save."""
    data = load_config()
    data[key] = value
    save_config(data)
