# Alpha Hunter Market System Demo Script

This is a 3-minute product demo flow for the OKX Agentic Wallet competition
showcase. The goal is to present Alpha Hunter Market System as a read-only AI
market intelligence system, not as a trading execution system.

## Before the Demo

Install dependencies:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Configure Telegram:

```bash
cp .env.example .env
```

Set `TELEGRAM_ENABLED=true`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`.
Keep `AUTO_TRADING_ENABLED=false`.

## How to Start

Terminal 1, start the Market Intelligence runtime:

```bash
python main.py
```

Terminal 2, start the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

Open the local Streamlit URL shown in the terminal.

## 3-Minute Demo Flow

### 0:00-0:30, Product Positioning

Say:

```text
Alpha Hunter Market System is a read-only AI market intelligence system. Its
direct subsystems are Market Intelligence, AI Workflow Engine, Memory Layer,
Content Engine, Automation Layer, and Future AI Trading Agent. It watches
public DexScreener data, filters noisy markets, scores tokens, and sends alerts
to Telegram. It does not connect to wallets and it does not execute trades.
```

Point to the dashboard header badges:

- Read-only system
- AI risk analysis
- Telegram alerts
- No wallet connection

### 0:30-1:15, Dashboard Showcase

Show the KPI strip:

- Token Count
- Average Alpha Score
- Average Risk Score
- Average Volume 24h
- Max 24h Move

Then show the Top AI Candidate panel. Explain that this is the token with the
strongest combined AI score and market attention, not a buy signal.

Say:

```text
The dashboard turns raw token metrics into an operator view. A user can see the
highest-alpha candidate, its liquidity, volume, risk score, and 24h movement in
one place.
```

### 1:15-2:05, Market Intelligence

Open the AI Summary Cards section.

Explain the five scoring dimensions:

- liquidity
- 24h volume
- FDV
- 24h price change
- pair age

Say:

```text
Market Intelligence turns raw market observations into Narrative Detection,
Signal Analysis, and Research Reports. Alpha Score estimates opportunity
quality. Risk Score highlights execution and manipulation risk. The summary
flags momentum, liquidity health, rug risk, suspicious volume, and short-term
speculative behavior.
```

Point out examples:

- Strong momentum detected
- Healthy liquidity
- Rug risk: LOW or MEDIUM
- Suspicious volume pattern detected
- Short-term speculative activity possible

### 2:05-2:40, Telegram Alert

Open Telegram and show the latest alert.

Explain that the alert contains:

- symbol
- token name
- volume
- liquidity
- price change
- FDV
- alpha score
- risk score
- AI Summary
- DexScreener URL

Say:

```text
The same intelligence leaves the dashboard and reaches the user through
Telegram, so the system can work as a background market monitor.
```

### 2:40-3:00, Safety and Closing

Say:

```text
The important safety boundary is that Alpha Hunter Market System is read-only.
It does not connect to a wallet, request private keys, sign messages, or
execute swaps. Future AI Trading Agent remains a placeholder until a separate
safety model exists.
```

End by showing the `AUTO_TRADING_ENABLED=false` setting in `.env` or README.

## Demo Fallback

If live market data or Telegram is unavailable, use the dashboard CSV output
from a previous run at `data/alpha_tokens.csv`. The dashboard reads the CSV and
can still show the full Market Intelligence experience.
