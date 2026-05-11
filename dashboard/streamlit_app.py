"""Competition dashboard for Alpha Hunter Agent v0.5."""

import html
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# Dashboard content refresh interval.
REFRESH_INTERVAL = "30s"

# The dashboard lives in dashboard/, so the project root is one level above it.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Alpha Hunter Agent writes scanner output to this CSV file.
DATA_FILE = PROJECT_ROOT / "data" / "alpha_tokens.csv"

# These are the fields used by the competition dashboard table.
DISPLAY_COLUMNS = [
    "symbol",
    "token_name",
    "price_usd",
    "liquidity_usd",
    "volume_24h",
    "price_change_24h",
    "fdv",
    "alpha_score",
    "risk_score",
    "ai_summary",
]


def configure_page() -> None:
    """Configure Streamlit page metadata and visual styling."""
    st.set_page_config(
        page_title="Alpha Hunter Agent",
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
    """Load Alpha Hunter token data from the scanner CSV file."""
    if not csv_path.exists():
        return pd.DataFrame(columns=DISPLAY_COLUMNS)

    # Read the CSV once per cache window so the UI remains responsive.
    df = pd.read_csv(csv_path)

    # Ensure the required table columns exist even if the scanner output changes.
    for column in DISPLAY_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA

    # Convert numeric columns for metrics, sorting, and formatting.
    numeric_columns = [
        "price_usd",
        "liquidity_usd",
        "volume_24h",
        "price_change_24h",
        "fdv",
        "alpha_score",
        "risk_score",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Keep the dashboard focused on the requested competition fields.
    return df[DISPLAY_COLUMNS].copy()


def get_data_updated_at(csv_path: Path) -> str:
    """Return the local file update time for the displayed data."""
    if not csv_path.exists():
        return "data/alpha_tokens.csv not found"

    updated_at = datetime.fromtimestamp(csv_path.stat().st_mtime)
    return updated_at.strftime("%Y-%m-%d %H:%M:%S")


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
    is_top = bool(top_symbol and row.get("symbol") == top_symbol)

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
            <h1>Alpha Hunter Agent v0.5</h1>
            <p>AI market-intelligence agent for Solana token discovery · Built for OKX Agentic Wallet showcase · Data updated at {updated_at}</p>
            <div class="hero-badges">
                <span class="badge">Read-only agent</span>
                <span class="badge">AI risk analysis</span>
                <span class="badge">Telegram alerts</span>
                <span class="badge">Auto refresh 30s</span>
                <span class="badge">No wallet connection</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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


def render_top_token(df: pd.DataFrame) -> str | None:
    """Render a special showcase panel for the highest-alpha token."""
    if df.empty:
        st.info("No alpha token data is available yet. Run `python main.py` to generate data.")
        return None

    # The demo spotlight favors the strongest AI-ranked token.
    top_row = df.sort_values(["alpha_score", "volume_24h"], ascending=[False, False]).iloc[0]
    top_symbol = str(top_row["symbol"])
    safe_symbol = html.escape(top_symbol)
    safe_token_name = html.escape(str(top_row["token_name"]))

    st.markdown(
        f"""
        <div class="top-token">
            <div class="top-token-title">Top AI Candidate · {safe_symbol} / {safe_token_name}</div>
            <div class="top-token-grid">
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
                <div class="top-token-metric">
                    <div class="top-token-label">24h Move</div>
                    <div class="top-token-value">{top_row["price_change_24h"]:.2f}%</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return top_symbol


def render_ai_summary_cards(df: pd.DataFrame) -> None:
    """Render AI Summary cards so the analysis feels product-facing."""
    st.markdown('<div class="section-title">AI Summary Cards</div>', unsafe_allow_html=True)

    if df.empty:
        st.info("AI Summary cards will appear after the first scanner run.")
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


@st.fragment(run_every=REFRESH_INTERVAL)
def render_dashboard() -> None:
    """Render dashboard content and refresh it every 30 seconds."""
    alpha_tokens = load_alpha_tokens(DATA_FILE)
    updated_at = get_data_updated_at(DATA_FILE)

    render_header(updated_at)
    st.write("")
    render_metrics(alpha_tokens)
    st.write("")
    top_symbol = render_top_token(alpha_tokens)
    st.write("")
    render_ai_summary_cards(alpha_tokens)
    st.write("")
    render_token_table(alpha_tokens, top_symbol)


def main() -> None:
    """Run the Alpha Hunter Streamlit dashboard."""
    configure_page()
    render_dashboard()


if __name__ == "__main__":
    main()
