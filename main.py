"""Alpha Hunter Market System v1.2 architecture entry point.

The agent only reads public DexScreener data. It does not connect to wallets
and it never executes trades.
"""

from __future__ import annotations

import logging
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic

import pandas as pd

from src.notifications.telegram_notifier import TelegramNotifier
from src.services.alpha_token_service import AlphaTokenService
from src.services.content_draft_service import ContentDraftService
from src.services.daily_brief_service import DailyBriefService
from src.services.early_alpha_service import EarlyAlphaService
from src.services.market_system_manifest_service import MarketSystemManifestService
from src.services.memory_note_service import MemoryNoteService
from src.services.narrative_service import NarrativeService
from src.services.report_notification_service import ReportNotificationService
from src.services.risk_intelligence_service import RiskIntelligenceService
from src.services.signal_calibration_service import SignalCalibrationService
from src.services.signal_quality_service import SignalQualityService
from src.services.smart_money_service import SmartMoneyService
from src.services.token_age_service import TokenAgeService
from src.services.trend_service import TrendService
from src.storage.sqlite_store import SQLiteStore
from src.utils.logging_config import setup_logging
from src.utils.paths import DATA_DIR


RUN_INTERVAL_SECONDS = 10 * 60


def load_fallback_tokens(service: AlphaTokenService, store: SQLiteStore) -> pd.DataFrame:
    """Load the latest available token data when DexScreener is unavailable."""
    logger = logging.getLogger(__name__)

    if service.csv_path.exists():
        try:
            csv_tokens = pd.read_csv(service.csv_path)
            if not csv_tokens.empty:
                logger.warning("Using fallback token data from %s", service.csv_path)
                return csv_tokens
            logger.warning("Fallback CSV is empty: %s", service.csv_path)
        except Exception as exc:
            logger.warning("Failed to read fallback CSV %s: %s", service.csv_path, exc)

    sqlite_tokens = store.load_latest_token_snapshots()
    if not sqlite_tokens.empty:
        logger.warning("Using fallback token data from SQLite database %s", store.db_path)
        return sqlite_tokens

    logger.warning("No fallback token data available from CSV or SQLite")
    return pd.DataFrame()


def _scanned_chains(current_snapshots: pd.DataFrame, top_tokens: pd.DataFrame) -> list[str]:
    """Return normalized chain names observed in the current run."""
    source = current_snapshots if "chain" in current_snapshots.columns else top_tokens
    if source.empty or "chain" not in source.columns:
        return []
    chains = source["chain"].fillna("unknown").astype(str).str.lower()
    return sorted(chain for chain in chains.unique().tolist() if chain)


def _artifact_references(*values: object) -> list[str]:
    references: list[str] = []
    for value in values:
        items = value.values() if isinstance(value, dict) else [value]
        for item in items:
            if isinstance(item, Path) and item.exists():
                reference = str(item.resolve())
                if reference not in references:
                    references.append(reference)
    return references


