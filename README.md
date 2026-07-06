# Alpha Hunter Market System

A multi-chain crypto market intelligence system for discovering emerging
narratives, monitoring early on-chain signals, and generating research-ready
alpha reports.

> Current version: v1.1  
> Status: Observation Phase  
> Mode: Read-only market intelligence system

Alpha Hunter Market System is the top-level parent system. Market Intelligence,
AI Workflow Engine, Memory Layer, Content Engine, Automation Layer, and Future
AI Trading Agent are its direct subsystems.

## Supported Chains

- Ethereum
- Solana
- BSC

## What It Does

- Scans multi-chain token markets.
- Filters early alpha candidates.
- Tracks signal quality.
- Supports agent-based analysis.
- Generates daily alpha reports.
- Generates a Daily Scan Report: a Chinese read-only scan summary, not market
  analysis or financial advice.
- Maintains local memory and research artifacts.
- Provides a Streamlit dashboard for monitoring.
- Runs GitHub Actions validation for baseline health checks.

## Safety Boundary

Alpha Hunter is not a trading bot.

It does not:

- connect wallets
- store private keys
- sign transactions
- execute swaps
- place trades
- provide financial advice

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

## System Overview

```text
Ethereum / Solana / BSC
        |
        v
Multi-chain Scanner
        |
        v
Signal Quality / Risk Intelligence
        |
        v
Agent Pipeline
        |
        v
Daily Alpha Report
        |
        v
Memory Layer / Content Layer / Dashboard
```

## Observation Phase

Alpha Hunter Market System v1.1 is in Observation Phase. The system is designed
to collect market evidence, monitor early signals, evaluate signal quality, and
prepare research reports without executing trades or making automated decisions.
Human review remains responsible for interpreting signals, identifying false
positives, and deciding any next research steps.

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
- Telegram alerts for configured `CRITICAL`, `HIGH`, and `WATCH` signals.
- Streamlit dashboard for live market intelligence with chain filtering.
- Agent Pipeline preview for theme scanning, social signal review, evidence
  grading, daily report generation, and memory archiving.
- Runtime manifest in `data/market_system_manifest.json`.
- Signal transition events in SQLite `signal_events`.
- Signal outcome tracking for 30m, 1h, and 4h follow-up windows.
- Signal quality metrics in the runtime manifest and dashboard.
- Repeated OLD-token WATCH suppression to reduce stale alert noise.
- Daily Scan Report in `reports/daily_scan_report.md`: Chinese read-only scan
  summary of run logs, chain coverage, token counts, signal counts, and theme
  distribution. It is not investment advice or market analysis.
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
