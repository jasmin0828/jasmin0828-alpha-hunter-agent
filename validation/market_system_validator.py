"""Fail-closed validation of Alpha Hunter architecture artifacts.

Runtime log markers that only exist on the non-empty reporting path are not
treated as universal architecture invariants. The validator classifies the
completed scan outcome first, then applies the contract for that outcome.
"""

from __future__ import annotations

import json
import sqlite3
from enum import Enum
from pathlib import Path


class ScanOutcome(str, Enum):
    """Allowed outcomes for a completed deterministic validation scan."""

    SUCCESS_WITH_DATA = "SUCCESS_WITH_DATA"
    SUCCESS_EMPTY = "SUCCESS_EMPTY"
    SUCCESS_FALLBACK = "SUCCESS_FALLBACK"
    EXTERNAL_DEGRADED = "EXTERNAL_DEGRADED"
    APPLICATION_FAILURE = "APPLICATION_FAILURE"


class ContractValidationError(AssertionError):
    """Raised when an architecture or outcome contract is not satisfied."""


EXPECTED_SUBSYSTEMS = [
    "Market Intelligence",
    "AI Workflow Engine",
    "Memory Layer",
    "Content Engine",
    "Automation Layer",
    "Future AI Trading Agent",
]
REQUIRED_FILES = (
    "data/market_system_manifest.json",
    "data/alpha_tokens.csv",
    "data/alpha_hunter.db",
    "data/aios_execution_summary.json",
    "logs/app.log",
)
REQUIRED_CSV_COLUMNS = {"chain", "token_symbol", "contract_address", "pair_url"}
REQUIRED_TABLES = {"scan_runs", "token_snapshots", "signal_events"}
REQUIRED_SNAPSHOT_COLUMNS = {
    "chain",
    "token_symbol",
    "contract_address",
    "pair_url",
    "first_seen_at",
    "is_first_seen",
    "scan_count",
    "consecutive_up_count",
    "early_alpha_score",
    "early_alpha_reason",
}
REQUIRED_EVENT_COLUMNS = {
    "event_type",
    "early_alpha_score",
    "outcome_status",
    "outcome_30m_price_change",
    "outcome_1h_price_change",
    "outcome_4h_price_change",
}
RUN_LEVEL_MARKERS = (
    "Starting Alpha Hunter Market System v1.2",
    "Alpha Hunter Market System Manifest",
    "Signal Quality Summary",
)
NON_EMPTY_MARKERS = ("Early Alpha Summary", "First Seen Tokens")


def validate_workspace(workspace: Path) -> ScanOutcome:
    """Validate one isolated runtime workspace and return its scan outcome."""
    workspace = workspace.resolve()
    for relative_path in REQUIRED_FILES:
        path = workspace / relative_path
        if not path.is_file() or path.stat().st_size == 0:
            raise ContractValidationError(f"Missing or empty artifact: {relative_path}")

    manifest = _read_json(workspace / "data/market_system_manifest.json")
    execution_summary = _read_json(workspace / "data/aios_execution_summary.json")
    _validate_manifest(manifest)
    _validate_csv(workspace / "data/alpha_tokens.csv")
    latest_scan = _validate_database(workspace / "data/alpha_hunter.db")
    outcome = classify_outcome(manifest, execution_summary, latest_scan)
    if outcome is ScanOutcome.APPLICATION_FAILURE:
        raise ContractValidationError(
            f"Application failure recorded in scan artifacts: {latest_scan.get('status')}"
        )

    log_text = (workspace / "logs/app.log").read_text(encoding="utf-8", errors="ignore")
    _require_markers(log_text, RUN_LEVEL_MARKERS)
    if outcome in {ScanOutcome.SUCCESS_WITH_DATA, ScanOutcome.SUCCESS_FALLBACK}:
        _require_markers(log_text, NON_EMPTY_MARKERS)
    else:
        _require_markers(log_text, ("No tokens matched the current filters",))

    if outcome is ScanOutcome.EXTERNAL_DEGRADED:
        _require_markers(
            log_text,
            (
                "DexScreener scan failed; attempting fallback data load",
                "No fallback token data available from CSV or SQLite",
            ),
        )
    return outcome


