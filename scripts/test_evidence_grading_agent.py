"""Run the first-stage Evidence Grading Agent on latest local scan data."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.evidence_grading_agent import EvidenceGradingAgent  # noqa: E402
from src.agents.social_signal_agent import SocialSignalAgent  # noqa: E402
from src.agents.theme_scanner_agent import ThemeScannerAgent  # noqa: E402
from src.storage.sqlite_store import SQLiteStore  # noqa: E402


SAMPLE_FILE = PROJECT_ROOT / "examples" / "social_signals_sample.json"


def main() -> None:
    """Print social-enhanced evidence grades and the top five graded subjects."""
    store = SQLiteStore()
    snapshots = store.load_latest_token_snapshots()
    themes = ThemeScannerAgent().scan_as_dicts(snapshots)
    social_inputs = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    social_signals = SocialSignalAgent().analyze_as_dicts(social_inputs, snapshots, themes)

    agent = EvidenceGradingAgent()
    baseline_grades = agent.grade_as_dicts(snapshots, themes)
    grades = agent.grade_as_dicts(snapshots, themes, social_signals=social_signals)

    assert grades, "EvidenceGradingAgent should return at least one grade for latest snapshots."
    for grade in grades:
        assert grade["subject_type"] in {"theme", "token"}
        assert grade["subject_name"]
        assert grade["evidence_grade"] in {"A", "B", "C", "D"}
        assert 0 <= grade["evidence_score"] <= 100
        assert isinstance(grade["evidence_sources"], list)
        assert isinstance(grade["positive_evidence"], list)
        assert isinstance(grade["weak_evidence"], list)
        assert isinstance(grade["risk_flags"], list)
        assert isinstance(grade["social_evidence"], list)
        assert isinstance(grade["social_risk_flags"], list)
        assert grade["reason"]

    baseline_lookup = {(row["subject_type"], row["subject_name"]): row for row in baseline_grades}
    enhanced_lookup = {(row["subject_type"], row["subject_name"]): row for row in grades}
    sports_base = baseline_lookup.get(("theme", "Sports"))
    sports_social = enhanced_lookup.get(("theme", "Sports"))
    fcm_base = baseline_lookup.get(("token", "FCM"))
    fcm_social = enhanced_lookup.get(("token", "FCM"))
    goku_social = enhanced_lookup.get(("token", "GOKU"))

    assert sports_base and sports_social and sports_social["evidence_score"] > sports_base["evidence_score"]
    assert fcm_base and fcm_social and fcm_social["evidence_score"] > fcm_base["evidence_score"]
    assert goku_social and "SocialSignalAgent" in goku_social["evidence_sources"]
    assert any("hype_risk HIGH" in flag for flag in goku_social["social_risk_flags"])
    assert goku_social["evidence_grade"] == "D"

    top_five = sorted(grades, key=lambda item: item["evidence_score"], reverse=True)[:5]

    print(json.dumps(grades, indent=2, ensure_ascii=False))
    print("\nTop 5 social-enhanced evidence grades:")
    print(json.dumps(top_five, indent=2, ensure_ascii=False))
    print("\nSocial comparison:")
    print(
        json.dumps(
            {
                "Sports": {
                    "baseline": sports_base["evidence_score"],
                    "social_enhanced": sports_social["evidence_score"],
                },
                "FCM": {
                    "baseline": fcm_base["evidence_score"],
                    "social_enhanced": fcm_social["evidence_score"],
                },
                "GOKU": {
                    "social_enhanced": goku_social["evidence_score"],
                    "social_risk_flags": goku_social["social_risk_flags"],
                    "evidence_grade": goku_social["evidence_grade"],
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
