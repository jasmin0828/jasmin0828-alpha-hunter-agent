# Alpha Hunter Agent v0.1

Alpha Hunter Agent v0.1 is a Python 3.13 data scanner for Solana tokens on
DexScreener. It reads public market data, filters potential candidates, prints
the Top 10 tokens, and saves the result to CSV.

This project does not connect to wallets and does not execute trades.

## Features

- Fetches Solana hot token candidates from DexScreener top boosts.
- Loads pair metrics with liquidity, 24h volume, 24h price change, and FDV.
- Filters tokens with the Alpha Hunter v0.1 rules.
- Prints the Top 10 tokens ranked by 24h volume.
- Saves results to `data/alpha_tokens.csv`.
- Writes runtime logs to `logs/app.log`.
- Sends Telegram messages when Top tokens are found.
- Adds AI Intelligence Layer v0.4 scores and summaries for each token.
- Runs once at startup and then every 10 minutes.

## Filters

Tokens must match all of these rules:

- `liquidity_usd > 50000`
- `volume_24h > 100000`
- `price_change_24h >= -30`
- `price_change_24h <= 200`
- `fdv < 50000000`

## AI Intelligence Layer v0.4

Each filtered token receives deterministic AI-style analysis based on:

- `liquidity_usd`
- `volume_24h`
- `fdv`
- `price_change_24h`
- `pair_created_at`

The output includes:

- `alpha_score`: 0-100 score for alpha potential.
- `risk_score`: 0-100 score where higher means higher risk.
- `ai_summary`: short summary covering momentum, liquidity, FDV, rug risk,
  suspicious volume, and speculative activity.

Example AI Summary:

```text
Strong momentum detected | Healthy liquidity | Moderate FDV | Rug risk: LOW | Short-term speculative activity possible
```

## Project Structure

```text
alpha-hunter-ai/
├── main.py
├── config.py
├── requirements.txt
├── README.md
├── dashboard/
│   └── streamlit_app.py
├── data/
│   └── alpha_tokens.csv
├── logs/
│   └── app.log
└── src/
    ├── ai/
    │   └── alpha_analyzer.py
    ├── api/
    │   └── dexscreener_client.py
    ├── notifications/
    │   └── telegram_notifier.py
    ├── services/
    │   └── alpha_token_service.py
    └── utils/
        ├── logging_config.py
        └── paths.py
```

## Setup

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Telegram Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then set these values:

```env
TELEGRAM_ENABLED=true
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
AUTO_TRADING_ENABLED=false
```

`TELEGRAM_BOT_TOKEN` comes from BotFather. `TELEGRAM_CHAT_ID` is the target
chat, group, or channel ID. When Top tokens are found, the agent sends a message
containing symbol, token name, 24h volume, liquidity, 24h price change, FDV, and
the DexScreener URL.

Automatic trading is disabled by default. The agent only reads market data,
saves CSV output, and sends notifications.

## Run

```bash
python main.py
```

The process keeps running because `schedule` executes the scan every 10 minutes.
Use `Ctrl+C` to stop it.

## Dashboard

Start the Streamlit dashboard in a second terminal after installing the
requirements:

```bash
streamlit run dashboard/streamlit_app.py
```

The dashboard reads `data/alpha_tokens.csv`, highlights the top token by 24h
volume, shows token count, average 24h volume, maximum 24h price change, and
refreshes automatically every 30 seconds.

## Output

- CSV: `data/alpha_tokens.csv`
- Logs: `logs/app.log`

## Notes

DexScreener is a public market data source. Returned tokens are not investment
advice, and the scanner does not perform wallet operations or trades.
