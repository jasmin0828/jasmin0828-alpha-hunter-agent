# Alpha Hunter Agent Architecture

This document defines the first-stage Specialist Agent architecture for Alpha
Hunter Market System. It is a system design document only. It does not change
runtime code, database schema, wallet behavior, or trading behavior.

Alpha Hunter should not become one general-purpose agent. The first-stage design
uses narrow Specialist Agents with clear inputs, outputs, memory boundaries, and
human-reviewable reports.

## First-Stage Agent Map

```text
Alpha Hunter Market System
|
+-- Alpha Hunter Core
|
+-- Theme Scanner Agent
|
+-- Social Signal Agent
|
+-- Value Chain Mapper
|
+-- Evidence Grading Agent
|
+-- Thesis Challenge Agent
|
+-- Memory Agent
|
+-- Daily Alpha Report Agent
```

`Thesis Challenge Agent` replaces the earlier `Company Challenge Agent` name.
Alpha Hunter will research tokens, protocols, narratives, and market themes, not
only public companies.

## Agent Responsibilities

| Agent | Responsibility | Input Data | Output Result | v1.0 Required | v2.0 Extension | Relationship To Current Code |
| --- | --- | --- | --- | --- | --- | --- |
| Alpha Hunter Core | Orchestrate the daily workflow, route tasks to Specialist Agents, merge outputs, enforce read-only safety boundaries, and produce the final run context. | Scan schedule, runtime config, current scan data, signal events, report state, user-approved workflow rules. | Agent run manifest, routed tasks, final report payload, error/status summary. | Yes | No | First-stage standalone Core now exists in `src/agents/alpha_hunter_core.py`; `main.py` remains separate. |
| Theme Scanner Agent | Detect active market themes and recurring narratives from current token candidates and historical snapshots. | DexScreener candidates, `token_snapshots`, narrative labels, volume and liquidity changes, Early Alpha fields. | Theme list, narrative distribution, theme momentum notes, candidate-to-theme mapping. | Yes | No | First-stage Agent now exists in `src/agents/theme_scanner_agent.py`, built from existing narrative, trend, and Early Alpha fields. |
| Social Signal Agent | Add external social context to market themes and token candidates. Detect whether attention is growing outside raw market data. | Manually curated social signal JSON, mentioned tokens, mentioned themes, engagement score, source URLs, timestamps. | Social signal summary, source links, attention strength, hype risk, evidence value. | Yes | No | First-stage manual-input Agent now exists in `src/agents/social_signal_agent.py`; external X/Reddit collection remains future work. |
| Value Chain Mapper | Map a theme to related assets, protocols, sectors, infrastructure, and second-order beneficiaries. | Theme output, project metadata, protocol docs, token/company lists, ecosystem maps, fund/ETF holdings when available. | Value chain map, upstream/downstream entities, related watchlist, research questions. | No | Yes | Not implemented. Should remain design-only until Theme Scanner and Social Signal are stable. |
| Evidence Grading Agent | Grade signal quality using explicit evidence instead of only scores. Separate strong evidence from weak hype. | Market metrics, social signals, signal history, risk flags, outcome tracking. | Evidence grade, evidence notes, weak evidence, risk flags, social evidence, social risk flags. | Yes | No | First-stage rule-based Agent now exists in `src/agents/evidence_grading_agent.py`. |
| Thesis Challenge Agent | Challenge the current investment or narrative thesis across tokens, protocols, narratives, and market themes. Identify counterarguments and failure conditions. | Draft thesis, evidence grade, market metrics, social signals, historical outcomes, risk notes. | Counter-thesis, invalidation points, key uncertainties, decision questions for human review. | No | Yes | Not implemented. Should be added after v1.0 reporting produces stable thesis drafts. |
| Memory Agent | Store durable research memory and retrieve relevant prior context for future reports. Keep memory separated from wallet, credential, or execution state. | Daily reports, report metadata, top theme, top tokens, risk count, social evidence summary. | Archived Markdown report, `memory/index.json` record, recent report list. | Yes | No | First-stage archive/index Agent now exists in `src/agents/memory_agent.py`; no RAG yet. |
| Daily Alpha Report Agent | Produce the operator-facing daily summary so users do not need to review every intraday alert manually. | Token snapshots, theme results, social signals, evidence grades. | Social-enhanced JSON and Markdown Daily Alpha Report. | Yes | No | First-stage report Agent now exists in `src/agents/daily_alpha_report_agent.py`; Telegram delivery remains separate future integration. |

## v1.0 Required Agents

