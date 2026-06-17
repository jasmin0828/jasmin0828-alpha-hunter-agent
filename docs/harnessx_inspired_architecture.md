# HarnessX-Inspired Architecture

> Future Architecture Reference Only  
> Not part of the v1.1 Runtime

This document maps the design ideas behind HarnessX, a composable, adaptive,
and evolvable agent harness, to the future architecture of Alpha Hunter Market
System.

This is an architecture planning document only. It does not introduce runtime
changes, trading behavior, wallet behavior, database schema changes, dashboard
changes, or automated workflow mutation.

## 1. Why HarnessX Matters

### Harness vs Agent

An agent is a reasoning or task unit. It can scan, grade, summarize, challenge,
or report.

A harness is the operating structure around agents. It decides how agents are
composed, what context they receive, how outputs are traced, how results are
verified, and how future runs can improve without becoming uncontrolled.

In Alpha Hunter terms:

- agents produce research outputs
- the harness coordinates agent execution
- the harness stores traces and run history
- the harness makes evaluation possible
- the harness keeps safety boundaries visible

The distinction matters because a stronger model does not automatically create
a better market intelligence system. The operating system around the model is
what makes outputs repeatable, inspectable, comparable, and eventually
improvable.

### Why the Running System Matters More Than a Single Model

Market intelligence quality depends on more than one agent response.

Alpha Hunter needs:

- consistent input preparation
- structured agent outputs
- traceable scoring rationale
- memory of prior signals
- human-reviewable reports
- reality checks after time passes
- regression memory for repeated mistakes
- clear safety boundaries

HarnessX matters because it frames Alpha Hunter as a living system, not a pile
of prompts. The future system should compose agents, adapt workflow selection,
and evolve from verified lessons while remaining read-only and human-approved.

## 2. Mapping to Alpha Hunter

Alpha Hunter currently belongs to the Compose Stage.

The current independent agent pipeline composes multiple specialist agents into
a research workflow:

```text
Token Snapshot
-> Theme Scanner
-> Social Signal
-> Evidence Grading
-> Memory Agent
-> Daily Report
-> Core Orchestrator
```

### Current Compose Components

| Component | Current Role |
| --- | --- |
| Theme Scanner | Groups token candidates into themes and narrative clusters. |
| Social Signal | Adds manually curated social evidence and hype-risk signals. |
| Evidence Grading | Scores the strength and weakness of market and social evidence. |
| Memory Agent | Archives daily reports and maintains local memory index records. |
| Daily Report | Produces a structured research report for human review. |
| Core Orchestrator | Runs the independent pipeline and summarizes the result. |

This stage is valuable because it creates a repeatable research loop. It is not
yet an adaptive or self-improving harness. It does not automatically rewrite
prompts, mutate workflows, adjust scoring weights, or change runtime behavior.

## 3. Future Adapt Layer

The Adapt Layer should make Alpha Hunter observable and evaluable across runs.

It should answer:

- What happened in this run?
- Which agents ran?
- What evidence was used?
- Which candidates were selected?
- Which candidates were rejected?
- Did later reality confirm or weaken the original signal?

### Trace Store

The Trace Store records meaningful agent activity.

Possible contents:

- run id
- agent name
- input snapshot reference
- scoring result
- reasoning summary
- selected candidates
- rejected candidates
- confidence score
- report reference

The Trace Store should make each research run inspectable without changing the
runtime system.

### Run History

Run History stores the sequence of Alpha Hunter runs over time.

Purpose:

- compare current signals against prior signals
- detect repeated stale patterns
- support weekly and monthly review
- provide future evaluation data
- make missed opportunities visible

Run History is the bridge between daily observations and later evaluation.

### Evaluation Layer

The Evaluation Layer measures how original Alpha Hunter observations compared
with later market behavior.

Possible evaluation dimensions:

- price change after signal
- volume change after signal
- liquidity retention
- narrative continuation
- social follow-through
- false positive rate
- missed opportunity rate
- evidence quality trend

The Evaluation Layer should not automatically change scoring rules in v1.x. It
should collect and organize evidence first.

### Reality Check Agent

The Reality Check Agent revisits prior signals after fixed windows.

