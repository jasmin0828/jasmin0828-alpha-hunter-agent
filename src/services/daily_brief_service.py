"""Daily brief writer for Alpha Hunter Market System Memory Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.paths import MEMORY_DIR, ensure_project_directories


class DailyBriefService:
    """Write Obsidian-ready daily market briefs from scan output."""

    def __init__(self, daily_dir: Path | None = None) -> None:
        self.daily_dir = daily_dir or MEMORY_DIR / "daily"

    def write_daily_brief(
        self,
        scan_run_id: int,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> Path:
        """Write or refresh today's daily brief markdown file."""
        ensure_project_directories()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        brief_path = self.daily_dir / f"{today}.md"
        brief_path.parent.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(
            self._render_brief(scan_run_id, snapshots, signal_events, manifest),
            encoding="utf-8",
        )
        return brief_path

    def _render_brief(
        self,
        scan_run_id: int,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> str:
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        summary = manifest.get("scan_summary", {})
        observation = manifest.get("observation_summary", {})
        latest_run = observation.get("latest_run", {}) if isinstance(observation, dict) else {}
        lines = [
            "# Alpha Hunter Daily Brief",
            "",
            f"- generated_at: {generated_at}",
            f"- scan_run_id: {scan_run_id}",
            "- system: Alpha Hunter Market System",
            "- subsystems: Market Intelligence, AI Workflow Engine, Memory Layer, Content Engine, Automation Layer, Future AI Trading Agent",
            "- market_intelligence_modules: Narrative Detection, Signal Analysis, Research Reports",
            "",
            "## Market Intelligence Snapshot",
            "",
            f"- token_count: {summary.get('token_count', 0)}",
            f"- alert_count: {summary.get('alert_count', 0)}",
            f"- first_seen_count: {summary.get('first_seen_count', 0)}",
            f"- consecutive_momentum_count: {summary.get('consecutive_momentum_count', 0)}",
            f"- max_early_alpha_score: {summary.get('max_early_alpha_score', 0)}",
            "",
            "## Observation Summary",
            "",
            f"- latest_run_status: {latest_run.get('status', 'unknown')}",
            f"- started_at: {latest_run.get('started_at', 'N/A')}",
            f"- finished_at: {latest_run.get('finished_at') or latest_run.get('completed_at', 'N/A')}",
            f"- scanned_chains: {latest_run.get('scanned_chains', '') or 'N/A'}",
            f"- tokens_scanned: {latest_run.get('tokens_scanned', latest_run.get('token_count', 0))}",
            f"- signals_found: {latest_run.get('signals_found', summary.get('signal_event_count', 0))}",
            f"- duration_seconds: {latest_run.get('duration_seconds', 0)}",
            f"- errors: {latest_run.get('errors', '') or 'None'}",
            "",
            "## New Signal Events",
            "",
        ]

        if signal_events.empty:
            lines.append("- No new signal transition events in the latest scan.")
        else:
            for _, event in signal_events.sort_values(
                ["early_alpha_score", "agent_score"],
                ascending=[False, False],
            ).head(10).iterrows():
                lines.append(
                    "- "
                    f"{event.get('event_type')} "
                    f"{event.get('symbol')} "
                    f"{event.get('previous_alert_level')} -> {event.get('alert_level')} "
                    f"early_alpha={self._number(event.get('early_alpha_score'))} "
                    f"age={event.get('token_age_bucket')} "
                    f"reason={event.get('early_alpha_reason')}"
                )

        lines.extend(
            [
                "",
                "## Early Alpha Ranking",
                "",
            ]
        )
        ranking = snapshots.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False]).head(10)
        if ranking.empty:
            lines.append("- No scan rows available.")
        else:
            for _, token in ranking.iterrows():
                lines.append(
                    "- "
                    f"{token.get('symbol')} "
                    f"alert={token.get('alert_level')} "
                    f"early_alpha={self._number(token.get('early_alpha_score'))} "
                    f"scan_count={token.get('scan_count')} "
                    f"momentum={token.get('consecutive_up_count')} "
                    f"age={token.get('token_age_bucket')} "
                    f"risk={token.get('rug_risk_level')}"
                )

        lines.extend(
            [
                "",
                "## Narrative Distribution",
                "",
            ]
        )
        narrative_distribution = summary.get("narrative_distribution", {})
        if narrative_distribution:
            for narrative, count in narrative_distribution.items():
                lines.append(f"- {narrative}: {count}")
        else:
            lines.append("- No narrative data available.")

        lines.extend(
            [
                "",
                "## Safety Boundary",
                "",
                "- no wallet connection",
                "- no private keys",
                "- no transaction signing",
                "- no automated trading",
            ]
        )
        return "\n".join(lines) + "\n"

    def _number(self, value: object) -> str:
        """Format a number for brief text."""
        if pd.isna(value):
            return "0.00"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
