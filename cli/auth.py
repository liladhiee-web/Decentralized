"""
CLI Local Credential and Configuration Manager.
Stores user JWT tokens, API keys, and server preferences in ~/.cloudai/config.json.
"""

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".cloudai"
CONFIG_FILE = CONFIG_DIR / "config.json"


def get_config() -> dict[str, Any]:
    """Load configuration from local file or return defaults."""
    if not CONFIG_FILE.exists():
        return {
            "coordinator_url": "http://localhost:8000",
            "access_token": None,
            "refresh_token": None,
            "api_key": None,
            "email": None,
        }
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "coordinator_url": "http://localhost:8000",
            "access_token": None,
            "refresh_token": None,
            "api_key": None,
            "email": None,
        }


def save_config(config_data: dict[str, Any]) -> None:
    """Persist configuration updates to local JSON file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2)


def set_credentials(
    access_token: str,
    refresh_token: str | None = None,
    email: str | None = None,
    api_key: str | None = None,
    coordinator_url: str | None = None,
) -> None:
    """Store active authentication credentials."""
    cfg = get_config()
    if access_token:
        cfg["access_token"] = access_token
    if refresh_token:
        cfg["refresh_token"] = refresh_token
    if email:
        cfg["email"] = email
    if api_key:
        cfg["api_key"] = api_key
    if coordinator_url:
        cfg["coordinator_url"] = coordinator_url
    save_config(cfg)


def clear_credentials() -> None:
    """Clear session credentials on logout."""
    cfg = get_config()
    cfg["access_token"] = None
    cfg["refresh_token"] = None
    cfg["api_key"] = None
    cfg["email"] = None
    save_config(cfg)
