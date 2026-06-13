"""Obsidian-ready memory note writer for Alpha Hunter Market System."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.paths import MEMORY_DIR, ensure_project_directories


class MemoryNoteService:
    """Write durable token, narrative, and signal quality notes."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.memory_dir = memory_dir or MEMORY_DIR

    def write_memory_notes(
        self,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> dict[str, list[Path] | Path]:
        """Write Memory Layer notes for the latest scan."""
        ensure_project_directories()
        token_paths = self._write_token_notes(snapshots)
        narrative_paths = self._write_narrative_notes(snapshots)
        signal_path = self._write_signal_quality_note(snapshots, signal_events, manifest)
        return {
            "tokens": token_paths,
            "narratives": narrative_paths,
            "signals": signal_path,
        }

    def _write_token_notes(self, snapshots: pd.DataFrame) -> list[Path]:
        """Write one Obsidian page per token in the latest scan."""
        token_dir = self.memory_dir / "tokens"
        token_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        if snapshots.empty:
            return paths

        for _, token in snapshots.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False]).iterrows():
            symbol = self._safe_text(token.get("symbol") or "UNKNOWN")
            address = self._safe_text(token.get("token_address") or "no-address")
            path = token_dir / f"{self._slug(symbol)}-{self._slug(address)[:12]}.md"
            path.write_text(self._render_token_note(token), encoding="utf-8")
            paths.append(path)
        return paths

    def _write_narrative_notes(self, snapshots: pd.DataFrame) -> list[Path]:
        """Write one note per narrative represented in the latest scan."""
        narrative_dir = self.memory_dir / "narratives"
        narrative_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        if snapshots.empty or "narrative" not in snapshots.columns:
            return paths

        for narrative, group in snapshots.groupby("narrative", dropna=False):
            narrative_name = self._safe_text(narrative or "Unknown")
            path = narrative_dir / f"{self._slug(narrative_name)}.md"
            path.write_text(self._render_narrative_note(narrative_name, group), encoding="utf-8")
            paths.append(path)
        return paths

    def _write_signal_quality_note(
        self,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> Path:
        """Write a compact signal quality note for Memory Layer review."""
        signal_dir = self.memory_dir / "signals"
        signal_dir.mkdir(parents=True, exist_ok=True)
        path = signal_dir / "signal-quality.md"
        path.write_text(self._render_signal_quality_note(snapshots, signal_events, manifest), encoding="utf-8")
        return path

    def _render_token_note(self, token: pd.Series) -> str:
        """Render a single token memory note."""
        generated_at = self._now()
        symbol = self._safe_text(token.get("symbol") or "UNKNOWN")
        token_name = self._safe_text(token.get("token_name") or "UNKNOWN")
        lines = [
            "---",
            f"symbol: {symbol}",
            f"token_name: {token_name}",
            f"token_address: {self._safe_text(token.get('token_address'))}",
            f"last_seen_at: {self._safe_text(token.get('created_at'))}",
            f"alert_level: {self._safe_text(token.get('alert_level'))}",
            f"token_age_bucket: {self._safe_text(token.get('token_age_bucket'))}",
            f"rug_risk_level: {self._safe_text(token.get('rug_risk_level'))}",
            "system: Alpha Hunter Market System",
            "---",
            "",
            f"# {symbol} / {token_name}",
            "",
            "## Latest Signal State",
            "",
            f"- early_alpha_score: {self._number(token.get('early_alpha_score'))}",
            f"- agent_score: {self._number(token.get('agent_score'))}",
            f"- alpha_score: {self._number(token.get('alpha_score'))}",
            f"- alert_level: {self._safe_text(token.get('alert_level'))}",
            f"- scan_count: {self._safe_text(token.get('scan_count'))}",
            f"- consecutive_up_count: {self._safe_text(token.get('consecutive_up_count'))}",
            f"- first_seen_at: {self._safe_text(token.get('first_seen_at'))}",
            f"- is_first_seen: {self._safe_text(token.get('is_first_seen'))}",
            "",
            "## Market Snapshot",
            "",
            f"- price_usd: {self._number(token.get('price_usd'), 8)}",
            f"- volume_24h: {self._number(token.get('volume_24h'))}",
            f"- liquidity_usd: {self._number(token.get('liquidity_usd'))}",
            f"- fdv: {self._number(token.get('fdv'))}",
            f"- market_cap: {self._number(token.get('market_cap'))}",
            "",
            "## Intelligence",
            "",
            f"- narrative: {self._safe_text(token.get('narrative'))}",
            f"- early_alpha_reason: {self._safe_text(token.get('early_alpha_reason'))}",
            f"- alert_reason: {self._safe_text(token.get('alert_reason'))}",
            f"- risk_notes: {self._safe_text(token.get('risk_notes'))}",
            f"- ai_summary: {self._safe_text(token.get('ai_summary'))}",
            "",
            "## Links",
            "",
            f"- DexScreener: {self._safe_text(token.get('url'))}",
            "",
            "## Memory Metadata",
            "",
            f"- generated_at: {generated_at}",
            "- safety: read-only, no wallet connection, no automated trading",
        ]
        return "\n".join(lines) + "\n"

    def _render_narrative_note(self, narrative: str, group: pd.DataFrame) -> str:
        """Render a narrative memory note."""
        generated_at = self._now()
        ranked = group.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False])
        alert_count = int(ranked["alert_level"].isin(["CRITICAL", "HIGH", "WATCH"]).sum())
        lines = [
            "---",
            f"narrative: {narrative}",
            f"last_updated_at: {generated_at}",
            "system: Alpha Hunter Market System",
            "---",
            "",
            f"# Narrative: {narrative}",
            "",
            "## Snapshot",
            "",
            f"- token_count: {len(ranked)}",
            f"- alert_count: {alert_count}",
            f"- max_early_alpha_score: {self._number(ranked['early_alpha_score'].max())}",
            "",
            "## Tokens",
            "",
        ]
        for _, token in ranked.head(12).iterrows():
            lines.append(
                "- "
                f"{self._safe_text(token.get('symbol'))} "
                f"alert={self._safe_text(token.get('alert_level'))} "
                f"early_alpha={self._number(token.get('early_alpha_score'))} "
                f"age={self._safe_text(token.get('token_age_bucket'))} "
                f"risk={self._safe_text(token.get('rug_risk_level'))}"
            )
        lines.extend(
            [
                "",
                "## Notes",
                "",
                "- Human review required before publishing or acting on any signal.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_signal_quality_note(
        self,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame,
        manifest: dict[str, Any],
    ) -> str:
        """Render signal quality memory note."""
        generated_at = self._now()
        summary = manifest.get("scan_summary", {})
        quality = manifest.get("signal_quality", {})
        repeated_watch = 0
        if not snapshots.empty:
            scan_count = pd.to_numeric(snapshots.get("scan_count", 0), errors="coerce").fillna(0)
            repeated_watch = int(((snapshots["alert_level"] == "WATCH") & (scan_count > 20)).sum())
        outcome_distribution = {}
        if not signal_events.empty and "outcome_status" in signal_events.columns:
            outcome_distribution = signal_events["outcome_status"].fillna("PENDING").value_counts().to_dict()

        lines = [
            "---",
            "topic: signal-quality",
            f"last_updated_at: {generated_at}",
            "system: Alpha Hunter Market System",
            "---",
            "",
            "# Signal Quality",
            "",
            "## Latest Scan",
            "",
            f"- token_count: {summary.get('token_count', 0)}",
            f"- alert_count: {summary.get('alert_count', 0)}",
            f"- signal_event_count: {summary.get('signal_event_count', 0)}",
            f"- watch_count: {quality.get('watch_count', 0)}",
            f"- high_count: {quality.get('high_count', 0)}",
            f"- critical_count: {quality.get('critical_count', 0)}",
            f"- old_watch_count: {quality.get('old_watch_count', 0)}",
            f"- repeated_watch_candidates: {quality.get('repeated_watch_count', repeated_watch)}",
            f"- avg_early_alpha_alert_score: {quality.get('avg_early_alpha_alert_score', 0)}",
            f"- max_early_alpha_score: {summary.get('max_early_alpha_score', 0)}",
            "",
            "## Outcome Distribution",
            "",
        ]
        distribution = quality.get("outcome_distribution") or outcome_distribution
        if distribution:
            for status, count in distribution.items():
                lines.append(f"- {status}: {count}")
        else:
            lines.append("- No completed signal outcome records yet.")

        lines.extend(["", "## Repeated WATCH", ""])
        repeated = quality.get("top_repeated_watch") or []
        if repeated:
            for token in repeated:
                lines.append(
                    "- "
                    f"{token.get('symbol')} "
                    f"scan_count={token.get('scan_count')} "
                    f"early_alpha={token.get('early_alpha_score')} "
                    f"age={token.get('token_age_bucket')} "
                    f"risk={token.get('rug_risk_level')}"
                )
        else:
            lines.append("- No repeated WATCH candidates in latest scan.")

        lines.extend(
            [
                "",
                "## Current Signal Events",
                "",
            ]
        )
        if signal_events.empty:
            lines.append("- No new signal events in latest scan.")
        else:
            for _, event in signal_events.sort_values("early_alpha_score", ascending=False).head(10).iterrows():
                lines.append(
                    "- "
                    f"{self._safe_text(event.get('symbol'))} "
                    f"{self._safe_text(event.get('event_type'))} "
                    f"{self._safe_text(event.get('previous_alert_level'))} -> {self._safe_text(event.get('alert_level'))} "
                    f"early_alpha={self._number(event.get('early_alpha_score'))}"
                )
        return "\n".join(lines) + "\n"

    def _slug(self, value: str) -> str:
        """Return a filesystem-safe slug."""
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
        cleaned = cleaned.strip("-._")
        return cleaned.lower() or "unknown"

    def _safe_text(self, value: object) -> str:
        """Convert nullable values to readable text."""
        if pd.isna(value) or value is None or value == "":
            return "N/A"
        return str(value).replace("\n", " ").strip()

    def _number(self, value: object, decimals: int = 2) -> str:
        """Format numeric values for markdown."""
        if pd.isna(value):
            return "0.00"
        try:
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    def _now(self) -> str:
        """Return current UTC time as ISO text."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
