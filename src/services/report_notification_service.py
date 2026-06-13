"""Daily and weekly Telegram report engine for Alpha Hunter Market System."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from config import (
    DAILY_REPORT_HOUR,
    REPORT_TIMEZONE,
    TELEGRAM_REPORTS_ENABLED,
    WEEKLY_REPORT_HOUR,
    WEEKLY_REPORT_WEEKDAY,
)
from src.storage.sqlite_store import DB_PATH
from src.utils.paths import DATA_DIR


@dataclass(frozen=True)
class ScheduledReport:
    """A due Telegram report that should be marked sent after delivery."""

    report_type: str
    period_key: str
    message: str


class ReportNotificationService:
    """Build low-frequency daily and weekly intelligence reports from SQLite."""

    STATE_PATH = DATA_DIR / "telegram_report_state.json"

    def __init__(
        self,
        db_path: Path = DB_PATH,
        state_path: Path | None = None,
        enabled: bool = TELEGRAM_REPORTS_ENABLED,
        timezone_name: str = REPORT_TIMEZONE,
    ) -> None:
        self.db_path = db_path
        self.state_path = state_path or self.STATE_PATH
        self.enabled = enabled
        self.timezone = ZoneInfo(timezone_name)

    def due_reports(self, now: datetime | None = None) -> list[ScheduledReport]:
        """Return daily and weekly reports that are due and not already sent."""
        if not self.enabled or not self.db_path.exists():
            return []

        local_now = (now or datetime.now(timezone.utc)).astimezone(self.timezone)
        state = self._read_state()
        reports: list[ScheduledReport] = []

        daily_key = local_now.strftime("%Y-%m-%d")
        if local_now.hour >= DAILY_REPORT_HOUR and state.get("daily") != daily_key:
            start = datetime.combine(local_now.date(), time.min, tzinfo=self.timezone)
            end = start + timedelta(days=1)
            reports.append(
                ScheduledReport(
                    report_type="daily",
                    period_key=daily_key,
                    message=self._render_report("Daily", daily_key, start, end),
                )
            )

        weekly_start_date = local_now.date() - timedelta(days=local_now.weekday())
        weekly_key = f"{weekly_start_date.isocalendar().year}-W{weekly_start_date.isocalendar().week:02d}"
        if (
            local_now.weekday() == WEEKLY_REPORT_WEEKDAY
            and local_now.hour >= WEEKLY_REPORT_HOUR
            and state.get("weekly") != weekly_key
        ):
            start = datetime.combine(weekly_start_date, time.min, tzinfo=self.timezone)
            end = start + timedelta(days=7)
            reports.append(
                ScheduledReport(
                    report_type="weekly",
                    period_key=weekly_key,
                    message=self._render_report("Weekly", weekly_key, start, end),
                )
            )

        return reports

    def mark_sent(self, report: ScheduledReport) -> None:
        """Persist the latest sent period after Telegram delivery succeeds."""
        state = self._read_state()
        state[report.report_type] = report.period_key
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _render_report(self, label: str, period_key: str, local_start: datetime, local_end: datetime) -> str:
        """Render an operator-focused report for the requested period."""
        data = self._load_period_data(local_start, local_end)
        scan_runs = data["scan_runs"]
        snapshots = data["snapshots"]
        signal_events = data["signal_events"]
        latest = self._latest_scan(snapshots)

        alert_counts = self._counts(snapshots, "alert_level")
        narrative_counts = self._counts(snapshots, "narrative")
        age_counts = self._counts(snapshots, "token_age_bucket")
        outcome_counts = self._counts(signal_events, "outcome_status")

        lines = [
            f"Alpha Hunter Market System v1.2 - {label} Report",
            f"period: {period_key}",
            f"timezone: {self.timezone.key}",
            f"scan_count: {len(scan_runs)}",
            f"snapshot_count: {len(snapshots)}",
            f"new_signal_events: {len(signal_events)}",
            f"first_seen_total: {self._sum_numeric(snapshots, 'is_first_seen')}",
            f"watch_total: {alert_counts.get('WATCH', 0)}",
            f"high_total: {alert_counts.get('HIGH', 0)}",
            f"critical_total: {alert_counts.get('CRITICAL', 0)}",
            f"risk_filtered_high_risk: {self._high_risk_count(snapshots)}",
            f"max_early_alpha_score: {self._max_numeric(snapshots, 'early_alpha_score')}",
            f"top_narratives: {self._top_counts(narrative_counts)}",
            f"age_distribution: {self._top_counts(age_counts)}",
            f"signal_outcomes: {self._top_counts(outcome_counts)}",
            "",
            "Top Signals:",
        ]

        if signal_events.empty:
            lines.append("- No new signal transition events in this period.")
        else:
            for _, event in signal_events.sort_values(
                ["early_alpha_score", "agent_score"],
                ascending=[False, False],
            ).head(5).iterrows():
                lines.append(
                    "- "
                    f"{event.get('symbol')} {event.get('event_type')} "
                    f"{event.get('previous_alert_level')}->{event.get('alert_level')} "
                    f"early_alpha={self._number(event.get('early_alpha_score'))} "
                    f"age={event.get('token_age_bucket')} "
                    f"risk={event.get('rug_risk_level')}"
                )

        lines.extend(["", "Current Watchlist:"])
        if latest.empty:
            lines.append("- No latest scan rows available.")
        else:
            for _, token in latest.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False]).head(5).iterrows():
                lines.append(
                    "- "
                    f"{token.get('symbol')} "
                    f"alert={token.get('alert_level')} "
                    f"early_alpha={self._number(token.get('early_alpha_score'))} "
                    f"scan_count={int(token.get('scan_count') or 0)} "
                    f"age={token.get('token_age_bucket')} "
                    f"risk={token.get('rug_risk_level')}"
                )

        lines.extend(
            [
                "",
                f"Conclusion: {self._conclusion(snapshots, signal_events)}",
                "Safety: read-only market intelligence; no wallet, no private keys, no trading.",
            ]
        )
        return "\n".join(lines)

    def _load_period_data(self, local_start: datetime, local_end: datetime) -> dict[str, pd.DataFrame]:
        start = local_start.astimezone(timezone.utc).isoformat()
        end = local_end.astimezone(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            scan_runs = pd.read_sql_query(
                """
                SELECT *
                FROM scan_runs
                WHERE started_at >= ? AND started_at < ?
                ORDER BY started_at ASC, id ASC
                """,
                conn,
                params=(start, end),
            )
            snapshots = pd.read_sql_query(
                """
                SELECT *
                FROM token_snapshots
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC, id ASC
                """,
                conn,
                params=(start, end),
            )
            signal_events = pd.read_sql_query(
                """
                SELECT *
                FROM signal_events
                WHERE created_at >= ? AND created_at < ?
                ORDER BY created_at ASC, id ASC
                """,
                conn,
                params=(start, end),
            )
        return {
            "scan_runs": scan_runs,
            "snapshots": snapshots,
            "signal_events": signal_events,
        }

    def _latest_scan(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        if snapshots.empty or "scan_run_id" not in snapshots.columns:
            return snapshots.head(0)
        latest_scan_run_id = snapshots["scan_run_id"].max()
        return snapshots[snapshots["scan_run_id"] == latest_scan_run_id].copy()

    def _conclusion(self, snapshots: pd.DataFrame, signal_events: pd.DataFrame) -> str:
        if snapshots.empty:
            return "No usable scan data was collected during this period."
        high_or_critical = snapshots["alert_level"].isin(["HIGH", "CRITICAL"]).sum()
        first_seen = self._sum_numeric(snapshots, "is_first_seen")
        max_score = float(pd.to_numeric(snapshots.get("early_alpha_score", 0), errors="coerce").fillna(0).max())
        if high_or_critical:
            return "Market produced high-priority signals; review top events before the next session."
        if len(signal_events) and max_score >= 60:
            return "Fresh signal activity appeared, but conviction stayed below HIGH."
        if first_seen:
            return "New tokens entered the system, but current quality/risk filters kept them below priority alert level."
        return "Quiet market period; scanner stayed active and mostly filtered repeated or old-token noise."

    def _read_state(self) -> dict[str, Any]:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _counts(self, frame: pd.DataFrame, column: str) -> dict[str, int]:
        if frame.empty or column not in frame.columns:
            return {}
        counts = frame[column].fillna("UNKNOWN").value_counts().head(5).to_dict()
        return {str(key): int(value) for key, value in counts.items()}

    def _top_counts(self, counts: dict[str, int]) -> str:
        if not counts:
            return "none"
        return ", ".join(f"{key}={value}" for key, value in counts.items())

    def _sum_numeric(self, frame: pd.DataFrame, column: str) -> int:
        if frame.empty or column not in frame.columns:
            return 0
        return int(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())

    def _max_numeric(self, frame: pd.DataFrame, column: str) -> str:
        if frame.empty or column not in frame.columns:
            return "0.00"
        return self._number(pd.to_numeric(frame[column], errors="coerce").fillna(0).max())

    def _high_risk_count(self, snapshots: pd.DataFrame) -> int:
        if snapshots.empty or "rug_risk_level" not in snapshots.columns:
            return 0
        return int((snapshots["rug_risk_level"] == "HIGH").sum())

    def _number(self, value: object) -> str:
        if pd.isna(value):
            return "0.00"
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)
