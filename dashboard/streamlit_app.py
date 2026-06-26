"""Dashboard for Alpha Hunter Market System."""

import html
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# Dashboard content refresh interval.
REFRESH_INTERVAL = "30s"

# The dashboard lives in dashboard/, so the project root is one level above it.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.alpha_hunter_core import AlphaHunterCore
from src.agents.daily_alpha_report_agent import DailyAlphaReportAgent
from src.agents.memory_agent import MemoryAgent
from src.agents.social_signal_agent import SocialSignalAgent
from src.agents.theme_scanner_agent import ThemeScannerAgent

# Market System runtime writes token output to this CSV file.
DATA_FILE = PROJECT_ROOT / "data" / "alpha_tokens.csv"
MANIFEST_FILE = PROJECT_ROOT / "data" / "market_system_manifest.json"
DB_FILE = PROJECT_ROOT / "data" / "alpha_hunter.db"
SOCIAL_SIGNALS_SAMPLE_FILE = PROJECT_ROOT / "examples" / "social_signals_sample.json"

# These are the fields used by the competition dashboard table.
DISPLAY_COLUMNS = [
    "chain",
    "symbol",
    "token_name",
    "price_usd",
    "liquidity_usd",
    "volume_24h",
    "price_change_24h",
    "fdv",
    "alpha_score",
    "risk_score",
    "score_change_10m",
    "score_change_30m",
    "volume_change_10m",
    "volume_spike_ratio",
    "liquidity_change_10m",
    "price_change_since_last_scan",
    "momentum_status",
    "narrative",
    "narrative_score",
    "smart_money_score",
    "smart_money_signal",
    "token_age_minutes",
    "token_age_hours",
    "token_age_bucket",
    "rug_risk_level",
    "rug_risk_score",
    "agent_score",
    "first_seen_at",
    "is_first_seen",
    "scan_count",
    "consecutive_up_count",
    "early_alpha_score",
    "early_alpha_reason",
    "alert_level",
    "alert_reason",
    "volume_liquidity_ratio",
    "fdv_liquidity_ratio",
    "extreme_pump_flag",
    "low_liquidity_flag",
    "suspicious_volume_flag",
    "risk_notes",
    "ai_summary",
]


def configure_page() -> None:
    """Configure Streamlit page metadata and visual styling."""
    st.set_page_config(
        page_title="Alpha Hunter Market System",
        page_icon="AH",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS gives the page a polished product-demo style for judges.
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at 20% 0%, rgba(20, 184, 166, 0.16), transparent 28rem),
                    radial-gradient(circle at 85% 10%, rgba(245, 158, 11, 0.12), transparent 26rem),
                    #08111f;
                color: #e5edf7;
            }
            [data-testid="stHeader"] {
                background: rgba(8, 17, 31, 0.72);
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 2rem;
                max-width: 1240px;
            }
            .hero {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 8px;
                padding: 1.65rem 1.7rem;
                background:
                    linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(20, 40, 52, 0.82));
                box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
            }
            .hero h1 {
                margin: 0;
                color: #f8fafc;
                font-size: 2.5rem;
                line-height: 1.1;
                letter-spacing: 0;
            }
            .hero p {
                margin: 0.55rem 0 0;
                color: #94a3b8;
                font-size: 1rem;
            }
            .hero-badges {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-top: 1rem;
            }
            .badge {
                border: 1px solid rgba(148, 163, 184, 0.24);
                border-radius: 999px;
                padding: 0.28rem 0.65rem;
                color: #cbd5e1;
                background: rgba(15, 23, 42, 0.72);
                font-size: 0.84rem;
            }
            .top-token {
                border: 1px solid rgba(20, 184, 166, 0.32);
                border-left: 5px solid #14b8a6;
                border-radius: 8px;
                padding: 1.2rem 1.25rem;
                background:
                    linear-gradient(135deg, rgba(20, 184, 166, 0.18), rgba(15, 23, 42, 0.88));
                color: #dffcf8;
            }
            .top-token-title {
                color: #ffffff;
                font-size: 1.25rem;
                font-weight: 800;
            }
            .top-token-grid {
                display: grid;
                grid-template-columns: repeat(5, minmax(0, 1fr));
                gap: 0.8rem;
                margin-top: 0.85rem;
            }
            .top-token-metric {
                border: 1px solid rgba(148, 163, 184, 0.18);
                border-radius: 8px;
                padding: 0.65rem 0.75rem;
                background: rgba(2, 6, 23, 0.36);
            }
            .top-token-label {
                color: #94a3b8;
                font-size: 0.78rem;
                margin-bottom: 0.18rem;
            }
            .top-token-value {
                color: #f8fafc;
                font-size: 1.02rem;
                font-weight: 700;
            }
            .top-token strong {
                color: #ffffff;
            }
            .stMetric {
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                padding: 0.85rem 1rem;
                background: rgba(15, 23, 42, 0.72);
            }
            [data-testid="stDataFrame"] {
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 8px;
                overflow: hidden;
            }
            .section-title {
                color: #f8fafc;
                font-size: 1.25rem;
                font-weight: 800;
                margin: 0.7rem 0 0.7rem;
            }
            .summary-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.85rem;
                margin-top: 0.5rem;
            }
            .summary-card {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 8px;
                padding: 0.95rem 1rem;
                background: rgba(15, 23, 42, 0.76);
            }
            .summary-card-header {
                display: flex;
                justify-content: space-between;
                gap: 0.75rem;
                align-items: center;
                margin-bottom: 0.55rem;
            }
            .summary-token {
                color: #f8fafc;
                font-weight: 800;
            }
            .summary-score {
                border-radius: 999px;
                padding: 0.18rem 0.5rem;
                color: #06111f;
                background: #5eead4;
                font-size: 0.8rem;
                font-weight: 800;
            }
            .summary-text {
                color: #cbd5e1;
                line-height: 1.45;
                font-size: 0.92rem;
            }
            @media (max-width: 900px) {
                .top-token-grid,
                .summary-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=25)
