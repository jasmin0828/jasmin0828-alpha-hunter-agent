"""Run the first-stage Social Signal Agent with manual sample data."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.social_signal_agent import SocialSignalAgent  # noqa: E402
from src.agents.theme_scanner_agent import ThemeScannerAgent  # noqa: E402
from src.storage.sqlite_store import SQLiteStore  # noqa: E402


SAMPLE_FILE = PROJECT_ROOT / "data" / "social_signals_sample.json"


def main() -> None:
    """Print JSON social signal results and top social signals."""
    samples = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    store = SQLiteStore()
    snapshots = store.load_latest_token_snapshots()
    themes = ThemeScannerAgent().scan_as_dicts(snapshots)

    signals = SocialSignalAgent().analyze_as_dicts(samples, snapshots, themes)
    assert signals, "SocialSignalAgent should return at least one signal."

    for signal in signals:
        assert signal["signal_id"]
        assert signal["source_platform"]
        assert signal["author"]
        assert isinstance(signal["mentioned_tokens"], list)
        assert isinstance(signal["mentioned_themes"], list)
        assert 0 <= signal["social_strength"] <= 100
        assert signal["hype_risk"] in {"LOW", "MEDIUM", "HIGH"}
        assert signal["evidence_value"] in {"LOW", "MEDIUM", "HIGH"}
        assert signal["reason"]
        assert "trading" not in signal["reason"].lower()

    top_signals = sorted(signals, key=lambda row: row["social_strength"], reverse=True)[:5]

    print(json.dumps(signals, indent=2, ensure_ascii=False))
    print("\nTop social signals:")
    print(json.dumps(top_signals, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
