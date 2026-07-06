# Future Outcome Evaluation Layer

This document defines the planned Outcome Evaluation Layer for Alpha Hunter
Market System. It is future architecture planning only.

It does not modify runtime code, scanner logic, report generation, database
schema, GitHub Actions, Telegram behavior, wallet behavior, or trading
behavior.

## Why Evaluation Phase Is Needed

Observation Phase helps Alpha Hunter discover and organize market signals.
That is necessary, but not enough.

A signal should not only record the moment it was discovered. It should also
record what happened afterward. Without later outcomes, Alpha Hunter cannot
distinguish:

- strong early alpha from short-lived noise
- useful narrative discovery from narrative decay
- social heat with follow-through from hype without evidence
- missed opportunities from correctly ignored noise
- high-confidence false positives from genuinely strong signals

Evaluation Phase turns observation into reviewable ground truth.

## Core Principle

Signal records should preserve both:

- discovery context: what Alpha Hunter saw at signal time
- outcome context: what happened after 24h, 3d, 7d, and 30d

The system should remain read-only. Outcome evaluation should observe later
market behavior; it should not trade, connect wallets, or execute any action.

## Outcome Tracking Lifecycle

Planned lifecycle:

```text
signal_created
-> 24h_review
-> 3d_review
-> 7d_review
-> 30d_review
```

### signal_created

Record the discovery state:

- signal id
- token symbol
- chain
- contract address
- signal timestamp
- alert level
- evidence grade
- theme
- price at signal
- liquidity at signal
- volume at signal
- social evidence if available

### 24h_review

Short-term follow-up:

- did price react?
- did volume continue?
- did liquidity hold?
- did the token survive filters?
- did the theme continue to appear?

### 3d_review

Near-term persistence check:

- did signal strength remain?
- did the narrative persist?
- did social heat decay or broaden?
- was the first move a one-off spike?

### 7d_review

Weekly outcome check:

- did the token/theme remain relevant?
- was the original evidence quality useful?
- did the signal become a repeated watch item?
- did new contradictory evidence appear?

### 30d_review

Longer outcome check:

- did the signal become a durable theme?
- did the original thesis age well?
- did the token retain liquidity and volume?
- should this pattern be added to future rule review?

## Outcome Fields

Each signal should eventually support outcome fields such as:

- `price_at_signal`
- `price_24h`
- `price_3d`
- `price_7d`
- `price_30d`
- `max_gain`
- `max_drawdown`
- `final_return`
- `theme_persistence`
- `social_heat_change`
- `exchange_listing_event`
- `outcome_label`

These fields should be filled only when the relevant review window has passed
and the data is available.

## Outcome Labels

Possible outcome labels:

- `strong_alpha`
- `weak_alpha`
- `false_positive`
- `narrative_decay`
- `insufficient_data`

Label definitions:

| Label | Meaning |
| --- | --- |
| `strong_alpha` | Signal showed meaningful follow-through in price, volume, liquidity, theme persistence, or evidence quality. |
| `weak_alpha` | Signal showed partial follow-through but lacked enough strength or persistence. |
| `false_positive` | Signal looked strong at discovery but later weakened, lost liquidity, or failed to persist. |
| `narrative_decay` | Theme or social narrative faded even if early market metrics looked active. |
| `insufficient_data` | Later review could not collect enough reliable data to classify the outcome. |

## Draft Future Schema

This is a draft schema only. It should not be applied to production runtime in
v1.1.

Table name:

```text
alpha_signal_outcomes
```

Draft fields:

| Field | Purpose |
| --- | --- |
| `id` | Outcome row id. |
| `signal_id` | Link to the original signal event or future signal registry row. |
| `token_symbol` | Human-readable token symbol at signal time. |
| `chain` | Chain name such as ethereum, solana, or bsc. |
| `contract_address` | Token contract or mint address. |
| `signal_created_at` | Timestamp when the signal was created. |
| `review_window` | Review window such as 24h, 3d, 7d, or 30d. |
| `price_at_signal` | Price when Alpha Hunter first recorded the signal. |
| `price_at_review` | Price at the review window. |
| `max_gain_pct` | Maximum observed gain during the review window. |
| `max_drawdown_pct` | Maximum observed drawdown during the review window. |
| `final_return_pct` | Return at the end of the review window. |
| `liquidity_change_pct` | Liquidity change from signal time to review time. |
| `volume_change_pct` | Volume change from signal time to review time. |
| `social_heat_change` | Optional social attention change, if available. |
| `theme_status` | Theme persisted, decayed, broadened, or unknown. |
| `outcome_label` | Outcome label such as strong_alpha or false_positive. |
| `reviewed_at` | Timestamp when the outcome was reviewed. |
| `notes` | Human or system notes about the outcome. |

## Relationship To Existing Observation Upgrade

The current Observation Upgrade already reserves discovery-stage outcome
placeholders on token and signal rows. Those placeholders are useful but not a
full Evaluation Phase.

The future Outcome Evaluation Layer should add:

- explicit review windows
- durable outcome rows
- ground-truth labels
- human-reviewable evidence
- separation between discovery data and later outcome data

## Position In Architecture

Planned architecture chain:

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

Outcome Evaluation sits after signal discovery and evidence grading. It should
feed Memory / STATE Store before any learning or adaptability layer is allowed.

## Safety Boundary

The Outcome Evaluation Layer is read-only.

It must not:

- trade
- connect wallets
- store private keys
- sign transactions
- execute swaps
- trigger automated buy/sell actions
- call external LLMs without a separate approved design
- automatically change production scoring weights

## Roadmap Placement

This layer is:

- not part of v1.1 runtime
- a foundation for v1.2 planning
- a prerequisite for future Ground Truth Store
- a prerequisite for future Verifier Agent
- a prerequisite for future Loss Function Engine
- a prerequisite for future Self-Improvement Loop

Before implementing this layer, Alpha Hunter should continue collecting stable
Observation Phase run logs and human-reviewed reports.
