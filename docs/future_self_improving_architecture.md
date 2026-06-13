# Future Self-Improving Architecture

This document records Alpha Hunter's future self-improving architecture. It is
for planning only. The current repository remains in v1.1 Observation Phase and
does not change runtime behavior.

Alpha Hunter's current goal is not to immediately upgrade code. The goal is to
fix the future architecture first so later upgrades can be introduced smoothly,
reviewed safely, and implemented without breaking the read-only market
intelligence boundary.

## Current State: v1.1 Observation Phase

Alpha Hunter Market System v1.1 is a read-only market intelligence system.

Current focus:

- observe multi-chain market signals
- identify early alpha candidates
- organize narratives and signal quality
- generate research artifacts
- preserve memory for later review

Current boundary:

- read-only
- no trading
- no wallet connection
- no private key
- no automated execution

The system can discover, summarize, score, and report. It does not act on
market opportunities.

## Future Architecture Overview

The future self-improving architecture should evolve Alpha Hunter from a pure
observation system into a system that can review its own outputs, learn from
mistakes, and improve future market intelligence.

```text
Market Observation
-> STATE Store
-> Specialist Agents
-> Verifier Agent
-> Thesis Challenge Agent
-> Learning Loop
-> Dynamic Workflow Router
-> Human-Approved Improvements
```

This architecture is not a trading system. It is a future research and
evaluation architecture.

## STATE Store

The STATE Store is the future memory backbone of Alpha Hunter.

Purpose:

- preserve agent run context
- store market snapshots
- record thesis state
- track evidence quality
- store verification outcomes
- support future replay and regression review

Possible state objects:

- market snapshot
- token thesis
- narrative thesis
- agent decision
- rejected candidate
- evidence grade
- verification result
- human review note
- regression lesson

The STATE Store should make Alpha Hunter's reasoning auditable over time. It
should not store private keys, wallet credentials, or execution instructions.

## Skill System

The Skill System is a future layer for reusable research capabilities.

Purpose:

- define repeatable market research workflows
- encode stable evaluation procedures
- separate reusable intelligence methods from one-off scripts
- help agents consult prior validated methods

Possible skills:

- narrative decay review
- liquidity retention review
- social hype follow-through review
- early token survival review
- false-positive investigation
- missed-opportunity investigation

Skills should be reviewed and versioned. They should improve research quality,
not introduce autonomous trading.

## Specialist Agents

Specialist Agents are domain-focused agents that perform narrow research tasks.

Possible future agents:

- Theme Scanner Agent
- Social Signal Agent
- Evidence Grading Agent
- Verifier Agent
- Thesis Challenge Agent
- Reality Check Agent
- Outcome Review Agent
- Memory Agent
- Report Agent

Specialist Agents should remain composable. They should produce structured
outputs that can be inspected, compared, and challenged.

## Verifier Agent

The Verifier Agent checks whether prior Alpha Hunter observations were supported
by later evidence.

Purpose:

- revisit prior signals after fixed time windows
- compare original confidence with later outcomes
- identify false positives
- identify missed opportunities
- record whether narratives continued or decayed

Possible checks:

- did price continue in the expected direction?
- did volume persist or fade?
- did liquidity remain healthy?
- did social attention continue?
- did the token survive later filters?
- did the narrative strengthen or decay?

The Verifier Agent should provide evidence, not automatic weight changes.

## Thesis Challenge Agent

The Thesis Challenge Agent challenges Alpha Hunter's own assumptions.

Purpose:

- question high-confidence signals
- surface weak evidence
- test narrative quality
- separate real momentum from temporary hype
- identify missing context
- reduce confirmation bias

Example challenge questions:

- Is this signal supported by more than one evidence source?
- Is liquidity retention strong enough?
- Is social attention organic or hype-driven?
- Is the theme durable or only a short-term pump?
- What would prove this thesis wrong?

The Thesis Challenge Agent is especially important because Alpha Hunter may
research tokens, protocols, narratives, and broader market themes.

## 5-Stage Learning Loop

The future learning loop should follow five stages:

```text
Fail -> Investigate -> Verify -> Distill -> Consult
```

### 1. Fail

Record where the system was wrong or incomplete.

Examples:

- high-confidence signal faded quickly
- weak signal became strong later
- social hype was over-weighted
- liquidity risk was under-weighted
- narrative decay was missed

### 2. Investigate

Analyze why the failure happened.

Questions:

- what evidence was missing?
- which rule overreacted?
- which signal was ignored?
- did the system confuse hype with durable momentum?
- did the report fail to explain uncertainty?

### 3. Verify

Compare the investigation against later data and human review.

Verification should look for:

- repeated patterns
- measurable outcome changes
- evidence quality
- whether the same issue appears across tokens, chains, or narratives

### 4. Distill

Turn verified lessons into reusable memory.

Outputs:

- regression note
- rule adjustment proposal
- new evaluation checklist
- updated skill guidance
- future dashboard metric proposal

### 5. Consult

Allow future agents to consult distilled lessons before making similar
judgments.

Consultation should improve the quality of future reports and evidence grading,
but production behavior should only change after human approval.

## Dynamic Workflow Router

The Dynamic Workflow Router is a future orchestration layer that decides which
agents and skills should run for a given market situation.

Example routing logic:

- high social hype -> run Thesis Challenge Agent
- strong volume but weak liquidity -> run liquidity retention skill
- repeated OLD-token WATCH noise -> run regression memory check
- new narrative cluster -> run Theme Scanner and Evidence Grading
- prior failed pattern detected -> run Verifier Agent and consult memory

The router should improve workflow selection. It should not execute trades or
take market actions.

## Future Trading Engine

Future Trading Engine is a distant placeholder only.

Current status:

- not enabled
- not implemented
- not part of v1.1
- not part of the current read-only system

Before any future trading-related module is considered, Alpha Hunter needs:

- stable observation history
- reliable evaluation data
- human-reviewed thesis outcomes
- clear safety controls
- explicit user approval

No wallet, private key, signing, swap, or automated execution logic is
introduced by this architecture.

## Safety Boundary

This document does not change Alpha Hunter's current safety boundary.

Alpha Hunter remains:

- read-only
- no trading
- no wallet connection
- no private key
- no signing
- no swaps
- no automated execution

Any future system change must require human approval before it affects runtime
behavior, scoring behavior, alerting behavior, or report behavior.

## Roadmap Placement

This document belongs to future architecture planning.

Placement:

- current version: v1.1 Observation Phase
- near future: Observation + Evaluation System
- long term: Self-Improving Market Intelligence System
- distant reserved area: Future Trading Engine, not enabled

The immediate value of this document is architectural clarity. It gives Alpha
Hunter a stable upgrade direction before implementation begins.
