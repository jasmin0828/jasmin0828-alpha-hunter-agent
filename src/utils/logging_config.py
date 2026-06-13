"""Central logging setup for Alpha Hunter Market System."""

from __future__ import annotations

import logging

from src.utils.paths import LOGS_DIR, ensure_project_directories


LOG_FILE = LOGS_DIR / "app.log"


def setup_logging() -> None:
    """Configure console and file logging for the whole application."""
    ensure_project_directories()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
