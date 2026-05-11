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
- Runs once at startup and then every 10 minutes.

## Filters

Tokens must match all of these rules:

- `liquidity_usd > 50000`
- `volume_24h > 100000`
- `price_change_24h >= -30`
- `price_change_24h <= 200`
- `fdv < 50000000`

## Project Structure

```text
alpha-hunter-ai/
├── main.py
├── requirements.txt
├── README.md
├── data/
│   └── alpha_tokens.csv
├── logs/
│   └── app.log
└── src/
    ├── api/
    │   └── dexscreener_client.py
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

## Run

```bash
python main.py
```

The process keeps running because `schedule` executes the scan every 10 minutes.
Use `Ctrl+C` to stop it.

## Output

- CSV: `data/alpha_tokens.csv`
- Logs: `logs/app.log`

## Notes

DexScreener is a public market data source. Returned tokens are not investment
advice, and the scanner does not perform wallet operations or trades.
