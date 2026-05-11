# Alpha Hunter Agent v0.5

Alpha Hunter Agent is an AI market-intelligence agent built for the OKX Agentic
Wallet competition showcase. It watches Solana token activity from public
DexScreener data, filters noisy markets, scores each candidate with an AI
Intelligence Layer, and delivers a dashboard plus Telegram alerts for fast
human review.

The product focus is simple: help a user detect early market attention without
asking the agent to custody funds, connect a wallet, or execute trades.

## Core Capabilities

- Solana hot-token discovery from DexScreener public APIs.
- Market-quality filters for liquidity, 24h volume, 24h price change, and FDV.
- Top 10 alpha candidate output to `data/alpha_tokens.csv`.
- AI Intelligence Layer v0.4 with alpha score, risk score, and AI Summary.
- Streamlit competition dashboard with score colors, risk colors, and summary cards.
- Telegram Alert delivery when Top tokens are found.
- Scheduled scanning every 10 minutes with file logging to `logs/app.log`.
- No wallet connection and no transaction execution.

## AI Intelligence Layer

Each candidate token is analyzed using deterministic scoring rules across five
market dimensions:

- `liquidity_usd`
- `volume_24h`
- `fdv`
- `price_change_24h`
- `pair_created_at`

The agent adds three AI fields to every token:

- `alpha_score`: 0-100 signal for opportunity quality.
- `risk_score`: 0-100 signal where higher means more risk.
- `ai_summary`: product-readable explanation of momentum, liquidity, FDV, rug
  risk, suspicious volume, and short-term speculation.

Example AI Summary:

```text
Strong momentum detected | Healthy liquidity | Moderate FDV | Rug risk: LOW | Short-term speculative activity possible
```

## Dashboard Showcase

The dashboard is designed as the primary competition demo surface:

- Top token spotlight with alpha score, risk score, liquidity, volume, and 24h move.
- KPI strip for token count, average alpha score, average risk score, and 24h volume.
- Color-coded Alpha Score and Risk Score table.
- AI Summary cards that translate raw metrics into a quick investment-research narrative.
- Auto-refresh every 30 seconds while the scanner updates data in the background.

Start it with:

```bash
streamlit run dashboard/streamlit_app.py
```

## Telegram Alert Showcase

When Top tokens are detected, the Telegram notifier sends a compact alert with:

- symbol
- token name
- 24h volume
- liquidity
- 24h price change
- FDV
- alpha score
- risk score
- AI Summary
- DexScreener URL

This makes the agent useful outside the dashboard, while keeping all actions
read-only and human-reviewed.

## System Architecture

```text
                         +----------------------+
                         |  DexScreener API     |
                         |  Public market data  |
                         +----------+-----------+
                                    |
                                    v
+------------------+     +----------+-----------+     +----------------------+
| schedule loop    | --> | DexScreener client   | --> | Token filter service |
| every 10 minutes |     | src/api/             |     | src/services/        |
+------------------+     +----------------------+     +----------+-----------+
                                                               |
                                                               v
                                                    +----------+-----------+
                                                    | AI Intelligence     |
                                                    | src/ai/             |
                                                    +----------+-----------+
                                                               |
                           +-----------------------------------+------------------+
                           |                                   |                  |
                           v                                   v                  v
                 +---------+----------+              +---------+---------+  +-----+------+
                 | data/alpha_tokens |              | Streamlit UI      |  | Telegram   |
                 | CSV output        |              | dashboard/        |  | alerts     |
                 +-------------------+              +-------------------+  +------------+
```

## Technical Stack

- Python 3.13
- requests
- pandas
- schedule
- logging
- python-dotenv
- Streamlit
- Telegram Bot API
- DexScreener public API

## Demo Flow

1. Start the agent loop:

```bash
python main.py
```

2. Open the dashboard in a second terminal:

```bash
streamlit run dashboard/streamlit_app.py
```

3. Show the Top Token spotlight and explain that raw market data is transformed
   into ranked, scored candidates.

4. Open the AI Summary cards and explain how the agent flags strong momentum,
   low liquidity, suspicious volume, rug risk, and speculative activity.

5. Show the Telegram alert as the off-dashboard notification channel.

Detailed demo notes are available in [docs/demo_script.md](docs/demo_script.md).
Architecture notes are available in [docs/architecture.md](docs/architecture.md).

## Installation

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Create a `.env` file:

```bash
cp .env.example .env
```

Set Telegram configuration:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
AUTO_TRADING_ENABLED=false
```

`AUTO_TRADING_ENABLED` is intentionally disabled by default. Alpha Hunter Agent
does not connect wallets, does not request private keys, and does not execute
transactions.

## Running

Run the scanner:

```bash
python main.py
```

Run the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

Outputs:

- CSV: `data/alpha_tokens.csv`
- Logs: `logs/app.log`
- Telegram: configured chat ID when enabled

## Risk Statement

Alpha Hunter Agent is a research and notification tool. It uses public market
data and heuristic scoring, which can be incomplete, delayed, or misleading.
Scores and summaries are not financial advice. Users should verify token
contracts, liquidity, holders, project credibility, and exchange conditions
before making any decision.

The agent is intentionally read-only:

- It does not connect to wallets.
- It does not sign messages.
- It does not execute swaps.
- It does not automate trading.
