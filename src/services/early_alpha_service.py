"""Early Alpha Engine for Alpha Hunter Agent v1.1."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


class EarlyAlphaService:
    """Detect first-seen tokens and repeated momentum without trading or wallets."""

    AGE_BONUS = {
        "NEWBORN": 20,
        "EARLY": 15,
        "TRENDING": 10,
    }

    def analyze_tokens(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        """Add v1.1 early alpha fields to all token snapshots."""
        enriched = self._ensure_columns(snapshots.copy())
        if enriched.empty:
            return enriched

        enriched["created_at"] = pd.to_datetime(enriched["created_at"], errors="coerce", utc=True)
        enriched = enriched.sort_values(["token_address", "created_at", "id"]).reset_index(drop=True)

        enriched["first_seen_at"] = pd.NA
        enriched["is_first_seen"] = False
        enriched["scan_count"] = 0
        enriched["consecutive_up_count"] = 0

        for _, group in enriched.groupby("token_address", dropna=False):
            if group.empty:
                continue

            first_seen_at = group["created_at"].min()
            for position, row_index in enumerate(group.index, start=1):
                history = group.loc[:row_index]
                recent = history.tail(3)
                enriched.at[row_index, "first_seen_at"] = self._iso_time(first_seen_at)
                enriched.at[row_index, "is_first_seen"] = position == 1
                enriched.at[row_index, "scan_count"] = position
                enriched.at[row_index, "consecutive_up_count"] = self._consecutive_up_count(recent)

        enriched["early_alpha_score"] = enriched.apply(self._early_alpha_score, axis=1)
        enriched["early_alpha_reason"] = enriched.apply(self._early_alpha_reason, axis=1)
        return enriched

    def _ensure_columns(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        """Ensure required input and output columns exist."""
        defaults = {
            "id": 0,
            "token_address": "",
            "created_at": pd.NA,
            "alpha_score": 0,
            "volume_24h": 0,
            "price_usd": 0,
            "agent_score": 0,
            "token_age_bucket": "UNKNOWN",
            "momentum_status": "STABLE",
            "rug_risk_level": "LOW",
            "suspicious_volume_flag": False,
            "first_seen_at": pd.NA,
            "is_first_seen": False,
            "scan_count": 0,
            "consecutive_up_count": 0,
            "early_alpha_score": 0,
            "early_alpha_reason": "",
        }
        for column, default in defaults.items():
            if column not in snapshots.columns:
                snapshots[column] = default
        return snapshots

    def _consecutive_up_count(self, recent: pd.DataFrame) -> int:
        """Count alpha, volume, and price fields that rose across the latest 3 snapshots."""
        if len(recent) < 3:
            return 0

        count = 0
        for column in ["alpha_score", "volume_24h", "price_usd"]:
            values = pd.to_numeric(recent[column], errors="coerce")
            if values.isna().any():
                continue
            if values.iloc[0] < values.iloc[1] < values.iloc[2]:
                count += 1
        return count

    def _early_alpha_score(self, token: pd.Series) -> float:
        """Calculate bounded v1.1 early alpha score."""
        score = float(token.get("agent_score") or 0)
        age_bucket = token.get("token_age_bucket") or "UNKNOWN"
        rug_risk_level = token.get("rug_risk_level") or "LOW"

        if bool(token.get("is_first_seen")):
            score += 15
        score += self.AGE_BONUS.get(age_bucket, 0)
        score += int(token.get("consecutive_up_count") or 0) * 8
        if token.get("momentum_status") == "HEATING_UP":
            score += 10
        if rug_risk_level == "LOW":
            score += 10
        if age_bucket == "OLD":
            score -= 15
        if rug_risk_level == "HIGH":
            score -= 30
        if bool(token.get("suspicious_volume_flag")):
            score -= 10

        return round(max(0, min(100, score)), 2)

    def _early_alpha_reason(self, token: pd.Series) -> str:
        """Explain the Early Alpha Engine score drivers."""
        reasons: list[str] = []
        age_bucket = token.get("token_age_bucket") or "UNKNOWN"
        rug_risk_level = token.get("rug_risk_level") or "LOW"
        consecutive_up_count = int(token.get("consecutive_up_count") or 0)

        if bool(token.get("is_first_seen")):
            reasons.append("first seen")
        if age_bucket in ["NEWBORN", "EARLY", "TRENDING"]:
            reasons.append("early age bucket")
        if consecutive_up_count > 0:
            reasons.append("consecutive momentum")
        if token.get("momentum_status") == "HEATING_UP":
            reasons.append("heating up")
        if rug_risk_level == "LOW":
            reasons.append("low rug risk")
        if age_bucket == "OLD":
            reasons.append("old token penalty")
        if rug_risk_level == "HIGH":
            reasons.append("high rug risk penalty")
        if bool(token.get("suspicious_volume_flag")):
            reasons.append("suspicious volume penalty")
        if not reasons:
            reasons.append("baseline agent score")
        return "; ".join(reasons)

    def _iso_time(self, value: pd.Timestamp | datetime) -> str:
        """Return UTC ISO text for timestamps stored in SQLite and CSV."""
        if pd.isna(value):
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        return pd.Timestamp(value).to_pydatetime().replace(microsecond=0).isoformat()
