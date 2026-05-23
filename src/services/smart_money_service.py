"""Simulated Smart Money Intelligence for Alpha Hunter Agent v0.8."""

from __future__ import annotations

import pandas as pd


class SmartMoneyService:
    """Generate simulated smart_money_score and smart_money_signal."""

    def analyze_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add smart money columns using public market-derived heuristics."""
        if tokens.empty:
            result = tokens.copy()
            result["smart_money_score"] = pd.Series(dtype="float64")
            result["smart_money_signal"] = pd.Series(dtype="object")
            return result

        result = tokens.copy()
        smart = result.apply(self._analyze_row, axis=1, result_type="expand")
        result["smart_money_score"] = smart["smart_money_score"]
        result["smart_money_signal"] = smart["smart_money_signal"]
        return result

    def _analyze_row(self, row: pd.Series) -> dict[str, object]:
        """Score accumulation intent from liquidity, volume, alpha, risk, and momentum."""
        alpha_score = self._number(row.get("alpha_score"))
        risk_score = self._number(row.get("risk_score"))
        liquidity_change_10m = self._number(row.get("liquidity_change_10m"))
        volume_spike_ratio = self._number(row.get("volume_spike_ratio"), default=1.0)
        momentum_status = str(row.get("momentum_status", "STABLE"))

        score = 0.0
        score += min(max(alpha_score, 0), 100) * 0.35
        score += max(0, 100 - min(max(risk_score, 0), 100)) * 0.20
        score += min(max(liquidity_change_10m, 0), 50) * 0.50
        score += min(max(volume_spike_ratio - 1, 0), 4) * 10

        if momentum_status == "HEATING_UP":
            score += 18
        elif momentum_status == "HOT":
            score += 14
        elif momentum_status == "COOLING_DOWN":
            score -= 20

        score = round(max(0, min(100, score)), 2)
        return {
            "smart_money_score": score,
            "smart_money_signal": self._signal(score, risk_score, momentum_status, liquidity_change_10m),
        }

    def _signal(self, score: float, risk_score: float, momentum_status: str, liquidity_change_10m: float) -> str:
        """Map smart money score to an interpretable signal."""
        if momentum_status == "COOLING_DOWN" or liquidity_change_10m < -10:
            return "EXITING"
        if score >= 70 and risk_score <= 55:
            return "ACCUMULATION"
        if score >= 45:
            return "WATCHING"
        return "NEUTRAL"

    def _number(self, value: object, default: float = 0.0) -> float:
        """Convert nullable dataframe values to float."""
        if pd.isna(value):
            return default
        return float(value)

