"""Token Age Intelligence for Alpha Hunter Market System."""

from __future__ import annotations

import time

import pandas as pd


class TokenAgeService:
    """Calculate pair age buckets from DexScreener pair_created_at timestamps."""

    def analyze_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add token age minutes, hours, and bucket fields."""
        enriched = tokens.copy()
        if enriched.empty:
            return self._ensure_columns(enriched)

        enriched = self._ensure_columns(enriched)
        now_ms = int(time.time() * 1000)
        pair_created_at = pd.to_numeric(enriched["pair_created_at"], errors="coerce")

        ages = pair_created_at.apply(lambda value: self._age_from_timestamp(value, now_ms))
        enriched["token_age_minutes"] = ages.apply(lambda item: item[0])
        enriched["token_age_hours"] = ages.apply(lambda item: item[1])
        enriched["token_age_bucket"] = ages.apply(lambda item: item[2])
        return enriched

    def _ensure_columns(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Ensure age output columns exist for empty or partial dataframes."""
        defaults = {
            "pair_created_at": pd.NA,
            "token_age_minutes": pd.NA,
            "token_age_hours": pd.NA,
            "token_age_bucket": "UNKNOWN",
        }
        for column, default in defaults.items():
            if column not in tokens.columns:
                tokens[column] = default
        return tokens

    def _age_from_timestamp(self, value: float, now_ms: int) -> tuple[float | None, float | None, str]:
        """Convert a DexScreener timestamp into age metrics and a bucket."""
        if pd.isna(value) or value <= 0:
            return None, None, "UNKNOWN"

        timestamp_ms = float(value)
        if timestamp_ms < 10_000_000_000:
            timestamp_ms *= 1000

        age_minutes = max((now_ms - timestamp_ms) / 60_000, 0)
        age_hours = age_minutes / 60
        return round(age_minutes, 2), round(age_hours, 2), self._bucket(age_minutes)

    def _bucket(self, age_minutes: float) -> str:
        """Classify token age into v0.9.1 buckets."""
        if age_minutes < 15:
            return "NEWBORN"
        if age_minutes <= 120:
            return "EARLY"
        if age_minutes <= 24 * 60:
            return "TRENDING"
        if age_minutes <= 7 * 24 * 60:
            return "MATURE"
        return "OLD"
