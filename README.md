# Alpha Hunter Market System

Alpha Hunter Market System is a read-only Multi-chain Alpha Hunter and AI
market intelligence system. It uses public market data to discover token
attention, analyze narratives and risk, track early alpha signals, and prepare
long-term research memory across Ethereum, Solana, and BSC.

Alpha Hunter Market System is the top-level parent system. Market Intelligence,
AI Workflow Engine, Memory Layer, Content Engine, Automation Layer, and Future
AI Trading Agent are its direct subsystems. The system does not connect
wallets, request private keys, sign transactions, execute swaps, or automate
trading.

## System Architecture

```text
Alpha Hunter Market System
|
+-- Market Intelligence
|
+-- AI Workflow Engine
|   +-- ChatGPT + Codex
|
+-- Memory Layer
|   +-- Obsidian
|
+-- Content Engine
|   +-- X / Threads / Notes
|
+-- Automation Layer
|   +-- Bots / Scripts / Scheduling
|
+-- Future AI Trading Agent
```

## Current Capabilities

- Multi-chain hot-token discovery from DexScreener public APIs.
- Current chain support: Ethereum, Solana, and BSC.
- Chain-specific market filters for liquidity, 24h volume, 24h price change, and FDV.
- Unified token identity using `chain + contract_address` to avoid cross-chain symbol collisions.
- SQLite scan history in `data/alpha_hunter.db`.
- CSV output in `data/alpha_tokens.csv`.
- Early Alpha Engine fields:
  - `first_seen_at`
  - `is_first_seen`
  - `scan_count`
  - `consecutive_up_count`
  - `early_alpha_score`
  - `early_alpha_reason`
- Narrative, Smart Money, Risk Intelligence, Token Age, and Signal Calibration.
- Telegram alerts for `CRITICAL`, `HIGH`, and `WATCH` signals.
- Streamlit dashboard for live market intelligence with chain filtering.
- Runtime manifest in `data/market_system_manifest.json`.
- Signal transition events in SQLite `signal_events`.
- Signal outcome tracking for 30m, 1h, and 4h follow-up windows.
- Signal quality metrics in the runtime manifest and dashboard.
- Repeated OLD-token WATCH suppression to reduce stale alert noise.
- Daily brief markdown output in `memory/daily/`.
- Obsidian-ready token, narrative, and signal-quality notes in `memory/`.
- Content drafts in `content/x/` and `content/notes/`.
- Memory and content directories for future Obsidian and publishing workflows.

## Subsystem Mapping

| Subsystem | Current implementation |
| --- | --- |
| Market Intelligence | Narrative Detection, Signal Analysis, Research Reports |
| AI Workflow Engine | ChatGPT + Codex workflow in `docs/ai_workflow_engine.md` |
| Memory Layer | `memory/daily`, `memory/tokens`, `memory/narratives`, `memory/signals` |
| Content Engine | `content/x`, `content/threads`, `content/notes` |
| Automation Layer | `main.py`, PM2-friendly loop, Telegram, logs, manifest |
| Future AI Trading Agent | Placeholder only; not implemented |

## Repository Directory Map

| Path | Subsystem relationship |
| --- | --- |
| `src/api`, `src/ai`, `src/services`, `src/storage` | Market Intelligence implementation |
| `dashboard/` | Market Intelligence operator view |
| `memory/` | Memory Layer artifacts for Obsidian-ready research |
| `content/` | Content Engine drafts for X, Threads, and Notes |
| `main.py`, `logs/`, `data/market_system_manifest.json` | Automation Layer runtime evidence |
| `docs/ai_workflow_engine.md` | AI Workflow Engine operating model |
| `labs/` | Experimental workspace, not a top-level subsystem |
| Future AI Trading Agent | Future-only subsystem; no current runtime directory |

## Running

Install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the Market Intelligence runtime:

```bash
python main.py
```

Run the dashboard:

```bash
streamlit run dashboard/streamlit_app.py
```

Outputs:

- `data/alpha_tokens.csv`
- `data/alpha_hunter.db`
- `data/market_system_manifest.json`
- `logs/app.log`
- Telegram alerts when configured

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
TELEGRAM_HEALTHCHECK_ENABLED=true
TELEGRAM_HEALTHCHECK_INTERVAL_HOURS=6
TELEGRAM_REPORTS_ENABLED=true
REPORT_TIMEZONE=Asia/Shanghai
DAILY_REPORT_HOUR=21
WEEKLY_REPORT_WEEKDAY=6
WEEKLY_REPORT_HOUR=21
AUTO_TRADING_ENABLED=false
```

When scans are healthy but no new signal event passes deduplication, Telegram
can send a quiet health check at the configured interval. This confirms the
system is still running without reintroducing repeated OLD token alert noise.

Daily and weekly Telegram reports summarize the scan history so operators do
not need to review every intraday signal manually. By default, the daily report
is sent after 21:00 Asia/Shanghai and the weekly report is sent after 21:00 on
Sunday. These reports do not automatically sync to Obsidian.

`AUTO_TRADING_ENABLED` remains disabled. The Future AI Trading Agent is not
implemented in this codebase.

Multi-chain settings live in `config.py`:

- `SUPPORTED_CHAINS = ["ethereum", "solana", "bsc"]`
- `CHAIN_FILTERS` defines per-chain liquidity, volume, FDV, and price-change thresholds.

## v1.2 Direction

The current v1.2 architecture milestone starts Signal Memory and Daily Brief:

- reduce repeated WATCH alerts by pushing only new signals and upgrades
- record signal transition events in SQLite
- evaluate 30m, 1h, and 4h signal outcomes
- generate daily markdown reports in `memory/daily/`
- send daily and weekly Telegram reports for operator review
- build token and narrative memory for Obsidian/RAG workflows
- prepare reusable content drafts in `content/`

Current architecture readiness is summarized in
[docs/system_readiness_report.md](docs/system_readiness_report.md).

## Safety Statement

Alpha Hunter Market System is a research and notification system. Scores,
alerts, and summaries are not financial advice. Public market data can be
delayed, incomplete, or misleading.

Current safety boundaries:

- no wallet connection
- no private keys
- no message signing
- no transaction submission
- no swaps
- no automated trading
- no buy/sell recommendations
