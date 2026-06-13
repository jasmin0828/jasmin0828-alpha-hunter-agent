"""Content draft writer for Alpha Hunter Market System."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.paths import CONTENT_DIR, ensure_project_directories


class ContentDraftService:
    """Create lightweight X and note drafts from scan intelligence."""

    def __init__(self, content_dir: Path | None = None) -> None:
        self.content_dir = content_dir or CONTENT_DIR

    def write_content_drafts(
        self,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> dict[str, Path]:
        """Write content drafts that can be reviewed before posting."""
        ensure_project_directories()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        x_path = self.content_dir / "x" / f"{today}.md"
        note_path = self.content_dir / "notes" / f"{today}-market-note.md"
        x_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        x_path.write_text(self._render_x_draft(snapshots, signal_events, manifest), encoding="utf-8")
        note_path.write_text(self._render_note_draft(snapshots, signal_events, manifest), encoding="utf-8")
        return {"x": x_path, "note": note_path}

    def _render_x_draft(self, snapshots: pd.DataFrame, signal_events: pd.DataFrame, manifest: dict[str, Any]) -> str:
        """Render a short post draft."""
        summary = manifest.get("scan_summary", {})
        top = self._top_token(snapshots)
        event_line = "No fresh signal transition this scan."
        if not signal_events.empty:
            event = signal_events.sort_values("early_alpha_score", ascending=False).iloc[0]
            event_line = (
                f"Fresh {event.get('event_type')} signal: {event.get('symbol')} "
                f"{event.get('previous_alert_level')} -> {event.get('alert_level')}."
            )

        lines = [
            "# X Draft",
            "",
            "Alpha Hunter Market System scan:",
            f"- tokens: {summary.get('token_count', 0)}",
            f"- alerts: {summary.get('alert_count', 0)}",
            f"- signal events: {summary.get('signal_event_count', 0)}",
            f"- top early alpha: {top}",
            f"- {event_line}",
            "",
            "Read-only market intelligence. No wallet connection, no automated trading.",
        ]
        return "\n".join(lines) + "\n"

    def _render_note_draft(self, snapshots: pd.DataFrame, signal_events: pd.DataFrame, manifest: dict[str, Any]) -> str:
        """Render a longer note draft."""
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        summary = manifest.get("scan_summary", {})
        lines = [
            "# Alpha Hunter Market Note",
            "",
            f"- generated_at: {generated_at}",
            "- source: Alpha Hunter Market System",
            "",
            "## Scan Summary",
            "",
            f"- token_count: {summary.get('token_count', 0)}",
            f"- alert_count: {summary.get('alert_count', 0)}",
            f"- signal_event_count: {summary.get('signal_event_count', 0)}",
            f"- max_early_alpha_score: {summary.get('max_early_alpha_score', 0)}",
            "",
            "## Signals To Review",
            "",
        ]

        if signal_events.empty:
            lines.append("- No new signal transitions. Review repeated WATCH noise and existing names.")
        else:
            for _, event in signal_events.sort_values("early_alpha_score", ascending=False).head(5).iterrows():
                lines.append(
                    "- "
                    f"{event.get('symbol')} "
                    f"{event.get('event_type')} "
                    f"{event.get('previous_alert_level')} -> {event.get('alert_level')} "
                    f"early_alpha={self._number(event.get('early_alpha_score'))}"
                )

        lines.extend(["", "## Top Early Alpha Names", ""])
        for _, token in snapshots.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False]).head(8).iterrows():
            lines.append(
                "- "
                f"{token.get('symbol')} "
                f"early_alpha={self._number(token.get('early_alpha_score'))} "
                f"alert={token.get('alert_level')} "
                f"age={token.get('token_age_bucket')} "
                f"risk={token.get('rug_risk_level')} "
                f"reason={token.get('early_alpha_reason')}"
            )

        lines.extend(
            [
                "",
                "## Safety",
                "",
                "- Draft only. Do not post without human review.",
                "- No wallet connection, private keys, transaction signing, or automated trading.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _top_token(self, snapshots: pd.DataFrame) -> str:
        """Return compact top-token text for short drafts."""
        if snapshots.empty:
            return "none"
        token = snapshots.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False]).iloc[0]
        return f"{token.get('symbol')} ({self._number(token.get('early_alpha_score'))})"

    def _number(self, value: object) -> str:
        """Format numeric values for content text."""
        if pd.isna(value):
            return "0.00"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
