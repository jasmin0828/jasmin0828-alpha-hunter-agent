"""Risk Intelligence Engine for Alpha Hunter Agent v0.9.1."""

from __future__ import annotations

import pandas as pd


class RiskIntelligenceService:
    """Calculate rule-based rug-risk signals without wallet access or trading."""

    def analyze_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add risk intelligence fields to token snapshots."""
        if tokens.empty:
            return self._ensure_columns(tokens.copy())

        enriched = self._ensure_columns(tokens.copy())
        liquidity = pd.to_numeric(enriched["liquidity_usd"], errors="coerce").fillna(0)
        volume = pd.to_numeric(enriched["volume_24h"], errors="coerce").fillna(0)
        fdv = pd.to_numeric(enriched["fdv"], errors="coerce").fillna(0)
        price_change = pd.to_numeric(enriched["price_change_24h"], errors="coerce").fillna(0)
        base_risk = pd.to_numeric(enriched["risk_score"], errors="coerce").fillna(0)

        enriched["volume_liquidity_ratio"] = self._safe_ratio(volume, liquidity)
        enriched["fdv_liquidity_ratio"] = self._safe_ratio(fdv, liquidity)
        enriched["suspicious_volume_flag"] = enriched["volume_liquidity_ratio"] > 10
        enriched["extreme_pump_flag"] = price_change > 150
        enriched["low_liquidity_flag"] = liquidity < 100_000

        rule_score = (
            base_risk
            + enriched["suspicious_volume_flag"].astype(int) * 25
            + enriched["extreme_pump_flag"].astype(int) * 20
            + enriched["low_liquidity_flag"].astype(int) * 15
            + (enriched["fdv_liquidity_ratio"] > 50).astype(int) * 35
            + (enriched["token_age_bucket"] == "NEWBORN").astype(int) * 20
            + (enriched["token_age_bucket"] == "EARLY").astype(int) * 10
        ).clip(lower=0, upper=100)

        enriched["rug_risk_score"] = rule_score.round(2)
        enriched["rug_risk_level"] = enriched.apply(self._risk_level, axis=1)
        enriched["risk_notes"] = enriched.apply(self._risk_notes, axis=1)
        return enriched

    def _ensure_columns(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Create expected input and output columns with safe defaults."""
        defaults = {
            "liquidity_usd": 0,
            "volume_24h": 0,
            "fdv": 0,
            "price_change_24h": 0,
            "risk_score": 0,
            "rug_risk_level": "LOW",
            "rug_risk_score": 0,
            "volume_liquidity_ratio": 0,
            "fdv_liquidity_ratio": 0,
            "extreme_pump_flag": False,
            "low_liquidity_flag": False,
            "suspicious_volume_flag": False,
            "risk_notes": "",
            "token_age_bucket": "UNKNOWN",
            "token_age_hours": pd.NA,
        }
        for column, default in defaults.items():
            if column not in tokens.columns:
                tokens[column] = default
        return tokens

    def _safe_ratio(self, numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        """Divide two numeric series and return zero when the denominator is invalid."""
        denominator = denominator.replace(0, pd.NA)
        return (numerator / denominator).replace([pd.NA, pd.NaT], 0).fillna(0)

    def _risk_level(self, token: pd.Series) -> str:
        """Convert rule outputs into LOW, MEDIUM, or HIGH rug risk."""
        risk_score = float(token.get("risk_score") or 0)
        rug_risk_score = float(token.get("rug_risk_score") or 0)
        fdv_liquidity_ratio = float(token.get("fdv_liquidity_ratio") or 0)

        if risk_score >= 50 or rug_risk_score >= 50 or fdv_liquidity_ratio > 50:
            return "HIGH"
        if risk_score >= 25 or rug_risk_score >= 25:
            return "MEDIUM"
        return "LOW"

    def _risk_notes(self, token: pd.Series) -> str:
        """Build concise risk notes for dashboards and Telegram alerts."""
        notes: list[str] = []
        if bool(token.get("suspicious_volume_flag")):
            notes.append("volume/liquidity ratio > 10")
        if float(token.get("fdv_liquidity_ratio") or 0) > 50:
            notes.append("FDV/liquidity ratio > 50")
        if bool(token.get("extreme_pump_flag")):
            notes.append("24h price change > 150%")
        if bool(token.get("low_liquidity_flag")):
            notes.append("liquidity below 100k")
        token_age_bucket = token.get("token_age_bucket") or "UNKNOWN"
        token_age_hours = token.get("token_age_hours")
        if token_age_bucket == "OLD":
            notes.append("age bucket OLD: alpha freshness decay")
        if pd.isna(token_age_hours):
            notes.append(f"age bucket {token_age_bucket}")
        else:
            notes.append(f"age bucket {token_age_bucket} ({float(token_age_hours):.2f}h)")
        if not notes:
            notes.append("no major rule-based risk flags")
        return "; ".join(notes)
