"""Generate a standalone Daily Alpha Report from latest local scan data."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.daily_alpha_report_agent import DailyAlphaReportAgent  # noqa: E402
from src.agents.social_signal_agent import SocialSignalAgent  # noqa: E402
from src.agents.theme_scanner_agent import ThemeScannerAgent  # noqa: E402
from src.storage.sqlite_store import SQLiteStore  # noqa: E402


REPORTS_DIR = PROJECT_ROOT / "reports"
SOCIAL_SIGNALS_SAMPLE = PROJECT_ROOT / "examples" / "social_signals_sample.json"


def generate_social_enhanced_daily_report() -> tuple[dict, Path]:
    """Generate the social-enhanced Daily Alpha Report and save Markdown."""
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    store = SQLiteStore()
    snapshots = store.load_latest_token_snapshots()
    themes = ThemeScannerAgent().scan_as_dicts(snapshots)
    social_inputs = json.loads(SOCIAL_SIGNALS_SAMPLE.read_text(encoding="utf-8"))
    social_signals = SocialSignalAgent().analyze_as_dicts(social_inputs, snapshots, themes)

    agent = DailyAlphaReportAgent()
    report = agent.build_report(snapshots, themes, report_date=report_date, social_signals=social_signals)
    report_dict = agent.build_report_dict(snapshots, themes, report_date=report_date, social_signals=social_signals)
    markdown = agent.render_markdown(report)

    for key in ["evidence_grades", "top_evidence", "weak_evidence", "risk_flags_summary"]:
        assert key in report_dict, f"Daily Alpha Report missing {key}"
    for key in ["social_signals", "social_summary", "social_enhanced_evidence_grades", "hype_risk_summary"]:
        assert key in report_dict, f"Daily Alpha Report missing {key}"
    assert report_dict["social_signals"], "Daily Alpha Report should include social signals"
    assert report_dict["social_summary"]["signal_count"] > 0
    assert report_dict["social_enhanced_evidence_grades"], "Expected social-enhanced evidence grades"
    assert "## Evidence Grades" in markdown
    assert "## Top Evidence" in markdown
    assert "## Weak Evidence / Risks" in markdown
    assert "## Social Signals" in markdown
    assert "## Social Evidence Summary" in markdown
    assert "## Hype Risk Summary" in markdown
    assert "## Social-enhanced Evidence Grades" in markdown

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORTS_DIR / f"daily_alpha_report_{report_date}.md"
    output_path.write_text(markdown, encoding="utf-8")
    return report_dict, output_path


def main() -> None:
    """Print JSON summary and save a Markdown report."""
    report_dict, output_path = generate_social_enhanced_daily_report()

    summary = {
        "report_date": report_dict["report_date"],
        "market_summary": report_dict["market_summary"],
        "social_summary": report_dict["social_summary"],
        "hype_risk_summary": report_dict["hype_risk_summary"],
        "top_social_enhanced_evidence": report_dict["social_enhanced_evidence_grades"][:3],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nMarkdown report saved to: {output_path}")


if __name__ == "__main__":
    main()
