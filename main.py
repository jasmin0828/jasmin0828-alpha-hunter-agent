"""Alpha Hunter Agent v1.1 entry point.

The agent only reads public DexScreener data. It does not connect to wallets
and it never executes trades.
"""

from __future__ import annotations

import logging
import time

import pandas as pd

from src.notifications.telegram_notifier import TelegramNotifier
from src.services.alpha_token_service import AlphaTokenService
from src.services.early_alpha_service import EarlyAlphaService
from src.services.narrative_service import NarrativeService
from src.services.risk_intelligence_service import RiskIntelligenceService
from src.services.signal_calibration_service import SignalCalibrationService
from src.services.smart_money_service import SmartMoneyService
from src.services.token_age_service import TokenAgeService
from src.services.trend_service import TrendService
from src.storage.sqlite_store import SQLiteStore
from src.utils.logging_config import setup_logging


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


def run_agent() -> None:
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
    store.initialize()
    scan_run_id = store.create_scan_run()

    try:
        top_tokens = service.find_and_save_top_tokens()
    except Exception as exc:
        logger.warning("DexScreener scan failed; attempting fallback data load: %s", exc)
        top_tokens = load_fallback_tokens(service, store)

    saved_count = store.save_token_snapshots(scan_run_id, top_tokens)
    all_snapshots = store.load_snapshots()
    if top_tokens.empty or "token_address" not in top_tokens.columns:
        pipeline_snapshots = all_snapshots[all_snapshots["scan_run_id"] == scan_run_id].copy()
    else:
        active_addresses = set(top_tokens["token_address"].dropna().astype(str))
        pipeline_snapshots = all_snapshots[all_snapshots["token_address"].astype(str).isin(active_addresses)].copy()

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
    store.finish_scan_run(scan_run_id, "completed", saved_count)
    current_snapshots = store.load_scan_snapshots(scan_run_id)
    current_snapshots.to_csv(service.csv_path, index=False)

    if top_tokens.empty:
        logger.info("No tokens matched the current filters")
        return

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

    logger.info("Top %s alpha tokens:\n%s", len(top_tokens), top_tokens.to_string(index=False))

    alert_tokens = current_snapshots[current_snapshots["alert_level"].isin(["CRITICAL", "HIGH", "WATCH"])]
    try:
        notifier.notify_top_tokens(alert_tokens)
    except Exception:
        logger.exception("Telegram notification failed")


def run_scheduled_scan() -> None:
    """Run one scheduled scan and keep the long-running process alive on errors."""
    logger = logging.getLogger(__name__)
    logger.info("Running scheduled Alpha Hunter scan")

    try:
        run_agent()
    except Exception:
        logger.exception("Scheduled Alpha Hunter scan failed")


def main() -> None:
    """Run Alpha Hunter Agent as a long-lived PM2-managed process."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Alpha Hunter Agent v1.1")
    run_scheduled_scan()

    while True:
        time.sleep(RUN_INTERVAL_SECONDS)
        run_scheduled_scan()


if __name__ == "__main__":
    main()