v1.0 should stay small and operational:

- Alpha Hunter Core
- Theme Scanner Agent
- Social Signal Agent
- Evidence Grading Agent
- Memory Agent
- Daily Alpha Report Agent

These six agents create the minimum viable research loop:

```text
Scan market
-> detect themes
-> add social evidence
-> grade evidence
-> write memory
-> produce daily report
```

## Current Implementation Status

The first-stage independent Agent Pipeline is now complete. It runs as a
standalone research loop and dashboard preview, while the existing `main.py`
runtime remains unchanged.

| Agent / Layer | First-Stage Status | Current Implementation | Notes |
| --- | --- | --- | --- |
| Theme Scanner Agent | Complete | `src/agents/theme_scanner_agent.py` | Produces structured theme rows from token snapshots and existing narrative/trend/early-alpha fields. |
| Social Signal Agent | Complete | `src/agents/social_signal_agent.py` | Manual JSON input only; does not call X, Reddit, Telegram, or other external APIs. |
| Evidence Grading Agent | Complete | `src/agents/evidence_grading_agent.py` | Rule-based market and social evidence grading; no LLM judgment. |
| Daily Alpha Report Agent | Complete | `src/agents/daily_alpha_report_agent.py` | Generates social-enhanced JSON and Markdown reports; no Telegram delivery in this pipeline. |
| Memory Agent | Complete | `src/agents/memory_agent.py` | Archives Daily Alpha Report Markdown and updates `memory/index.json`. |
| Alpha Hunter Core / Orchestrator | Complete | `src/agents/alpha_hunter_core.py` | Coordinates Theme, Social, Evidence, Daily Report, and Memory as an independent pipeline. |
| Dashboard Preview | Complete | `dashboard/streamlit_app.py` | Shows Theme Scanner, Daily Report, Evidence, Social, Memory, and Core Run Preview sections. |

Current closed loop:

```text
Token Snapshot
-> Theme Scanner
-> Social Signal
-> Evidence Grading
-> Daily Alpha Report
-> Memory Agent
-> Core Orchestrator
-> Dashboard Preview
```

## v1.1 Positioning

Alpha Hunter v1.1 = Loop System Preview.

Alpha Hunter v1.1 also marks the scanner layer as Multi-chain Alpha Hunter /
Multi-chain Scanner. The Market Intelligence runtime now monitors Ethereum,
Solana, and BSC with chain-aware token identity and chain-specific filters.

Current multi-chain boundary:

- supported chains: Ethereum, Solana, BSC
- token identity should be treated as `chain + contract_address`
- the system remains read-only monitoring and research
- no trading
- no wallet connection
- no private key storage
- no swap execution

## v1.1 Observation Upgrade

The v1.1 Observation Upgrade improves run visibility without promoting Alpha
Hunter into a Learning Phase or Evaluation Loop runtime.

Current observation additions:

- `scan_runs` is reused as the run log for scanner/orchestrator runs.
- Run-log fields record run id, start/finish time, status, scanned chains,
  token count, signal count, errors, and duration.
- Token and signal rows reserve outcome placeholders such as
  `price_at_discovery`, `price_24h`, `price_72h`, `price_7d`,
  `outcome_status`, and `outcome_checked_at`.
- Dashboard and Daily Brief surfaces show Observation Summary.

This does not enable Verifier Agent, Thesis Challenge Agent, Skill System,
automatic learning, external LLM calls, wallet logic, or trading behavior.

The next stage should not focus on adding more agents. It should focus on making
the current agents form sustainable operating loops:

- observable loops
- reviewable loops
- memory-updating loops
- iterative improvement loops

Alpha Hunter should now be treated as an Agent + Loop System. The agents produce
structured work; the loops determine whether that work becomes better over time.

## Loop Layer

The Loop Layer sits above the first-stage agents. It coordinates repeated use,
review, memory update, and future improvement without changing the current
runtime behavior.

```text
Agent Pipeline
-> Daily Output
-> Human Review
-> Memory Update
-> Weekly / Monthly Review
-> Next Pipeline Improvement
```

The v1.1 Loop Layer should make the existing pipeline:

- sustainable across repeated runs
- visible in dashboard previews
- easy to inspect after each run
- easy to compare against prior runs
- useful for future Weekly and Monthly Review
- conservative about integrations and automation

The Loop Layer is not a trading loop. It is a research, review, and memory loop.

## Human Review Layer

Human review remains required in the current stage.

AI can find signals, cluster themes, score evidence, summarize social inputs,
flag hype risk, and write reports. It should not make final market judgments.
The human reviewer remains responsible for:

