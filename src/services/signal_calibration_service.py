"""Signal Calibration service for Alpha Hunter Agent v1.0."""

from __future__ import annotations

import pandas as pd


class SignalCalibrationService:
    """Convert raw alpha/risk/intelligence metrics into alert tiers."""

    MOMENTUM_BONUS = {
        "HOT": 10,
        "HEATING_UP": 8,
        "STABLE": 0,
        "COOLING_DOWN": -10,
    }
    RISK_PENALTY = {
        "LOW": 0,
        "MEDIUM": 10,
        "HIGH": 30,
    }
    AGE_PENALTY = {
        "NEWBORN": 15,
        "EARLY": 5,
        "TRENDING": 0,
        "MATURE": 3,
        "OLD": 8,
        "UNKNOWN": 10,
    }

    def calibrate_tokens(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Add agent score, alert level, and alert reason columns."""
        calibrated = self._ensure_columns(tokens.copy())
        if calibrated.empty:
            return calibrated

        alpha_score = pd.to_numeric(calibrated["alpha_score"], errors="coerce").fillna(0)
        narrative_score = pd.to_numeric(calibrated["narrative_score"], errors="coerce").fillna(0)
        smart_money_score = pd.to_numeric(calibrated["smart_money_score"], errors="coerce").fillna(0)
        momentum_bonus = calibrated["momentum_status"].fillna("STABLE").map(self.MOMENTUM_BONUS).fillna(0)
        risk_penalty = calibrated["rug_risk_level"].fillna("LOW").map(self.RISK_PENALTY).fillna(10)
        age_penalty = calibrated["token_age_bucket"].fillna("UNKNOWN").map(self.AGE_PENALTY).fillna(10)

        calibrated["agent_score"] = (
            alpha_score * 0.35
            + narrative_score * 0.15
            + smart_money_score * 0.20
            + momentum_bonus
            - risk_penalty
            - age_penalty
        ).clip(lower=0, upper=100).round(2)
        calibrated["alert_level"] = calibrated.apply(self._alert_level, axis=1)
        calibrated["alert_reason"] = calibrated.apply(self._alert_reason, axis=1)
        return calibrated

    def _ensure_columns(self, tokens: pd.DataFrame) -> pd.DataFrame:
        """Ensure all signal inputs and outputs have safe defaults."""
        defaults = {
            "alpha_score": 0,
            "narrative_score": 0,
            "smart_money_score": 0,
            "momentum_status": "STABLE",
            "rug_risk_level": "LOW",
            "token_age_bucket": "UNKNOWN",
            "smart_money_signal": "NEUTRAL",
            "narrative": "Unknown",
            "agent_score": 0,
            "early_alpha_score": 0,
            "early_alpha_reason": "",
            "alert_level": "IGNORE",
            "alert_reason": "",
        }
        for column, default in defaults.items():
            if column not in tokens.columns:
                tokens[column] = default
        return tokens

    def _alert_level(self, token: pd.Series) -> str:
        """Assign CRITICAL, HIGH, WATCH, or IGNORE."""
        if token.get("rug_risk_level") == "HIGH":
            return "IGNORE"

        early_alpha_score = float(token.get("early_alpha_score") or 0)
        if early_alpha_score >= 85:
            return "CRITICAL"
        if early_alpha_score >= 75:
            return "HIGH"
        if early_alpha_score >= 60:
            return "WATCH"

        agent_score = float(token.get("agent_score") or 0)
        alpha_score = float(token.get("alpha_score") or 0)
        narrative_score = float(token.get("narrative_score") or 0)
        smart_money_score = float(token.get("smart_money_score") or 0)
        token_age_bucket = token.get("token_age_bucket")
        momentum_status = token.get("momentum_status")

        if agent_score >= 85:
            return "CRITICAL"
        if agent_score >= 75:
            return "HIGH"
        if (
            alpha_score >= 80
            or token_age_bucket in ["EARLY", "TRENDING"]
            or (narrative_score >= 70 and alpha_score >= 70)
            or smart_money_score >= 65
            or momentum_status in ["HOT", "HEATING_UP"]
        ):
            return "WATCH"
        return "IGNORE"

    def _alert_reason(self, token: pd.Series) -> str:
        """Explain why the token landed in its alert tier."""
        if token.get("rug_risk_level") == "HIGH":
            return "ignored: rug risk HIGH"

        reasons: list[str] = []
        early_alpha_score = float(token.get("early_alpha_score") or 0)
        early_alpha_reason = token.get("early_alpha_reason") or ""
        agent_score = float(token.get("agent_score") or 0)
        alpha_score = float(token.get("alpha_score") or 0)
        narrative_score = float(token.get("narrative_score") or 0)
        smart_money_score = float(token.get("smart_money_score") or 0)
        token_age_bucket = token.get("token_age_bucket")
        momentum_status = token.get("momentum_status")

        if early_alpha_score >= 85:
            reasons.append("early_alpha_score >= 85")
        elif early_alpha_score >= 75:
            reasons.append("early_alpha_score >= 75")
        elif early_alpha_score >= 60:
            reasons.append("early_alpha_score >= 60")
        if early_alpha_reason:
            reasons.append(early_alpha_reason)
        if agent_score >= 85:
            reasons.append("agent_score >= 85")
        elif agent_score >= 75:
            reasons.append("agent_score >= 75")
        if alpha_score >= 80:
            reasons.append("alpha_score >= 80")
        if token_age_bucket in ["EARLY", "TRENDING"]:
            reasons.append(f"age bucket {token_age_bucket}")
        if narrative_score >= 70 and alpha_score >= 70:
            reasons.append("strong narrative with alpha_score >= 70")
        if smart_money_score >= 65:
            reasons.append("smart_money_score >= 65")
        if momentum_status in ["HOT", "HEATING_UP"]:
            reasons.append(f"momentum_status {momentum_status}")

        if not reasons:
            reasons.append("below calibrated alert thresholds")
        return "; ".join(reasons)
