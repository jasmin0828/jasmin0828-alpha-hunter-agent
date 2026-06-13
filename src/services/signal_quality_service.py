"""Signal quality analytics for Alpha Hunter Market System."""

from __future__ import annotations

from typing import Any

import pandas as pd


class SignalQualityService:
    """Calculate reusable quality metrics for signal analysis and memory."""

    ALERT_LEVELS = ["CRITICAL", "HIGH", "WATCH"]

    def summarize(self, snapshots: pd.DataFrame, signal_events: pd.DataFrame) -> dict[str, Any]:
        """Return quality metrics for the latest scan and available signal events."""
        if snapshots.empty:
            return {
                "watch_count": 0,
                "high_count": 0,
                "critical_count": 0,
                "old_watch_count": 0,
                "repeated_watch_count": 0,
                "fresh_signal_count": int(len(signal_events)),
                "signal_event_distribution": self._event_distribution(signal_events),
                "outcome_distribution": self._outcome_distribution(signal_events),
                "risk_filtered_alert_count": 0,
                "avg_early_alpha_alert_score": 0,
                "top_repeated_watch": [],
            }

        frame = snapshots.copy()
        frame["scan_count"] = pd.to_numeric(frame.get("scan_count", 0), errors="coerce").fillna(0)
        frame["early_alpha_score"] = pd.to_numeric(frame.get("early_alpha_score", 0), errors="coerce").fillna(0)
        alert_mask = frame["alert_level"].isin(self.ALERT_LEVELS)
        watch_mask = frame["alert_level"] == "WATCH"
        old_watch_mask = watch_mask & (frame["token_age_bucket"] == "OLD")
        repeated_watch_mask = watch_mask & (frame["scan_count"] > 20)
        risk_filtered_alert_mask = alert_mask & (frame["rug_risk_level"] == "HIGH")
        alert_scores = frame.loc[alert_mask, "early_alpha_score"]

        return {
            "watch_count": int(watch_mask.sum()),
            "high_count": int((frame["alert_level"] == "HIGH").sum()),
            "critical_count": int((frame["alert_level"] == "CRITICAL").sum()),
            "old_watch_count": int(old_watch_mask.sum()),
            "repeated_watch_count": int(repeated_watch_mask.sum()),
            "fresh_signal_count": int(len(signal_events)),
            "signal_event_distribution": self._event_distribution(signal_events),
            "outcome_distribution": self._outcome_distribution(signal_events),
            "risk_filtered_alert_count": int(risk_filtered_alert_mask.sum()),
            "avg_early_alpha_alert_score": round(float(alert_scores.mean()), 2) if not alert_scores.empty else 0,
            "top_repeated_watch": self._top_repeated_watch(frame[repeated_watch_mask]),
        }

    def _top_repeated_watch(self, repeated_watch: pd.DataFrame) -> list[dict[str, Any]]:
        """Return compact repeated WATCH rows for manifest and memory."""
        if repeated_watch.empty:
            return []
        rows: list[dict[str, Any]] = []
        for _, token in repeated_watch.sort_values(["scan_count", "early_alpha_score"], ascending=[False, False]).head(10).iterrows():
            rows.append(
                {
                    "symbol": str(token.get("symbol") or "N/A"),
                    "scan_count": int(token.get("scan_count") or 0),
                    "early_alpha_score": round(float(token.get("early_alpha_score") or 0), 2),
                    "token_age_bucket": str(token.get("token_age_bucket") or "UNKNOWN"),
                    "rug_risk_level": str(token.get("rug_risk_level") or "UNKNOWN"),
                }
            )
        return rows

    def _event_distribution(self, signal_events: pd.DataFrame) -> dict[str, int]:
        """Return signal event type counts."""
        if signal_events.empty or "event_type" not in signal_events.columns:
            return {}
        return {str(key): int(value) for key, value in signal_events["event_type"].fillna("UNKNOWN").value_counts().to_dict().items()}

    def _outcome_distribution(self, signal_events: pd.DataFrame) -> dict[str, int]:
        """Return signal outcome status counts."""
        if signal_events.empty or "outcome_status" not in signal_events.columns:
            return {}
        return {
            str(key): int(value)
            for key, value in signal_events["outcome_status"].fillna("PENDING").value_counts().to_dict().items()
        }
