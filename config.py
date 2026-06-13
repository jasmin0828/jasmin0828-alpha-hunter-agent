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
TELEGRAM_HEALTHCHECK_ENABLED = _env_bool("TELEGRAM_HEALTHCHECK_ENABLED", default=True)
TELEGRAM_HEALTHCHECK_INTERVAL_HOURS = float(os.getenv("TELEGRAM_HEALTHCHECK_INTERVAL_HOURS", "6"))
TELEGRAM_REPORTS_ENABLED = _env_bool("TELEGRAM_REPORTS_ENABLED", default=True)
REPORT_TIMEZONE = os.getenv("REPORT_TIMEZONE", "Asia/Shanghai").strip()
DAILY_REPORT_HOUR = int(os.getenv("DAILY_REPORT_HOUR", "21"))
WEEKLY_REPORT_WEEKDAY = int(os.getenv("WEEKLY_REPORT_WEEKDAY", "6"))
WEEKLY_REPORT_HOUR = int(os.getenv("WEEKLY_REPORT_HOUR", "21"))

# Multi-chain market intelligence configuration. These filters are monitoring
# thresholds only; the system does not trade or connect to wallets.
SUPPORTED_CHAINS = ["ethereum", "solana", "bsc"]
CHAIN_FILTERS = {
    "ethereum": {
        "liquidity_usd": 50_000,
        "volume_24h": 50_000,
        "min_price_change_24h": -35,
        "max_price_change_24h": 220,
        "fdv": 500_000_000,
    },
    "solana": {
        "liquidity_usd": 50_000,
        "volume_24h": 100_000,
        "min_price_change_24h": -30,
        "max_price_change_24h": 200,
        "fdv": 50_000_000,
    },
    "bsc": {
        "liquidity_usd": 25_000,
        "volume_24h": 50_000,
        "min_price_change_24h": -80,
        "max_price_change_24h": 250,
        "fdv": 500_000_000,
    },
}
CHAIN_SEARCH_QUERIES = {
    "ethereum": ["PEPE", "MOG", "SPX", "FLOKI"],
    "solana": ["SOL", "pump"],
    "bsc": ["PancakeSwap", "BSC", "FLOKI"],
}

# Trading stays disabled by default. This project only sends data notifications.
AUTO_TRADING_ENABLED = _env_bool("AUTO_TRADING_ENABLED", default=False)
