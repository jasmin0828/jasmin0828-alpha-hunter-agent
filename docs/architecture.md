# Alpha Hunter Market System Architecture

Alpha Hunter Market System is the long-term architecture for building a
read-only market intelligence system. It is the top-level parent system.
Market Intelligence, AI Workflow Engine, Memory Layer, Content Engine,
Automation Layer, and Future AI Trading Agent are direct subsystems. Future
work can grow from this foundation without turning the current system into a
trading execution system.

## System Map

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

## Subsystem Responsibilities

### Market Intelligence

This subsystem reads public DexScreener data, filters candidate tokens, detects
narratives, calibrates signals, and writes research artifacts.

Current components:

- `src/api/dexscreener_client.py`
- `src/services/alpha_token_service.py`
- `src/ai/alpha_analyzer.py`
- `src/storage/sqlite_store.py`
- `src/services/trend_service.py`
- `src/services/narrative_service.py`
- `src/services/token_age_service.py`
- `src/services/risk_intelligence_service.py`
- `src/services/smart_money_service.py`
- `src/services/signal_calibration_service.py`
- `src/services/early_alpha_service.py`
- `src/services/signal_quality_service.py`

Market Intelligence capabilities:

- Narrative Detection: trend, narrative, smart money, risk, token age, and Early Alpha analysis
- Signal Analysis: signal calibration, signal quality, alert transitions, and outcome tracking
- Research Reports: daily briefs, token notes, narrative notes, and signal-quality notes

### Automation Layer

This subsystem keeps the system running on a schedule and pushes human-reviewed
alerts. PM2 or shell process management can run `main.py` as a long-lived loop.

Current components:

- `main.py`
- `logs/app.log`
- `src/notifications/telegram_notifier.py`
- `data/market_system_manifest.json`
- SQLite `signal_events`

### Memory Layer

This subsystem stores durable research memory that can later be synced into
Obsidian or used by a RAG workflow. It is read/write research memory, not wallet
state.

Reserved paths:

- `memory/daily/`
- `memory/tokens/`
- `memory/narratives/`
- `memory/signals/`
- `memory/daily/YYYY-MM-DD.md`
- Obsidian-ready token and narrative pages generated from each scan

### Content Engine

This subsystem turns market intelligence into publishable notes and drafts for X,
Threads, and longer market notes.

Reserved paths:

- `content/x/`
- `content/threads/`
- `content/notes/`

### AI Workflow Engine

This subsystem is the human-in-the-loop workflow between ChatGPT and Codex. ChatGPT
helps reason about market structure, reports, and product direction. Codex
implements, validates, and maintains the codebase.

### Future AI Trading Agent

The AI Trading Agent is explicitly future-only. The current system does not
connect wallets, hold private keys, sign messages, submit transactions, execute
swaps, or automate trading.

## Runtime Flow

```text
DexScreener public API
        |
        v
Market Intelligence
        |
        v
Narrative Detection + Signal Analysis + Research Reports
        |
        +------------------------+
        |                        |
        v                        v
SQLite + CSV              Telegram Alerts
        |
        v
Dashboard + Manifest
        |
        v
Memory Layer + Content Engine
```

## Repository Directory Map

```text
Alpha Hunter Market System
|
+-- Market Intelligence
|   +-- src/api
|   +-- src/ai
|   +-- src/services
|   +-- src/storage
|   +-- dashboard
|
+-- AI Workflow Engine
|   +-- docs/ai_workflow_engine.md
|
+-- Memory Layer
|   +-- memory
|
+-- Content Engine
|   +-- content
|
+-- Automation Layer
|   +-- main.py
|   +-- logs
|   +-- data/market_system_manifest.json
|
+-- Future AI Trading Agent
    +-- future-only, no current runtime directory
```

## v1.2 Direction

The current v1.2 system step is Signal Memory and Daily Brief:

- record alert transitions as durable signal events
- reduce repeated WATCH noise by notifying only new signals and upgrades
- suppress stale OLD-token WATCH fallback unless the token has strong renewed momentum
- update signal event outcomes when 30m, 1h, and 4h follow-up snapshots exist
- write research reports and daily markdown summaries into `memory/daily/`
- preserve best catches and false positives for review
- prepare research notes that the Content Engine can reuse

## Safety Boundaries

Alpha Hunter Market System currently does not:

- connect wallets
- request seed phrases or private keys
- sign messages
- submit transactions
- execute swaps
- automate trading

The system only reads public data, creates analysis, saves research artifacts,
and sends notifications for human review.
