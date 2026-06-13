"""Theme Scanner Agent for Alpha Hunter Market System v1.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ThemeScanResult:
    """Structured theme output produced from current market intelligence data."""

    theme_name: str
    description: str
    source: str
    related_tokens: list[str]
    signal_strength: float
    reason: str
    detected_at: str


class ThemeScannerAgent:
    """Detect active themes from narrative, trend, and Early Alpha fields."""

    SOURCE = "DexScreener + NarrativeService + TrendService + EarlyAlphaService"
    ALERT_LEVELS = {"WATCH", "HIGH", "CRITICAL"}
    MAX_RELATED_TOKENS = 5

    def scan(self, snapshots: pd.DataFrame) -> list[ThemeScanResult]:
        """Return theme summaries from the latest token snapshot set."""
        frame = self._prepare_frame(snapshots)
        if frame.empty:
            return []

        results = [
            self._theme_from_group(str(theme_name or "Unknown"), group)
            for theme_name, group in frame.groupby("narrative", dropna=False)
        ]
        return sorted(results, key=lambda result: result.signal_strength, reverse=True)

    def scan_as_dicts(self, snapshots: pd.DataFrame) -> list[dict[str, Any]]:
        """Return JSON-serializable theme summaries."""
        return [asdict(result) for result in self.scan(snapshots)]

    def _prepare_frame(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        """Normalize expected columns without mutating the caller's dataframe."""
        if snapshots.empty:
            return snapshots.copy()

        frame = snapshots.copy()
        defaults: dict[str, Any] = {
            "symbol": "",
            "token_name": "",
            "narrative": "Unknown",
            "narrative_score": 20,
            "early_alpha_score": 0,
            "agent_score": 0,
            "alpha_score": 0,
            "volume_24h": 0,
            "liquidity_usd": 0,
            "score_change_10m": 0,
            "volume_spike_ratio": 1,
            "momentum_status": "STABLE",
            "is_first_seen": 0,
            "consecutive_up_count": 0,
            "alert_level": "IGNORE",
            "rug_risk_level": "UNKNOWN",
            "created_at": pd.NA,
        }
        for column, default in defaults.items():
            if column not in frame.columns:
                frame[column] = default

        for column in [
            "narrative_score",
            "early_alpha_score",
            "agent_score",
            "alpha_score",
            "volume_24h",
            "liquidity_usd",
            "score_change_10m",
            "volume_spike_ratio",
            "consecutive_up_count",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

        frame["narrative"] = frame["narrative"].fillna("Unknown").replace("", "Unknown")
        frame["created_at"] = pd.to_datetime(frame["created_at"], errors="coerce", utc=True)
        return frame

    def _theme_from_group(self, theme_name: str, group: pd.DataFrame) -> ThemeScanResult:
        """Build one theme result from a narrative group."""
        signal_strength = self._signal_strength(group)
        related_tokens = self._related_tokens(group)
        detected_at = self._detected_at(group)
        return ThemeScanResult(
            theme_name=theme_name,
            description=self._description(theme_name, group),
            source=self.SOURCE,
            related_tokens=related_tokens,
            signal_strength=signal_strength,
            reason=self._reason(group),
            detected_at=detected_at,
        )

    def _signal_strength(self, group: pd.DataFrame) -> float:
        """Calculate a bounded 0-100 theme strength score."""
        token_count = len(group)
        alert_ratio = self._ratio(group["alert_level"].isin(self.ALERT_LEVELS).sum(), token_count)
        heating_ratio = self._ratio(group["momentum_status"].isin(["HEATING_UP", "HOT"]).sum(), token_count)
        first_seen_ratio = self._ratio(pd.to_numeric(group["is_first_seen"], errors="coerce").fillna(0).sum(), token_count)
        consecutive_ratio = self._ratio((group["consecutive_up_count"] > 0).sum(), token_count)
        high_risk_ratio = self._ratio((group["rug_risk_level"] == "HIGH").sum(), token_count)

        score = (
            group["early_alpha_score"].max() * 0.30
            + group["agent_score"].max() * 0.20
            + group["narrative_score"].max() * 0.15
            + min(group["volume_spike_ratio"].max(), 3) * 8
            + max(group["score_change_10m"].max(), 0) * 0.40
            + alert_ratio * 15
            + heating_ratio * 12
            + first_seen_ratio * 10
            + consecutive_ratio * 10
            - high_risk_ratio * 15
        )
        return round(max(0, min(100, float(score))), 2)

    def _related_tokens(self, group: pd.DataFrame) -> list[str]:
        """Return top token symbols tied to the theme."""
        ranked = group.sort_values(
            ["early_alpha_score", "agent_score", "volume_24h"],
            ascending=[False, False, False],
        )
        tokens: list[str] = []
        for _, token in ranked.head(self.MAX_RELATED_TOKENS).iterrows():
            symbol = str(token.get("symbol") or "").strip()
            name = str(token.get("token_name") or "").strip()
            label = symbol or name
            if label and label not in tokens:
                tokens.append(label)
        return tokens

    def _description(self, theme_name: str, group: pd.DataFrame) -> str:
        """Describe what the theme represents in the current scan."""
        token_count = len(group)
        top_token = self._related_tokens(group)[:1]
        lead = top_token[0] if top_token else "no leading token"
        if theme_name == "Unknown":
            return f"Unclassified market activity across {token_count} token(s), led by {lead}."
        return f"{theme_name} narrative activity across {token_count} token(s), led by {lead}."

    def _reason(self, group: pd.DataFrame) -> str:
        """Explain why the theme appeared in the output."""
        token_count = len(group)
        alert_count = int(group["alert_level"].isin(self.ALERT_LEVELS).sum())
        heating_count = int(group["momentum_status"].isin(["HEATING_UP", "HOT"]).sum())
        first_seen_count = int(pd.to_numeric(group["is_first_seen"], errors="coerce").fillna(0).sum())
        consecutive_count = int((group["consecutive_up_count"] > 0).sum())
        max_early_alpha = float(group["early_alpha_score"].max())
        max_volume_spike = float(group["volume_spike_ratio"].max())

        parts = [
            f"{token_count} related token(s)",
            f"max early_alpha_score {max_early_alpha:.2f}",
        ]
        if alert_count:
            parts.append(f"{alert_count} active alert token(s)")
        if heating_count:
            parts.append(f"{heating_count} heating/hot token(s)")
        if first_seen_count:
            parts.append(f"{first_seen_count} first-seen token(s)")
        if consecutive_count:
            parts.append(f"{consecutive_count} consecutive momentum token(s)")
        if max_volume_spike > 1:
            parts.append(f"max volume_spike_ratio {max_volume_spike:.2f}")
        return "; ".join(parts)

    def _detected_at(self, group: pd.DataFrame) -> str:
        """Use the latest source row time or current UTC time."""
        latest = group["created_at"].max()
        if pd.isna(latest):
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return pd.Timestamp(latest).to_pydatetime().replace(microsecond=0).isoformat()

    def _ratio(self, numerator: object, denominator: int) -> float:
        """Return a zero-safe ratio."""
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)