Possible windows:

- 1 hour
- 6 hours
- 24 hours
- 3 days
- 7 days

Purpose:

- check whether a signal strengthened or decayed
- verify whether the theme continued
- identify false positives
- identify missed opportunities
- feed Regression Memory and future reports

## 4. Future Evolve Layer

The Evolve Layer should turn verified lessons into safer future behavior.

It should not mutate production workflows automatically. It should propose
reviewable improvements that a human can approve, reject, or park.

### Skill System

The Skill System stores repeatable research procedures.

Examples:

- liquidity retention review
- social hype follow-through review
- narrative decay review
- missed-opportunity investigation
- false-positive investigation

Skills should be versioned, inspected, and improved through human-approved
changes.

### STATE Store

The STATE Store is the future structured memory backbone.

It can hold:

- market snapshots
- token theses
- narrative theses
- agent decisions
- verification outcomes
- regression lessons
- human review notes

The STATE Store should make Alpha Hunter's reasoning durable and auditable. It
must not hold private keys, wallet credentials, signing instructions, or trade
execution state.

### Thesis Challenge Agent

The Thesis Challenge Agent challenges Alpha Hunter's assumptions before they
become durable conclusions.

It should ask:

- What would prove this signal wrong?
- Is this theme durable or only short-term hype?
- Is the evidence multi-source or single-source?
- Is liquidity retention strong enough?
- Is social attention organic or amplified?
- Did prior similar patterns fail?

This agent is a quality-control layer for market theses, not a trading agent.

### Dynamic Workflow Router

The Dynamic Workflow Router decides which agents or skills should run based on
the situation.

Example routing:

- high social hype -> run Thesis Challenge Agent
- strong volume with weak liquidity -> run liquidity retention review
- repeated stale WATCH signals -> consult Regression Memory
- new theme cluster -> run Theme Scanner and Evidence Grading
- prior failed pattern detected -> run Reality Check and Verifier paths

The router should improve research workflow selection. It should not perform
automated trading, wallet operations, prompt rewrites, or uncontrolled workflow
mutation.

## 5. Alignment with Existing Roadmap

This document aligns with the existing future architecture documents:

- `docs/future_self_improving_architecture.md`
- `docs/future_architecture_evaluation_loop.md`

### Alignment with Future Self-Improving Architecture

This HarnessX-inspired view reinforces the same future components:

- STATE Store
- Skill System
- Verifier Agent
- Thesis Challenge Agent
- Dynamic Workflow Router
- 5-stage learning loop: Fail -> Investigate -> Verify -> Distill -> Consult
- Future Trading Engine as a distant placeholder only

The difference is emphasis. The self-improving architecture defines the future
parts; this document explains the harness idea that composes, adapts, and
eventually evolves those parts.

### Alignment with Future Evaluation Loop

This document also aligns with the evaluation-loop path:

```text
Observation System
-> Observation + Evaluation System
-> Self-Improving Market Intelligence System
```

The HarnessX-inspired mapping is:

```text
Compose Stage
-> Adapt Layer
-> Evolve Layer
```

These are compatible views of the same direction:

- Compose Stage maps to current v1.1 Observation Phase.
- Adapt Layer maps to Trace Store, Run History, Evaluation Layer, and Reality Check Agent.
- Evolve Layer maps to Skill System, STATE Store, Thesis Challenge Agent, and Dynamic Workflow Router.

## 6. Explicit Non-Goals

The current version does not implement:

- automated trading
- automated wallet operations
- automated prompt rewrite
- automated workflow mutation
- Reinforcement Learning Runtime

The current version also does not change:

- `main.py`
- database schema
- dashboard behavior
- Telegram behavior
- runtime scheduling
- trading logic

Alpha Hunter remains a read-only market intelligence system in v1.1.

## Roadmap Placement

This document is a future architecture reference only.

It is:

- not part of the v1.1 runtime
- not an implementation specification for immediate code changes
- a planning bridge between the current Compose Stage and future Adapt/Evolve layers
- a conceptual foundation for later v1.2 and v2.0 planning

The immediate goal is architectural clarity. Alpha Hunter should first fix the
shape of the future system, then gradually implement the safest parts after
human review.
