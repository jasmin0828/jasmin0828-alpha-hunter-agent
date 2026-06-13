"""Daily Alpha Report Agent for Alpha Hunter Market System v1.0."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from src.agents.evidence_grading_agent import EvidenceGradingAgent


@dataclass(frozen=True)
class DailyAlphaReport:
    """Structured daily alpha report for research review."""

    report_date: str
    market_summary: dict[str, Any]
    top_themes: list[dict[str, Any]]
    top_tokens: list[dict[str, Any]]
    notable_signals: list[dict[str, Any]]
    risks: list[str]
    watchlist: list[dict[str, Any]]
    next_actions: list[str]
    evidence_grades: list[dict[str, Any]]
    top_evidence: list[dict[str, Any]]
    weak_evidence: list[dict[str, Any]]
    risk_flags_summary: list[str]
    social_signals: list[dict[str, Any]]
    social_summary: dict[str, Any]
    social_enhanced_evidence_grades: list[dict[str, Any]]
    hype_risk_summary: dict[str, Any]


class DailyAlphaReportAgent:
    """Build JSON and Markdown reports from token snapshots and theme results."""

    ALERT_LEVELS = {"WATCH", "HIGH", "CRITICAL"}
    MAX_TOP_THEMES = 5
    MAX_TOP_TOKENS = 5
    MAX_NOTABLE_SIGNALS = 5
    MAX_WATCHLIST = 5
    MAX_SOCIAL_SIGNALS = 5

    def build_report(
        self,
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
        report_date: str | None = None,
        social_signals: list[dict[str, Any]] | None = None,
    ) -> DailyAlphaReport:
        """Return a structured report from the latest market intelligence data."""
        frame = self._prepare_frame(snapshots)
        themes = self._prepare_themes(theme_results)
        social_rows = self._prepare_social_signals(social_signals or [])
        evidence_agent = EvidenceGradingAgent()
        baseline_evidence_grades = evidence_agent.grade_as_dicts(frame, themes)
        social_enhanced_evidence_grades = (
            evidence_agent.grade_as_dicts(frame, themes, social_signals=social_rows)
            if social_rows
            else []
        )
        active_evidence_grades = social_enhanced_evidence_grades or baseline_evidence_grades
        date_value = report_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return DailyAlphaReport(
            report_date=date_value,
            market_summary=self._market_summary(frame, themes),
            top_themes=themes[: self.MAX_TOP_THEMES],
            top_tokens=self._top_tokens(frame),
            notable_signals=self._notable_signals(frame),
            risks=self._risks(frame, themes, social_rows),
            watchlist=self._watchlist(frame),
            next_actions=self._next_actions(frame, themes),
            evidence_grades=active_evidence_grades,
            top_evidence=self._top_evidence(active_evidence_grades),
            weak_evidence=self._weak_evidence(active_evidence_grades),
            risk_flags_summary=self._risk_flags_summary(active_evidence_grades),
            social_signals=social_rows[: self.MAX_SOCIAL_SIGNALS],
            social_summary=self._social_summary(social_rows),
            social_enhanced_evidence_grades=social_enhanced_evidence_grades,
            hype_risk_summary=self._hype_risk_summary(social_rows),
        )

    def build_report_dict(
        self,
        snapshots: pd.DataFrame,
        theme_results: list[dict[str, Any]],
        report_date: str | None = None,
        social_signals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Return a JSON-serializable report dictionary."""
        return asdict(self.build_report(snapshots, theme_results, report_date, social_signals))

    def render_markdown(self, report: DailyAlphaReport | dict[str, Any]) -> str:
        """Render a structured report as Markdown."""
        data = asdict(report) if isinstance(report, DailyAlphaReport) else report
        lines = [
            f"# Daily Alpha Report - {data['report_date']}",
            "",
            "## Market Summary",
            "",
        ]
        for key, value in data["market_summary"].items():
            lines.append(f"- {key}: {value}")

        lines.extend(["", "## Top Themes", ""])
        if data["top_themes"]:
            for theme in data["top_themes"]:
                lines.append(
                    "- "
                    f"{theme.get('theme_name')} "
                    f"strength={self._number(theme.get('signal_strength'))} "
                    f"tokens={self._join_list(theme.get('related_tokens'))} "
                    f"reason={theme.get('reason')}"
                )
        else:
            lines.append("- No themes detected from the latest snapshot.")

        lines.extend(["", "## Top Tokens", ""])
        self._append_token_rows(lines, data["top_tokens"])

        lines.extend(["", "## Notable Signals", ""])
        self._append_token_rows(lines, data["notable_signals"], empty_text="No WATCH / HIGH / CRITICAL signals.")

        lines.extend(["", "## Social Signals", ""])
        self._append_social_signal_rows(lines, data.get("social_signals", []))

        lines.extend(["", "## Social Evidence Summary", ""])
        self._append_summary_rows(lines, data.get("social_summary", {}), empty_text="No social evidence supplied for this report.")

        lines.extend(["", "## Hype Risk Summary", ""])
        self._append_summary_rows(lines, data.get("hype_risk_summary", {}), empty_text="No hype risk data supplied for this report.")

        lines.extend(["", "## Social-enhanced Evidence Grades", ""])
        self._append_evidence_rows(
            lines,
            data.get("social_enhanced_evidence_grades", []),
            empty_text="No social-enhanced evidence grades available.",
        )

        lines.extend(["", "## Evidence Grades", ""])
        self._append_evidence_rows(lines, data.get("evidence_grades", []))

        lines.extend(["", "## Top Evidence", ""])
        self._append_evidence_rows(lines, data.get("top_evidence", []), empty_text="No strong evidence rows available.")

        lines.extend(["", "## Weak Evidence / Risks", ""])
        self._append_weak_evidence_rows(lines, data.get("weak_evidence", []))
        risk_summary = data.get("risk_flags_summary", [])
        if risk_summary:
            lines.append("")
            for risk in risk_summary:
                lines.append(f"- risk_flag: {risk}")
        elif not data.get("weak_evidence", []):
            lines.append("- No weak evidence or risk flags available.")

        lines.extend(["", "## Risks", ""])
        for risk in data["risks"]:
            lines.append(f"- {risk}")

        lines.extend(["", "## Watchlist", ""])
        self._append_token_rows(lines, data["watchlist"], empty_text="No current watchlist candidates.")

        lines.extend(["", "## Next Actions", ""])
        for action in data["next_actions"]:
            lines.append(f"- {action}")

        lines.extend(
            [
                "",
                "## Safety Boundary",
                "",
                "- Research observation only.",
                "- No wallet connection.",
                "- No private keys.",
                "- No transaction signing.",
                "- No automated trading.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _prepare_frame(self, snapshots: pd.DataFrame) -> pd.DataFrame:
        if snapshots.empty:
            return snapshots.copy()

        frame = snapshots.copy()
        defaults: dict[str, Any] = {
            "symbol": "",
            "token_name": "",
            "narrative": "Unknown",
            "alert_level": "IGNORE",
            "early_alpha_score": 0,
            "agent_score": 0,
            "alpha_score": 0,
            "risk_score": 0,
            "volume_24h": 0,
            "liquidity_usd": 0,
            "price_change_24h": 0,
            "score_change_10m": 0,
            "volume_spike_ratio": 1,
            "momentum_status": "STABLE",
            "rug_risk_level": "UNKNOWN",
            "token_age_bucket": "UNKNOWN",
            "consecutive_up_count": 0,
            "is_first_seen": 0,
            "early_alpha_reason": "",
            "risk_notes": "",
            "url": "",
        }
        for column, default in defaults.items():
            if column not in frame.columns:
                frame[column] = default

        for column in [
            "early_alpha_score",
            "agent_score",
            "alpha_score",
            "risk_score",
            "volume_24h",
            "liquidity_usd",
            "price_change_24h",
            "score_change_10m",
            "volume_spike_ratio",
            "consecutive_up_count",
            "is_first_seen",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

        frame["narrative"] = frame["narrative"].fillna("Unknown").replace("", "Unknown")
        return frame

    def _prepare_themes(self, theme_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        themes = []
        for theme in theme_results:
            row = dict(theme)
            if row.get("theme_name") == "Unknown":
                row["theme_name"] = "Unclassified Theme"
            row["signal_strength"] = round(float(row.get("signal_strength") or 0), 2)
            themes.append(row)
        return sorted(themes, key=lambda item: float(item.get("signal_strength") or 0), reverse=True)

    def _market_summary(self, frame: pd.DataFrame, themes: list[dict[str, Any]]) -> dict[str, Any]:
        if frame.empty:
            return {
                "token_count": 0,
                "theme_count": len(themes),
                "active_alert_count": 0,
                "first_seen_count": 0,
                "max_early_alpha_score": "0.00",
                "top_theme": themes[0]["theme_name"] if themes else "none",
                "market_read": "No usable snapshot data.",
            }

        active_alerts = int(frame["alert_level"].isin(self.ALERT_LEVELS).sum())
        max_score = float(frame["early_alpha_score"].max())
        first_seen = int(frame["is_first_seen"].sum())
        high_risk = int((frame["rug_risk_level"] == "HIGH").sum())
        top_theme = themes[0]["theme_name"] if themes else "none"
        market_read = "Quiet scan; mostly research watchlist."
        if active_alerts:
            market_read = "Active watch conditions detected; review notable signals."
        if high_risk > len(frame) / 2:
            market_read = "High-risk scan; treat signals as research leads only."

        return {
            "token_count": int(len(frame)),
            "theme_count": len(themes),
            "active_alert_count": active_alerts,
            "first_seen_count": first_seen,
            "max_early_alpha_score": f"{max_score:.2f}",
            "top_theme": top_theme,
            "market_read": market_read,
        }

    def _top_tokens(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        ranked = frame.sort_values(
            ["early_alpha_score", "agent_score", "alpha_score", "volume_24h"],
            ascending=[False, False, False, False],
        ).head(self.MAX_TOP_TOKENS)
        return [self._token_row(row) for _, row in ranked.iterrows()]

    def _notable_signals(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        signals = frame[frame["alert_level"].isin(self.ALERT_LEVELS)].sort_values(
            ["early_alpha_score", "agent_score", "alpha_score"],
            ascending=[False, False, False],
        ).head(self.MAX_NOTABLE_SIGNALS)
        return [self._token_row(row) for _, row in signals.iterrows()]

    def _watchlist(self, frame: pd.DataFrame) -> list[dict[str, Any]]:
        if frame.empty:
            return []
        watch = frame[
            (frame["alert_level"].isin(self.ALERT_LEVELS))
            | (frame["consecutive_up_count"] > 0)
            | (frame["momentum_status"].isin(["HEATING_UP", "HOT"]))
            | (frame["early_alpha_score"] >= 25)
        ].sort_values(["early_alpha_score", "volume_24h"], ascending=[False, False])
        return [self._token_row(row) for _, row in watch.head(self.MAX_WATCHLIST).iterrows()]

    def _risks(self, frame: pd.DataFrame, themes: list[dict[str, Any]], social_signals: list[dict[str, Any]]) -> list[str]:
        if social_signals:
            risks = [
                "Data source concentration: market data still comes from DexScreener/local Alpha Hunter data; social inputs are manually curated research evidence.",
            ]
        else:
            risks = [
                "Data source concentration: current report uses DexScreener/local Alpha Hunter data only; no external social confirmation yet.",
            ]
        if frame.empty:
            risks.append("No latest token snapshot was available for review.")
            return risks

        low_liquidity_count = int((frame["liquidity_usd"] < 75_000).sum())
        high_volatility_count = int((frame["price_change_24h"].abs() >= 50).sum())
        unknown_theme_count = sum(1 for theme in themes if theme.get("theme_name") == "Unclassified Theme")
        high_risk_count = int((frame["rug_risk_level"] == "HIGH").sum())

        risks.append(f"Low liquidity: {low_liquidity_count} token(s) below $75k liquidity.")
        risks.append(f"High volatility: {high_volatility_count} token(s) moved at least 50% in 24h.")
        risks.append(f"Unknown theme: {unknown_theme_count} unclassified theme bucket(s) require manual review.")
        if high_risk_count:
            risks.append(f"Risk intelligence: {high_risk_count} token(s) marked HIGH rug risk.")
        high_hype_count = sum(1 for signal in social_signals if signal.get("hype_risk") == "HIGH")
        if high_hype_count:
            risks.append(f"Social hype risk: {high_hype_count} signal(s) marked HIGH hype risk.")
        return risks

    def _next_actions(self, frame: pd.DataFrame, themes: list[dict[str, Any]]) -> list[str]:
        actions: list[str] = []
        if themes:
            actions.append(f"Review the top theme '{themes[0].get('theme_name')}' and verify whether the related tokens share a real narrative.")
        if not frame.empty and frame["alert_level"].isin(self.ALERT_LEVELS).any():
            actions.append("Check notable WATCH/HIGH/CRITICAL signals against source links, liquidity, and risk notes before adding research memory.")
        else:
            actions.append("Keep monitoring the watchlist; current scan does not justify escalation beyond research observation.")
        actions.append("Collect social evidence next before upgrading any theme conviction.")
        return actions[:3]

    def _top_evidence(self, evidence_grades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        strong = [
            row
            for row in evidence_grades
            if row.get("evidence_grade") in {"A", "B"}
        ]
        return sorted(strong, key=lambda row: float(row.get("evidence_score") or 0), reverse=True)[:5]

    def _weak_evidence(self, evidence_grades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        weak = [
            row
            for row in evidence_grades
            if row.get("evidence_grade") in {"C", "D"} or row.get("risk_flags")
        ]
        return sorted(weak, key=lambda row: float(row.get("evidence_score") or 0))[:5]

    def _risk_flags_summary(self, evidence_grades: list[dict[str, Any]]) -> list[str]:
        counts: dict[str, int] = {}
        for row in evidence_grades:
            for flag in row.get("risk_flags", []):
                key = str(flag)
                counts[key] = counts.get(key, 0) + 1
            for flag in row.get("social_risk_flags", []):
                key = f"social: {flag}"
                counts[key] = counts.get(key, 0) + 1
        return [f"{flag}: {count}" for flag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]

    def _prepare_social_signals(self, social_signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows = []
        for signal in social_signals:
            row = dict(signal)
            row["social_strength"] = round(float(row.get("social_strength") or 0), 2)
            row["mentioned_tokens"] = self._list_value(row.get("mentioned_tokens"))
            row["mentioned_themes"] = self._list_value(row.get("mentioned_themes"))
            rows.append(row)
        return sorted(rows, key=lambda item: float(item.get("social_strength") or 0), reverse=True)

    def _social_summary(self, social_signals: list[dict[str, Any]]) -> dict[str, Any]:
        if not social_signals:
            return {
                "signal_count": 0,
                "platforms": {},
                "evidence_value_distribution": {},
                "avg_social_strength": "0.00",
                "top_social_signal": "none",
            }

        platforms: dict[str, int] = {}
        evidence_values: dict[str, int] = {}
        total_strength = 0.0
        for signal in social_signals:
            platform = str(signal.get("source_platform") or "Manual")
            evidence_value = str(signal.get("evidence_value") or "UNKNOWN")
            platforms[platform] = platforms.get(platform, 0) + 1
            evidence_values[evidence_value] = evidence_values.get(evidence_value, 0) + 1
            total_strength += float(signal.get("social_strength") or 0)

        top_signal = max(social_signals, key=lambda item: float(item.get("social_strength") or 0))
        return {
            "signal_count": len(social_signals),
            "platforms": platforms,
            "evidence_value_distribution": evidence_values,
            "avg_social_strength": f"{total_strength / len(social_signals):.2f}",
            "top_social_signal": (
                f"{top_signal.get('source_platform')}:{top_signal.get('author')} "
                f"strength={self._number(top_signal.get('social_strength'))} "
                f"evidence={top_signal.get('evidence_value')}"
            ),
        }

    def _hype_risk_summary(self, social_signals: list[dict[str, Any]]) -> dict[str, Any]:
        if not social_signals:
            return {
                "signal_count": 0,
                "hype_risk_distribution": {},
                "high_hype_signals": [],
            }

        distribution: dict[str, int] = {}
        high_hype: list[str] = []
        for signal in social_signals:
            risk = str(signal.get("hype_risk") or "UNKNOWN")
            distribution[risk] = distribution.get(risk, 0) + 1
            if risk == "HIGH":
                high_hype.append(
                    f"{signal.get('source_platform')}:{signal.get('author')} "
                    f"tokens={self._join_list(signal.get('mentioned_tokens'))} "
                    f"reason={signal.get('reason')}"
                )

        return {
            "signal_count": len(social_signals),
            "hype_risk_distribution": distribution,
            "high_hype_signals": high_hype[:3],
        }

    def _token_row(self, row: pd.Series) -> dict[str, Any]:
        return {
            "symbol": str(row.get("symbol") or "N/A"),
            "token_name": str(row.get("token_name") or "N/A"),
            "narrative": str(row.get("narrative") or "Unknown"),
            "alert_level": str(row.get("alert_level") or "IGNORE"),
            "early_alpha_score": round(float(row.get("early_alpha_score") or 0), 2),
            "agent_score": round(float(row.get("agent_score") or 0), 2),
            "alpha_score": round(float(row.get("alpha_score") or 0), 2),
            "volume_24h": round(float(row.get("volume_24h") or 0), 2),
            "liquidity_usd": round(float(row.get("liquidity_usd") or 0), 2),
            "momentum_status": str(row.get("momentum_status") or "STABLE"),
            "rug_risk_level": str(row.get("rug_risk_level") or "UNKNOWN"),
            "reason": str(row.get("early_alpha_reason") or row.get("risk_notes") or "baseline research candidate"),
            "url": str(row.get("url") or ""),
        }

    def _append_token_rows(self, lines: list[str], rows: list[dict[str, Any]], empty_text: str = "No token rows available.") -> None:
        if not rows:
            lines.append(f"- {empty_text}")
            return
        for row in rows:
            lines.append(
                "- "
                f"{row.get('symbol')} "
                f"theme={row.get('narrative')} "
                f"alert={row.get('alert_level')} "
                f"early_alpha={self._number(row.get('early_alpha_score'))} "
                f"risk={row.get('rug_risk_level')} "
                f"reason={row.get('reason')}"
            )

    def _append_evidence_rows(self, lines: list[str], rows: list[dict[str, Any]], empty_text: str = "No evidence rows available.") -> None:
        if not rows:
            lines.append(f"- {empty_text}")
            return
        for row in rows:
            lines.append(
                "- "
                f"{row.get('subject_type')}:{row.get('subject_name')} "
                f"grade={row.get('evidence_grade')} "
                f"score={self._number(row.get('evidence_score'))} "
                f"reason={row.get('reason')}"
            )

    def _append_weak_evidence_rows(self, lines: list[str], rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        for row in rows:
            weak = self._join_list(row.get("weak_evidence"))
            risks = self._join_list(row.get("risk_flags"))
            social_risks = self._join_list(row.get("social_risk_flags"))
            lines.append(
                "- "
                f"{row.get('subject_type')}:{row.get('subject_name')} "
                f"grade={row.get('evidence_grade')} "
                f"score={self._number(row.get('evidence_score'))} "
                f"weak={weak} "
                f"risks={risks} "
                f"social_risks={social_risks}"
            )

    def _append_social_signal_rows(self, lines: list[str], rows: list[dict[str, Any]]) -> None:
        if not rows:
            lines.append("- No social signals supplied for this report.")
            return
        for row in rows:
            lines.append(
                "- "
                f"{row.get('source_platform')}:{row.get('author')} "
                f"strength={self._number(row.get('social_strength'))} "
                f"evidence={row.get('evidence_value')} "
                f"hype={row.get('hype_risk')} "
                f"tokens={self._join_list(row.get('mentioned_tokens'))} "
                f"themes={self._join_list(row.get('mentioned_themes'))} "
                f"reason={row.get('reason')}"
            )

    def _append_summary_rows(self, lines: list[str], summary: dict[str, Any], empty_text: str) -> None:
        if not summary or not summary.get("signal_count"):
            lines.append(f"- {empty_text}")
            return
        for key, value in summary.items():
            if isinstance(value, dict):
                lines.append(f"- {key}: {self._join_mapping(value)}")
            elif isinstance(value, list):
                if value:
                    lines.append(f"- {key}:")
                    for item in value:
                        lines.append(f"  - {item}")
                else:
                    lines.append(f"- {key}: none")
            else:
                lines.append(f"- {key}: {value}")

    def _join_mapping(self, value: dict[str, Any]) -> str:
        if not value:
            return "none"
        return ", ".join(f"{key}={count}" for key, count in value.items())

    def _list_value(self, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _join_list(self, value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, tuple):
            return ", ".join(str(item) for item in value)
        if isinstance(value, str) and value.strip():
            return value
        return str(value or "none")

    def _number(self, value: object) -> str:
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return "0.00"