def classify_outcome(
    manifest: dict[str, object],
    execution_summary: dict[str, object],
    latest_scan: dict[str, object],
) -> ScanOutcome:
    """Classify a completed run without making live-network assumptions."""
    if execution_summary.get("implementation_status") != "completed":
        return ScanOutcome.APPLICATION_FAILURE
    if str(latest_scan.get("status", "")).lower() != "completed":
        return ScanOutcome.APPLICATION_FAILURE

    scan_summary = manifest.get("scan_summary")
    if not isinstance(scan_summary, dict) or "token_count" not in scan_summary:
        raise ContractValidationError("Manifest scan_summary is incomplete")
    token_count = int(scan_summary["token_count"] or 0)
    fallbacks = execution_summary.get("fallbacks") or []
    if not isinstance(fallbacks, list):
        raise ContractValidationError("Execution summary fallbacks must be a list")
    if token_count > 0 and fallbacks:
        return ScanOutcome.SUCCESS_FALLBACK
    if token_count == 0 and fallbacks:
        return ScanOutcome.EXTERNAL_DEGRADED
    if token_count == 0:
        return ScanOutcome.SUCCESS_EMPTY
    return ScanOutcome.SUCCESS_WITH_DATA


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractValidationError(f"JSON artifact must be an object: {path}")
    return value


def _validate_manifest(manifest: dict[str, object]) -> None:
    if list((manifest.get("subsystems") or {}).keys()) != EXPECTED_SUBSYSTEMS:
        raise ContractValidationError(f"Unexpected subsystems: {manifest.get('subsystems')}")
    if "layers" in manifest:
        raise ContractValidationError("Manifest must use `subsystems`, not `layers`.")

    safety = manifest.get("safety_boundary") or {}
    for key in ["wallet_connection", "private_keys", "transaction_signing", "automated_trading"]:
        if safety.get(key) is not False:
            raise ContractValidationError(f"Safety boundary failed for {key}: {safety.get(key)}")

    scan_summary = manifest.get("scan_summary") or {}
    for key in ["token_count", "alert_distribution"]:
        if key not in scan_summary:
            raise ContractValidationError(f"Manifest scan_summary is incomplete: {scan_summary}")


def _validate_csv(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ContractValidationError(f"CSV is empty: {path}")
    missing = REQUIRED_CSV_COLUMNS - set(lines[0].split(","))
    if missing:
        raise ContractValidationError(f"Missing CSV columns: {sorted(missing)}")


def _validate_database(path: Path) -> dict[str, object]:
    with sqlite3.connect(path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing_tables = REQUIRED_TABLES - tables
        if missing_tables:
            raise ContractValidationError(f"Missing SQLite tables: {sorted(missing_tables)}")

        snapshot_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(token_snapshots)")
        }
        missing_snapshot_columns = REQUIRED_SNAPSHOT_COLUMNS - snapshot_columns
        if missing_snapshot_columns:
            raise ContractValidationError(
                f"Missing token_snapshots columns: {sorted(missing_snapshot_columns)}"
            )

        event_columns = {row[1] for row in connection.execute("PRAGMA table_info(signal_events)")}
        missing_event_columns = REQUIRED_EVENT_COLUMNS - event_columns
        if missing_event_columns:
            raise ContractValidationError(
                f"Missing signal_events columns: {sorted(missing_event_columns)}"
            )

        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM scan_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise ContractValidationError("SQLite scan_runs has no recorded run")
    return dict(row)


def _require_markers(log_text: str, markers: tuple[str, ...]) -> None:
    for marker in markers:
        if marker not in log_text:
            raise ContractValidationError(f"Missing log marker for current outcome: {marker}")
