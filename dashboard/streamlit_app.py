"""Streamlit dashboard for Alpha Hunter Agent v0.1."""

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

# These are the fields required for the competition display table.
DISPLAY_COLUMNS = [
    "symbol",
    "token_name",
    "price_usd",
    "liquidity_usd",
    "volume_24h",
    "price_change_24h",
    "fdv",
]


def configure_page() -> None:
    """Configure Streamlit page metadata and visual styling."""
    st.set_page_config(
        page_title="Alpha Hunter Agent",
        page_icon="AH",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS gives the page a polished AI-agent demo style.
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
                max-width: 1180px;
            }
            .hero {
                border: 1px solid rgba(148, 163, 184, 0.22);
                border-radius: 8px;
                padding: 1.4rem 1.5rem;
                background: linear-gradient(135deg, rgba(15, 23, 42, 0.94), rgba(17, 24, 39, 0.78));
                box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
            }
            .hero h1 {
                margin: 0;
                color: #f8fafc;
                font-size: 2.35rem;
                line-height: 1.1;
                letter-spacing: 0;
            }
            .hero p {
                margin: 0.55rem 0 0;
                color: #94a3b8;
                font-size: 1rem;
            }
            .top-token {
                border-left: 4px solid #14b8a6;
                border-radius: 8px;
                padding: 1rem 1.1rem;
                background: rgba(20, 184, 166, 0.12);
                color: #dffcf8;
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


def highlight_top_token(row: pd.Series, top_symbol: str | None) -> list[str]:
    """Highlight the top token row in the data table."""
    if top_symbol and row.get("symbol") == top_symbol:
        return [
            "background-color: rgba(20, 184, 166, 0.18); color: #f8fafc; font-weight: 700;"
            for _ in row
        ]
    return ["" for _ in row]


def render_header(updated_at: str) -> None:
    """Render the dashboard title area and data timestamp."""
    st.markdown(
        f"""
        <div class="hero">
            <h1>Alpha Hunter Agent</h1>
            <p>Solana alpha token scanner dashboard v0.1 · Auto refresh every 30 seconds · Data updated at {updated_at}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metrics(df: pd.DataFrame) -> None:
    """Render token count, average volume, and max 24h gain."""
    token_count = len(df)
    avg_volume = df["volume_24h"].mean() if token_count else 0
    max_gain = df["price_change_24h"].max() if token_count else 0

    col_count, col_volume, col_gain = st.columns(3)
    col_count.metric("Token Count", f"{token_count:,}")
    col_volume.metric("Average Volume 24h", format_compact_usd(avg_volume))
    col_gain.metric("Max Price Change 24h", f"{max_gain:.2f}%")


def render_top_token(df: pd.DataFrame) -> str | None:
    """Render the highest-volume token as the highlighted top token."""
    if df.empty:
        st.info("No alpha token data is available yet. Run `python main.py` to generate data.")
        return None

    # Existing scanner output is ranked by 24h volume, so the dashboard uses the same signal.
    top_row = df.sort_values("volume_24h", ascending=False).iloc[0]
    top_symbol = str(top_row["symbol"])

    st.markdown(
        f"""
        <div class="top-token">
            Top Token · <strong>{top_row["symbol"]}</strong> / {top_row["token_name"]}
            · 24h Volume {format_compact_usd(top_row["volume_24h"])}
            · 24h Change {top_row["price_change_24h"]:.2f}%
        </div>
        """,
        unsafe_allow_html=True,
    )

    return top_symbol


def render_token_table(df: pd.DataFrame, top_symbol: str | None) -> None:
    """Render the token table with top-token row highlighting."""
    st.subheader("Token Table")

    # Apply numeric formatting and row styling for a competition-ready table.
    styled_df = (
        df.style.apply(highlight_top_token, top_symbol=top_symbol, axis=1)
        .format(
            {
                "price_usd": "${:,.8f}",
                "liquidity_usd": "${:,.2f}",
                "volume_24h": "${:,.2f}",
                "price_change_24h": "{:,.2f}%",
                "fdv": "${:,.2f}",
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
    render_token_table(alpha_tokens, top_symbol)


def main() -> None:
    """Run the Alpha Hunter Streamlit dashboard."""
    configure_page()
    render_dashboard()


if __name__ == "__main__":
    main()
