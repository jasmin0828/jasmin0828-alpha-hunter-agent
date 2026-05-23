"""Minimal SQLite storage patch for Alpha Hunter Agent v1.0.

Uses only Python's standard-library sqlite3 module. Each scan creates one
scan_runs row and appends token_snapshots rows without overwriting history.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.paths import DATA_DIR


DB_PATH = DATA_DIR / "alpha_hunter.db"


class SQLiteStore:
    """Small SQLite writer for scan runs, token snapshots, and alerts."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> None:
        """Create the SQLite database and required v0.6 tables."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    token_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL,
                    symbol TEXT,
                    token_name TEXT,
                    token_address TEXT,
                    price_usd REAL,
                    liquidity_usd REAL,
                    volume_24h REAL,
                    price_change_24h REAL,
                    fdv REAL,
                    market_cap REAL,
                    pair_created_at REAL,
                    alpha_score REAL,
                    risk_score REAL,
                    ai_summary TEXT,
                    dex TEXT,
                    url TEXT,
                    score_change_10m REAL DEFAULT 0,
                    score_change_30m REAL DEFAULT 0,
                    volume_change_10m REAL DEFAULT 0,
                    volume_spike_ratio REAL DEFAULT 1,
                    liquidity_change_10m REAL DEFAULT 0,
                    price_change_since_last_scan REAL DEFAULT 0,
                    momentum_status TEXT DEFAULT 'STABLE',
                    narrative TEXT DEFAULT 'Unknown',
                    narrative_score REAL DEFAULT 0,
                    smart_money_score REAL DEFAULT 0,
                    smart_money_signal TEXT DEFAULT 'NEUTRAL',
                    token_age_minutes REAL DEFAULT 0,
                    token_age_hours REAL DEFAULT 0,
                    token_age_bucket TEXT DEFAULT 'UNKNOWN',
                    rug_risk_level TEXT DEFAULT 'LOW',
                    rug_risk_score REAL DEFAULT 0,
                    volume_liquidity_ratio REAL DEFAULT 0,
                    fdv_liquidity_ratio REAL DEFAULT 0,
                    extreme_pump_flag INTEGER DEFAULT 0,
                    low_liquidity_flag INTEGER DEFAULT 0,
                    suspicious_volume_flag INTEGER DEFAULT 0,
                    risk_notes TEXT DEFAULT '',
                    alert_level TEXT DEFAULT 'IGNORE',
                    alert_reason TEXT DEFAULT '',
                    agent_score REAL DEFAULT 0,
                    first_seen_at TEXT,
                    is_first_seen INTEGER DEFAULT 0,
                    scan_count INTEGER DEFAULT 0,
                    consecutive_up_count INTEGER DEFAULT 0,
                    early_alpha_score REAL DEFAULT 0,
                    early_alpha_reason TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER,
                    token_snapshot_id INTEGER,
                    symbol TEXT,
                    message TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id),
                    FOREIGN KEY (token_snapshot_id) REFERENCES token_snapshots(id)
                )
                """
            )
            self._ensure_trend_columns(conn)
        self.logger.info("Initialized SQLite database at %s", self.db_path)

    def _ensure_trend_columns(self, conn: sqlite3.Connection) -> None:
        """Add v0.7-v1.0 columns when upgrading an existing database."""
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(token_snapshots)").fetchall()
        }
        migrations = {
            "score_change_10m": "REAL DEFAULT 0",
            "score_change_30m": "REAL DEFAULT 0",
            "volume_change_10m": "REAL DEFAULT 0",
            "volume_spike_ratio": "REAL DEFAULT 1",
            "liquidity_change_10m": "REAL DEFAULT 0",
            "price_change_since_last_scan": "REAL DEFAULT 0",
            "momentum_status": "TEXT DEFAULT 'STABLE'",
            "narrative": "TEXT DEFAULT 'Unknown'",
            "narrative_score": "REAL DEFAULT 0",
            "smart_money_score": "REAL DEFAULT 0",
            "smart_money_signal": "TEXT DEFAULT 'NEUTRAL'",
            "token_age_minutes": "REAL DEFAULT 0",
            "token_age_hours": "REAL DEFAULT 0",
            "token_age_bucket": "TEXT DEFAULT 'UNKNOWN'",
            "rug_risk_level": "TEXT DEFAULT 'LOW'",
            "rug_risk_score": "REAL DEFAULT 0",
            "volume_liquidity_ratio": "REAL DEFAULT 0",
            "fdv_liquidity_ratio": "REAL DEFAULT 0",
            "extreme_pump_flag": "INTEGER DEFAULT 0",
            "low_liquidity_flag": "INTEGER DEFAULT 0",
            "suspicious_volume_flag": "INTEGER DEFAULT 0",
            "risk_notes": "TEXT DEFAULT ''",
            "alert_level": "TEXT DEFAULT 'IGNORE'",
            "alert_reason": "TEXT DEFAULT ''",
            "agent_score": "REAL DEFAULT 0",
            "first_seen_at": "TEXT",
            "is_first_seen": "INTEGER DEFAULT 0",
            "scan_count": "INTEGER DEFAULT 0",
            "consecutive_up_count": "INTEGER DEFAULT 0",
            "early_alpha_score": "REAL DEFAULT 0",
            "early_alpha_reason": "TEXT DEFAULT ''",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE token_snapshots ADD COLUMN {column} {definition}")

    def create_scan_run(self) -> int:
        """Create a scan_runs record and return its id."""
        started_at = self._now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO scan_runs (started_at, status) VALUES (?, ?)",
                (started_at, "running"),
            )
            return int(cursor.lastrowid)

    def save_token_snapshots(self, scan_run_id: int, tokens: pd.DataFrame) -> int:
        """Append token snapshots for the current scan run."""
        if tokens.empty:
            return 0

        created_at = self._now()
        rows = [self._row_values(scan_run_id, row, created_at) for _, row in tokens.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO token_snapshots (
                    scan_run_id, symbol, token_name, token_address, price_usd,
                    liquidity_usd, volume_24h, price_change_24h, fdv, market_cap,
                    pair_created_at, alpha_score, risk_score, ai_summary, dex, url, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self.logger.info("Saved %s token snapshots to SQLite", len(rows))
        return len(rows)

    def finish_scan_run(self, scan_run_id: int, status: str, token_count: int) -> None:
        """Mark a scan run as completed or failed."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET completed_at = ?, status = ?, token_count = ?
                WHERE id = ?
                """,
                (self._now(), status, token_count, scan_run_id),
            )

    def load_snapshots(self) -> pd.DataFrame:
        """Load all token snapshots for trend calculations."""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM token_snapshots
                ORDER BY created_at ASC, id ASC
                """,
                conn,
            )

    def update_trend_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist trend metric columns computed by TrendService."""
        if snapshots.empty:
            return

        columns = [
            "score_change_10m",
            "score_change_30m",
            "volume_change_10m",
            "volume_spike_ratio",
            "liquidity_change_10m",
            "price_change_since_last_scan",
            "momentum_status",
            "id",
        ]
        rows = [tuple(row[column] for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET score_change_10m = ?,
                    score_change_30m = ?,
                    volume_change_10m = ?,
                    volume_spike_ratio = ?,
                    liquidity_change_10m = ?,
                    price_change_since_last_scan = ?,
                    momentum_status = ?
                WHERE id = ?
                """,
                rows,
            )

    def update_intelligence_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist Narrative Engine and Smart Money Intelligence columns."""
        if snapshots.empty:
            return

        columns = [
            "narrative",
            "narrative_score",
            "smart_money_score",
            "smart_money_signal",
            "id",
        ]
        rows = [tuple(row[column] for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET narrative = ?,
                    narrative_score = ?,
                    smart_money_score = ?,
                    smart_money_signal = ?
                WHERE id = ?
                """,
                rows,
            )

    def update_token_age_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist Token Age Intelligence columns."""
        if snapshots.empty:
            return

        columns = [
            "token_age_minutes",
            "token_age_hours",
            "token_age_bucket",
            "id",
        ]
        rows = [tuple(self._sqlite_value(row[column]) for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET token_age_minutes = ?,
                    token_age_hours = ?,
                    token_age_bucket = ?
                WHERE id = ?
                """,
                rows,
            )

    def update_risk_intelligence_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist Risk Intelligence Engine columns."""
        if snapshots.empty:
            return

        columns = [
            "rug_risk_level",
            "rug_risk_score",
            "volume_liquidity_ratio",
            "fdv_liquidity_ratio",
            "extreme_pump_flag",
            "low_liquidity_flag",
            "suspicious_volume_flag",
            "risk_notes",
            "id",
        ]
        rows = [tuple(self._sqlite_value(row[column]) for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET rug_risk_level = ?,
                    rug_risk_score = ?,
                    volume_liquidity_ratio = ?,
                    fdv_liquidity_ratio = ?,
                    extreme_pump_flag = ?,
                    low_liquidity_flag = ?,
                    suspicious_volume_flag = ?,
                    risk_notes = ?
                WHERE id = ?
                """,
                rows,
            )

    def update_signal_calibration_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist Signal Calibration columns."""
        if snapshots.empty:
            return

        columns = [
            "alert_level",
            "alert_reason",
            "agent_score",
            "id",
        ]
        rows = [tuple(self._sqlite_value(row[column]) for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET alert_level = ?,
                    alert_reason = ?,
                    agent_score = ?
                WHERE id = ?
                """,
                rows,
            )

    def update_early_alpha_metrics(self, snapshots: pd.DataFrame) -> None:
        """Persist Early Alpha Engine columns."""
        if snapshots.empty:
            return

        columns = [
            "first_seen_at",
            "is_first_seen",
            "scan_count",
            "consecutive_up_count",
            "early_alpha_score",
            "early_alpha_reason",
            "id",
        ]
        rows = [tuple(self._sqlite_value(row[column]) for column in columns) for _, row in snapshots.iterrows()]
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                UPDATE token_snapshots
                SET first_seen_at = ?,
                    is_first_seen = ?,
                    scan_count = ?,
                    consecutive_up_count = ?,
                    early_alpha_score = ?,
                    early_alpha_reason = ?
                WHERE id = ?
                """,
                rows,
            )

    def load_scan_snapshots(self, scan_run_id: int) -> pd.DataFrame:
        """Load snapshots for a single scan run."""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM token_snapshots
                WHERE scan_run_id = ?
                ORDER BY early_alpha_score DESC, agent_score DESC, score_change_10m DESC, volume_spike_ratio DESC, alpha_score DESC
                """,
                conn,
                params=(scan_run_id,),
            )

    def load_latest_token_snapshots(self) -> pd.DataFrame:
        """Load the most recent token snapshot set for fallback mode."""
        if not self.db_path.exists():
            return pd.DataFrame()

        with sqlite3.connect(self.db_path) as conn:
            latest_scan = conn.execute(
                "SELECT MAX(scan_run_id) FROM token_snapshots"
            ).fetchone()[0]
            if latest_scan is None:
                return pd.DataFrame()

            return pd.read_sql_query(
                """
                SELECT *
                FROM token_snapshots
                WHERE scan_run_id = ?
                ORDER BY alpha_score DESC, volume_24h DESC
                """,
                conn,
                params=(latest_scan,),
            )

    def _row_values(self, scan_run_id: int, row: pd.Series, created_at: str) -> tuple[Any, ...]:
        """Convert a token dataframe row into SQLite insert values."""
        return (
            scan_run_id,
            self._value(row, "symbol"),
            self._value(row, "token_name"),
            self._value(row, "token_address"),
            self._number(row, "price_usd"),
            self._number(row, "liquidity_usd"),
            self._number(row, "volume_24h"),
            self._number(row, "price_change_24h"),
            self._number(row, "fdv"),
            self._number(row, "market_cap"),
            self._number(row, "pair_created_at"),
            self._number(row, "alpha_score"),
            self._number(row, "risk_score"),
            self._value(row, "ai_summary"),
            self._value(row, "dex"),
            self._value(row, "url"),
            created_at,
        )

    def _value(self, row: pd.Series, key: str) -> str:
        """Return a string value that is safe for SQLite."""
        value = row.get(key)
        if pd.isna(value):
            return ""
        return str(value)

    def _number(self, row: pd.Series, key: str) -> float | None:
        """Return a numeric value or None when missing."""
        value = row.get(key)
        if pd.isna(value):
            return None
        return float(value)

    def _sqlite_value(self, value: Any) -> Any:
        """Normalize pandas and bool values for sqlite3 writes."""
        if pd.isna(value):
            return None
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, bool):
            return int(value)
        return value

    def _now(self) -> str:
        """Return current UTC time as ISO text."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