- deciding whether a signal is useful or noisy
- identifying false positives
- identifying missed signals
- choosing follow-up research questions
- deciding what belongs in durable memory
- deciding whether a future change should affect reporting, content, or system design

This layer is an intentional safety and quality boundary. Alpha Hunter should
make human review faster and more structured, not remove it.

## Memory Update Loop

The Memory Update Loop turns one-off reports into accumulated learning.

Daily outputs should gradually feed memory with:

- daily run summaries
- false positives
- missed opportunities
- review conclusions
- theme changes
- social evidence quality
- hype risk patterns
- useful and unhelpful report sections
- questions for Weekly or Monthly Review

This memory becomes the evidence base for future Weekly Review, Monthly Review,
theme history, and better report generation. v1.1 should improve this loop
before adding external social collection or push automation.

## Long-Term Learning Architecture

Alpha Hunter should evolve in three stages:

### Stage 1: Information System

```text
Discovery -> Analysis -> Memory -> Report
```

Stage 1 is the current v1.x focus. It covers discovery, analysis, memory, and
reporting. The goal is to reliably discover and organize market signals, not to
automatically learn, trade, or change signal weights.

Stage 1 includes:

- Discovery
- Analysis
- Memory
- Report

### Stage 2: Verification System

```text
Thesis -> Registry -> Outcome Review -> Feedback Memory
```

Stage 2 should record each market thesis and verify the result after 7D, 30D,
and 90D. The goal is to collect Prediction vs Outcome data, not to automatically
adjust scoring rules.

Stage 2 includes:

- Thesis Tracker
- Outcome Review Agent
- Prediction Registry
- Signal Follow-up

### Stage 3: Learning System

```text
Prediction Dataset -> Loss Function -> Weight Adjustment -> Better Future Signals
```

Stage 3 is a future learning layer. It should use historical thesis and outcome
data to improve signal weights and rules over time. This is not implemented in
v1.x.

Stage 3 includes:

- Loss Function Engine
- Signal Weight Update
- Feedback Memory
- Rule Adjustment Log

Current learning boundary:

- v1.x does not perform automatic learning.
- v1.x does not adjust signal weights automatically.
- v1.x does not execute trades.
- Loss Function Engine is a future module.
- Before implementing Loss Function Engine, Alpha Hunter needs enough historical thesis/outcome data.

## Future Architecture Reference

Additional future architecture notes:

- `docs/observation_review.md`: v1.1 Observation Review after roughly half a
  month of runtime, with stability, coverage, signal-quality, theme-discovery,
  performance, and daily-report reliability review.
- `docs/future_outcome_evaluation_layer.md`: future Outcome Evaluation Layer
  for tracking signal results across 24h, 3d, 7d, and 30d review windows.
- `docs/future_context_selection_layer.md`: future Context Selection Layer for
  selecting the smallest sufficient context for each agent run using
  provenance, supersession, relevance scoring, and deliberate forgetting.
- `docs/future_skill_self_improvement_loop.md`: future Inner Loop / Outer Loop
  self-improvement architecture for generating human-reviewed Skill Diffs and
  Skill Changelogs from memory, evaluation, and feedback.

This reference is not part of the v1.1 runtime. It does not change `main.py`,
agent execution, database schema, dashboard behavior, scheduler behavior,
Telegram behavior, API behavior, or any trading-related logic.

### Outcome Evaluation Layer

Outcome Evaluation is a future architecture reference. It is not implemented in
the v1.1 runtime.

It sits after scanner and signal discovery, but before memory-driven learning
or adaptability:

```text
Market Data
-> Scanner
-> Signal Discovery
-> Evidence Grading
-> Outcome Evaluation
-> Memory / STATE Store
-> Learning Loop
-> Adaptability Layer
```

Purpose:

- preserve what happened after a signal was discovered
- compare original evidence with later market behavior
- store review-window outcomes such as 24h, 3d, 7d, and 30d
- prepare durable ground-truth data before any Verifier Agent or Loss Function
  Engine is enabled

The layer should support a future `alpha_signal_outcomes` table or equivalent
store, but no production migration is applied in v1.1. It must remain
read-only and must not trigger trading, wallet connection, private-key
handling, swaps, automatic scoring changes, or external LLM runtime.

## Future Self-Improvement Layer

The Future Self-Improvement Layer is not implemented.

Conceptual flow:

```text
Inner Loop
-> Memory
-> Evaluation
-> Research Improvement Agent
-> Skill Diff
-> Human Approval
-> Updated Skills
-> Inner Loop
```

