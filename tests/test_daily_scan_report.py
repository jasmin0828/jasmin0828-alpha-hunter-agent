from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.reports.daily_scan_report import DailyScanReportConfig, DailyScanReportGenerator


class DailyScanReportTest(unittest.TestCase):
    def test_generator_writes_report_with_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "alpha_hunter.db"
            output_path = tmp_path / "daily_scan_report.md"
            self._create_sample_db(db_path)

            generator = DailyScanReportGenerator(
                DailyScanReportConfig(
                    db_path=db_path,
                    output_path=output_path,
                    report_date="2026-07-06",
                    timezone="Asia/Shanghai",
                )
            )
            generated_path = generator.generate()

            self.assertEqual(generated_path, output_path)
            report = output_path.read_text(encoding="utf-8")
            for heading in [
                "# Alpha Hunter 每日扫链报告",
                "## 一、今日运行概况",
                "## 二、扫描概况",
                "## 三、24H 交易量 TOP10",
                "## 四、Social Heat TOP10",
                "## 五、Evidence Score TOP10",
                "## 六、今日新增 Candidate",
                "## 七、Theme 分布",
                "## 八、较昨日变化",
                "## 九、系统运行记录",
                "## 十、数据完整性检查",
            ]:
                self.assertIn(heading, report)

            for forbidden in ["买入", "卖出", "建议建仓", "预测上涨", "目标价"]:
                self.assertNotIn(forbidden, report)

    def _create_sample_db(self, db_path: Path) -> None:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE scan_runs (
                    id INTEGER PRIMARY KEY,
                    run_id TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    completed_at TEXT,
                    status TEXT,
                    scanned_chains TEXT,
                    tokens_scanned INTEGER,
                    signals_found INTEGER,
                    errors TEXT,
                    duration_seconds REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE token_snapshots (
                    id INTEGER PRIMARY KEY,
                    scan_run_id INTEGER,
                    chain TEXT,
                    symbol TEXT,
                    token_symbol TEXT,
                    token_name TEXT,
                    token_address TEXT,
                    contract_address TEXT,
                    volume_24h REAL,
                    liquidity_usd REAL,
                    fdv REAL,
                    narrative TEXT,
                    early_alpha_score REAL,
                    first_seen_at TEXT,
                    is_first_seen INTEGER,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE signal_events (
                    id INTEGER PRIMARY KEY,
                    scan_run_id INTEGER,
                    token_snapshot_id INTEGER,
                    chain TEXT,
                    symbol TEXT,
                    alert_level TEXT,
                    event_type TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT INTO scan_runs (
                    id, run_id, started_at, finished_at, status, scanned_chains,
                    tokens_scanned, signals_found, errors, duration_seconds
                )
                VALUES (1, 'scan-test', '2026-07-06T09:00:00+08:00',
                    '2026-07-06T09:00:18+08:00', 'completed',
                    'ethereum,solana,bsc', 3, 1, '', 18.0)
                """
            )
            conn.execute(
                """
                INSERT INTO scan_runs (
                    id, run_id, started_at, finished_at, status, scanned_chains,
                    tokens_scanned, signals_found, errors, duration_seconds
                )
                VALUES (2, 'scan-yesterday', '2026-07-05T09:00:00+08:00',
                    '2026-07-05T09:00:20+08:00', 'completed',
                    'ethereum,solana,bsc', 2, 1, '', 20.0)
                """
            )
            conn.executemany(
                """
                INSERT INTO token_snapshots (
                    scan_run_id, chain, symbol, token_symbol, token_name,
                    token_address, contract_address, volume_24h, liquidity_usd,
                    fdv, narrative, early_alpha_score, first_seen_at,
                    is_first_seen, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        1,
                        "ethereum",
                        "AAA",
                        "AAA",
                        "Alpha A",
                        "0xaaa",
                        "0xaaa",
                        100000.0,
                        50000.0,
                        1000000.0,
                        "AI",
                        80.0,
                        "2026-07-06T09:00:00+08:00",
                        1,
                        "2026-07-06T09:00:00+08:00",
                    ),
                    (
                        1,
                        "solana",
                        "BBB",
                        "BBB",
                        "Beta B",
                        "bbb",
                        "bbb",
                        90000.0,
                        40000.0,
                        900000.0,
                        "Unknown",
                        60.0,
                        "2026-07-05T09:00:00+08:00",
                        0,
                        "2026-07-06T09:00:00+08:00",
                    ),
                    (
                        2,
                        "bsc",
                        "CCC",
                        "CCC",
                        "Gamma C",
                        "0xccc",
                        "0xccc",
                        50000.0,
                        30000.0,
                        500000.0,
                        "AI",
                        50.0,
                        "2026-07-05T09:00:00+08:00",
                        1,
                        "2026-07-05T09:00:00+08:00",
                    ),
                ],
            )
            conn.execute(
                """
                INSERT INTO signal_events (
                    scan_run_id, token_snapshot_id, chain, symbol, alert_level,
                    event_type, created_at
                )
                VALUES (1, 1, 'ethereum', 'AAA', 'WATCH', 'NEW_SIGNAL',
                    '2026-07-06T09:00:00+08:00')
                """
            )
            conn.execute(
                """
                INSERT INTO signal_events (
                    scan_run_id, token_snapshot_id, chain, symbol, alert_level,
                    event_type, created_at
                )
                VALUES (2, 3, 'bsc', 'CCC', 'WATCH', 'NEW_SIGNAL',
                    '2026-07-05T09:00:00+08:00')
                """
            )


if __name__ == "__main__":
    unittest.main()
