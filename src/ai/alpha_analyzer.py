"""AI Intelligence Layer v0.4 for token scoring and risk summaries."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd


class AlphaAnalyzer:
    """Score alpha potential and risk using deterministic market-data rules."""

    LOW_LIQUIDITY_USD = 75_000
    HEALTHY_LIQUIDITY_USD = 250_000
    HIGH_VOLUME_USD = 1_000_000
    LOW_FDV_USD = 5_000_000
    MODERATE_FDV_USD = 20_000_000
    NEW_PAIR_HOURS = 24
    VERY_NEW_PAIR_HOURS = 6

    def analyze_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add AI scores and summary columns for every token row."""
        if tokens.empty:
            analyzed = tokens.copy()
            analyzed["alpha_score"] = pd.Series(dtype="float64")
            analyzed["risk_score"] = pd.Series(dtype="float64")
            analyzed["ai_summary"] = pd.Series(dtype="object")
            return analyzed

        analyzed = tokens.copy()

        # Apply row-level analysis so every token gets its own explainable result.
        results = analyzed.apply(self._analyze_token, axis=1, result_type="expand")
        analyzed["alpha_score"] = results["alpha_score"]
        analyzed["risk_score"] = results["risk_score"]
        analyzed["ai_summary"] = results["ai_summary"]
        return analyzed

    def _analyze_token(self, token: pd.Series) -> dict[str, Any]:
        """Analyze one token and return alpha score, risk score, and summary."""
        liquidity_usd = self._number(token.get("liquidity_usd"))
        volume_24h = self._number(token.get("volume_24h"))
        fdv = self._number(token.get("fdv"))
        price_change_24h = self._number(token.get("price_change_24h"))
        pair_age_hours = self._pair_age_hours(token.get("pair_created_at"))

        alpha_score = self._calculate_alpha_score(
            liquidity_usd=liquidity_usd,
            volume_24h=volume_24h,
            fdv=fdv,
            price_change_24h=price_change_24h,
            pair_age_hours=pair_age_hours,
        )
        risk_score = self._calculate_risk_score(
            liquidity_usd=liquidity_usd,
            volume_24h=volume_24h,
            fdv=fdv,
            price_change_24h=price_change_24h,
            pair_age_hours=pair_age_hours,
        )
        summary = self._build_ai_summary(
            liquidity_usd=liquidity_usd,
            volume_24h=volume_24h,
            fdv=fdv,
            price_change_24h=price_change_24h,
            pair_age_hours=pair_age_hours,
            risk_score=risk_score,
        )

        return {
            "alpha_score": round(alpha_score, 2),
            "risk_score": round(risk_score, 2),
            "ai_summary": " | ".join(summary),
        }

    def _calculate_alpha_score(
        self,
        liquidity_usd: float,
        volume_24h: float,
        fdv: float,
        price_change_24h: float,
        pair_age_hours: float | None,
    ) -> float:
        """Calculate a 0-100 alpha score from momentum, liquidity, FDV, and age."""
        score = 0.0

        # Liquidity improves execution quality and reduces fragile token setups.
        if liquidity_usd >= self.HEALTHY_LIQUIDITY_USD:
            score += 25
        elif liquidity_usd >= self.LOW_LIQUIDITY_USD:
            score += 17
        else:
            score += 8

        # Volume is the primary attention signal for this Market Intelligence run.
        if volume_24h >= self.HIGH_VOLUME_USD:
            score += 25
        elif volume_24h >= 300_000:
            score += 18
        else:
            score += 10

        # Smaller FDV can leave more upside, while very large FDV lowers alpha.
        if fdv <= self.LOW_FDV_USD:
            score += 20
        elif fdv <= self.MODERATE_FDV_USD:
            score += 14
        else:
            score += 7

        # Positive but not extreme momentum receives the strongest score.
        if 20 <= price_change_24h <= 120:
            score += 20
        elif 0 <= price_change_24h < 20 or 120 < price_change_24h <= 200:
            score += 12
        else:
            score += 5

        # Newer pairs can be attractive, but extremely new pairs are penalized.
        if pair_age_hours is None:
            score += 5
        elif self.VERY_NEW_PAIR_HOURS <= pair_age_hours <= 72:
            score += 10
        elif pair_age_hours < self.VERY_NEW_PAIR_HOURS:
            score += 4
        else:
            score += 7

        return self._clamp(score, 0, 100)

    def _calculate_risk_score(
        self,
        liquidity_usd: float,
        volume_24h: float,
        fdv: float,
        price_change_24h: float,
        pair_age_hours: float | None,
    ) -> float:
        """Calculate a 0-100 risk score where higher values mean higher risk."""
        score = 10.0

        # Low liquidity is a direct rug and slippage risk indicator.
        if liquidity_usd < self.LOW_LIQUIDITY_USD:
            score += 30
        elif liquidity_usd < self.HEALTHY_LIQUIDITY_USD:
            score += 15

        # Volume far above liquidity can indicate wash trading or unstable flows.
        volume_liquidity_ratio = volume_24h / liquidity_usd if liquidity_usd else float("inf")
        if volume_liquidity_ratio > 20:
            score += 25
        elif volume_liquidity_ratio > 8:
            score += 15

        # Very new pairs deserve extra caution because history is limited.
        if pair_age_hours is None:
            score += 8
        elif pair_age_hours < self.VERY_NEW_PAIR_HOURS:
            score += 20
        elif pair_age_hours < self.NEW_PAIR_HOURS:
            score += 10

        # Extreme 24h moves can reverse quickly and often attract speculative flow.
        if price_change_24h > 150:
            score += 18
        elif price_change_24h < -20:
            score += 12

        # Very low FDV plus high volume can be explosive, but also easier to manipulate.
        if fdv < 1_000_000 and volume_24h > 300_000:
            score += 12

        return self._clamp(score, 0, 100)

    def _build_ai_summary(
        self,
        liquidity_usd: float,
        volume_24h: float,
        fdv: float,
        price_change_24h: float,
        pair_age_hours: float | None,
        risk_score: float,
    ) -> list[str]:
        """Generate short AI Summary bullets for dashboard and Telegram output."""
        summary: list[str] = []

        if price_change_24h >= 20:
            summary.append("Strong momentum detected")
        elif price_change_24h >= 0:
            summary.append("Positive momentum detected")
        else:
            summary.append("Momentum is cooling")

        if liquidity_usd >= self.HEALTHY_LIQUIDITY_USD:
            summary.append("Healthy liquidity")
        elif liquidity_usd < self.LOW_LIQUIDITY_USD:
            summary.append("Low liquidity warning")
        else:
            summary.append("Moderate liquidity")

        if fdv <= self.LOW_FDV_USD:
            summary.append("Low FDV")
        elif fdv <= self.MODERATE_FDV_USD:
            summary.append("Moderate FDV")
        else:
            summary.append("Elevated FDV")

        summary.append(f"Rug risk: {self._rug_risk_label(risk_score)}")

        if self._is_suspicious_volume(liquidity_usd, volume_24h):
            summary.append("Suspicious volume pattern detected")

        if pair_age_hours is not None and pair_age_hours < self.NEW_PAIR_HOURS:
            summary.append("Short-term speculative activity possible")

        return summary

    def _rug_risk_label(self, risk_score: float) -> str:
        """Convert numeric risk score into a simple rug-risk label."""
        if risk_score >= 70:
            return "HIGH"
        if risk_score >= 40:
            return "MEDIUM"
        return "LOW"

    def _is_suspicious_volume(self, liquidity_usd: float, volume_24h: float) -> bool:
        """Flag volume that is high relative to available liquidity."""
        if liquidity_usd <= 0:
            return True

        return volume_24h / liquidity_usd > 8

    def _pair_age_hours(self, pair_created_at: Any) -> float | None:
        """Convert DexScreener pair creation timestamp in milliseconds to age hours."""
        created_at = self._number(pair_created_at)
        if created_at <= 0:
            return None

        now_ms = time.time() * 1000
        age_hours = (now_ms - created_at) / 3_600_000
        return max(age_hours, 0)

    def _number(self, value: Any) -> float:
        """Safely convert unknown values into floats for scoring."""
        if pd.isna(value):
            return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        """Keep scores inside the configured 0-100 range."""
        return max(minimum, min(value, maximum))
