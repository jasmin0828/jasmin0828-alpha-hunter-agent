# Alpha Hunter v1.0 Roadmap

This roadmap defines the minimum viable first version of the Specialist Agent
architecture. It is intentionally narrow: build the research loop first, keep
the system read-only, and postpone advanced mapping, thesis challenge, ranking,
kill-switch, and content repurposing work.

## v1.0 Goal

Build a daily market-intelligence loop that can:

1. scan market candidates,
2. detect themes,
3. collect social signal evidence,
4. grade evidence,
5. write memory,
6. produce a Daily Alpha Report.

## v1.0 Current Status

Status: independent Agent Pipeline loop completed.

The current implementation now has a standalone research pipeline that can run
outside `main.py`:

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

This is the first complete Alpha Hunter v1.0 Agent loop. It is available as an
independent pipeline preview and test path, not as the PM2 production loop.

## v1.1 Positioning

Alpha Hunter v1.1 = Loop System Preview + Multi-chain Scanner.

The scanner layer has now been upgraded to Multi-chain Alpha Hunter. The
current supported chains are:

- Ethereum
- Solana
- BSC

Multi-chain identity should use `chain + contract_address` so tokens with the
same symbol on different chains do not collide. Chain-specific filters should
handle liquidity, 24h volume, FDV, and price-change thresholds.

The v1.1 safety boundary remains unchanged:

- no trading
- no wallet connection
- no private key storage
- no swap execution
- no buy/sell recommendations

The next stage is not to keep adding more agents. The priority is to turn the
existing agents into durable loops that can run repeatedly, be observed, be
reviewed, and improve over time.

v1.1 should evolve Alpha Hunter from an Agent System into an Agent + Loop
System:

```text
Agent output
-> human review
-> memory update
-> next run context
-> better report
-> next review
```

The loop matters more than the number of agents. A smaller set of reliable
agents with strong review and memory loops is more valuable than a larger set of
unreviewed agents.

## Loop Layer

The Loop Layer is the v1.1 operating layer above the completed v1.0 Agent
Pipeline. Its job is to make the existing agents sustainable:

- run consistently without changing the current production logic
- expose what happened in each run
- preserve reviewable artifacts
- compare current outputs with prior observations
- create a feedback path from review back into memory
- support Weekly and Monthly Review later

The Loop Layer should initially stay in preview mode through dashboard and
standalone scripts. It should not automatically change `main.py`, Telegram,
database schema, or external integrations.

## Human Review Layer

The current system still requires human review.

AI can discover candidates, organize themes, score evidence, detect social
signals, identify hype risk, and generate reports. Final judgment remains human:

- decide whether a signal is meaningful or noise
- identify false positives
- identify missed opportunities
- decide what should be watched next
- decide what should be written into durable memory
- decide whether a future action is research, content, or system improvement

This layer is intentional. Alpha Hunter should support judgment, not replace it.

## Memory Update Loop

The Memory Update Loop turns daily outputs into durable learning.

Each run can produce report artifacts, but the review result is what makes the
system improve. The following should gradually be captured in memory:

- daily run results
- false positives
- missed signals
- human observation notes
- theme changes
- social evidence quality
- hype risk patterns
- report usefulness
- follow-up questions for Weekly or Monthly Review

This memory should become the basis for later Weekly Review, Monthly Review,
theme history, and better future reports. v1.1 should focus on stable memory
updates before introducing external social APIs or automated push delivery.

## Long-Term Stage Roadmap

Alpha Hunter should evolve from the current Information System into a future
Verification System and eventually a Learning System.

### Stage 1: Information System

Stage 1 is the current v1.x focus.

```text
Discovery -> Analysis -> Memory -> Report
```

Scope:

- Discovery
- Analysis
- Memory
- Report

Goal: stabilize signal discovery and reporting. Stage 1 does not perform
automatic learning or automatic signal-weight updates.

### Stage 2: Verification System

```text
Thesis -> Registry -> Outcome Review -> Feedback Memory
```

Scope:

- Thesis Tracker
- Outcome Review Agent
- Prediction Registry
- Signal Follow-up

Goal: record each market thesis and verify outcomes after 7D / 30D / 90D. Stage
2 collects Prediction vs Outcome data, but it does not automatically adjust
weights.

### Stage 3: Learning System

```text
Prediction Dataset -> Loss Function -> Weight Adjustment -> Better Future Signals
```

Scope:

- Loss Function Engine
- Signal Weight Update
- Feedback Memory
- Rule Adjustment Log

Goal: use enough historical thesis/outcome data to improve future signal weights
and rule quality. Stage 3 is Future / Not implemented in v1.x.

## v1.0 Scope

```text
Alpha Hunter v1.0
|
+-- Alpha Hunter Core
|
+-- Theme Scanner Agent
|
+-- Social Signal Agent
|
+-- Evidence Grading Agent
|
+-- Memory Agent
|
+-- Daily Alpha Report Agent
```

## v1.0 Required Modules