def _write_execution_summary(
    *, scan_run_id: int, output_references: list[str], warnings: list[dict[str, object]],
    fallbacks: list[dict[str, object]], delivery_results: list[dict[str, object]],
) -> dict[str, object]:
    summary_path = DATA_DIR / "aios_execution_summary.json"
    summary = {
        "implementation_status": "completed",
        "scan_run_id": scan_run_id,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "output_references": output_references,
        "warnings": warnings,
        "fallbacks": fallbacks,
        "delivery_results": delivery_results,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_agent() -> dict[str, object]:
    """Run one complete alpha-token scan and save CSV plus SQLite history."""
    logger = logging.getLogger(__name__)
    service = AlphaTokenService()
    notifier = TelegramNotifier()
    store = SQLiteStore()
    trend_service = TrendService()
    narrative_service = NarrativeService()
    smart_money_service = SmartMoneyService()
    token_age_service = TokenAgeService()
    risk_intelligence_service = RiskIntelligenceService()
    early_alpha_service = EarlyAlphaService()
    signal_calibration_service = SignalCalibrationService()
    signal_quality_service = SignalQualityService()
    manifest_service = MarketSystemManifestService()
    daily_brief_service = DailyBriefService()
    content_draft_service = ContentDraftService()
    memory_note_service = MemoryNoteService()
    report_notification_service = ReportNotificationService()
    store.initialize()
    outcome_count = store.update_signal_event_outcomes()
    if outcome_count:
        logger.info("Updated %s signal event outcomes", outcome_count)
    scan_run_id = store.create_scan_run()
    run_started = monotonic()
    scan_errors: list[str] = []
    fallbacks: list[dict[str, object]] = []
    delivery_results: list[dict[str, object]] = []
    saved_count = 0

    try:
        try:
            top_tokens = service.find_and_save_top_tokens()
        except Exception as exc:
            message = f"DexScreener scan failed; fallback attempted: {exc}"
            scan_errors.append(message)
            fallbacks.append({
                "code": "DEXSCREENER_SCAN_FALLBACK",
                "message": "DexScreener scan failed; persisted fallback data was attempted",
                "source": "main.run_agent",
                "fatal": False,
            })
            logger.warning("DexScreener scan failed; attempting fallback data load: %s", exc)
            top_tokens = load_fallback_tokens(service, store)

        saved_count = store.save_token_snapshots(scan_run_id, top_tokens)
        all_snapshots = store.load_snapshots()
        if top_tokens.empty or "token_address" not in top_tokens.columns:
            pipeline_snapshots = all_snapshots[all_snapshots["scan_run_id"] == scan_run_id].copy()
        else:
            if "chain" not in top_tokens.columns:
                top_tokens["chain"] = "unknown"
            if "chain" not in all_snapshots.columns:
                all_snapshots["chain"] = "unknown"
            active_token_keys = top_tokens.dropna(subset=["token_address"]).copy()
            active_keys = set(
                zip(
                    active_token_keys["chain"].fillna("unknown").astype(str).str.lower(),
                    active_token_keys["token_address"].astype(str),
                )
            )
            snapshot_keys = list(
                zip(
                    all_snapshots["chain"].fillna("unknown").astype(str).str.lower(),
                    all_snapshots["token_address"].astype(str),
                )
            )
            pipeline_snapshots = all_snapshots[pd.Series(snapshot_keys, index=all_snapshots.index).isin(active_keys)].copy()

        trend_snapshots = trend_service.calculate_trends(pipeline_snapshots)
        current_trend_snapshots = trend_snapshots[trend_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_trend_metrics(current_trend_snapshots)
        enriched_snapshots = narrative_service.classify_tokens(trend_snapshots)
        enriched_snapshots = smart_money_service.analyze_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_intelligence_metrics(current_enriched_snapshots)
        enriched_snapshots = token_age_service.analyze_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_token_age_metrics(current_enriched_snapshots)
        enriched_snapshots = risk_intelligence_service.analyze_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_risk_intelligence_metrics(current_enriched_snapshots)
        enriched_snapshots = signal_calibration_service.calibrate_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_signal_calibration_metrics(current_enriched_snapshots)
        enriched_snapshots = early_alpha_service.analyze_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_early_alpha_metrics(current_enriched_snapshots)
        enriched_snapshots = signal_calibration_service.calibrate_tokens(enriched_snapshots)
        current_enriched_snapshots = enriched_snapshots[enriched_snapshots["scan_run_id"] == scan_run_id].copy()
        store.update_signal_calibration_metrics(current_enriched_snapshots)
        current_snapshots = store.load_scan_snapshots(scan_run_id)
        current_snapshots.to_csv(service.csv_path, index=False)
        signal_events = store.create_signal_events(scan_run_id, current_snapshots)
        scanned_chains = _scanned_chains(current_snapshots, top_tokens)
        duration_seconds = round(monotonic() - run_started, 2)
        store.finish_scan_run(
            scan_run_id,
            "completed",
            saved_count,
            scanned_chains=scanned_chains,
            signals_found=len(signal_events),
            errors=scan_errors,
            duration_seconds=duration_seconds,
        )
    except Exception as exc:
        scan_errors.append(str(exc))
        store.finish_scan_run(
            scan_run_id,
            "failed",
            saved_count,
            errors=scan_errors,
            duration_seconds=round(monotonic() - run_started, 2),
        )
        raise

    scan_run = store.load_scan_run(scan_run_id)
    recent_scan_runs = store.load_recent_scan_runs(days=7)
    signal_quality = signal_quality_service.summarize(current_snapshots, signal_events)
    manifest = manifest_service.write_scan_manifest(
        scan_run_id,
        current_snapshots,
        signal_events,
        signal_quality,
        scan_run=scan_run,
        recent_scan_runs=recent_scan_runs,
    )
    logger.info("Alpha Hunter Market System Manifest:\n%s", manifest["scan_summary"])
    logger.info("Signal Quality Summary:\n%s", signal_quality)
    brief_path = daily_brief_service.write_daily_brief(scan_run_id, current_snapshots, signal_events, manifest)
    logger.info("Alpha Hunter Daily Brief written to %s", brief_path)
    content_paths = content_draft_service.write_content_drafts(current_snapshots, signal_events, manifest)
    logger.info("Alpha Hunter Content Drafts written to %s", content_paths)
    memory_paths = memory_note_service.write_memory_notes(current_snapshots, signal_events, manifest)
    logger.info("Alpha Hunter Memory Notes written to %s", memory_paths)

    if top_tokens.empty:
        logger.info("No tokens matched the current filters")
        delivery_results.append(notifier.capture_delivery(
            "health", lambda: notifier.notify_health_status(current_snapshots, manifest, "no tokens matched current filters")
        ))
        delivery_results.extend(notify_due_reports(notifier, report_notification_service))
        outputs = _artifact_references(service.csv_path, manifest_service.manifest_path, brief_path, content_paths, memory_paths)
        return _write_execution_summary(
            scan_run_id=scan_run_id, output_references=outputs, warnings=service.diagnostics,
            fallbacks=fallbacks, delivery_results=delivery_results,
        )

    heating_tokens = current_snapshots[current_snapshots["momentum_status"] == "HEATING_UP"]
    if heating_tokens.empty:
        logger.info("Top Heating Up Tokens:\nNone")
    else:
        heating_display = heating_tokens.sort_values(
            ["score_change_10m", "volume_spike_ratio", "alpha_score"],
            ascending=[False, False, False],
        ).head(10)
        logger.info("Top Heating Up Tokens:\n%s", heating_display.to_string(index=False))

    accumulation_tokens = current_snapshots[
        current_snapshots["smart_money_signal"] == "ACCUMULATION"
    ].sort_values(["smart_money_score", "alpha_score"], ascending=[False, False]).head(10)
    if accumulation_tokens.empty:
        logger.info("Top Smart Money Accumulation Tokens:\nNone")
    else:
        logger.info("Top Smart Money Accumulation Tokens:\n%s", accumulation_tokens.to_string(index=False))

    narrative_distribution = current_snapshots["narrative"].value_counts(dropna=False)
    logger.info("Narrative Distribution:\n%s", narrative_distribution.to_string())

    age_distribution = current_snapshots["token_age_bucket"].value_counts(dropna=False)
    logger.info("Token Age Distribution:\n%s", age_distribution.to_string())

    risk_summary = current_snapshots["rug_risk_level"].value_counts(dropna=False)
    logger.info("Risk Intelligence Summary:\n%s", risk_summary.to_string())

    signal_summary = current_snapshots[["alert_level", "agent_score", "alert_reason"]].sort_values(
        "agent_score",
        ascending=False,
    )
    logger.info("Signal Calibration Summary:\n%s", signal_summary.head(10).to_string(index=False))

    alert_distribution = current_snapshots["alert_level"].value_counts(dropna=False)
    logger.info("Alert Level Distribution:\n%s", alert_distribution.to_string())

    early_alpha_summary = current_snapshots[
        [
            "chain",
            "symbol",
            "early_alpha_score",
            "early_alpha_reason",
            "is_first_seen",
            "scan_count",
            "consecutive_up_count",
            "token_age_bucket",
            "alert_level",
        ]
    ].sort_values("early_alpha_score", ascending=False)
    logger.info("Early Alpha Summary:\n%s", early_alpha_summary.head(10).to_string(index=False))

    first_seen_tokens = current_snapshots[current_snapshots["is_first_seen"].astype(bool)]
    if first_seen_tokens.empty:
        logger.info("First Seen Tokens:\nNone")
    else:
        logger.info(
            "First Seen Tokens:\n%s",
            first_seen_tokens.sort_values("early_alpha_score", ascending=False)[
                [
                    "chain",
                    "symbol",
                    "token_name",
                    "early_alpha_score",
                    "early_alpha_reason",
                    "scan_count",
                    "token_age_bucket",
                    "alert_level",
                ]
            ].to_string(index=False),
        )

    logger.info(
        "All-chain Top 10 Alpha Candidates:\n%s",
        top_tokens.sort_values(["volume_24h", "liquidity_usd"], ascending=[False, False])
        .head(10)
        .to_string(index=False),
    )
    if "chain" in top_tokens.columns:
        for chain in ["ethereum", "solana", "bsc"]:
            chain_tokens = top_tokens[top_tokens["chain"].astype(str).str.lower() == chain]
            if chain_tokens.empty:
                logger.info("%s Top 5:\nNone", chain.capitalize())
                continue
            logger.info(
                "%s Top 5:\n%s",
                chain.capitalize(),
                chain_tokens.sort_values(["volume_24h", "liquidity_usd"], ascending=[False, False])
                .head(5)
                .to_string(index=False),
            )

    if signal_events.empty:
        alert_tokens = current_snapshots.head(0)
        logger.info("No new signal events for Telegram after deduplication")
        delivery_results.append(notifier.capture_delivery(
            "health", lambda: notifier.notify_health_status(current_snapshots, manifest, "no new signal events after deduplication")
        ))
    else:
        event_ids = set(signal_events["token_snapshot_id"].astype(int))
        alert_tokens = current_snapshots[current_snapshots["id"].astype(int).isin(event_ids)].copy()
        event_context = signal_events.set_index("token_snapshot_id")[["previous_alert_level", "event_type"]]
        alert_tokens = alert_tokens.join(event_context, on="id")
    delivery_results.append(notifier.capture_delivery("signals", lambda: notifier.notify_top_tokens(alert_tokens)))
    delivery_results.extend(notify_due_reports(notifier, report_notification_service))
    outputs = _artifact_references(service.csv_path, manifest_service.manifest_path, brief_path, content_paths, memory_paths)
    return _write_execution_summary(
        scan_run_id=scan_run_id, output_references=outputs, warnings=service.diagnostics,
        fallbacks=fallbacks, delivery_results=delivery_results,
    )


def notify_due_reports(notifier: TelegramNotifier, report_service: ReportNotificationService) -> list[dict[str, object]]:
    """Send scheduled Telegram reports after a scan has refreshed the database."""
    logger = logging.getLogger(__name__)
    results: list[dict[str, object]] = []
    if os.getenv("GITHUB_ACTIONS") == "true":
        logger.info("Telegram scheduled reports skipped in GitHub Actions")
        return results

    for report in report_service.due_reports():
        result = notifier.capture_delivery(
            report.report_type,
            lambda report=report: notifier.notify_report(report.message, report.report_type),
        )
        results.append(result)
        if result["status"] == "succeeded":
            report_service.mark_sent(report)
    return results


def run_scheduled_scan() -> None:
    """Run one scheduled scan and keep the long-running process alive on errors."""
    logger = logging.getLogger(__name__)
    logger.info("Running scheduled Alpha Hunter scan")

    try:
        run_agent()
    except Exception:
        logger.exception("Scheduled Alpha Hunter scan failed")


def main() -> None:
    """Run Alpha Hunter Market System as a long-lived PM2-managed process."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Alpha Hunter Market System v1.2")
    run_scheduled_scan()

    if os.getenv("GITHUB_ACTIONS") == "true":
        logger.info("GitHub Actions detected; completed one scan and exiting")
        return

    while True:
        time.sleep(RUN_INTERVAL_SECONDS)
        run_scheduled_scan()


if __name__ == "__main__":
    main()