def load_alpha_tokens(csv_path: Path) -> pd.DataFrame:
    """Load Market Intelligence token data from the runtime CSV file."""
    if not csv_path.exists():
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    # Read the CSV once per cache window so the UI remains responsive.
    df = pd.read_csv(csv_path)

    # Ensure the required table columns exist even if runtime output changes.
    for column in DISPLAY_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
    df["chain"] = df["chain"].fillna("unknown").astype(str).str.lower()

    # Convert numeric columns for metrics, sorting, and formatting.
    numeric_columns = [
        "price_usd",
        "liquidity_usd",
        "volume_24h",
        "price_change_24h",
        "fdv",
        "alpha_score",
        "risk_score",
        "score_change_10m",
        "score_change_30m",
        "volume_change_10m",
        "volume_spike_ratio",
        "liquidity_change_10m",
        "price_change_since_last_scan",
        "narrative_score",
        "smart_money_score",
        "token_age_minutes",
        "token_age_hours",
        "rug_risk_score",
        "agent_score",
        "scan_count",
        "consecutive_up_count",
        "early_alpha_score",
        "volume_liquidity_ratio",
        "fdv_liquidity_ratio",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Boolean flags may arrive as CSV text, integers, or SQLite values.
    for column in ["extreme_pump_flag", "low_liquidity_flag", "suspicious_volume_flag", "is_first_seen"]:
        df[column] = df[column].fillna(False).map(
            lambda value: str(value).strip().lower() in {"1", "true", "yes"}
        )

    # Keep the dashboard focused on the requested competition fields.
    return df[DISPLAY_COLUMNS].copy()


def filter_tokens_by_chain(df: pd.DataFrame, selected_chain: str) -> pd.DataFrame:
    """Return a chain-filtered token frame for dashboard views."""
    if df.empty or selected_chain == "All":
        return df
    if "chain" not in df.columns:
        return df.head(0)
    return df[df["chain"].astype(str).str.lower() == selected_chain.lower()].copy()


def get_data_updated_at(csv_path: Path) -> str:
    """Return the local file update time for the displayed data."""
    if not csv_path.exists():
        return "data/alpha_tokens.csv not found"

    updated_at = datetime.fromtimestamp(csv_path.stat().st_mtime)
    return updated_at.strftime("%Y-%m-%d %H:%M:%S")


@st.cache_data(ttl=25)
def load_market_system_manifest(manifest_path: Path) -> dict:
    """Load latest Market System manifest when available."""
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@st.cache_data(ttl=25)
def load_signal_events(db_path: Path) -> pd.DataFrame:
    """Load recent signal transition events for audit panels."""
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM signal_events
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """,
                conn,
            )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=25)
def load_scan_runs(db_path: Path) -> pd.DataFrame:
    """Load recent run-log rows for Observation Summary."""
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(
                """
                SELECT *
                FROM scan_runs
                WHERE datetime(started_at) >= datetime('now', '-7 days')
                ORDER BY started_at DESC, id DESC
                """,
                conn,
            )
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=25)
def build_core_run_preview() -> dict:
    """Run a dry Core preview without writing reports, memory, or database state."""
    try:
        return {
            "ok": True,
            "result": AlphaHunterCore(project_root=PROJECT_ROOT).run_pipeline(
                social_signals_path=SOCIAL_SIGNALS_SAMPLE_FILE,
                archive_to_memory=False,
                dry_run=True,
            ),
            "error": "",
        }
    except Exception as exc:
        return {
            "ok": False,
            "result": {},
            "error": str(exc),
        }


@st.cache_data(ttl=25)
def build_theme_scanner_results(tokens: pd.DataFrame) -> pd.DataFrame:
    """Run Theme Scanner Agent on the latest dashboard token frame."""
    if tokens.empty:
        return pd.DataFrame(
            columns=[
                "theme_name",
                "signal_strength",
                "description",
                "related_tokens",
                "reason",
                "detected_at",
                "source",
            ]
        )

    results = ThemeScannerAgent().scan_as_dicts(tokens)
    if not results:
        return pd.DataFrame(
            columns=[
                "theme_name",
                "signal_strength",
                "description",
                "related_tokens",
                "reason",
                "detected_at",
                "source",
            ]
        )

    frame = pd.DataFrame(results)
    frame["theme_name"] = frame["theme_name"].replace({"Unknown": "Unclassified Theme"})
    frame["related_tokens"] = frame["related_tokens"].apply(
        lambda tokens: ", ".join(tokens) if isinstance(tokens, list) else str(tokens)
    )
    frame["signal_strength"] = pd.to_numeric(frame["signal_strength"], errors="coerce").fillna(0)
    return frame[
        [
            "theme_name",
            "signal_strength",
            "description",
            "related_tokens",
            "reason",
            "detected_at",
            "source",
        ]
    ].sort_values("signal_strength", ascending=False)


@st.cache_data(ttl=25)
def load_social_signal_inputs(json_path: Path) -> list[dict]:
    """Load optional manual social signals for dashboard report preview."""
    if not json_path.exists():
        return []
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload if isinstance(payload, list) else []


@st.cache_data(ttl=25)
def build_daily_alpha_report(tokens: pd.DataFrame) -> dict:
    """Build a Daily Alpha Report preview from latest dashboard token data."""
    if tokens.empty:
        return {}

    themes = ThemeScannerAgent().scan_as_dicts(tokens)
    social_inputs = load_social_signal_inputs(SOCIAL_SIGNALS_SAMPLE_FILE)
    social_signals = (
        SocialSignalAgent().analyze_as_dicts(social_inputs, tokens, themes)
        if social_inputs
        else []
    )
    return DailyAlphaReportAgent().build_report_dict(tokens, themes, social_signals=social_signals)


@st.cache_data(ttl=25)
def build_memory_summary(limit: int = 7) -> list[dict]:
    """Read recent Daily Alpha Report memory records without writing memory state."""
    return MemoryAgent(project_root=PROJECT_ROOT).list_recent_reports(limit=limit)


def format_compact_usd(value: float) -> str:
    """Format large USD numbers for top-line metrics."""
    if pd.isna(value):
        return "$0"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:,.2f}"


def score_color(value: float, score_type: str) -> str:
    """Return a product-demo color for alpha and risk score cells."""
    if pd.isna(value):
        return "color: #cbd5e1;"

    if score_type == "alpha":
        if value >= 75:
            return "background-color: rgba(34, 197, 94, 0.28); color: #dcfce7; font-weight: 800;"
        if value >= 55:
            return "background-color: rgba(245, 158, 11, 0.24); color: #fef3c7; font-weight: 800;"
        return "background-color: rgba(148, 163, 184, 0.14); color: #e2e8f0; font-weight: 700;"

    if value >= 70:
        return "background-color: rgba(239, 68, 68, 0.32); color: #fee2e2; font-weight: 800;"
    if value >= 40:
        return "background-color: rgba(245, 158, 11, 0.24); color: #fef3c7; font-weight: 800;"
    return "background-color: rgba(20, 184, 166, 0.22); color: #ccfbf1; font-weight: 800;"


def highlight_top_token(row: pd.Series, top_symbol: str | None) -> list[str]:
    """Highlight the top token row in the data table."""
    styles = []
    row_key = f"{str(row.get('chain', 'unknown')).lower()}:{row.get('symbol')}"
    is_top = bool(top_symbol and row_key == top_symbol)

    for column, value in row.items():
        style = ""
        if is_top:
            style = "background-color: rgba(20, 184, 166, 0.14); color: #f8fafc; font-weight: 700;"
        if column == "alpha_score":
            style = score_color(value, "alpha")
        if column == "risk_score":
            style = score_color(value, "risk")
        styles.append(style)

    return styles


def render_header(updated_at: str) -> None:
    """Render the dashboard title area and data timestamp."""
    st.markdown(
        f"""
        <div class="hero">
            <h1>Alpha Hunter Market System</h1>
            <p>Market Intelligence · AI Workflow · Memory · Content · Automation · Data updated at {updated_at}</p>
            <div class="hero-badges">
                <span class="badge">Read-only system</span>
                <span class="badge">Multi-chain</span>
                <span class="badge">Ethereum · Solana · BSC</span>
                <span class="badge">AI risk analysis</span>
                <span class="badge">Telegram alerts</span>
                <span class="badge">Auto refresh 30s</span>
                <span class="badge">No wallet connection</span>
                <span class="badge">Market Intelligence</span>
                <span class="badge">Narrative Detection</span>
                <span class="badge">Signal Analysis</span>
                <span class="badge">Research Reports</span>
                <span class="badge">Momentum engine</span>
                <span class="badge">Smart Money Intelligence</span>
                <span class="badge">Risk Intelligence</span>
                <span class="badge">Token Age Intelligence</span>
                <span class="badge">Signal Calibration</span>
                <span class="badge">Early Alpha Engine</span>
                <span class="badge">AI Workflow Engine</span>
                <span class="badge">Memory Layer</span>
                <span class="badge">Content Engine</span>
                <span class="badge">Automation Layer</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_market_system_manifest(manifest: dict) -> None:
    """Render compact Market System runtime status."""
    if not manifest:
        return

    summary = manifest.get("scan_summary", {})
    quality = manifest.get("signal_quality", {})
    col_scan, col_alerts, col_events, col_first, col_momentum, col_score = st.columns(6)
    col_scan.metric("Scan Run", manifest.get("scan_run_id", "-"))
    col_alerts.metric("Signal Alerts", summary.get("alert_count", 0))
    col_events.metric("Signal Events", summary.get("signal_event_count", 0))
    col_first.metric("First Seen", summary.get("first_seen_count", 0))
    col_momentum.metric("Momentum", summary.get("consecutive_momentum_count", 0))
    col_score.metric("Max Early Alpha", f"{float(summary.get('max_early_alpha_score', 0)):.2f}")

    q_watch, q_old, q_repeat, q_avg = st.columns(4)
    q_watch.metric("WATCH", quality.get("watch_count", 0))
    q_old.metric("OLD WATCH", quality.get("old_watch_count", 0))
    q_repeat.metric("Repeated WATCH", quality.get("repeated_watch_count", 0))
    q_avg.metric("Avg Alert Early Alpha", f"{float(quality.get('avg_early_alpha_alert_score', 0)):.2f}")

    event_count = int(summary.get("signal_event_count", 0) or 0)
    if event_count == 0:
        st.caption("Telegram quiet: no new signal transition events in the latest scan.")


def render_observation_summary(scan_runs: pd.DataFrame, manifest: dict) -> None:
    """Render recent run-log health for the v1.1 Observation Phase."""
    st.markdown('<div class="section-title">Observation Summary</div>', unsafe_allow_html=True)

    if scan_runs.empty:
        observation = manifest.get("observation_summary", {}) if manifest else {}
        latest = observation.get("latest_run", {})
        if not observation and not latest:
            st.info("Observation run log will appear after the next scanner run.")
            return
        total_runs = observation.get("total_runs", 0)
        successful_runs = observation.get("successful_runs", 0)
        failed_runs = observation.get("failed_runs", 0)
        tokens_scanned = observation.get("tokens_scanned", 0)
        signals_found = observation.get("signals_found", 0)
        chain_distribution = observation.get("chain_distribution", {})
    else:
        runs = scan_runs.copy()
        status = runs.get("status", pd.Series(dtype="object")).fillna("unknown").astype(str).str.lower()
        tokens = pd.to_numeric(runs.get("tokens_scanned", runs.get("token_count", 0)), errors="coerce").fillna(0)
        signals = pd.to_numeric(runs.get("signals_found", 0), errors="coerce").fillna(0)
        total_runs = len(runs)
        successful_runs = int((status == "completed").sum())
        failed_runs = int((status == "failed").sum())
        tokens_scanned = int(tokens.sum())
        signals_found = int(signals.sum())
        chain_distribution: dict[str, int] = {}
        if "scanned_chains" in runs.columns:
            for value in runs["scanned_chains"].fillna(""):
                for chain in str(value).split(","):
                    normalized = chain.strip().lower()
                    if normalized:
                        chain_distribution[normalized] = chain_distribution.get(normalized, 0) + 1
        latest = runs.iloc[0].to_dict()

    col_total, col_success, col_failed, col_tokens, col_signals = st.columns(5)
    col_total.metric("Runs 7D", total_runs)
    col_success.metric("Success", successful_runs)
    col_failed.metric("Failed", failed_runs)
    col_tokens.metric("Tokens Scanned", tokens_scanned)
    col_signals.metric("Signals Found", signals_found)

    latest_status = latest.get("status", "unknown") if latest else "unknown"
    latest_started = latest.get("started_at", "N/A") if latest else "N/A"
    latest_duration = latest.get("duration_seconds", 0) if latest else 0
    st.caption(f"Latest run: {latest_status} · started_at={latest_started} · duration={latest_duration}s")

    errors = str(latest.get("errors", "") if latest else "").strip()
    if errors:
        st.warning(f"Latest run errors: {errors}")

    if chain_distribution:
        chain_rows = [{"chain": chain, "run_count": count} for chain, count in sorted(chain_distribution.items())]
        st.dataframe(pd.DataFrame(chain_rows), width="stretch", hide_index=True)


def render_latest_scan_snapshot(df: pd.DataFrame, manifest: dict) -> None:
    """Render the latest Market Intelligence state even when no Telegram event is emitted."""
    if df.empty:
        return

    st.markdown('<div class="section-title">Latest Scan Snapshot</div>', unsafe_allow_html=True)
    summary = manifest.get("scan_summary", {}) if manifest else {}
    col_tokens, col_alerts, col_ignored, col_updated = st.columns(4)
    col_tokens.metric("Candidates", len(df))
    col_alerts.metric("Current Alerts", int((df["alert_level"] != "IGNORE").sum()))
    col_ignored.metric("Ignored", int((df["alert_level"] == "IGNORE").sum()))
    col_updated.metric("Scan Run", manifest.get("scan_run_id", "-") if manifest else "-")

    snapshot_columns = [
        "chain",
        "symbol",
        "token_name",
        "alert_level",
        "early_alpha_score",
        "early_alpha_reason",
        "scan_count",
        "consecutive_up_count",
        "token_age_bucket",
        "rug_risk_level",
        "volume_24h",
        "price_change_24h",
    ]
    available_columns = [column for column in snapshot_columns if column in df.columns]
    current_alerts = df[df["alert_level"] != "IGNORE"].sort_values(
        ["early_alpha_score", "agent_score"],
        ascending=[False, False],
    )
    if current_alerts.empty:
        st.info("No active WATCH / HIGH / CRITICAL tokens in the latest scan.")
    else:
        st.markdown('<div class="section-title">Current Alert Pool</div>', unsafe_allow_html=True)
        st.dataframe(current_alerts[available_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Current Candidate Pool</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values(["early_alpha_score", "volume_24h"], ascending=[False, False])[available_columns],
        width="stretch",
        hide_index=True,
    )

    if summary:
        distributions = {
            "Alert Levels": summary.get("alert_distribution", {}),
            "Age Buckets": summary.get("age_distribution", {}),
            "Narratives": summary.get("narrative_distribution", {}),
        }
        distribution_rows = []
        for group, values in distributions.items():
            for name, count in values.items():
                distribution_rows.append({"group": group, "name": name, "count": count})
        if distribution_rows:
            st.markdown('<div class="section-title">Latest Scan Distribution</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(distribution_rows), width="stretch", hide_index=True)


def render_theme_scanner_section(df: pd.DataFrame) -> None:
    """Render Theme Scanner Agent output without changing runtime flow."""
    st.markdown('<div class="section-title">Theme Scanner Agent</div>', unsafe_allow_html=True)

    themes = build_theme_scanner_results(df)
    if themes.empty:
        st.info("Theme Scanner has no results yet. Run the Market Intelligence scanner to populate token data.")
        return

    top_theme = themes.iloc[0]
    col_theme, col_strength, col_count = st.columns(3)
    col_theme.metric("Top Theme", str(top_theme.get("theme_name", "N/A")))
    col_strength.metric("Signal Strength", f"{float(top_theme.get('signal_strength', 0)):.2f}")
    col_count.metric("Theme Count", len(themes))

    st.dataframe(
        themes,
        width="stretch",
        hide_index=True,
        column_config={
            "theme_name": st.column_config.TextColumn("Theme"),
            "signal_strength": st.column_config.ProgressColumn(
                "Signal Strength",
                min_value=0,
                max_value=100,
                format="%.2f",
            ),
            "description": st.column_config.TextColumn("Description"),
            "related_tokens": st.column_config.TextColumn("Related Tokens"),
            "reason": st.column_config.TextColumn("Reason"),
            "detected_at": st.column_config.TextColumn("Detected At"),
            "source": st.column_config.TextColumn("Source"),
        },
    )


def _records_frame(records: list[dict], columns: list[str]) -> pd.DataFrame:
    """Return a stable dataframe for report preview tables."""
    if not records:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(records)
    for column in columns:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[columns]


def _stringify_list_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Render list-valued report fields as comma-separated strings for Streamlit tables."""
    for column in columns:
        if column in frame.columns:
            frame[column] = frame[column].apply(
                lambda value: ", ".join(str(item) for item in value)
                if isinstance(value, list)
                else str(value or "")
            )
    return frame


def render_core_run_preview_section() -> None:
    """Render a read-only Alpha Hunter Core pipeline preview."""
    st.markdown('<div class="section-title">Core Run Preview</div>', unsafe_allow_html=True)

    preview = build_core_run_preview()
    if not preview.get("ok"):
        st.error(f"Core Run Preview could not run: {preview.get('error') or 'unknown error'}")
        return

    result = preview.get("result", {})
    if not result:
        st.info("Core Run Preview has no result yet.")
        return

    st.caption(f"Run at: {result.get('run_at', 'N/A')}")
    col_tokens, col_themes, col_social, col_evidence = st.columns(4)
    col_tokens.metric("Tokens", result.get("token_count", 0))
    col_themes.metric("Themes", result.get("theme_count", 0))
    col_social.metric("Social Signals", result.get("social_signal_count", 0))
    col_evidence.metric("Evidence Grades", result.get("evidence_grade_count", 0))

    col_theme, col_social_signal = st.columns(2)
    col_theme.metric("Top Theme", result.get("top_theme", "none"))
    col_social_signal.metric("Top Social Signal", result.get("top_social_signal", "none"))

    top_evidence = result.get("top_evidence", {})
    st.markdown('<div class="section-title">Core Top Evidence</div>', unsafe_allow_html=True)
    if top_evidence:
        evidence_frame = pd.DataFrame([top_evidence])
        st.dataframe(
            evidence_frame,
            width="stretch",
            hide_index=True,
            column_config={
                "subject_type": st.column_config.TextColumn("Subject Type"),
                "subject_name": st.column_config.TextColumn("Subject"),
                "evidence_grade": st.column_config.TextColumn("Grade"),
                "evidence_score": st.column_config.ProgressColumn(
                    "Evidence Score",
                    min_value=0,
                    max_value=100,
                    format="%.2f",
                ),
                "reason": st.column_config.TextColumn("Reason"),
            },
        )
    else:
        st.info("No top evidence available from the Core preview.")

    warnings = result.get("warnings", [])
    st.markdown('<div class="section-title">Core Warnings</div>', unsafe_allow_html=True)
    if warnings:
        st.markdown("\n".join(f"- {warning}" for warning in warnings))
    else:
        st.success("Core preview completed with no warnings.")


def render_daily_alpha_report_section(df: pd.DataFrame) -> None:
    """Render Daily Alpha Report Agent preview without scheduling or notifications."""
    st.markdown('<div class="section-title">Daily Alpha Report Preview</div>', unsafe_allow_html=True)

    report = build_daily_alpha_report(df)
    if not report:
        st.info("Daily Alpha Report preview will appear after token snapshot data is available.")
        return

    summary = report.get("market_summary", {})
    st.caption(f"Report date: {report.get('report_date', 'N/A')}")
    col_tokens, col_themes, col_alerts, col_score = st.columns(4)
    col_tokens.metric("Tokens", summary.get("token_count", 0))
    col_themes.metric("Themes", summary.get("theme_count", 0))
    col_alerts.metric("Active Alerts", summary.get("active_alert_count", 0))
    col_score.metric("Max Early Alpha", summary.get("max_early_alpha_score", "0.00"))

    st.info(str(summary.get("market_read", "No market summary available.")))

    summary_rows = [{"metric": key, "value": value} for key, value in summary.items()]
    st.markdown('<div class="section-title">Report Summary</div>', unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)

    theme_columns = ["theme_name", "signal_strength", "description", "related_tokens", "reason"]
    top_themes = _records_frame(report.get("top_themes", []), theme_columns)
    if "related_tokens" in top_themes.columns:
        top_themes["related_tokens"] = top_themes["related_tokens"].apply(
            lambda tokens: ", ".join(tokens) if isinstance(tokens, list) else str(tokens)
        )
    st.markdown('<div class="section-title">Report Top Themes</div>', unsafe_allow_html=True)
    if top_themes.empty:
        st.info("No themes detected for this report preview.")
    else:
        st.dataframe(top_themes, width="stretch", hide_index=True)

    token_columns = [
        "symbol",
        "token_name",
        "narrative",
        "alert_level",
        "early_alpha_score",
        "agent_score",
        "alpha_score",
        "volume_24h",
        "liquidity_usd",
        "momentum_status",
        "rug_risk_level",
        "reason",
    ]
    st.markdown('<div class="section-title">Report Top Tokens</div>', unsafe_allow_html=True)
    top_tokens = _records_frame(report.get("top_tokens", []), token_columns)
    if top_tokens.empty:
        st.info("No top tokens available for this report preview.")
    else:
        st.dataframe(top_tokens, width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Report Notable Signals</div>', unsafe_allow_html=True)
    notable_signals = _records_frame(report.get("notable_signals", []), token_columns)
    if notable_signals.empty:
        st.info("No WATCH / HIGH / CRITICAL signals in this report preview.")
    else:
        st.dataframe(notable_signals, width="stretch", hide_index=True)

    social_columns = [
        "source_platform",
        "author",
        "mentioned_tokens",
        "mentioned_themes",
        "social_strength",
        "evidence_value",
        "hype_risk",
        "reason",
    ]
    st.markdown('<div class="section-title">Social Signals</div>', unsafe_allow_html=True)
    social_signals = _records_frame(report.get("social_signals", []), social_columns)
    if social_signals.empty:
        st.info("No social signal data supplied for this Daily Alpha Report preview.")
    else:
        social_signals = _stringify_list_columns(social_signals, ["mentioned_tokens", "mentioned_themes"])
        st.dataframe(
            social_signals,
            width="stretch",
            hide_index=True,
            column_config={
                "source_platform": st.column_config.TextColumn("Platform"),
                "author": st.column_config.TextColumn("Author"),
                "mentioned_tokens": st.column_config.TextColumn("Tokens"),
                "mentioned_themes": st.column_config.TextColumn("Themes"),
                "social_strength": st.column_config.ProgressColumn(
                    "Social Strength",
                    min_value=0,
                    max_value=100,
                    format="%.2f",
                ),
                "evidence_value": st.column_config.TextColumn("Evidence Value"),
                "hype_risk": st.column_config.TextColumn("Hype Risk"),
                "reason": st.column_config.TextColumn("Reason"),
            },
        )

    st.markdown('<div class="section-title">Social Evidence Summary</div>', unsafe_allow_html=True)
    social_summary = report.get("social_summary", {})
    if social_summary and social_summary.get("signal_count"):
        col_signal_count, col_avg_strength, col_top_signal = st.columns([1, 1, 2])
        col_signal_count.metric("Social Signals", social_summary.get("signal_count", 0))
        col_avg_strength.metric("Avg Social Strength", social_summary.get("avg_social_strength", "0.00"))
        col_top_signal.metric("Top Social Signal", social_summary.get("top_social_signal", "none"))
        summary_rows = [
            {"metric": key, "value": json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value}
            for key, value in social_summary.items()
        ]
        st.dataframe(pd.DataFrame(summary_rows), width="stretch", hide_index=True)
    else:
        st.info("Social Evidence Summary will appear after manual social signal data is available.")

    st.markdown('<div class="section-title">Hype Risk Summary</div>', unsafe_allow_html=True)
    hype_risk_summary = report.get("hype_risk_summary", {})
    if hype_risk_summary and hype_risk_summary.get("signal_count"):
        distribution = hype_risk_summary.get("hype_risk_distribution", {})
        high_hype_signals = hype_risk_summary.get("high_hype_signals", [])
        st.json(
            {
                "signal_count": hype_risk_summary.get("signal_count", 0),
                "hype_risk_distribution": distribution,
            }
        )
        if high_hype_signals:
            st.markdown("\n".join(f"- {signal}" for signal in high_hype_signals))
        else:
            st.info("No HIGH hype risk social signals in this preview.")
    else:
        st.info("Hype Risk Summary will appear after social signal data is available.")

    social_evidence_columns = [
        "subject_type",
        "subject_name",
        "evidence_grade",
        "evidence_score",
        "social_evidence",
        "social_risk_flags",
        "reason",
    ]
    st.markdown('<div class="section-title">Social-enhanced Evidence Grades</div>', unsafe_allow_html=True)
    social_enhanced = _records_frame(report.get("social_enhanced_evidence_grades", []), social_evidence_columns)
    if social_enhanced.empty:
        st.info("Social-enhanced Evidence Grades will appear after social signal data is available.")
    else:
        social_enhanced = _stringify_list_columns(social_enhanced, ["social_evidence", "social_risk_flags"])
        st.dataframe(
            social_enhanced,
            width="stretch",
            hide_index=True,
            column_config={
                "subject_type": st.column_config.TextColumn("Subject Type"),
                "subject_name": st.column_config.TextColumn("Subject"),
                "evidence_grade": st.column_config.TextColumn("Grade"),
                "evidence_score": st.column_config.ProgressColumn(
                    "Evidence Score",
                    min_value=0,
                    max_value=100,
                    format="%.2f",
                ),
                "social_evidence": st.column_config.TextColumn("Social Evidence"),
                "social_risk_flags": st.column_config.TextColumn("Social Risk Flags"),
                "reason": st.column_config.TextColumn("Reason"),
            },
        )

    evidence_columns = [
        "subject_type",
        "subject_name",
        "evidence_grade",
        "evidence_score",
        "social_evidence",
        "social_risk_flags",
        "reason",
    ]
    st.markdown('<div class="section-title">Evidence Grades</div>', unsafe_allow_html=True)
    evidence_grades = _records_frame(report.get("evidence_grades", []), evidence_columns)
    if evidence_grades.empty:
        st.info("No evidence grades available for this report preview.")
    else:
        evidence_grades = _stringify_list_columns(evidence_grades, ["social_evidence", "social_risk_flags"])
        st.dataframe(
            evidence_grades,
            width="stretch",
            hide_index=True,
            column_config={
                "subject_type": st.column_config.TextColumn("Subject Type"),
                "subject_name": st.column_config.TextColumn("Subject"),
                "evidence_grade": st.column_config.TextColumn("Grade"),
                "evidence_score": st.column_config.ProgressColumn(
                    "Evidence Score",
                    min_value=0,
                    max_value=100,
                    format="%.2f",
                ),
                "social_evidence": st.column_config.TextColumn("Social Evidence"),
                "social_risk_flags": st.column_config.TextColumn("Social Risk Flags"),
                "reason": st.column_config.TextColumn("Reason"),
            },
        )

    st.markdown('<div class="section-title">Top Evidence</div>', unsafe_allow_html=True)
    top_evidence = report.get("top_evidence", [])
    if top_evidence:
        st.markdown(
            "\n".join(
                "- "
                f"{row.get('subject_type')}:{row.get('subject_name')} "
                f"grade={row.get('evidence_grade')} "
                f"score={float(row.get('evidence_score') or 0):.2f} "
                f"reason={row.get('reason')}"
                for row in top_evidence
            )
        )
    else:
        st.info("No strong evidence rows available for this report preview.")

    st.markdown('<div class="section-title">Weak Evidence / Risks</div>', unsafe_allow_html=True)
    weak_evidence = report.get("weak_evidence", [])
    if weak_evidence:
        st.markdown(
            "\n".join(
                "- "
                f"{row.get('subject_type')}:{row.get('subject_name')} "
                f"grade={row.get('evidence_grade')} "
                f"score={float(row.get('evidence_score') or 0):.2f} "
                f"weak={', '.join(row.get('weak_evidence') or [])} "
                f"risks={', '.join(row.get('risk_flags') or [])}"
                for row in weak_evidence
            )
        )
    else:
        st.info("No weak evidence rows available for this report preview.")

    st.markdown('<div class="section-title">Risk Flags Summary</div>', unsafe_allow_html=True)
    risk_flags_summary = report.get("risk_flags_summary", [])
    if risk_flags_summary:
        st.markdown("\n".join(f"- {risk_flag}" for risk_flag in risk_flags_summary))
    else:
        st.info("No evidence risk flags available for this report preview.")

    st.markdown('<div class="section-title">Report Risks</div>', unsafe_allow_html=True)
    risks = report.get("risks", [])
    if risks:
        st.markdown("\n".join(f"- {risk}" for risk in risks))
    else:
        st.info("No report risks available.")

    st.markdown('<div class="section-title">Report Watchlist</div>', unsafe_allow_html=True)
    watchlist = _records_frame(report.get("watchlist", []), token_columns)
    if watchlist.empty:
        st.info("No watchlist candidates in this report preview.")
    else:
        st.dataframe(watchlist, width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Report Next Actions</div>', unsafe_allow_html=True)
    next_actions = report.get("next_actions", [])
    if next_actions:
        st.markdown("\n".join(f"- {action}" for action in next_actions))
    else:
        st.info("No next actions generated.")


def render_memory_summary_section() -> None:
    """Render first-stage Memory Agent report index without writing memory state."""
    st.markdown('<div class="section-title">Memory Summary</div>', unsafe_allow_html=True)

    reports = build_memory_summary(limit=7)
    if not reports:
        st.info("Memory Summary will appear after a Daily Alpha Report is archived into memory/index.json.")
        return

    frame = _records_frame(
        reports,
        [
            "report_date",
            "top_theme",
            "top_tokens",
            "risk_count",
            "social_signal_count",
            "high_hype_count",
            "top_social_signal",
            "file_path",
        ],
    )
    if "top_tokens" in frame.columns:
        frame["top_tokens"] = frame["top_tokens"].apply(
            lambda tokens: ", ".join(tokens) if isinstance(tokens, list) else str(tokens)
        )
    for column in ["risk_count", "social_signal_count", "high_hype_count"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0).astype(int)
    if "top_social_signal" in frame.columns:
        frame["top_social_signal"] = frame["top_social_signal"].fillna("none").replace("", "none")

    latest_report = reports[0]
    col_count, col_latest, col_theme, col_risks, col_social, col_hype = st.columns(6)
    col_count.metric("Archived Reports", len(reports))
    col_latest.metric("Latest Report", latest_report.get("report_date", "N/A"))
    col_theme.metric("Latest Top Theme", latest_report.get("top_theme", "none"))
    col_risks.metric("Latest Risk Count", latest_report.get("risk_count", 0))
    col_social.metric("Latest Social Signals", latest_report.get("social_signal_count", 0) or 0)
    col_hype.metric("Latest High Hype Count", latest_report.get("high_hype_count", 0) or 0)

    st.dataframe(
        frame,
        width="stretch",
        hide_index=True,
        column_config={
            "report_date": st.column_config.TextColumn("Report Date"),
            "top_theme": st.column_config.TextColumn("Top Theme"),
            "top_tokens": st.column_config.TextColumn("Top Tokens"),
            "risk_count": st.column_config.NumberColumn("Risk Count", format="%d"),
            "social_signal_count": st.column_config.NumberColumn("Social Signals", format="%d"),
            "high_hype_count": st.column_config.NumberColumn("High Hype Count", format="%d"),
            "top_social_signal": st.column_config.TextColumn("Top Social Signal"),
            "file_path": st.column_config.TextColumn("File Path"),
        },
    )


def render_metrics(df: pd.DataFrame) -> None:
    """Render the dashboard KPI strip."""
    token_count = len(df)
    avg_volume = df["volume_24h"].mean() if token_count else 0
    max_gain = df["price_change_24h"].max() if token_count else 0
    avg_alpha = df["alpha_score"].mean() if token_count else 0
    avg_risk = df["risk_score"].mean() if token_count else 0

    col_count, col_alpha, col_risk, col_volume, col_gain = st.columns(5)
    col_count.metric("Token Count", f"{token_count:,}")
    col_alpha.metric("Average Alpha Score", f"{avg_alpha:.2f}")
    col_risk.metric("Average Risk Score", f"{avg_risk:.2f}")
    col_volume.metric("Average Volume 24h", format_compact_usd(avg_volume))
    col_gain.metric("Max 24h Move", f"{max_gain:.2f}%")


def render_chain_filter(df: pd.DataFrame) -> str:
    """Render a read-only chain filter for the multi-chain dashboard."""
    available = set(df["chain"].dropna().astype(str).str.lower()) if "chain" in df.columns else set()
    labels = ["All", "Ethereum", "Solana", "BSC"]
    help_text = "Filter dashboard views by chain. This does not change scanner behavior."
    if available:
        help_text = f"Available chains in latest CSV: {', '.join(sorted(available))}"
    return st.sidebar.selectbox("Chain", labels, index=0, help=help_text)


def render_chain_stats(df: pd.DataFrame) -> None:
    """Render per-chain candidate count, liquidity, and volume statistics."""
    st.markdown('<div class="section-title">Multi-chain Summary</div>', unsafe_allow_html=True)
    if df.empty or "chain" not in df.columns:
        st.info("Multi-chain stats will appear after the next scan writes chain data.")
        return

    stats = (
        df.groupby("chain", dropna=False)
        .agg(
            candidate_count=("symbol", "count"),
            avg_liquidity=("liquidity_usd", "mean"),
            avg_volume_24h=("volume_24h", "mean"),
        )
        .reset_index()
        .sort_values("chain")
    )
    stats["avg_liquidity"] = stats["avg_liquidity"].map(format_compact_usd)
    stats["avg_volume_24h"] = stats["avg_volume_24h"].map(format_compact_usd)
    st.dataframe(
        stats.rename(
            columns={
                "chain": "Chain",
                "candidate_count": "Candidate Count",
                "avg_liquidity": "Average Liquidity",
                "avg_volume_24h": "Average Volume 24h",
            }
        ),
        width="stretch",
        hide_index=True,
    )


def render_top_token(df: pd.DataFrame) -> str | None:
    """Render a special showcase panel for the highest-alpha token."""
    if df.empty:
        st.info("No alpha token data is available yet. Run `python main.py` to generate data.")
        return None

    # The demo spotlight favors the strongest AI-ranked token.
    top_row = df.sort_values(["early_alpha_score", "alpha_score", "volume_24h"], ascending=[False, False, False]).iloc[0]
    top_symbol = str(top_row["symbol"])
    safe_symbol = html.escape(top_symbol)
    safe_token_name = html.escape(str(top_row["token_name"]))
    safe_chain = html.escape(str(top_row.get("chain", "unknown")).upper())

    st.markdown(
        f"""
        <div class="top-token">
            <div class="top-token-title">Top AI Candidate · {safe_chain} · {safe_symbol} / {safe_token_name}</div>
            <div class="top-token-grid">
                <div class="top-token-metric">
                    <div class="top-token-label">Early Alpha</div>
                    <div class="top-token-value">{top_row["early_alpha_score"]:.2f}</div>
                </div>
                <div class="top-token-metric">
                    <div class="top-token-label">Alpha Score</div>
                    <div class="top-token-value">{top_row["alpha_score"]:.2f}</div>
                </div>
                <div class="top-token-metric">
                    <div class="top-token-label">Risk Score</div>
                    <div class="top-token-value">{top_row["risk_score"]:.2f}</div>
                </div>
                <div class="top-token-metric">
                    <div class="top-token-label">24h Volume</div>
                    <div class="top-token-value">{format_compact_usd(top_row["volume_24h"])}</div>
                </div>
                <div class="top-token-metric">
                    <div class="top-token-label">Liquidity</div>
                    <div class="top-token-value">{format_compact_usd(top_row["liquidity_usd"])}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return f"{str(top_row.get('chain', 'unknown')).lower()}:{top_symbol}"


def render_ai_summary_cards(df: pd.DataFrame) -> None:
    """Render AI Summary cards so the analysis feels product-facing."""
    st.markdown('<div class="section-title">AI Summary Cards</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("AI Summary cards will appear after the first Market Intelligence run.")
        return

    cards = []
    summary_rows = df.sort_values(["alpha_score", "volume_24h"], ascending=[False, False]).head(4)

    for _, row in summary_rows.iterrows():
        symbol = html.escape(str(row.get("symbol", "N/A")))
        token_name = html.escape(str(row.get("token_name", "N/A")))
        summary = html.escape(str(row.get("ai_summary", "No AI Summary available")))
        summary_text = summary.replace(" | ", "<br>")
        cards.append(
            f"""
            <div class="summary-card">
                <div class="summary-card-header">
                    <span class="summary-token">{symbol} / {token_name}</span>
                    <span class="summary-score">Alpha {row["alpha_score"]:.2f}</span>
                </div>
                <div class="summary-text">{summary_text}</div>
            </div>
            """
        )

    st.markdown(f'<div class="summary-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_token_table(df: pd.DataFrame, top_symbol: str | None) -> None:
    """Render the token table with top-token row highlighting."""
    st.markdown('<div class="section-title">Ranked Token Intelligence</div>', unsafe_allow_html=True)
    display_df = df.rename(columns={"ai_summary": "AI Summary"})

    # Apply numeric formatting and row styling for a competition-ready table.
    styled_df = (
        display_df.style.apply(highlight_top_token, top_symbol=top_symbol, axis=1)
        .format(
            {
                "price_usd": "${:,.8f}",
                "liquidity_usd": "${:,.2f}",
                "volume_24h": "${:,.2f}",
                "price_change_24h": "{:,.2f}%",
                "fdv": "${:,.2f}",
                "alpha_score": "{:,.2f}",
                "risk_score": "{:,.2f}",
            },
            na_rep="-",
        )
    )

    st.dataframe(styled_df, width="stretch", hide_index=True)


def render_v07_momentum_sections(df: pd.DataFrame) -> None:
    """Render v0.7 momentum sections from trend-enriched CSV output."""
    if df.empty or "momentum_status" not in df.columns:
        return

    heating = df[df["momentum_status"] == "HEATING_UP"].copy()
    hot = df[df["momentum_status"] == "HOT"].copy()
    cooling = df[df["momentum_status"] == "COOLING_DOWN"].copy()
    trend_columns = [
        "symbol",
        "token_name",
        "alpha_score",
        "risk_score",
        "score_change_10m",
        "score_change_30m",
        "volume_change_10m",
        "volume_spike_ratio",
        "momentum_status",
    ]

    st.markdown('<div class="section-title">Heating Up Tokens</div>', unsafe_allow_html=True)
    st.dataframe(heating[trend_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">HOT Tokens</div>', unsafe_allow_html=True)
    st.dataframe(hot[trend_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Cooling Down Tokens</div>', unsafe_allow_html=True)
    st.dataframe(cooling[trend_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Score Trend</div>', unsafe_allow_html=True)
    score_trend = df.sort_values(["score_change_10m", "score_change_30m"], ascending=[False, False])
    st.dataframe(score_trend[trend_columns].head(10), width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Volume Spike</div>', unsafe_allow_html=True)
    volume_spike = df.sort_values("volume_spike_ratio", ascending=False)
    st.dataframe(
        volume_spike[
            [
                "symbol",
                "token_name",
                "volume_24h",
                "volume_change_10m",
                "volume_spike_ratio",
                "liquidity_change_10m",
                "momentum_status",
            ]
        ].head(10),
        width="stretch",
        hide_index=True,
    )


def render_v08_intelligence_sections(df: pd.DataFrame) -> None:
    """Render Narrative Engine and Smart Money Intelligence sections."""
    required = {"narrative", "smart_money_signal", "smart_money_score", "narrative_score"}
    if df.empty or not required.issubset(df.columns):
        return

    narrative_columns = [
        "symbol",
        "token_name",
        "narrative",
        "narrative_score",
        "alpha_score",
        "smart_money_score",
        "smart_money_signal",
    ]

    st.markdown('<div class="section-title">Narrative Heat Map</div>', unsafe_allow_html=True)
    heat_map = df.sort_values(["narrative_score", "alpha_score"], ascending=[False, False])
    st.dataframe(heat_map[narrative_columns].head(15), width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Top AI Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["narrative"] == "AI"].sort_values("alpha_score", ascending=False)[narrative_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Top Meme Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["narrative"] == "Meme"].sort_values("alpha_score", ascending=False)[narrative_columns],
        width="stretch",
        hide_index=True,
    )

    smart_columns = [
        "symbol",
        "token_name",
        "alpha_score",
        "risk_score",
        "momentum_status",
        "narrative",
        "smart_money_score",
        "smart_money_signal",
    ]
    st.markdown('<div class="section-title">Smart Money Accumulation</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["smart_money_signal"] == "ACCUMULATION"].sort_values("smart_money_score", ascending=False)[smart_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Smart Money Exiting</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["smart_money_signal"] == "EXITING"].sort_values("smart_money_score", ascending=True)[smart_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Narrative Distribution Chart</div>', unsafe_allow_html=True)
    narrative_counts = df["narrative"].value_counts()
    st.bar_chart(narrative_counts)


def render_v09_risk_sections(df: pd.DataFrame) -> None:
    """Render Risk Intelligence Engine panels."""
    required = {
        "rug_risk_level",
        "rug_risk_score",
        "volume_liquidity_ratio",
        "fdv_liquidity_ratio",
        "suspicious_volume_flag",
        "extreme_pump_flag",
        "risk_notes",
    }
    if df.empty or not required.issubset(df.columns):
        return

    risk_columns = [
        "symbol",
        "token_name",
        "alpha_score",
        "risk_score",
        "token_age_bucket",
        "token_age_hours",
        "rug_risk_level",
        "rug_risk_score",
        "volume_liquidity_ratio",
        "fdv_liquidity_ratio",
        "risk_notes",
    ]

    st.markdown('<div class="section-title">Risk Intelligence</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values(["rug_risk_score", "volume_liquidity_ratio"], ascending=[False, False])[risk_columns].head(15),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">High Risk Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["rug_risk_level"] == "HIGH"].sort_values("rug_risk_score", ascending=False)[risk_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Low Risk Alpha Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["rug_risk_level"] == "LOW"].sort_values("alpha_score", ascending=False)[risk_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Suspicious Volume Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["suspicious_volume_flag"]].sort_values("volume_liquidity_ratio", ascending=False)[risk_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Extreme Pump Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["extreme_pump_flag"]].sort_values("price_change_24h", ascending=False)[
            risk_columns + ["price_change_24h"]
        ],
        width="stretch",
        hide_index=True,
    )


def render_v091_token_age_sections(df: pd.DataFrame) -> None:
    """Render Token Age Intelligence panels."""
    required = {"token_age_bucket", "token_age_hours", "alpha_score", "rug_risk_level"}
    if df.empty or not required.issubset(df.columns):
        return

    age_columns = [
        "symbol",
        "token_name",
        "alpha_score",
        "risk_score",
        "token_age_bucket",
        "token_age_hours",
        "rug_risk_level",
        "rug_risk_score",
    ]

    st.markdown('<div class="section-title">Token Age Distribution</div>', unsafe_allow_html=True)
    age_counts = df["token_age_bucket"].fillna("UNKNOWN").value_counts()
    st.bar_chart(age_counts)

    st.markdown('<div class="section-title">NEWBORN Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["token_age_bucket"] == "NEWBORN"].sort_values("alpha_score", ascending=False)[age_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">EARLY Trending Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["token_age_bucket"] == "EARLY"].sort_values(["alpha_score", "volume_24h"], ascending=[False, False])[
            age_columns + ["volume_24h"]
        ],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">OLD Tokens</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["token_age_bucket"] == "OLD"].sort_values("token_age_hours", ascending=False)[age_columns],
        width="stretch",
        hide_index=True,
    )


def render_v10_signal_sections(df: pd.DataFrame) -> None:
    """Render Signal Calibration panels."""
    required = {"alert_level", "alert_reason", "agent_score"}
    if df.empty or not required.issubset(df.columns):
        return

    signal_columns = [
        "symbol",
        "token_name",
        "alert_level",
        "agent_score",
        "alert_reason",
        "alpha_score",
        "rug_risk_level",
        "token_age_bucket",
        "narrative",
        "smart_money_signal",
    ]

    st.markdown('<div class="section-title">Signal Calibration</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values("agent_score", ascending=False)[signal_columns].head(15),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">CRITICAL Signals</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["alert_level"] == "CRITICAL"].sort_values("agent_score", ascending=False)[signal_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">HIGH Signals</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["alert_level"] == "HIGH"].sort_values("agent_score", ascending=False)[signal_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">WATCH Signals</div>', unsafe_allow_html=True)
    st.dataframe(
        df[df["alert_level"] == "WATCH"].sort_values("agent_score", ascending=False)[signal_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Agent Score Ranking</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values("agent_score", ascending=False)[signal_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Alert Level Distribution</div>', unsafe_allow_html=True)
    st.bar_chart(df["alert_level"].fillna("IGNORE").value_counts())


def render_v11_early_alpha_sections(df: pd.DataFrame) -> None:
    """Render Early Alpha Engine panels."""
    required = {
        "early_alpha_score",
        "early_alpha_reason",
        "is_first_seen",
        "scan_count",
        "consecutive_up_count",
        "token_age_bucket",
        "alert_level",
    }
    if df.empty or not required.issubset(df.columns):
        return

    early_columns = [
        "symbol",
        "token_name",
        "early_alpha_score",
        "early_alpha_reason",
        "is_first_seen",
        "scan_count",
        "consecutive_up_count",
        "token_age_bucket",
        "alert_level",
        "agent_score",
        "rug_risk_level",
    ]

    st.markdown('<div class="section-title">Early Alpha Engine</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values("early_alpha_score", ascending=False)[early_columns].head(15),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">First Seen Tokens</div>', unsafe_allow_html=True)
    first_seen = df[df["is_first_seen"]].sort_values("early_alpha_score", ascending=False)
    if first_seen.empty:
        st.info("No first-seen tokens in the latest scan.")
    else:
        st.dataframe(first_seen[early_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Early Alpha Ranking</div>', unsafe_allow_html=True)
    st.dataframe(
        df.sort_values(["early_alpha_score", "agent_score"], ascending=[False, False])[early_columns],
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="section-title">Consecutive Momentum Tokens</div>', unsafe_allow_html=True)
    consecutive = df[df["consecutive_up_count"] > 0].sort_values(
        ["consecutive_up_count", "early_alpha_score"],
        ascending=[False, False],
    )
    if consecutive.empty:
        st.info("No consecutive momentum tokens in the latest scan.")
    else:
        st.dataframe(consecutive[early_columns], width="stretch", hide_index=True)

    st.markdown('<div class="section-title">Early Alpha Score Distribution</div>', unsafe_allow_html=True)
    score_bins = pd.cut(
        df["early_alpha_score"].fillna(0),
        bins=[-1, 20, 40, 60, 75, 85, 100],
        labels=["0-20", "21-40", "41-60", "61-75", "76-85", "86-100"],
    )
    st.bar_chart(score_bins.value_counts().sort_index())


def render_signal_memory_sections(signal_events: pd.DataFrame, alpha_tokens: pd.DataFrame) -> None:
    """Render v1.2 Signal Memory and outcome audit panels."""
    st.markdown('<div class="section-title">Signal Memory</div>', unsafe_allow_html=True)

    if signal_events.empty:
        st.info("No new signal transition events yet. Latest scan candidates are shown above.")
    else:
        numeric_columns = [
            "early_alpha_score",
            "agent_score",
            "outcome_30m_price_change",
            "outcome_1h_price_change",
            "outcome_4h_price_change",
            "outcome_1h_volume_change",
            "outcome_1h_early_alpha_change",
        ]
        events = signal_events.copy()
        for column in numeric_columns:
            if column in events.columns:
                events[column] = pd.to_numeric(events[column], errors="coerce")

        event_columns = [
            "created_at",
            "symbol",
            "event_type",
            "previous_alert_level",
            "alert_level",
            "early_alpha_score",
            "outcome_status",
            "outcome_30m_price_change",
            "outcome_1h_price_change",
            "outcome_4h_price_change",
            "outcome_1h_early_alpha_change",
            "early_alpha_reason",
        ]
        available_columns = [column for column in event_columns if column in events.columns]
        st.dataframe(events[available_columns].head(25), width="stretch", hide_index=True)

        st.markdown('<div class="section-title">Signal Outcome Distribution</div>', unsafe_allow_html=True)
        if "outcome_status" in events.columns:
            st.bar_chart(events["outcome_status"].fillna("PENDING").value_counts())

    st.markdown('<div class="section-title">Repeated WATCH Candidates</div>', unsafe_allow_html=True)
    if alpha_tokens.empty:
        st.info("Repeated WATCH candidates will appear after scan data is available.")
        return

    repeated_watch = alpha_tokens[
        (alpha_tokens["alert_level"] == "WATCH")
        & (pd.to_numeric(alpha_tokens["scan_count"], errors="coerce").fillna(0) > 20)
    ].sort_values(["scan_count", "early_alpha_score"], ascending=[False, False])
    watch_columns = [
        "symbol",
        "token_name",
        "scan_count",
        "early_alpha_score",
        "consecutive_up_count",
        "token_age_bucket",
        "rug_risk_level",
        "early_alpha_reason",
    ]
    if repeated_watch.empty:
        st.info("No repeated WATCH candidates in the latest scan.")
    else:
        st.dataframe(repeated_watch[watch_columns], width="stretch", hide_index=True)


def render_signal_quality_summary(manifest: dict) -> None:
    """Render structured signal quality metrics from the manifest."""
    quality = manifest.get("signal_quality", {}) if manifest else {}
    if not quality:
        return

    st.markdown('<div class="section-title">Signal Quality Summary</div>', unsafe_allow_html=True)
    quality_rows = [
        {"metric": "WATCH", "value": quality.get("watch_count", 0)},
        {"metric": "HIGH", "value": quality.get("high_count", 0)},
        {"metric": "CRITICAL", "value": quality.get("critical_count", 0)},
        {"metric": "OLD WATCH", "value": quality.get("old_watch_count", 0)},
        {"metric": "Repeated WATCH", "value": quality.get("repeated_watch_count", 0)},
        {"metric": "Fresh Signal Events", "value": quality.get("fresh_signal_count", 0)},
        {"metric": "Avg Early Alpha Alert Score", "value": quality.get("avg_early_alpha_alert_score", 0)},
    ]
    st.dataframe(pd.DataFrame(quality_rows), width="stretch", hide_index=True)


@st.fragment(run_every=REFRESH_INTERVAL)
def render_dashboard() -> None:
    """Render dashboard content and refresh it every 30 seconds."""
    alpha_tokens = load_alpha_tokens(DATA_FILE)
    manifest = load_market_system_manifest(MANIFEST_FILE)
    signal_events = load_signal_events(DB_FILE)
    scan_runs = load_scan_runs(DB_FILE)
    updated_at = get_data_updated_at(DATA_FILE)
    selected_chain = render_chain_filter(alpha_tokens)
    filtered_tokens = filter_tokens_by_chain(alpha_tokens, selected_chain)
    if "chain" in signal_events.columns:
        signal_events["chain"] = signal_events["chain"].fillna("unknown").astype(str).str.lower()
    filtered_signal_events = filter_tokens_by_chain(signal_events, selected_chain)

    render_header(updated_at)
    st.write("")
    render_market_system_manifest(manifest)
    st.write("")
    render_observation_summary(scan_runs, manifest)
    st.write("")
    render_metrics(filtered_tokens)
    st.write("")
    render_chain_stats(alpha_tokens)
    st.write("")
    render_latest_scan_snapshot(filtered_tokens, manifest)
    st.write("")
    render_core_run_preview_section()
    st.write("")
    render_theme_scanner_section(filtered_tokens)
    st.write("")
    render_daily_alpha_report_section(filtered_tokens)
    st.write("")
    render_memory_summary_section()
    st.write("")
    top_symbol = render_top_token(filtered_tokens)
    st.write("")
    render_ai_summary_cards(filtered_tokens)
    st.write("")
    render_v07_momentum_sections(filtered_tokens)
    st.write("")
    render_v08_intelligence_sections(filtered_tokens)
    st.write("")
    render_v091_token_age_sections(filtered_tokens)
    st.write("")
    render_v09_risk_sections(filtered_tokens)
    st.write("")
    render_v11_early_alpha_sections(filtered_tokens)
    st.write("")
    render_signal_quality_summary(manifest)
    st.write("")
    render_signal_memory_sections(filtered_signal_events, filtered_tokens)
    st.write("")
    render_v10_signal_sections(filtered_tokens)
    st.write("")
    render_token_table(filtered_tokens, top_symbol)


def main() -> None:
    """Run the Alpha Hunter Market System Streamlit dashboard."""
    configure_page()
    render_dashboard()


if __name__ == "__main__":
    main()
