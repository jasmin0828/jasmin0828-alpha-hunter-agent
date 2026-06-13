"""Rule-based Evidence Grading Agent for Alpha Hunter Market System v1.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class EvidenceGrade:
    """Explainable evidence grade for a theme or token."""

    subject_type: str
    subject_name: str
    evidence_grade: str
    evidence_score: float
    evidence_sources: list[str]
    positive_evidence: list[str]
    weak_evidence: list[str]
    risk_flags: list[str]
    social_evidence: list[str]
    social_risk_flags: list[str]
    reason: str


class EvidenceGradingAgent:
    """Grade market evidence with deterministic rules and no external API calls."""

    TOKEN_SOURCE = "SQLite token_snapshots"
    THEME_SOURCE = "ThemeScannerAgent"
    SOCIAL_SOURCE = "SocialSignalAgent"

    def grade(
        self,
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
        social_signals: list[dict[str, Any]] | None = None,
    ) -> list[EvidenceGrade]:
        """Return evidence grades for themes and tokens."""
        frame = self._prepare_frame(snapshots)
        social_index = self._build_social_index(social_signals or [])
        grades: list[EvidenceGrade] = []
        grades.extend(self._grade_theme(theme, frame, social_index) for theme in theme_results)
        grades.extend(self._grade_token(row, social_index) for _, row in frame.iterrows())
        grades.extend(self._grade_unmatched_social_tokens(frame, social_index))
        return sorted(grades, key=lambda grade: grade.evidence_score, reverse=True)

    def grade_as_dicts(
        self,
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
        social_signals: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Return JSON-serializable evidence grades."""
        return [asdict(grade) for grade in self.grade(snapshots, theme_results, social_signals)]

    def _prepare_frame(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        if snapshots.empty:
            return snapshots.copy()

        frame = snapshots.copy()
        defaults: dict[str, Any] = {
            "symbol": "",
            "token_name": "",
            "narrative": "Unknown",
            "early_alpha_score": 0,
            "volume_24h": 0,
            "liquidity_usd": 0,
            "price_change_24h": 0,
            "rug_risk_level": "UNKNOWN",
            "low_liquidity_flag": False,
            "suspicious_volume_flag": False,
            "momentum_status": "STABLE",
            "consecutive_up_count": 0,
        }
        for column, default in defaults.items():
            if column not in frame.columns:
                frame[column] = default

        for column in [
            "early_alpha_score",
            "volume_24h",
            "liquidity_usd",
            "price_change_24h",
            "consecutive_up_count",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

        frame["narrative"] = frame["narrative"].fillna("Unknown").replace("", "Unknown")
        frame["rug_risk_level"] = frame["rug_risk_level"].fillna("UNKNOWN").replace("", "UNKNOWN")
        return frame

    def _grade_theme(self, theme: dict[str, Any], frame: pd.DataFrame, social_index: dict[str, dict[str, list[dict[str, Any]]]]) -> EvidenceGrade:
        theme_name = str(theme.get("theme_name") or "Unknown")
        related_tokens = self._list_value(theme.get("related_tokens"))
        theme_frame = self._related_token_frame(frame, related_tokens)
        positive: list[str] = []
        weak: list[str] = ["single data source: DexScreener/local Alpha Hunter data only"]
        risks: list[str] = ["data source concentration"]
        social_evidence: list[str] = []
        social_risk_flags: list[str] = []

        score = 35.0
        signal_strength = self._float_value(theme.get("signal_strength"))
        score += min(signal_strength * 0.25, 20)
        if signal_strength >= 50:
            positive.append(f"theme signal_strength is {signal_strength:.2f}")
        else:
            weak.append(f"theme signal_strength is {signal_strength:.2f}")

        token_count = len(related_tokens)
        if token_count >= 3:
            score += 12
            positive.append(f"{token_count} related tokens support the theme")
        elif token_count > 0:
            score += 5
            weak.append(f"only {token_count} related token(s)")
        else:
            weak.append("no related tokens")

        if self._is_known_theme(theme_name):
            score += 12
            positive.append("classified theme")
        else:
            score -= 15
            weak.append("Unknown theme")
            risks.append("unknown theme")

        if not theme_frame.empty:
            max_liquidity = float(theme_frame["liquidity_usd"].max())
            max_volume = float(theme_frame["volume_24h"].max())
            max_early_alpha = float(theme_frame["early_alpha_score"].max())
            high_volatility_count = int((theme_frame["price_change_24h"].abs() >= 50).sum())
            low_liquidity_count = int((theme_frame["liquidity_usd"] < 75_000).sum())

            score += min(max_liquidity / 500_000 * 10, 10)
            score += min(max_volume / 1_000_000 * 10, 10)
            score += min(max_early_alpha * 0.20, 12)

            if max_liquidity >= 150_000:
                positive.append(f"max liquidity ${max_liquidity:,.0f}")
            if max_volume >= 250_000:
                positive.append(f"max 24h volume ${max_volume:,.0f}")
            if max_early_alpha >= 25:
                positive.append(f"max early_alpha_score {max_early_alpha:.2f}")
            elif max_early_alpha < 10:
                weak.append(f"low max early_alpha_score {max_early_alpha:.2f}")

            if high_volatility_count:
                score -= min(high_volatility_count * 8, 18)
                risks.append(f"{high_volatility_count} high volatility token(s)")
            if low_liquidity_count:
                score -= min(low_liquidity_count * 6, 15)
                risks.append(f"{low_liquidity_count} low liquidity token(s)")

        score = self._apply_social_evidence(
            score=score,
            social_rows=social_index["themes"].get(self._normalize_key(theme_name), []),
            social_evidence=social_evidence,
            social_risk_flags=social_risk_flags,
        )

        return self._build_grade("theme", self._display_theme(theme_name), score, [self.THEME_SOURCE, self.TOKEN_SOURCE], positive, weak, risks, social_evidence, social_risk_flags)

    def _grade_token(self, row: pd.Series, social_index: dict[str, dict[str, list[dict[str, Any]]]]) -> EvidenceGrade:
        symbol = str(row.get("symbol") or row.get("token_name") or "Unknown Token")
        narrative = str(row.get("narrative") or "Unknown")
        liquidity = self._float_value(row.get("liquidity_usd"))
        volume = self._float_value(row.get("volume_24h"))
        early_alpha = self._float_value(row.get("early_alpha_score"))
        price_change = self._float_value(row.get("price_change_24h"))
        rug_risk = str(row.get("rug_risk_level") or "UNKNOWN")
        consecutive = self._float_value(row.get("consecutive_up_count"))

        score = 25.0
        positive: list[str] = []
        weak: list[str] = ["single data source: DexScreener/local Alpha Hunter data only"]
        risks: list[str] = ["data source concentration"]
        social_evidence: list[str] = []
        social_risk_flags: list[str] = []

        liquidity_points = min(liquidity / 500_000 * 20, 20)
        volume_points = min(volume / 1_000_000 * 18, 18)
        early_alpha_points = min(early_alpha * 0.35, 20)
        score += liquidity_points + volume_points + early_alpha_points

        if liquidity >= 150_000:
            positive.append(f"liquidity ${liquidity:,.0f}")
        elif liquidity < 75_000:
            score -= 12
            weak.append(f"low liquidity ${liquidity:,.0f}")
            risks.append("low liquidity")

        if volume >= 250_000:
            positive.append(f"24h volume ${volume:,.0f}")
        else:
            weak.append(f"modest 24h volume ${volume:,.0f}")

        if early_alpha >= 25:
            positive.append(f"early_alpha_score {early_alpha:.2f}")
        elif early_alpha < 10:
            weak.append(f"low early_alpha_score {early_alpha:.2f}")

        if self._is_known_theme(narrative):
            score += 10
            positive.append(f"classified theme: {narrative}")
        else:
            score -= 10
            weak.append("Unknown theme")
            risks.append("unknown theme")

        if consecutive > 0:
            score += min(consecutive * 5, 10)
            positive.append(f"consecutive momentum count {int(consecutive)}")

        if abs(price_change) >= 50:
            score -= 10
            risks.append(f"high volatility {price_change:.2f}%")
        if rug_risk == "HIGH":
            score -= 25
            risks.append("HIGH rug risk")
        elif rug_risk == "LOW":
            score += 8
            positive.append("LOW rug risk")

        if bool(row.get("suspicious_volume_flag")):
            score -= 8
            risks.append("suspicious volume flag")

        score = self._apply_social_evidence(
            score=score,
            social_rows=social_index["tokens"].get(self._normalize_key(symbol), []),
            social_evidence=social_evidence,
            social_risk_flags=social_risk_flags,
        )

        return self._build_grade("token", symbol, score, [self.TOKEN_SOURCE], positive, weak, risks, social_evidence, social_risk_flags)

    def _build_grade(
        self,
        subject_type: str,
        subject_name: str,
        score: float,
        sources: list[str],
        positive: list[str],
        weak: list[str],
        risks: list[str],
        social_evidence: list[str],
        social_risk_flags: list[str],
    ) -> EvidenceGrade:
        bounded_score = round(max(0, min(100, float(score))), 2)
        grade = self._letter_grade(bounded_score)
        sources = list(sources)
        if social_evidence or social_risk_flags:
            sources.append(self.SOCIAL_SOURCE)
        reason = self._reason(grade, bounded_score, positive, weak, risks, social_evidence, social_risk_flags)
        return EvidenceGrade(
            subject_type=subject_type,
            subject_name=subject_name,
            evidence_grade=grade,
            evidence_score=bounded_score,
            evidence_sources=sources,
            positive_evidence=positive,
            weak_evidence=weak,
            risk_flags=risks,
            social_evidence=social_evidence,
            social_risk_flags=social_risk_flags,
            reason=reason,
        )

    def _grade_unmatched_social_tokens(
        self,
        frame: pd.DataFrame,
        social_index: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> list[EvidenceGrade]:
        existing_tokens = set()
        if not frame.empty and "symbol" in frame.columns:
            existing_tokens = {self._normalize_key(symbol) for symbol in frame["symbol"].dropna().tolist()}

        grades: list[EvidenceGrade] = []
        for token_key, rows in social_index["tokens"].items():
            if token_key in existing_tokens:
                continue
            social_evidence: list[str] = []
            social_risk_flags: list[str] = []
            score = self._apply_social_evidence(
                score=10,
                social_rows=rows,
                social_evidence=social_evidence,
                social_risk_flags=social_risk_flags,
            )
            score -= 20
            grades.append(
                self._build_grade(
                    "token",
                    self._display_social_subject(rows, "mentioned_tokens", token_key),
                    score,
                    [],
                    [],
                    ["no matching token in latest snapshot"],
                    ["missing market data"],
                    social_evidence,
                    social_risk_flags,
                )
            )
        return grades

    def _letter_grade(self, score: float) -> str:
        if score >= 80:
            return "A"
        if score >= 60:
            return "B"
        if score >= 40:
            return "C"
        return "D"

    def _reason(
        self,
        grade: str,
        score: float,
        positive: list[str],
        weak: list[str],
        risks: list[str],
        social_evidence: list[str],
        social_risk_flags: list[str],
    ) -> str:
        label = {
            "A": "strong evidence",
            "B": "moderate evidence",
            "C": "weak evidence",
            "D": "watch/noise",
        }[grade]
        lead = positive[0] if positive else "limited positive evidence"
        drag = risks[0] if risks else (weak[0] if weak else "no major weakness")
        social_note = ""
        if social_evidence:
            social_note = f"; social boost: {social_evidence[0]}"
        if social_risk_flags:
            social_note += f"; social risk: {social_risk_flags[0]}"
        return f"{grade} ({score:.2f}) {label}: {lead}; main constraint: {drag}{social_note}"

    def _build_social_index(self, social_signals: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
        index: dict[str, dict[str, list[dict[str, Any]]]] = {"tokens": {}, "themes": {}}
        for signal in social_signals:
            for token in self._list_value(signal.get("mentioned_tokens")):
                index["tokens"].setdefault(self._normalize_key(token), []).append(signal)
            for theme in self._list_value(signal.get("mentioned_themes")):
                index["themes"].setdefault(self._normalize_key(theme), []).append(signal)
        return index

    def _display_social_subject(self, rows: list[dict[str, Any]], field: str, fallback: str) -> str:
        for row in rows:
            for value in self._list_value(row.get(field)):
                if self._normalize_key(value) == fallback:
                    return str(value)
        return fallback.upper()

    def _apply_social_evidence(
        self,
        score: float,
        social_rows: list[dict[str, Any]],
        social_evidence: list[str],
        social_risk_flags: list[str],
    ) -> float:
        if not social_rows:
            return score

        platforms = {str(row.get("source_platform") or "Manual") for row in social_rows}
        high_value_count = sum(1 for row in social_rows if row.get("evidence_value") == "HIGH")
        low_value_count = sum(1 for row in social_rows if row.get("evidence_value") == "LOW")
        high_hype_count = sum(1 for row in social_rows if row.get("hype_risk") == "HIGH")
        max_strength = max(self._float_value(row.get("social_strength")) for row in social_rows)

        score += min(max_strength * 0.12, 10)
        social_evidence.append(f"{len(social_rows)} matched social signal(s), max social_strength {max_strength:.2f}")

        if high_value_count:
            score += min(high_value_count * 8, 16)
            social_evidence.append(f"{high_value_count} HIGH evidence social signal(s)")
        if len(platforms) > 1:
            score += 8
            social_evidence.append(f"multi-platform social confirmation: {', '.join(sorted(platforms))}")
        if low_value_count:
            score -= min(low_value_count * 6, 14)
            social_risk_flags.append(f"{low_value_count} LOW evidence social signal(s)")
        if high_hype_count:
            score -= min(high_hype_count * 12, 24)
            social_risk_flags.append(f"hype_risk HIGH in {high_hype_count} social signal(s)")

        return score

    def _related_token_frame(self, frame: pd.DataFrame, related_tokens: list[str]) -> pd.DataFrame:
        if frame.empty or not related_tokens:
            return frame.iloc[0:0].copy()
        labels = {str(token).strip() for token in related_tokens if str(token).strip()}
        return frame[
            frame["symbol"].astype(str).isin(labels)
            | frame["token_name"].astype(str).isin(labels)
        ]

    def _display_theme(self, theme_name: str) -> str:
        if not self._is_known_theme(theme_name):
            return "Unclassified Theme"
        return theme_name

    def _is_known_theme(self, value: str) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized not in {"", "unknown", "unclassified theme", "none", "nan"}

    def _normalize_key(self, value: object) -> str:
        return str(value or "").strip().lower()

    def _list_value(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _float_value(self, value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