The Inner Loop performs the current research workflow: scan, theme detection,
social signal review, evidence grading, report generation, and memory archive.

The future Outer Loop reviews historical outputs, outcome observations, memory
archives, and human feedback. It may propose Skill Diffs and Skill Changelog
entries, but it must not automatically modify production logic, runtime code,
agent execution, prompts, workflows, alerts, or scoring behavior.

## v2.0 Extension Agents

The following agents are important, but should not block v1.0:

- Value Chain Mapper
- Thesis Challenge Agent

They require better upstream theme and social evidence quality. Adding them too
early would create a more complex system before the evidence layer is reliable.

## Future Version Modules

The following modules remain future work:

| Future Module | Status | Reason To Wait |
| --- | --- | --- |
| Value Chain Mapper | Future version | Needs richer project metadata and stable theme outputs. |
| Thesis Challenge Agent | Future version | Needs stable thesis drafts and enough evidence history to challenge. |
| Thesis Tracker | Future version | Stage 2 module for recording explicit market theses before outcome review. |
| Outcome Review Agent | Future version | Stage 2 module for checking 7D / 30D / 90D outcomes against recorded theses. |
| Prediction Registry | Future version | Stage 2 module for storing Prediction vs Outcome records without automatic reweighting. |
| Ranking / Scorecard Agent | Future version | Should build on validated evidence grades and outcomes. |
| Risk Kill-Switch | Future version | More relevant if any future execution or automated escalation layer exists. |
| Content Agent | Future version | Should follow stable Daily/Weekly reports. |
| Telegram / Push Layer | Future integration | Should wait until Core report output is stable. Existing Telegram runtime remains separate. |
| External API Social Collector | Future integration | Manual social signal path should prove useful before X/Reddit API collection is added. |
| Loss Function Engine | Future version | Stage 3 module for learning from enough historical thesis/outcome data; not implemented in v1.x. |
| Signal Weight Update | Future version | Stage 3 module for applying validated learning to scoring weights; not automatic in v1.x. |
| Rule Adjustment Log | Future version | Stage 3 module for recording why any rule or weight changed. |

## Current Code Relationship

Current runtime code already covers parts of the first-stage design:

- `main.py`: early form of Alpha Hunter Core.
- `src/services/trend_service.py`: market momentum input for Theme Scanner.
- `src/services/narrative_service.py`: current narrative classification.
- `src/services/early_alpha_service.py`: first-seen and early alpha scoring.
- `src/services/risk_intelligence_service.py`: risk evidence inputs.
- `src/services/signal_quality_service.py`: signal quality and outcome summary.
- `src/services/memory_note_service.py`: memory note writer.
- `src/services/daily_brief_service.py`: markdown daily brief writer.
- `src/services/report_notification_service.py`: Telegram daily and weekly reports.
- `src/storage/sqlite_store.py`: scan, snapshot, and signal event history.

The earlier missing v1.0 pieces now exist as independent Agent modules. The next
architecture decision is not whether the loop can run, but when and how to
connect it to a scheduler, Telegram, or the long-running `main.py` process.

## v1.0 Current Boundary

The current v1.0 Agent Pipeline remains a read-only research loop:

- no trading
- no wallet connection
- no private keys
- no transaction signing
- no swaps
- no trading advice
- no automatic X or Reddit collection
- no Telegram push from the new Core pipeline
- no external LLM calls
- no automatic learning
- no automatic signal weight adjustment
- `main.py` production loop is not connected to `AlphaHunterCore`
- no change to the current main runtime logic

The new Core / Orchestrator is a standalone pipeline entry and dashboard preview
layer. It should be observed and stabilized before it is promoted into the
production scan loop.

## Next Recommended Phase

Recommended next phase:

1. Stabilize the Core Pipeline with repeated dry-run previews and standalone test runs.
2. Add a Human Review Layer so outputs can be marked as useful, noisy, false positive, or missed opportunity.
3. Build the Memory Update Loop so review conclusions become future context.
4. Keep observing the dashboard before connecting Core to `main.py` or an independent scheduler.
5. Consider Telegram or push delivery only after the Daily Alpha Report and review loop are stable.
6. Add external social API collection last, after the manual Social Signal workflow proves useful.

## Safety Boundary

This architecture remains read-only in the current phase:

- no wallet connection
- no private keys
- no message signing
- no transaction submission
- no swaps
- no automated trading

Trading Engine work belongs to a later phase and must require separate design,
approval, and safety review.
