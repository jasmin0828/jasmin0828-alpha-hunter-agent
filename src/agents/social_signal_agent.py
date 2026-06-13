"""Manual-input Social Signal Agent for Alpha Hunter Market System v1.0."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SocialSignal:
    """Structured social signal derived from manually curated evidence."""

    signal_id: str
    source_platform: str
    author: str
    mentioned_tokens: list[str]
    mentioned_themes: list[str]
    social_strength: float
    hype_risk: str
    evidence_value: str
    reason: str
    url: str
    posted_at: str


class SocialSignalAgent:
    """Score manually collected social signals without external API calls."""

    HYPE_TERMS = {
        "100x",
        "moon",
        "send",
        "sending",
        "ape",
        "guaranteed",
        "no chart needed",
        "pure conviction",
        "next gem",
    }

    def analyze(
        self,
        social_inputs: list[dict[str, Any]],
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
    ) -> list[SocialSignal]:
        """Return scored social signals from manually curated JSON rows."""
        token_symbols = self._token_symbols(snapshots)
        theme_names = self._theme_names(theme_results)
        theme_platforms = self._theme_platforms(social_inputs)

        signals = [
            self._analyze_row(row, token_symbols, theme_names, theme_platforms)
            for row in social_inputs
        ]
        return sorted(signals, key=lambda signal: signal.social_strength, reverse=True)

    def analyze_as_dicts(
        self,
        social_inputs: list[dict[str, Any]],
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return JSON-serializable social signal results."""
        return [asdict(signal) for signal in self.analyze(social_inputs, snapshots, theme_results)]

    def _analyze_row(
        self,
        row: dict[str, Any],
        token_symbols: set[str],
        theme_names: set[str],
        theme_platforms: dict[str, set[str]],
    ) -> SocialSignal:
        platform = str(row.get("source_platform") or "Manual")
        author = str(row.get("author") or "unknown")
        content = str(row.get("content") or "")
        url = str(row.get("url") or "")
        posted_at = str(row.get("posted_at") or "")
        mentioned_tokens = self._list_value(row.get("mentioned_tokens"))
        mentioned_themes = self._list_value(row.get("mentioned_themes"))
        engagement = self._float_value(row.get("engagement_score"))

        matched_tokens = [token for token in mentioned_tokens if token.upper() in token_symbols]
        matched_themes = [
            theme
            for theme in mentioned_themes
            if self._normalize_theme(theme) in theme_names and self._is_known_theme(theme)
        ]
        multi_platform_themes = [
            theme
            for theme in mentioned_themes
            if self._is_known_theme(theme) and len(theme_platforms.get(self._normalize_theme(theme), set())) > 1
        ]
        hype_terms = self._hype_terms(content)
        has_market_support = bool(matched_tokens or matched_themes)
        is_single_source = all(len(theme_platforms.get(self._normalize_theme(theme), set())) <= 1 for theme in mentioned_themes)

        social_strength = min(100.0, engagement * 0.55)
        positive: list[str] = []
        weak: list[str] = []
        risks: list[str] = []

        if matched_tokens:
            social_strength += 15
            positive.append(f"matched token snapshot: {', '.join(matched_tokens)}")
        elif mentioned_tokens:
            weak.append("mentioned tokens not found in latest snapshot")

        if matched_themes:
            social_strength += 12
            positive.append(f"matched theme output: {', '.join(matched_themes)}")
        elif mentioned_themes:
            weak.append("mentioned themes not confirmed by a classified ThemeScannerAgent theme")

        if multi_platform_themes:
            social_strength += 10
            positive.append(f"multi-platform theme confirmation: {', '.join(multi_platform_themes)}")
        elif mentioned_themes:
            weak.append("single-platform theme mention")

        if hype_terms:
            social_strength -= 8
            risks.append(f"hype language: {', '.join(hype_terms[:3])}")
        if is_single_source:
            social_strength -= 5
            risks.append("single source")
        if not has_market_support:
            social_strength -= 18
            risks.append("no current market/theme support")

        bounded_strength = round(max(0, min(100, social_strength)), 2)
        hype_risk = self._hype_risk(hype_terms, has_market_support, engagement, is_single_source)
        evidence_value = self._evidence_value(bounded_strength, hype_risk, has_market_support, bool(multi_platform_themes))
        reason = self._reason(positive, weak, risks, evidence_value, hype_risk)

        return SocialSignal(
            signal_id=self._signal_id(platform, author, content, url, posted_at),
            source_platform=platform,
            author=author,
            mentioned_tokens=mentioned_tokens,
            mentioned_themes=mentioned_themes,
            social_strength=bounded_strength,
            hype_risk=hype_risk,
            evidence_value=evidence_value,
            reason=reason,
            url=url,
            posted_at=posted_at,
        )

    def _token_symbols(self, snapshots: pd.DataFrame) -> set[str]:
        if snapshots.empty or "symbol" not in snapshots.columns:
            return set()
        return {
            str(symbol).strip().upper()
            for symbol in snapshots["symbol"].dropna().tolist()
            if str(symbol).strip()
        }

    def _theme_names(self, theme_results: list[dict[str, Any]]) -> set[str]:
        names = set()
        for theme in theme_results:
            name = self._normalize_theme(theme.get("theme_name"))
            if name:
                names.add(name)
            if name == "unknown":
                names.add("unclassified theme")
        return names

    def _theme_platforms(self, social_inputs: list[dict[str, Any]]) -> dict[str, set[str]]:
        platforms: dict[str, set[str]] = {}
        for row in social_inputs:
            platform = str(row.get("source_platform") or "Manual")
            for theme in self._list_value(row.get("mentioned_themes")):
                key = self._normalize_theme(theme)
                if key:
                    platforms.setdefault(key, set()).add(platform)
        return platforms

    def _hype_terms(self, content: str) -> list[str]:
        lower = content.lower()
        return sorted(term for term in self.HYPE_TERMS if term in lower)

    def _hype_risk(self, hype_terms: list[str], has_market_support: bool, engagement: float, is_single_source: bool) -> str:
        if hype_terms and (not has_market_support or engagement >= 75):
            return "HIGH"
        if len(hype_terms) >= 2 or (is_single_source and engagement >= 70):
            return "HIGH"
        if hype_terms or is_single_source or not has_market_support:
            return "MEDIUM"
        return "LOW"

    def _evidence_value(self, strength: float, hype_risk: str, has_market_support: bool, multi_platform: bool) -> str:
        if strength >= 70 and hype_risk != "HIGH" and has_market_support:
            return "HIGH"
        if hype_risk == "HIGH":
            return "LOW"
        if strength >= 45 and has_market_support and (multi_platform or hype_risk == "LOW"):
            return "MEDIUM"
        if strength >= 50 and has_market_support and hype_risk == "MEDIUM":
            return "MEDIUM"
        return "LOW"

    def _reason(self, positive: list[str], weak: list[str], risks: list[str], evidence_value: str, hype_risk: str) -> str:
        parts = [f"evidence_value {evidence_value}", f"hype_risk {hype_risk}"]
        if positive:
            parts.append("; ".join(positive))
        if weak:
            parts.append("weak: " + "; ".join(weak))
        if risks:
            parts.append("risk: " + "; ".join(risks))
        return " | ".join(parts)

    def _signal_id(self, platform: str, author: str, content: str, url: str, posted_at: str) -> str:
        raw = "|".join([platform, author, content, url, posted_at])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _list_value(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _normalize_theme(self, value: object) -> str:
        return str(value or "").strip().lower()

    def _is_known_theme(self, value: object) -> bool:
        normalized = self._normalize_theme(value)
        return normalized not in {"", "unknown", "unclassified theme", "none", "nan"}

    def _float_value(self, value: object) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
