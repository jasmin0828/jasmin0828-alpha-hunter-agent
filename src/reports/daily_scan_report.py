"""Generate a Chinese daily scan report from existing SQLite observations.

This report is read-only. It summarizes scanner output and run-log state
without changing scanner logic, ranking logic, database schema, or runtime flow.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from config import REPORT_TIMEZONE
from src.storage.sqlite_store import DB_PATH
from src.utils.paths import REPORTS_DIR


REPORT_PATH = REPORTS_DIR / "daily_scan_report.md"
MISSING = "暂无数据"
SYSTEM_VERSION = "v1.1 Observation Phase"
FORBIDDEN_REPORT_TERMS = ("买入", "卖出", "建议建仓", "预测上涨", "目标价")


@dataclass(frozen=True)
class DailyScanReportConfig:
    """Configuration for the daily scan report generator."""

    db_path: Path = DB_PATH
    output_path: Path = REPORT_PATH
    report_date: str | None = None
    timezone: str = REPORT_TIMEZONE


class DailyScanReportGenerator:
    """Build a Chinese Markdown scan summary from local SQLite data."""

    def __init__(self, config: DailyScanReportConfig | None = None) -> None:
        self.config = config or DailyScanReportConfig()
        self.db_path = Path(self.config.db_path)
        self.output_path = Path(self.config.output_path)
        self.timezone = ZoneInfo(self.config.timezone or "Asia/Shanghai")
        self.generated_at = datetime.now(self.timezone)
        self.report_date = self.config.report_date or self.generated_at.date().isoformat()

    def generate(self) -> Path:
        """Write the report and return the generated Markdown path."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = self.build_markdown()
        self._assert_read_only_language(markdown)
        self.output_path.write_text(markdown, encoding="utf-8")
        return self.output_path

    def build_markdown(self) -> str:
        """Return the report Markdown without writing it."""
        if not self.db_path.exists():
            return self._render_missing_database()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            context = self._load_context(conn)

        sections = [
            "# Alpha Hunter 每日扫链报告",
            "",
            self._render_basic_info(context),
            "## 一、今日运行概况",
            "",
            self._render_run_overview(context),
            "## 二、扫描概况",
            "",
            self._render_scan_overview(context),
            "## 三、24H 交易量 TOP10",
            "",
            self._render_volume_top10(context),
            "## 四、Social Heat TOP10",
            "",
            self._render_social_heat_top10(context),
            "## 五、Evidence Score TOP10",
            "",
            self._render_evidence_top10(context),
            "## 六、今日新增 Candidate",
            "",
            self._render_new_candidates(context),
            "## 七、Theme 分布",
            "",
            self._render_theme_distribution(context),
            "## 八、较昨日变化",
            "",
            self._render_day_change(context),
            "## 九、系统运行记录",
            "",
            self._render_run_log_summary(context),
            "## 十、数据完整性检查",
            "",
            self._render_integrity_check(context),
            "",
        ]
        return "\n".join(sections)

    def _load_context(self, conn: sqlite3.Connection) -> dict[str, Any]:
        token_columns = self._columns(conn, "token_snapshots")
        run_columns = self._columns(conn, "scan_runs")
        signal_columns = self._columns(conn, "signal_events")

        latest_run = self._latest_run(conn, run_columns)
        today_runs = self._runs_for_date(conn, run_columns, self.report_date)
        yesterday = (datetime.fromisoformat(self.report_date) - timedelta(days=1)).date().isoformat()
        yesterday_runs = self._runs_for_date(conn, run_columns, yesterday)

        today_tokens = self._tokens_for_date(conn, token_columns, self.report_date)
        yesterday_tokens = self._tokens_for_date(conn, token_columns, yesterday)
        today_signals = self._signals_for_date(conn, signal_columns, self.report_date)
        yesterday_signals = self._signals_for_date(conn, signal_columns, yesterday)
        today_unique_tokens = self._latest_unique_tokens(today_tokens)
        yesterday_unique_tokens = self._latest_unique_tokens(yesterday_tokens)

        return {
            "token_columns": token_columns,
            "run_columns": run_columns,
            "signal_columns": signal_columns,
            "latest_run": latest_run,
            "today_runs": today_runs,
            "yesterday_runs": yesterday_runs,
            "today_tokens": today_tokens,
            "yesterday_tokens": yesterday_tokens,
            "today_unique_tokens": today_unique_tokens,
            "yesterday_unique_tokens": yesterday_unique_tokens,
            "today_signals": today_signals,
            "yesterday_signals": yesterday_signals,
        }

    def _latest_unique_tokens(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            address = self._value(row.get("contract_address") or row.get("token_address") or self._symbol(row))
            key = (self._chain(row), address.lower())
            current = latest.get(key)
            if current is None or self._value(row.get("created_at")) >= self._value(current.get("created_at")):
                latest[key] = row
        return list(latest.values())

    def _columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        if not self._table_exists(conn, table):
            return set()
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _latest_run(self, conn: sqlite3.Connection, columns: set[str]) -> dict[str, Any] | None:
        if not columns:
            return None
        order_column = "started_at" if "started_at" in columns else "id"
        row = conn.execute(f"SELECT * FROM scan_runs ORDER BY {order_column} DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def _runs_for_date(self, conn: sqlite3.Connection, columns: set[str], date_value: str) -> list[dict[str, Any]]:
        if not columns or "started_at" not in columns:
            return []
        rows = conn.execute(
            "SELECT * FROM scan_runs WHERE DATE(started_at) = ? ORDER BY started_at",
            (date_value,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _tokens_for_date(self, conn: sqlite3.Connection, columns: set[str], date_value: str) -> list[dict[str, Any]]:
        if not columns or "created_at" not in columns:
            return []
        rows = conn.execute(
            "SELECT * FROM token_snapshots WHERE DATE(created_at) = ? ORDER BY created_at",
            (date_value,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _signals_for_date(self, conn: sqlite3.Connection, columns: set[str], date_value: str) -> list[dict[str, Any]]:
        if not columns or "created_at" not in columns:
            return []
        rows = conn.execute(
            "SELECT * FROM signal_events WHERE DATE(created_at) = ? ORDER BY created_at",
            (date_value,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _render_missing_database(self) -> str:
        context = {
            "latest_run": None,
            "today_runs": [],
            "today_tokens": [],
            "today_unique_tokens": [],
            "today_signals": [],
            "yesterday_runs": [],
            "yesterday_tokens": [],
            "yesterday_unique_tokens": [],
            "yesterday_signals": [],
            "token_columns": set(),
            "run_columns": set(),
            "signal_columns": set(),
        }
        return "\n".join(
            [
                "# Alpha Hunter 每日扫链报告",
                "",
                self._render_basic_info(context, running_status="数据库不可用"),
                "## 一、今日运行概况",
                "",
                self._empty_table(["Run ID", "开始时间", "结束时间", "运行耗时", "Runtime Status", "Errors"]),
                "## 二、扫描概况",
                "",
                self._empty_table(["扫描链", "扫描 Token 数", "Signal 数"]),
                "## 三、24H 交易量 TOP10",
                "",
                MISSING,
                "",
                "## 四、Social Heat TOP10",
                "",
                MISSING,
                "",
                "## 五、Evidence Score TOP10",
                "",
                MISSING,
                "",
                "## 六、今日新增 Candidate",
                "",
                "暂无新增 Candidate。",
                "",
                "## 七、Theme 分布",
                "",
                MISSING,
                "",
                "## 八、较昨日变化",
                "",
                "暂无昨日数据。",
                "",
                "## 九、系统运行记录",
                "",
                self._empty_table(["Run Count", "Success Count", "Failed Count", "Average Duration", "Error Count"]),
                "## 十、数据完整性检查",
                "",
                self._render_integrity_check(context),
                "",
            ]
        )

    def _render_basic_info(self, context: dict[str, Any], running_status: str | None = None) -> str:
        latest_run = context.get("latest_run") or {}
        status = running_status or self._value(latest_run.get("status"))
        rows = [
            ("日期", self.report_date),
            ("系统版本", SYSTEM_VERSION),
            ("运行状态", status),
            ("数据来源", str(self.db_path)),
            ("生成时间", self.generated_at.isoformat(timespec="seconds")),
        ]
        return self._kv_table(rows)

    def _render_run_overview(self, context: dict[str, Any]) -> str:
        latest_run = context.get("latest_run")
        if not latest_run:
            return self._empty_table(["Run ID", "开始时间", "结束时间", "运行耗时", "Runtime Status", "Errors"])
        row = [
            self._value(latest_run.get("run_id") or latest_run.get("id")),
            self._value(latest_run.get("started_at")),
            self._value(latest_run.get("finished_at") or latest_run.get("completed_at")),
            self._duration(latest_run.get("duration_seconds")),
            self._value(latest_run.get("status")),
            self._value(latest_run.get("errors")),
        ]
        return self._markdown_table(
            ["Run ID", "开始时间", "结束时间", "运行耗时", "Runtime Status", "Errors"],
            [row],
        )

    def _render_scan_overview(self, context: dict[str, Any]) -> str:
        tokens = context["today_tokens"]
        signals = context["today_signals"]
        if not tokens and not signals:
            return self._empty_table(["扫描链", "扫描 Token 数", "Signal 数"])

        chains = sorted({self._chain(row) for row in tokens + signals if self._chain(row) != MISSING})
        rows = []
        for chain in chains:
            rows.append(
                [
                    chain,
                    str(sum(1 for row in tokens if self._chain(row) == chain)),
                    str(sum(1 for row in signals if self._chain(row) == chain)),
                ]
            )
        unique_tokens = context["today_unique_tokens"]
        total_themes = len({self._theme(row) for row in unique_tokens if self._theme(row) != MISSING})
        rows.append(["合计", str(len(tokens)), str(len(signals))])
        table = self._markdown_table(["扫描链", "扫描 Token 数", "Signal 数"], rows)
        return "\n".join([table, "", self._kv_table([("扫描 Token 总数", len(tokens)), ("Signal 总数", len(signals)), ("Theme 总数", total_themes)])])

    def _render_volume_top10(self, context: dict[str, Any]) -> str:
        tokens = [row for row in context["today_unique_tokens"] if self._number(row.get("volume_24h")) is not None]
        if not tokens:
            return MISSING + "\n"
        ordered = sorted(tokens, key=lambda row: self._number(row.get("volume_24h")) or 0, reverse=True)[:10]
        rows = []
        for index, row in enumerate(ordered, start=1):
            rows.append(
                [
                    str(index),
                    self._symbol(row),
                    self._chain(row),
                    self._money(row.get("volume_24h")),
                    self._money(row.get("liquidity_usd")),
                    self._money(row.get("fdv")),
                ]
            )
        return self._markdown_table(["Rank", "Symbol", "Chain", "24H Volume", "Liquidity", "FDV"], rows)

    def _render_social_heat_top10(self, context: dict[str, Any]) -> str:
        social_fields = [
            "social_heat_score",
            "heat_score",
            "social_score",
            "mentions",
            "engagement",
            "engagement_score",
        ]
        if not any(field in context["token_columns"] for field in social_fields):
            return MISSING + "\n"
        heat_field = next((field for field in ["social_heat_score", "heat_score", "social_score"] if field in context["token_columns"]), None)
        if not heat_field:
            return MISSING + "\n"
        tokens = [row for row in context["today_unique_tokens"] if self._number(row.get(heat_field)) is not None]
        if not tokens:
            return MISSING + "\n"
        ordered = sorted(tokens, key=lambda row: self._number(row.get(heat_field)) or 0, reverse=True)[:10]
        rows = []
        for index, row in enumerate(ordered, start=1):
            rows.append(
                [
                    str(index),
                    self._symbol(row),
                    self._chain(row),
                    self._value(row.get(heat_field)),
                    self._value(row.get("mentions")),
                    self._value(row.get("engagement") or row.get("engagement_score")),
                ]
            )
        return self._markdown_table(["Rank", "Symbol", "Chain", "Heat Score", "Mentions", "Engagement"], rows)

    def _render_evidence_top10(self, context: dict[str, Any]) -> str:
        tokens = context["today_unique_tokens"]
        score_field = self._score_field(context["token_columns"])
        if not tokens or not score_field:
            return MISSING + "\n"
        scored = [row for row in tokens if self._number(row.get(score_field)) is not None]
        if not scored:
            return MISSING + "\n"
        ordered = sorted(scored, key=lambda row: self._number(row.get(score_field)) or 0, reverse=True)[:10]
        rows = []
        for index, row in enumerate(ordered, start=1):
            rows.append(
                [
                    str(index),
                    self._symbol(row),
                    self._chain(row),
                    self._theme(row),
                    self._score(row.get(score_field)),
                ]
            )
        return self._markdown_table(["Rank", "Symbol", "Chain", "Theme", "Evidence Score"], rows)

    def _render_new_candidates(self, context: dict[str, Any]) -> str:
        tokens = [row for row in context["today_unique_tokens"] if int(row.get("is_first_seen") or 0) == 1]
        if not tokens:
            return "暂无新增 Candidate。\n"
        score_field = self._score_field(context["token_columns"])
        rows = []
        for row in sorted(tokens, key=lambda item: self._number(item.get(score_field)) or 0, reverse=True):
            rows.append(
                [
                    self._symbol(row),
                    self._chain(row),
                    self._theme(row),
                    self._value(row.get("first_seen_at")),
                    self._score(row.get(score_field)) if score_field else MISSING,
                ]
            )
        return self._markdown_table(["Symbol", "Chain", "Theme", "First Seen At", "Evidence Score"], rows)

    def _render_theme_distribution(self, context: dict[str, Any]) -> str:
        counts: dict[str, int] = {}
        for row in context["today_unique_tokens"]:
            theme = self._theme(row)
            counts[theme] = counts.get(theme, 0) + 1
        if not counts:
            return MISSING + "\n"
        rows = [[theme, str(count)] for theme, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)]
        return self._markdown_table(["Theme", "Count"], rows)

    def _render_day_change(self, context: dict[str, Any]) -> str:
        if not context["yesterday_runs"] and not context["yesterday_tokens"]:
            return "暂无昨日数据。\n"
        today_duration = self._average_duration(context["today_runs"])
        yesterday_duration = self._average_duration(context["yesterday_runs"])
        today_themes = {self._theme(row) for row in context["today_unique_tokens"] if self._theme(row) != MISSING}
        yesterday_themes = {
            self._theme(row) for row in context["yesterday_unique_tokens"] if self._theme(row) != MISSING
        }
        rows = [
            ["扫描 Token", self._signed(len(context["today_tokens"]) - len(context["yesterday_tokens"]))],
            ["Signal", self._signed(len(context["today_signals"]) - len(context["yesterday_signals"]))],
            ["Theme", self._signed(len(today_themes) - len(yesterday_themes))],
            ["平均运行耗时", self._duration_change(today_duration, yesterday_duration)],
        ]
        return self._markdown_table(["指标", "较昨日变化"], rows)

    def _render_run_log_summary(self, context: dict[str, Any]) -> str:
        runs = context["today_runs"]
        success_count = sum(1 for row in runs if str(row.get("status")).lower() == "completed")
        failed_count = sum(1 for row in runs if str(row.get("status")).lower() == "failed")
        error_count = sum(1 for row in runs if str(row.get("errors") or "").strip())
        rows = [
            [
                str(len(runs)),
                str(success_count),
                str(failed_count),
                self._duration(self._average_duration(runs)),
                str(error_count),
            ]
        ]
        return self._markdown_table(["Run Count", "Success Count", "Failed Count", "Average Duration", "Error Count"], rows)

    def _render_integrity_check(self, context: dict[str, Any]) -> str:
        tokens = context["today_tokens"]
        runs = context["today_runs"]
        errors = sum(1 for row in runs if str(row.get("errors") or "").strip())
        chain_counts = {chain: sum(1 for row in tokens if self._chain(row) == chain) for chain in ["ethereum", "solana", "bsc"]}
        rows = [
            ["Ethereum", self._check(chain_counts["ethereum"] > 0)],
            ["Solana", self._check(chain_counts["solana"] > 0)],
            ["BSC", self._check(chain_counts["bsc"] > 0)],
            ["Run Log", self._check(len(runs) > 0)],
            ["Daily Scan Report", "✅"],
            ["Errors", str(errors)],
        ]
        return self._markdown_table(["检查项", "状态"], rows)

    def _score_field(self, columns: set[str]) -> str | None:
        for field in ["evidence_score", "early_alpha_score", "agent_score", "alpha_score"]:
            if field in columns:
                return field
        return None

    def _average_duration(self, runs: list[dict[str, Any]]) -> float | None:
        values = [self._number(row.get("duration_seconds")) for row in runs]
        clean_values = [value for value in values if value is not None]
        if not clean_values:
            return None
        return sum(clean_values) / len(clean_values)

    def _kv_table(self, rows: list[tuple[str, Any]]) -> str:
        return self._markdown_table(["字段", "内容"], [[str(key), self._value(value)] for key, value in rows]) + "\n"

    def _empty_table(self, headers: list[str]) -> str:
        return self._markdown_table(headers, [[MISSING for _ in headers]]) + "\n"

    def _markdown_table(self, headers: list[str], rows: list[list[str]]) -> str:
        clean_headers = [self._escape_cell(header) for header in headers]
        lines = [
            "| " + " | ".join(clean_headers) + " |",
            "| " + " | ".join("---" for _ in clean_headers) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(self._escape_cell(cell) for cell in row) + " |")
        return "\n".join(lines) + "\n"

    def _escape_cell(self, value: Any) -> str:
        return self._value(value).replace("|", "\\|").replace("\n", " ")

    def _value(self, value: Any) -> str:
        if value is None:
            return MISSING
        text = str(value).strip()
        return text if text else MISSING

    def _number(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _money(self, value: Any) -> str:
        number = self._number(value)
        if number is None:
            return MISSING
        return f"{number:,.2f}"

    def _score(self, value: Any) -> str:
        number = self._number(value)
        if number is None:
            return MISSING
        return f"{number:.2f}"

    def _duration(self, value: Any) -> str:
        number = self._number(value)
        if number is None:
            return MISSING
        return f"{number:.2f}s"

    def _duration_change(self, today: float | None, yesterday: float | None) -> str:
        if today is None or yesterday is None:
            return MISSING
        return self._signed(today - yesterday, suffix="s")

    def _signed(self, value: float | int, suffix: str = "") -> str:
        sign = "+" if value > 0 else ""
        if isinstance(value, float):
            return f"{sign}{value:.2f}{suffix}"
        return f"{sign}{value}{suffix}"

    def _check(self, passed: bool) -> str:
        return "✅" if passed else "⚠️"

    def _symbol(self, row: dict[str, Any]) -> str:
        return self._value(row.get("token_symbol") or row.get("symbol"))

    def _chain(self, row: dict[str, Any]) -> str:
        return self._value(row.get("chain")).lower()

    def _theme(self, row: dict[str, Any]) -> str:
        return self._value(row.get("narrative") or row.get("theme"))

    def _assert_read_only_language(self, markdown: str) -> None:
        for term in FORBIDDEN_REPORT_TERMS:
            if term in markdown:
                raise ValueError(f"Daily Scan Report contains forbidden term: {term}")


def generate_daily_scan_report(
    db_path: Path = DB_PATH,
    output_path: Path = REPORT_PATH,
    report_date: str | None = None,
) -> Path:
    """Generate `reports/daily_scan_report.md` from existing SQLite data."""
    config = DailyScanReportConfig(db_path=Path(db_path), output_path=Path(output_path), report_date=report_date)
    return DailyScanReportGenerator(config).generate()


if __name__ == "__main__":
    path = generate_daily_scan_report()
    print(path)
