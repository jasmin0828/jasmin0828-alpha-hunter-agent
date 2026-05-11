"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable with common true-value support."""
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_ENABLED = _env_bool("TELEGRAM_ENABLED", default=True)

# Trading stays disabled by default. This project only sends data notifications.
AUTO_TRADING_ENABLED = _env_bool("AUTO_TRADING_ENABLED", default=False)
