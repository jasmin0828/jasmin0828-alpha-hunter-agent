"""Run the first-stage Alpha Hunter Core pipeline once."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.alpha_hunter_core import AlphaHunterCore  # noqa: E402


def main() -> None:
    """Run Core once, print JSON summary, and validate generated artifacts."""
    social_signals_path = PROJECT_ROOT / "data" / "social_signals_sample.json"
    core = AlphaHunterCore(project_root=PROJECT_ROOT)

    result = core.run_pipeline(
        social_signals_path=social_signals_path,
        archive_to_memory=True,
        dry_run=False,
    )

    required_fields = [
        "run_id",
        "run_at",
        "token_count",
        "theme_count",
        "social_signal_count",
        "evidence_grade_count",
        "report_path",
        "memory_archive_path",
        "top_theme",
        "top_social_signal",
        "top_evidence",
        "warnings",
    ]
    for field in required_fields:
        assert field in result, f"AlphaHunterCore result missing {field}"

    assert result["token_count"] > 0, "Core should read latest token snapshots"
    assert result["theme_count"] > 0, "Core should produce ThemeScannerAgent output"
    assert result["social_signal_count"] > 0, "Core should load optional social signals sample"
    assert result["evidence_grade_count"] > 0, "Core should produce EvidenceGradingAgent output"
    assert result["report_path"], "Core should write a Daily Alpha Report markdown file"
    assert result["memory_archive_path"], "Core should archive report when archive_to_memory=True"
    assert Path(result["report_path"]).exists(), "Daily report file was not generated"
    assert Path(result["memory_archive_path"]).exists(), "Memory archive file was not generated"

    memory_index = PROJECT_ROOT / "memory" / "index.json"
    assert memory_index.exists(), "Memory index was not updated"

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
