"""First-stage Alpha Hunter Core pipeline orchestrator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from src.agents.daily_alpha_report_agent import DailyAlphaReportAgent
from src.agents.evidence_grading_agent import EvidenceGradingAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.social_signal_agent import SocialSignalAgent
from src.agents.theme_scanner_agent import ThemeScannerAgent
from src.storage.sqlite_store import SQLiteStore


class AlphaHunterCore:
    """Coordinate the v1.0 specialist-agent research pipeline."""

    def __init__(self, project_root: Path | str | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2])
        self.reports_dir = self.project_root / "reports"

    def run_pipeline(
        self,
        social_signals_path: Path | str | None = None,
        archive_to_memory: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run one read-only Agent pipeline and return a structured summary."""
        run_at = datetime.now(timezone.utc)
        report_date = run_at.strftime("%Y-%m-%d")
        warnings: list[str] = []

        snapshots = self._load_latest_snapshots(warnings)
        themes = ThemeScannerAgent().scan_as_dicts(snapshots)
        social_inputs = self._load_social_inputs(social_signals_path, warnings)
        social_signals = (
            SocialSignalAgent().analyze_as_dicts(social_inputs, snapshots, themes)
            if social_inputs
            else []
        )
        evidence_grades = EvidenceGradingAgent().grade_as_dicts(
            snapshots,
            themes,
            social_signals=social_signals or None,
        )

        report_dict, report_path = self._build_report(
            snapshots=snapshots,
            themes=themes,
            social_signals=social_signals,
            report_date=report_date,
            dry_run=dry_run,
            warnings=warnings,
        )
        memory_archive_path = self._archive_report(
            report_path=report_path,
            archive_to_memory=archive_to_memory,
            dry_run=dry_run,
            warnings=warnings,
        )

        return {
            "run_id": f"alpha-core-{run_at.strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
            "run_at": run_at.replace(microsecond=0).isoformat(),
            "token_count": int(len(snapshots)),
            "theme_count": len(themes),
            "social_signal_count": len(social_signals),
            "evidence_grade_count": len(evidence_grades),
            "report_path": str(report_path) if report_path else "",
            "memory_archive_path": str(memory_archive_path) if memory_archive_path else "",
            "top_theme": self._top_theme(themes),
            "top_social_signal": self._top_social_signal(report_dict, social_signals),
            "top_evidence": self._top_evidence(evidence_grades),
            "warnings": warnings,
        }

    def _load_latest_snapshots(self, warnings: list[str]) -> pd.DataFrame:
        snapshots = SQLiteStore().load_latest_token_snapshots()
        if snapshots.empty:
            warnings.append("No latest token snapshots found; pipeline produced an empty research report.")
        return snapshots

    def _load_social_inputs(self, social_signals_path: Path | str | None, warnings: list[str]) -> list[dict[str, Any]]:
        if social_signals_path is None:
            warnings.append("No social_signals_path supplied; running without SocialSignalAgent inputs.")
            return []

        path = Path(social_signals_path)
        if not path.exists():
            warnings.append(f"Social signals file not found: {path}; running without social inputs.")
            return []

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warnings.append(f"Social signals file is invalid JSON: {path}; {exc}")
            return []

        if not isinstance(payload, list):
            warnings.append(f"Social signals file must contain a list: {path}; running without social inputs.")
            return []

        return [row for row in payload if isinstance(row, dict)]

    def _build_report(
        self,
        snapshots: pd.DataFrame,
        themes: list[dict[str, Any]],
        social_signals: list[dict[str, Any]],
        report_date: str,
        dry_run: bool,
        warnings: list[str],
    ) -> tuple[dict[str, Any], Path | None]:
        report_agent = DailyAlphaReportAgent()
        report = report_agent.build_report(
            snapshots,
            themes,
            report_date=report_date,
            social_signals=social_signals,
        )
        report_dict = report_agent.build_report_dict(
            snapshots,
            themes,
            report_date=report_date,
            social_signals=social_signals,
        )
        markdown = report_agent.render_markdown(report)
        if not markdown.strip():
            raise RuntimeError("DailyAlphaReportAgent returned an empty Markdown report.")

        report_path = self.reports_dir / f"daily_alpha_report_{report_date}.md"
        if dry_run:
            warnings.append("dry_run=True; Daily Alpha Report was generated but not written to disk.")
            return report_dict, None

        self.reports_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        return report_dict, report_path

    def _archive_report(
        self,
        report_path: Path | None,
        archive_to_memory: bool,
        dry_run: bool,
        warnings: list[str],
    ) -> Path | None:
        if not archive_to_memory:
            warnings.append("archive_to_memory=False; report was not archived to MemoryAgent.")
            return None
        if dry_run:
            warnings.append("dry_run=True; report was not archived to MemoryAgent.")
            return None
        if report_path is None or not report_path.exists():
            raise FileNotFoundError("Cannot archive Daily Alpha Report because report file was not created.")

        archived = MemoryAgent(project_root=self.project_root).archive_daily_report(report_path)
        archive_path = Path(str(archived.get("file_path") or ""))
        if not archive_path.exists():
            raise FileNotFoundError(f"MemoryAgent did not produce an archive file: {archive_path}")
        return archive_path

    def _top_theme(self, themes: list[dict[str, Any]]) -> str:
        if not themes:
            return "none"
        return str(themes[0].get("theme_name") or "none")

    def _top_social_signal(self, report_dict: dict[str, Any], social_signals: list[dict[str, Any]]) -> str:
        summary = report_dict.get("social_summary", {})
        top_signal = summary.get("top_social_signal")
        if top_signal:
            return str(top_signal)
        if not social_signals:
            return "none"
        signal = max(social_signals, key=lambda row: float(row.get("social_strength") or 0))
        return (
            f"{signal.get('source_platform')}:{signal.get('author')} "
            f"strength={float(signal.get('social_strength') or 0):.2f} "
            f"evidence={signal.get('evidence_value')}"
        )

    def _top_evidence(self, evidence_grades: list[dict[str, Any]]) -> dict[str, Any]:
        if not evidence_grades:
            return {}
        top = max(evidence_grades, key=lambda row: float(row.get("evidence_score") or 0))
        return {
            "subject_type": top.get("subject_type"),
            "subject_name": top.get("subject_name"),
            "evidence_grade": top.get("evidence_grade"),
            "evidence_score": top.get("evidence_score"),
            "reason": top.get("reason"),
        }