| Module | v1.0 Outcome | Current Status |
| --- | --- | --- |
| Alpha Hunter Core / Orchestrator | One orchestrated daily research flow with clear task routing and report output. | First-stage standalone pipeline completed in `src/agents/alpha_hunter_core.py`; not connected to `main.py`. |
| Theme Scanner Agent | Theme and narrative summary from market data and historical snapshots. | First-stage implementation completed in `src/agents/theme_scanner_agent.py`. |
| Social Signal Agent | Social attention evidence for candidate themes and tokens. | First-stage manual-input implementation completed in `src/agents/social_signal_agent.py`; no external X/Reddit API collection yet. |
| Evidence Grading Agent | Explainable evidence grade for each candidate or theme. | First-stage rule-based implementation completed in `src/agents/evidence_grading_agent.py`. |
| Memory Agent | Durable notes and retrieval-ready history for future reports. | First-stage report archive and index completed in `src/agents/memory_agent.py`. |
| Daily Alpha Report Agent | Markdown daily report that reduces manual review. | First-stage social-enhanced Markdown report completed in `src/agents/daily_alpha_report_agent.py`; not connected to Telegram. |
| Dashboard Preview | Operator preview surface for the independent Agent Pipeline. | Completed in `dashboard/streamlit_app.py` with Theme, Daily Report, Memory, Evidence, Social, and Core Run Preview sections. |

## v1.0 Non-Goals

Do not implement these in v1.0:

- Value Chain Mapper
- Thesis Challenge Agent
- Ranking / Scorecard Agent
- Risk Kill-Switch Agent
- Content Repurposing Agent
- ETF / Fund Exposure Agent

These are useful later, but they should not block the first reliable research
loop.

## Recommended Build Order

The original v1.0 build order has now reached a standalone closed loop. Keep the
historical build order below for context, but treat the next work as stabilization
and integration planning rather than initial module creation.

### Step 1: Stabilize Alpha Hunter Core

Keep the existing PM2-friendly runtime and define clear task boundaries inside
the current workflow.

Deliverables:

- documented Core responsibilities
- explicit stage names in logs and reports
- no database schema change unless required by a later approved task

### Step 2: Build Theme Scanner Agent

Convert existing narrative and trend outputs into a clearer theme layer.

Deliverables:

- theme summary per scan
- daily theme distribution
- theme momentum notes
- theme-to-token mapping

### Step 3: Build Social Signal Agent

Add social evidence to avoid relying only on market metrics.

Deliverables:

- source list per token or theme
- mention count or attention indicator
- social evidence snippets or URLs
- confidence notes

### Step 4: Build Evidence Grading Agent

Create a simple evidence rubric that explains why a signal is strong, weak, or
blocked.

Suggested grade inputs:

- market momentum
- first-seen status
- social confirmation
- source credibility
- liquidity/risk flags
- repeated OLD-token noise
- prior signal outcomes

Deliverables:

- evidence grade
- evidence reason
- missing evidence
- report inclusion decision

### Step 5: Strengthen Memory Agent

Make memory useful for future reports instead of only writing notes.

Deliverables:

- daily report memory
- token memory
- narrative/theme memory
- signal outcome memory
- retrieval-ready summary blocks

### Step 6: Upgrade Daily Alpha Report Agent

Make the daily report the main operator review surface.

Deliverables:

- Telegram Daily Report
- markdown Daily Report
- Top Signals
- Current Watchlist
- social evidence summary
- evidence grade summary
- clear conclusion

Note: Telegram delivery is now treated as a later integration step, not part of
the completed independent Agent Pipeline.

## Future Modules

| Module | Priority | Stage | Current Status |
| --- | --- | --- | --- |
| Thesis Tracker | Near-term | Stage 2: Verification System | Future module; records explicit market theses. |
| Outcome Review Agent | Near-term | Stage 2: Verification System | Future module; reviews 7D / 30D / 90D outcomes. |
| Prediction Registry | Near-term | Stage 2: Verification System | Future module; stores Prediction vs Outcome data without automatic reweighting. |
| Loss Function Engine | Later | Stage 3: Learning System | Future module; not implemented in v1.x and requires enough historical thesis/outcome data first. |

Priority order:

- Near-term: Thesis Tracker, Outcome Review Agent, Prediction Registry
- Later: Loss Function Engine

## v2.0 Parking Lot

The following should be parked for v2.0 or later:

| Module | Reason To Postpone |
| --- | --- |
| Value Chain Mapper | Needs reliable theme detection and external metadata first. |
| Thesis Challenge Agent | Needs stable thesis drafts and evidence grades first. |
| Ranking / Scorecard Agent | Should be built after evidence grading proves useful. |
| Risk Kill-Switch Agent | More relevant when any semi-automated action exists; current system is read-only. |
| Content Repurposing Agent | Better after Daily/Weekly Reports become consistently useful. |
| ETF / Fund Exposure Agent | Useful later for macro and equity workflows, not needed for first token/narrative loop. |

## v1.0 Current Boundary

The completed v1.0 loop is still a read-only research system:

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

The Core pipeline can generate and preview research artifacts, but it does not
execute market actions or publish alerts by itself.

## Next Recommended Phase

Recommended next phase:

1. Stabilize the Core Pipeline through repeated dashboard previews and test runs.
2. Add a Human Review Layer so outputs can be marked as useful, noisy, false positive, or missed opportunity.
3. Build the Memory Update Loop so daily observations feed Weekly and Monthly Review.
4. Observe dashboard behavior before connecting Core to `main.py` or a standalone scheduler.
5. Add Telegram or push delivery only after the report and review loop are stable.
6. Add external social API collection last, after the manual Social Signal path proves useful.

## Current Safety Boundary

v1.0 remains a research and reporting system:

- no wallet connection
- no private keys
- no message signing
- no transaction submission
- no swaps
- no automated trading

Report first. Trade later.
