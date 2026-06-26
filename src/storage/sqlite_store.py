"""SQLite storage for Alpha Hunter Market System.

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
                    run_id TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    token_count INTEGER NOT NULL DEFAULT 0,
                    scanned_chains TEXT DEFAULT '',
                    tokens_scanned INTEGER NOT NULL DEFAULT 0,
                    signals_found INTEGER NOT NULL DEFAULT 0,
                    errors TEXT DEFAULT '',
                    duration_seconds REAL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS token_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL,
                    chain TEXT DEFAULT 'unknown',
                    symbol TEXT,
                    token_symbol TEXT,
                    token_name TEXT,
                    token_address TEXT,
                    contract_address TEXT,
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
                    pair_url TEXT,
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
                    price_at_discovery REAL,
                    price_24h REAL,
                    price_72h REAL,
                    price_7d REAL,
                    outcome_status TEXT DEFAULT 'PENDING',
                    outcome_checked_at TEXT,
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_run_id INTEGER NOT NULL,
                    token_snapshot_id INTEGER NOT NULL,
                    chain TEXT DEFAULT 'unknown',
                    token_address TEXT,
                    symbol TEXT,
                    token_name TEXT,
                    previous_alert_level TEXT DEFAULT 'IGNORE',
                    alert_level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    early_alpha_score REAL DEFAULT 0,
                    agent_score REAL DEFAULT 0,
                    price_usd REAL,
                    volume_24h REAL,
                    liquidity_usd REAL,
                    token_age_bucket TEXT,
                    rug_risk_level TEXT,
                    consecutive_up_count INTEGER DEFAULT 0,
                    early_alpha_reason TEXT DEFAULT '',
                    alert_reason TEXT DEFAULT '',
                    outcome_30m_price_change REAL,
                    outcome_1h_price_change REAL,
                    outcome_4h_price_change REAL,
                    outcome_1h_volume_change REAL,
                    outcome_1h_early_alpha_change REAL,
                    price_at_discovery REAL,
                    price_24h REAL,
                    price_72h REAL,
                    price_7d REAL,
                    outcome_checked_at TEXT,
                    outcome_status TEXT DEFAULT 'PENDING',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scan_run_id) REFERENCES scan_runs(id),
                    FOREIGN KEY (token_snapshot_id) REFERENCES token_snapshots(id)
                )
                """
            )
            self._ensure_scan_run_columns(conn)
            self._ensure_trend_columns(conn)
            self._ensure_signal_event_columns(conn)
        self.logger.info("Initialized SQLite database at %s", self.db_path)

    def _ensure_scan_run_columns(self, conn: sqlite3.Connection) -> None:
        """Add v1.1 Observation run-log columns to existing scan_runs tables."""
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(scan_runs)").fetchall()
        }
        migrations = {
            "run_id": "TEXT",
            "finished_at": "TEXT",
            "scanned_chains": "TEXT DEFAULT ''",
            "tokens_scanned": "INTEGER NOT NULL DEFAULT 0",
            "signals_found": "INTEGER NOT NULL DEFAULT 0",
            "errors": "TEXT DEFAULT ''",
            "duration_seconds": "REAL DEFAULT 0",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE scan_runs ADD COLUMN {column} {definition}")

    def _ensure_trend_columns(self, conn: sqlite3.Connection) -> None:
        """Add v0.7-v1.0 columns when upgrading an existing database."""
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(token_snapshots)").fetchall()
        }
        migrations = {
            "chain": "TEXT DEFAULT 'unknown'",
            "token_symbol": "TEXT",
            "contract_address": "TEXT",
            "pair_url": "TEXT",
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
            "price_at_discovery": "REAL",
            "price_24h": "REAL",
            "price_72h": "REAL",
            "price_7d": "REAL",
            "outcome_status": "TEXT DEFAULT 'PENDING'",
            "outcome_checked_at": "TEXT",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE token_snapshots ADD COLUMN {column} {definition}")

    def _ensure_signal_event_columns(self, conn: sqlite3.Connection) -> None:
        """Add v1.2 Signal Memory outcome columns when upgrading an existing database."""
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(signal_events)").fetchall()
        }
        migrations = {
            "chain": "TEXT DEFAULT 'unknown'",
            "outcome_30m_price_change": "REAL",
            "outcome_1h_price_change": "REAL",
            "outcome_4h_price_change": "REAL",
            "outcome_1h_volume_change": "REAL",
            "outcome_1h_early_alpha_change": "REAL",
            "price_at_discovery": "REAL",
            "price_24h": "REAL",
            "price_72h": "REAL",
            "price_7d": "REAL",
            "outcome_checked_at": "TEXT",
            "outcome_status": "TEXT DEFAULT 'PENDING'",
        }
        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(f"ALTER TABLE signal_events ADD COLUMN {column} {definition}")

    def create_scan_run(self) -> int:
        """Create a scan_runs record and return its id."""
        started_at = self._now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO scan_runs (run_id, started_at, status) VALUES (?, ?, ?)",
                ("", started_at, "running"),
            )
            scan_run_id = int(cursor.lastrowid)
            conn.execute(
                "UPDATE scan_runs SET run_id = ? WHERE id = ?",
                (f"scan-{scan_run_id}", scan_run_id),
            )
            return scan_run_id

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
                    scan_run_id, chain, symbol, token_symbol, token_name, token_address,
                    contract_address, price_usd,
                    liquidity_usd, volume_24h, price_change_24h, fdv, market_cap,
                    pair_created_at, alpha_score, risk_score, ai_summary, dex, url,
                    pair_url, price_at_discovery, outcome_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        self.logger.info("Saved %s token snapshots to SQLite", len(rows))
        return len(rows)

    def finish_scan_run(
        self,
        scan_run_id: int,
        status: str,
        token_count: int,
        scanned_chains: list[str] | None = None,
        signals_found: int = 0,
        errors: list[str] | None = None,
        duration_seconds: float | None = None,
    ) -> None:
        """Mark a scan run as completed or failed."""
        finished_at = self._now()
        chain_text = ",".join(scanned_chains or [])
        error_text = "\n".join(errors or [])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET completed_at = ?,
                    finished_at = ?,
                    status = ?,
                    token_count = ?,
                    tokens_scanned = ?,
                    scanned_chains = ?,
                    signals_found = ?,
                    errors = ?,
                    duration_seconds = ?
                WHERE id = ?
                """,
                (
                    finished_at,
                    finished_at,
                    status,
                    token_count,
                    token_count,
                    chain_text,
                    int(signals_found or 0),
                    error_text,
                    float(duration_seconds or 0),
                    scan_run_id,
                ),
            )

    def load_scan_run(self, scan_run_id: int) -> dict[str, Any]:
        """Load one scan run as a dict for manifest/report summaries."""
        if not self.db_path.exists():
            return {}
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT *
                FROM scan_runs
                WHERE id = ?
                """,
                (scan_run_id,),
            ).fetchone()
        return dict(row) if row else {}

    def load_recent_scan_runs(self, days: int = 7) -> pd.DataFrame:
        """Load recent scan run logs for observation dashboard summaries."""
        if not self.db_path.exists():
            return pd.DataFrame()
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM scan_runs
                WHERE datetime(started_at) >= datetime('now', ?)
                ORDER BY started_at DESC, id DESC
                """,
                conn,
                params=(f"-{int(days)} days",),
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

    def create_signal_events(self, scan_run_id: int, snapshots: pd.DataFrame) -> pd.DataFrame:
        """Create durable events only for first alerts or alert-level upgrades."""
        if snapshots.empty or "alert_level" not in snapshots.columns:
            return pd.DataFrame()

        candidates = snapshots[snapshots["alert_level"].isin(["CRITICAL", "HIGH", "WATCH"])].copy()
        if candidates.empty:
            return candidates.head(0)

        events: list[dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            for _, token in candidates.iterrows():
                previous_level = self._previous_alert_level(
                    conn,
                    self._chain_value(token),
                    str(token.get("token_address") or ""),
                    scan_run_id,
                )
                event_type = self._signal_event_type(previous_level, str(token.get("alert_level") or "IGNORE"))
                if event_type is None:
                    continue
                events.append(self._signal_event_row(scan_run_id, token, previous_level, event_type))

            if events:
                conn.executemany(
                    """
                    INSERT INTO signal_events (
                        scan_run_id, token_snapshot_id, chain, token_address, symbol, token_name,
                        previous_alert_level, alert_level, event_type, early_alpha_score,
                        agent_score, price_usd, volume_24h, liquidity_usd, token_age_bucket,
                        rug_risk_level, consecutive_up_count, early_alpha_reason,
                        alert_reason, price_at_discovery, created_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    [
                        (
                            event["scan_run_id"],
                            event["token_snapshot_id"],
                            event["chain"],
                            event["token_address"],
                            event["symbol"],
                            event["token_name"],
                            event["previous_alert_level"],
                            event["alert_level"],
                            event["event_type"],
                            event["early_alpha_score"],
                            event["agent_score"],
                            event["price_usd"],
                            event["volume_24h"],
                            event["liquidity_usd"],
                            event["token_age_bucket"],
                            event["rug_risk_level"],
                            event["consecutive_up_count"],
                            event["early_alpha_reason"],
                            event["alert_reason"],
                            event["price_at_discovery"],
                            event["created_at"],
                        )
                        for event in events
                    ],
                )

        if not events:
            return candidates.head(0)
        event_df = pd.DataFrame(events)
        self.logger.info("Created %s signal events", len(event_df))
        return event_df

    def load_latest_signal_events(self, limit: int = 100) -> pd.DataFrame:
        """Load recent signal transition events for dashboard and audit views."""
        if not self.db_path.exists():
            return pd.DataFrame()
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM signal_events
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                conn,
                params=(limit,),
            )

    def update_signal_event_outcomes(self) -> int:
        """Update signal events with 30m, 1h, and 4h follow-up outcomes when available."""
        if not self.db_path.exists():
            return 0

        with sqlite3.connect(self.db_path) as conn:
            events = pd.read_sql_query(
                """
                SELECT *
                FROM signal_events
                WHERE outcome_status = 'PENDING'
                ORDER BY created_at ASC, id ASC
                """,
                conn,
            )
            if events.empty:
                return 0

            snapshots = pd.read_sql_query(
                """
                SELECT chain, token_address, created_at, price_usd, volume_24h, early_alpha_score
                FROM token_snapshots
                WHERE COALESCE(chain, 'unknown') || ':' || token_address IN (
                    SELECT DISTINCT COALESCE(chain, 'unknown') || ':' || token_address
                    FROM signal_events
                    WHERE outcome_status = 'PENDING'
                )
                ORDER BY chain ASC, token_address ASC, created_at ASC, id ASC
                """,
                conn,
            )
            if snapshots.empty:
                return 0

            outcome_rows = self._calculate_signal_outcomes(events, snapshots)
            if not outcome_rows:
                return 0

            conn.executemany(
                """
                UPDATE signal_events
                SET outcome_30m_price_change = ?,
                    outcome_1h_price_change = ?,
                    outcome_4h_price_change = ?,
                    outcome_1h_volume_change = ?,
                    outcome_1h_early_alpha_change = ?,
                    outcome_status = ?,
                    outcome_checked_at = ?
                WHERE id = ?
                """,
                outcome_rows,
            )

        self.logger.info("Updated %s signal event outcomes", len(outcome_rows))
        return len(outcome_rows)

    def _row_values(self, scan_run_id: int, row: pd.Series, created_at: str) -> tuple[Any, ...]:
        """Convert a token dataframe row into SQLite insert values."""
        return (
            scan_run_id,
            self._chain_value(row),
            self._value(row, "symbol"),
            self._value(row, "token_symbol") or self._value(row, "symbol"),
            self._value(row, "token_name"),
            self._value(row, "token_address"),
            self._value(row, "contract_address") or self._value(row, "token_address"),
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
            self._value(row, "pair_url") or self._value(row, "url"),
            self._number(row, "price_usd"),
            "PENDING",
            created_at,
        )

    def _value(self, row: pd.Series, key: str) -> str:
        """Return a string value that is safe for SQLite."""
        value = row.get(key)
        if pd.isna(value):
            return ""
        return str(value)

    def _chain_value(self, row: pd.Series) -> str:
        """Return the normalized chain field for multi-chain token identity."""
        return self._normalize_chain(row.get("chain"))

    def _normalize_chain(self, value: object) -> str:
        """Normalize nullable chain values for SQLite identity comparisons."""
        if pd.isna(value):
            return "unknown"
        normalized = str(value or "").strip().lower()
        return normalized or "unknown"

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

    def _previous_alert_level(
        self,
        conn: sqlite3.Connection,
        chain: str,
        token_address: str,
        scan_run_id: int,
    ) -> str:
        """Return the latest prior alert level for this token before the current scan."""
        if not token_address:
            return "IGNORE"
        row = conn.execute(
            """
            SELECT alert_level
            FROM token_snapshots
            WHERE COALESCE(chain, 'unknown') = ?
              AND token_address = ?
              AND scan_run_id < ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (self._normalize_chain(chain), token_address, scan_run_id),
        ).fetchone()
        if row is None or row[0] is None:
            return "IGNORE"
        return str(row[0])

    def _signal_event_type(self, previous_level: str, current_level: str) -> str | None:
        """Return event type for first alerts and upgrades; suppress repeated noise."""
        rank = {"IGNORE": 0, "WATCH": 1, "HIGH": 2, "CRITICAL": 3}
        previous_rank = rank.get(previous_level, 0)
        current_rank = rank.get(current_level, 0)
        if current_rank <= 0:
            return None
        if previous_rank <= 0:
            return "NEW_SIGNAL"
        if current_rank > previous_rank:
            return "UPGRADE"
        return None

    def _signal_event_row(
        self,
        scan_run_id: int,
        token: pd.Series,
        previous_alert_level: str,
        event_type: str,
    ) -> dict[str, Any]:
        """Convert one snapshot into a signal event row."""
        return {
            "scan_run_id": scan_run_id,
            "token_snapshot_id": int(token.get("id") or 0),
            "chain": self._chain_value(token),
            "token_address": self._value(token, "token_address"),
            "symbol": self._value(token, "symbol"),
            "token_name": self._value(token, "token_name"),
            "previous_alert_level": previous_alert_level,
            "alert_level": self._value(token, "alert_level") or "IGNORE",
            "event_type": event_type,
            "early_alpha_score": self._number(token, "early_alpha_score") or 0,
            "agent_score": self._number(token, "agent_score") or 0,
            "price_usd": self._number(token, "price_usd"),
            "volume_24h": self._number(token, "volume_24h"),
            "liquidity_usd": self._number(token, "liquidity_usd"),
            "price_at_discovery": self._number(token, "price_usd"),
            "token_age_bucket": self._value(token, "token_age_bucket"),
            "rug_risk_level": self._value(token, "rug_risk_level"),
            "consecutive_up_count": int(token.get("consecutive_up_count") or 0),
            "early_alpha_reason": self._value(token, "early_alpha_reason"),
            "alert_reason": self._value(token, "alert_reason"),
            "created_at": self._value(token, "created_at") or self._now(),
        }

    def _calculate_signal_outcomes(self, events: pd.DataFrame, snapshots: pd.DataFrame) -> list[tuple[Any, ...]]:
        """Return SQLite update rows for events with enough follow-up data."""
        events = events.copy()
        snapshots = snapshots.copy()
        events["created_at"] = pd.to_datetime(events["created_at"], errors="coerce", utc=True)
        snapshots["created_at"] = pd.to_datetime(snapshots["created_at"], errors="coerce", utc=True)
        snapshots["price_usd"] = pd.to_numeric(snapshots["price_usd"], errors="coerce")
        snapshots["volume_24h"] = pd.to_numeric(snapshots["volume_24h"], errors="coerce")
        snapshots["early_alpha_score"] = pd.to_numeric(snapshots["early_alpha_score"], errors="coerce")

        rows: list[tuple[Any, ...]] = []
        grouped_snapshots = {
            (self._normalize_chain(chain), token_address): group.sort_values("created_at")
            for (chain, token_address), group in snapshots.groupby(["chain", "token_address"], dropna=False)
        }

        for _, event in events.iterrows():
            event_time = event.get("created_at")
            chain = self._normalize_chain(event.get("chain"))
            token_address = event.get("token_address")
            history = grouped_snapshots.get((chain, token_address))
            if history is None or history.empty or pd.isna(event_time):
                continue

            base_price = float(event.get("price_usd") or 0)
            base_volume = float(event.get("volume_24h") or 0)
            base_early_alpha = float(event.get("early_alpha_score") or 0)
            follow_30m = self._first_snapshot_after(history, event_time, 30)
            follow_1h = self._first_snapshot_after(history, event_time, 60)
            follow_4h = self._first_snapshot_after(history, event_time, 240)

            if follow_30m is None and follow_1h is None and follow_4h is None:
                continue

            price_30m = self._pct_change_from_row(base_price, follow_30m, "price_usd")
            price_1h = self._pct_change_from_row(base_price, follow_1h, "price_usd")
            price_4h = self._pct_change_from_row(base_price, follow_4h, "price_usd")
            volume_1h = self._pct_change_from_row(base_volume, follow_1h, "volume_24h")
            early_alpha_1h = self._change_from_row(base_early_alpha, follow_1h, "early_alpha_score")
            status = "COMPLETE" if follow_4h is not None else "PARTIAL"

            rows.append(
                (
                    price_30m,
                    price_1h,
                    price_4h,
                    volume_1h,
                    early_alpha_1h,
                    status,
                    self._now(),
                    int(event["id"]),
                )
            )
        return rows

    def _first_snapshot_after(self, history: pd.DataFrame, event_time: pd.Timestamp, minutes: int) -> pd.Series | None:
        """Find the first snapshot at or after an event follow-up horizon."""
        cutoff = event_time + pd.Timedelta(minutes=minutes)
        candidates = history[history["created_at"] >= cutoff]
        if candidates.empty:
            return None
        return candidates.iloc[0]

    def _pct_change_from_row(self, base: float, row: pd.Series | None, column: str) -> float | None:
        """Return percentage change from event value to a follow-up row."""
        if row is None or base == 0:
            return None
        value = row.get(column)
        if pd.isna(value):
            return None
        return round(((float(value) - base) / base) * 100, 2)

    def _change_from_row(self, base: float, row: pd.Series | None, column: str) -> float | None:
        """Return absolute change from event value to a follow-up row."""
        if row is None:
            return None
        value = row.get(column)
        if pd.isna(value):
            return None
        return round(float(value) - base, 2)

    def _now(self) -> str:
        """Return current UTC time as ISO text."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
