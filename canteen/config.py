import json
import os
from pathlib import Path

_settings: dict | None = None


def _load() -> dict:
    global _settings
    if _settings is not None:
        return _settings

    settings_path = Path(__file__).parent.parent / "local.settings.json"
    if settings_path.exists():
        with open(settings_path) as f:
            data = json.load(f)
        _settings = data.get("Values", {})
    else:
        _settings = {}

    return _settings


def get(key: str) -> str | None:
    """Return config value from local.settings.json, falling back to environment variables."""
    value = _load().get(key)
    if not value:
        value = os.environ.get(key)
    return value

