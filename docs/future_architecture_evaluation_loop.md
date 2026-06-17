# Future Architecture: Evaluation Loop

This document defines a future upgrade path for Alpha Hunter from an
Observation System into an Observation + Evaluation System, and eventually into
a Self-Improving Market Intelligence System.

This is an architecture planning document only. It does not describe current
runtime behavior and does not introduce trading, wallet, private key, signing,
swap, or automated execution logic.

## 1. Current State: v1.1 Observation Phase

Alpha Hunter Market System v1.1 is a read-only market intelligence system.

Current boundaries:

- no trading
- no wallet connection
- no private keys
- no signing
- no swaps
- no automated execution

Current focus:

- observe multi-chain market signals across Ethereum, Solana, and BSC
- scan public market data
- filter early alpha candidates
- evaluate signal quality and risk
- generate research-ready reports
- preserve local memory and content artifacts

v1.1 is an Observation Phase system. It can help identify and organize market
signals, but it does not act on them.

## 2. Future Layer: Trace / Run Log

### Purpose

The Trace / Run Log layer should record every meaningful agent run so future
debugging, review, and evaluation are possible.

It should preserve:

- input data
- scoring rationale
- selected candidates
- rejected candidates
- report output
- references to generated artifacts

This layer turns each Alpha Hunter run into an auditable research event.

### Fields To Consider

- `run_id`
- `timestamp`
- `chain`
- `token_address`
- `token_symbol`
- `agent_name`
- `input_snapshot`
- `scoring_result`
- `reasoning_summary`
- `output_decision`
- `confidence_score`
- `rejected_reason`
- `report_reference`

## 3. Future Layer: Reality Check Agent

### Purpose

The Reality Check Agent should revisit previous Alpha Hunter observations after
fixed windows and compare the original signal quality against later market
behavior.

This agent should answer:

- Did the signal strengthen or decay?
- Did the token survive later filters?
- Did liquidity remain healthy?
- Did the theme continue or fade?
- Was the original confidence appropriate?

### Evaluation Windows

- 1 hour
- 6 hours
- 24 hours
- 3 days
- 7 days

### Metrics To Consider

- `price_change_since_signal`
- `volume_change_since_signal`
- `liquidity_change_since_signal`
- `holder_growth` if available
- `social_mentions_change` if available
- whether token survived filters
- whether theme momentum continued

## 4. Future Layer: Evaluation / Loss Function

### Purpose

The Evaluation / Loss Function layer should measure the gap between Alpha
Hunter's original judgment and later reality.

Its job is to turn subjective observations into measurable feedback.

### Possible Metrics

- `prediction_error`
- `confidence_error`
- `false_positive_signal`
- `missed_opportunity`
- `stale_theme_score`
- `narrative_decay_score`
- `evidence_quality_score`

### Example

If Alpha Hunter gave a token or theme high confidence but later market
performance weakened, record a higher loss.

If Alpha Hunter gave low confidence but the token or theme later performed
strongly, record a missed-opportunity loss.

This layer should not automatically change production scoring in v1.x. It
should first collect enough evaluation history to make future calibration
credible.

## 5. Future Layer: Regression Memory

### Purpose

Regression Memory should store historical mistakes and validated signals so
future agents can avoid repeating the same reasoning errors.

It should preserve both:

- mistakes that caused false confidence
- weak signals that later became meaningful

### Examples

- tokens with high volume but weak liquidity retention
- social hype without follow-through
- repeated short-term pumps with no narrative continuation
- themes that looked strong but decayed quickly
- signals that were initially weak but later became strong

Regression Memory should support future Weekly Review, Monthly Review,
evaluation dashboards, and replay tests.

## 6. Future v2.0 Direction: Self-Improving Market Intelligence

The Self-Improving Market Intelligence System is a future possibility only, not
the current implementation.

Future capabilities may include:

- weight adjustment
- agent scoring calibration
- automated evaluation dashboards
- signal replay
- agent sandbox
- regression test suite
- human-approved system changes

The system should only move toward self-improvement after Alpha Hunter has
enough historical run logs, thesis records, outcome reviews, and regression
memory to support responsible calibration.

Human approval should remain required before any system change affects
production scoring, alerting, or report behavior.

## 7. Safety Boundary

This architecture is for future planning only.

It does not introduce:

- trading logic
- wallet logic
- private key logic
- transaction signing
- swaps
- automated execution

Human approval is required before any system change.

The current repository remains in read-only observation mode.

## 8. Roadmap Placement

This evaluation-loop architecture is:

- not part of the v1.1 runtime
- a candidate for v1.2 planning
- a foundation for v2.0 self-improving architecture

Suggested progression:

```text
Observation System
-> Observation + Evaluation System
-> Self-Improving Market Intelligence System
```

Practical sequence:

```text
Run Log
-> Reality Check
-> Evaluation Metrics
-> Regression Memory
-> Human-Approved Calibration
```
