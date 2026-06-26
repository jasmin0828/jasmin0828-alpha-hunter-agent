"""Runtime manifest writer for Alpha Hunter Market System."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.paths import CONTENT_DIR, DATA_DIR, LABS_DIR, MEMORY_DIR, PROJECT_ROOT, ensure_project_directories


class MarketSystemManifestService:
    """Write a compact manifest that maps each scan into the Market System."""

    MANIFEST_PATH = DATA_DIR / "market_system_manifest.json"

    SUBSYSTEMS = {
        "Market Intelligence": "Narrative Detection, Signal Analysis, Research Reports",
        "AI Workflow Engine": "ChatGPT + Codex",
        "Memory Layer": "Obsidian-ready markdown and signal memory",
        "Content Engine": "X / Threads / Notes drafts",
        "Automation Layer": "Bots / Scripts / Scheduling",
        "Future AI Trading Agent": "Placeholder only; disabled by safety boundary",
    }

    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = manifest_path or self.MANIFEST_PATH

    def write_scan_manifest(
        self,
        scan_run_id: int,
        snapshots: pd.DataFrame,
        signal_events: pd.DataFrame | None = None,
        signal_quality: dict[str, Any] | None = None,
        scan_run: dict[str, Any] | None = None,
        recent_scan_runs: pd.DataFrame | None = None,
    ) -> dict[str, Any]:
        """Persist latest scan metadata for dashboard, audit, and memory workflows."""
        ensure_project_directories()
        manifest = {
            "system_name": "Alpha Hunter Market System",
            "version": "v1.2-architecture",
            "generated_at": self._now(),
            "scan_run_id": scan_run_id,
            "subsystems": self.SUBSYSTEMS,
            "paths": {
                "project_root": str(PROJECT_ROOT),
                "data": str(DATA_DIR),
                "memory": str(MEMORY_DIR),
                "content": str(CONTENT_DIR),
                "labs": str(LABS_DIR),
            },
            "safety_boundary": {
                "wallet_connection": False,
                "private_keys": False,
                "transaction_signing": False,
                "automated_trading": False,
                "future_trade_layer_enabled": False,
            },
            "scan_summary": self._scan_summary(snapshots, signal_events),
            "observation_summary": self._observation_summary(scan_run, recent_scan_runs),
            "signal_quality": signal_quality or {},
            "data_checksum": self._checksum(snapshots),
        }
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest

    def _scan_summary(self, snapshots: pd.DataFrame, signal_events: pd.DataFrame | None = None) -> dict[str, Any]:
        """Summarize the latest scan using Market System vocabulary."""
        signal_event_count = 0 if signal_events is None else int(len(signal_events))
        if snapshots.empty:
            return {
                "token_count": 0,
                "alert_count": 0,
                "signal_event_count": signal_event_count,
                "first_seen_count": 0,
                "consecutive_momentum_count": 0,
                "max_early_alpha_score": 0,
                "alert_distribution": {},
                "narrative_distribution": {},
                "age_distribution": {},
                "chain_distribution": {},
            }

        alert_mask = snapshots.get("alert_level", pd.Series(dtype="object")).isin(["CRITICAL", "HIGH", "WATCH"])
        first_seen = snapshots.get("is_first_seen", pd.Series(dtype="object")).fillna(False).astype(bool)
        consecutive = pd.to_numeric(snapshots.get("consecutive_up_count", 0), errors="coerce").fillna(0)
        early_alpha = pd.to_numeric(snapshots.get("early_alpha_score", 0), errors="coerce").fillna(0)

        return {
            "token_count": int(len(snapshots)),
            "alert_count": int(alert_mask.sum()),
            "signal_event_count": signal_event_count,
            "first_seen_count": int(first_seen.sum()),
            "consecutive_momentum_count": int((consecutive > 0).sum()),
            "max_early_alpha_score": round(float(early_alpha.max()), 2),
            "alert_distribution": self._counts(snapshots, "alert_level"),
            "narrative_distribution": self._counts(snapshots, "narrative"),
            "age_distribution": self._counts(snapshots, "token_age_bucket"),
            "chain_distribution": self._counts(snapshots, "chain"),
        }

    def _observation_summary(
        self,
        scan_run: dict[str, Any] | None,
        recent_scan_runs: pd.DataFrame | None,
    ) -> dict[str, Any]:
        """Summarize run-log health for the Observation Phase."""
        latest = scan_run or {}
        if recent_scan_runs is None or recent_scan_runs.empty:
            return {
                "window_days": 7,
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "tokens_scanned": 0,
                "signals_found": 0,
                "chain_distribution": {},
                "latest_run": latest,
            }

        runs = recent_scan_runs.copy()
        status = runs.get("status", pd.Series(dtype="object")).fillna("unknown").astype(str).str.lower()
        tokens = pd.to_numeric(runs.get("tokens_scanned", runs.get("token_count", 0)), errors="coerce").fillna(0)
        signals = pd.to_numeric(runs.get("signals_found", 0), errors="coerce").fillna(0)

        chain_distribution: dict[str, int] = {}
        if "scanned_chains" in runs.columns:
            for value in runs["scanned_chains"].fillna(""):
                for chain in str(value).split(","):
                    normalized = chain.strip().lower()
                    if normalized:
                        chain_distribution[normalized] = chain_distribution.get(normalized, 0) + 1

        return {
            "window_days": 7,
            "total_runs": int(len(runs)),
            "successful_runs": int((status == "completed").sum()),
            "failed_runs": int((status == "failed").sum()),
            "tokens_scanned": int(tokens.sum()),
            "signals_found": int(signals.sum()),
            "chain_distribution": chain_distribution,
            "latest_run": latest,
        }

    def _counts(self, snapshots: pd.DataFrame, column: str) -> dict[str, int]:
        """Return stable value counts for manifest JSON."""
        if column not in snapshots.columns:
            return {}
        counts = snapshots[column].fillna("UNKNOWN").value_counts().to_dict()
        return {str(key): int(value) for key, value in counts.items()}

    def _checksum(self, snapshots: pd.DataFrame) -> str:
        """Generate a deterministic checksum for the latest scan table."""
        if snapshots.empty:
            return hashlib.sha256(b"").hexdigest()
        csv_bytes = snapshots.sort_index(axis=1).to_csv(index=False).encode("utf-8")
        return hashlib.sha256(csv_bytes).hexdigest()

    def _now(self) -> str:
        """Return current UTC time as ISO text."""
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
