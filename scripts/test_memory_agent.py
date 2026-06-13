"""Archive the latest Daily Alpha Report into the first-stage Memory Agent."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.test_daily_alpha_report import generate_social_enhanced_daily_report  # noqa: E402
from src.agents.memory_agent import MemoryAgent  # noqa: E402


def main() -> None:
    """Generate and archive today's social-enhanced Markdown report."""
    report_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _, report_path = generate_social_enhanced_daily_report()
    agent = MemoryAgent(project_root=PROJECT_ROOT)

    try:
        archived = agent.archive_daily_report(report_path)
    except FileNotFoundError as exc:
        print(f"Memory Agent could not archive the report: {exc}")
        print("Run this first: venv/bin/python scripts/test_daily_alpha_report.py")
        raise SystemExit(1) from exc

    index = agent.load_index()
    recent_reports = agent.list_recent_reports(limit=3)

    assert archived["report_date"] == report_date
    assert len([row for row in index["reports"] if row["report_date"] == report_date]) == 1
    assert Path(archived["file_path"]).exists()
    assert archived["social_signal_count"] > 0
    assert archived["high_hype_count"] > 0
    assert archived["top_social_signal"] != "none"

    archived_markdown = Path(archived["file_path"]).read_text(encoding="utf-8")
    for section in [
        "## Top Themes",
        "## Evidence Grades",
        "## Social Signals",
        "## Social Evidence Summary",
        "## Hype Risk Summary",
        "## Social-enhanced Evidence Grades",
    ]:
        assert section in archived_markdown, f"Archived report missing {section}"

    summary = {
        "index_path": str(agent.index_path),
        "report_count": len(index["reports"]),
        "latest_report": index["reports"][0] if index["reports"] else None,
        "archived_sections": {
            "social_signals": "## Social Signals" in archived_markdown,
            "hype_risk_summary": "## Hype Risk Summary" in archived_markdown,
            "evidence_grades": "## Evidence Grades" in archived_markdown,
            "social_enhanced_evidence_grades": "## Social-enhanced Evidence Grades" in archived_markdown,
        },
    }

    print("Archived report:")
    print(json.dumps(archived, indent=2, ensure_ascii=False))
    print("\nMemory index summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\nRecent reports:")
    print(json.dumps(recent_reports, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
