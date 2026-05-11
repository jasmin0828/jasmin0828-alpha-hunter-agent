"""Alpha Hunter Agent v0.5 entry point.

The agent only reads public DexScreener data. It does not connect to wallets
and it never executes trades.
"""

from __future__ import annotations

import logging
import time

import schedule

from config import AUTO_TRADING_ENABLED
from src.notifications.telegram_notifier import TelegramNotifier
from src.services.alpha_token_service import AlphaTokenService
from src.utils.logging_config import setup_logging


RUN_INTERVAL_MINUTES = 10


def run_agent() -> None:
    """Run one complete alpha-token scan and log all recoverable failures."""
    logger = logging.getLogger(__name__)
    service = AlphaTokenService()
    notifier = TelegramNotifier()

    try:
        top_tokens = service.find_and_save_top_tokens()
    except Exception:
        logger.exception("Alpha Hunter scan failed")
        return

    if top_tokens.empty:
        logger.info("No tokens matched the current filters")
        print("No tokens matched the current filters.")
        return

    logger.info("Top %s alpha tokens:\n%s", len(top_tokens), top_tokens.to_string(index=False))
    print(top_tokens.to_string(index=False))

    try:
        notifier.notify_top_tokens(top_tokens)
    except Exception:
        logger.exception("Telegram notification failed")


def main() -> None:
    """Start the scheduled Alpha Hunter Agent loop."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Alpha Hunter Agent v0.5")
    logger.info("Auto trading enabled: %s", AUTO_TRADING_ENABLED)
    run_agent()

    schedule.every(RUN_INTERVAL_MINUTES).minutes.do(run_agent)
    logger.info("Scheduled scans every %s minutes", RUN_INTERVAL_MINUTES)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
