"""Run Theme Scanner Agent against the latest SQLite token snapshots."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.theme_scanner_agent import ThemeScannerAgent  # noqa: E402
from src.storage.sqlite_store import SQLiteStore  # noqa: E402


def main() -> None:
    """Print latest theme scan results as JSON."""
    store = SQLiteStore()
    snapshots = store.load_latest_token_snapshots()
    results = ThemeScannerAgent().scan_as_dicts(snapshots)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
