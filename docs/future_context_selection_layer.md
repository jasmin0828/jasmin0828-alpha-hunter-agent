# Future Context Selection Layer

> Future Architecture Reference Only  
> Not part of the v1.1 Runtime

This document records a future Alpha Hunter architecture idea based on recent
thinking about long-context agent failure, context selection, and relevance over
recall.

It is a planning reference only. Alpha Hunter v1.1 remains in Observation Phase.
This document does not modify `main.py`, agents, database schema, dashboard
behavior, scheduler behavior, Telegram behavior, API behavior, or any runtime
logic.

## 1. Core Problem

The core problem is not that agents always need larger context windows.

The harder problem is that agents need the ability to select the right context
for each step.

Long context can help preserve more information, but it can also create noise,
stale assumptions, contradictory memory, and irrelevant recall. Alpha Hunter
should therefore evolve toward a Context Selection Layer that chooses the
smallest sufficient context for each agent run.

```text
More context is not always better context.
Relevant context is better than maximal context.
```

## 2. Current State: v1.1 Observation Phase

Alpha Hunter Market System v1.1 remains a read-only observation system.

Current focus:

- observe multi-chain market signals
- monitor Ethereum, Solana, and BSC
- organize token, theme, social, evidence, and report artifacts
- support human review
- preserve memory for future evaluation

Current non-changes:

- no `main.py` changes
- no agent runtime changes
- no database schema changes
- no dashboard behavior changes
- no scheduler changes
- no Telegram behavior changes
- no API logic changes

This document describes a future architectural layer, not an implementation
task.

## 3. Key Concepts

### Smallest Sufficient Context

Smallest Sufficient Context means giving an agent the minimum context required
to perform the current task well.

For Alpha Hunter, this means a Theme Scanner should not automatically receive
every historical report, every token note, and every social signal. It should
receive the current market snapshot, relevant recent themes, and only the
memory needed to interpret the current run.

Benefits:

- less noise
- clearer reasoning
- lower chance of stale memory dominating current evidence
- easier debugging
- more reproducible agent outputs

### Relevance over Recall

Relevance over Recall means the system should prefer the most relevant context,
not the largest amount of remembered context.

High recall can surface everything the system has ever seen. High relevance
surfaces the few items that matter for the current decision.

For Alpha Hunter, this matters because token markets are noisy. Old pumps,
expired narratives, stale social hype, and outdated risk notes can mislead an
agent if they are recalled without relevance scoring.

### Provenance

Provenance records where a piece of context came from.

Possible provenance fields:

- source type
- source file
- source agent
- run id
- timestamp
- chain
- token address
- report reference
- human review status

Alpha Hunter should know whether a context item came from market data, a daily
report, a manual note, a social signal, a verifier result, or a human review.

### Supersession

Supersession records when one context item replaces or weakens another.

Examples:

- a newer Reality Check result supersedes an old high-confidence signal
- a verified false positive supersedes an earlier bullish report note
- a newer liquidity-retention failure supersedes a prior strong volume note
- a human review marks an earlier theme interpretation as stale

Without supersession, agents may treat old and new context as equally valid.

### Deliberate Forgetting

Deliberate Forgetting means intentionally excluding stale, low-quality, or
misleading context from an agent run.

It does not mean deleting all history. It means not loading irrelevant history
into the working context.

Examples:

- ignore old social hype with no follow-through
- exclude rejected candidates unless the agent is investigating false positives
- avoid loading stale themes unless they are part of a decay analysis
- prefer verified memory over raw unreviewed notes

### Context Selection Layer

The Context Selection Layer is a future system layer that selects context before
each agent run.

It should consider:

- task type
- agent type
- current market state
- relevant token or theme
- provenance
- supersession status
- recency
- evidence quality
- human review labels
- constraints and safety boundaries

Its goal is to provide each agent with the smallest sufficient context.

## 4. Relationship to Existing Future Architecture

The Context Selection Layer fits between Alpha Hunter's memory systems and its
agent execution layer.

### STATE Store

The STATE Store can hold structured market state, thesis state, run history,
verification results, and human review notes.

The Context Selection Layer queries STATE and chooses which state records are
relevant for the current agent task.

### Memory Agent

The Memory Agent archives reports and keeps local memory assets.

The Context Selection Layer should not blindly load all memory. It should select
the relevant reports, summaries, and review notes for the specific task.

### Skill System

The Skill System can define reusable research procedures.

The Context Selection Layer can select which skill instructions or historical
skill outputs are relevant for the current situation.

### Constraint Library

The Constraint Library is a future safety and quality boundary store.

Possible constraints:

- read-only mode
- no trading language
- no wallet assumptions
- no private key handling
- no automated execution
- no stale-context reuse without provenance
- no superseded thesis reuse without warning

The Context Selection Layer should always load the relevant constraints before
agent execution.

### Verifier / Thesis Challenge Agent

Verifier and Thesis Challenge agents need especially careful context selection.

They should receive:

- original thesis or signal
- later market evidence
- relevant social follow-through
- superseding notes
- human review labels
- known failure patterns

They should not receive broad unrelated memory that distracts from the specific
verification or challenge task.

### Dynamic Workflow Router

The Dynamic Workflow Router decides which agents and skills should run.

The Context Selection Layer decides what context those agents and skills should
receive.

Together:

```text
Dynamic Workflow Router = choose the workflow
Context Selection Layer = choose the working context
```

## 5. Possible Future Data Flow

Future context flow:

```text
Market Data / Reports / Manual Notes / Social Signals
-> Memory + STATE + Skill + Constraint
-> Context Selection Layer
-> Theme Scanner / Evidence Grading / Verifier / Daily Report
```

Expanded view:

```text
Raw Inputs
-> normalized memory and state records
-> provenance tagging
-> supersession checks
-> relevance scoring
-> deliberate forgetting
-> smallest sufficient context package
-> agent execution
-> trace and review output
```

The goal is not to make every agent know everything. The goal is to make every
agent receive the right things.

## 6. Example Agent Context Packages

### Theme Scanner

Possible context:

- current token snapshot
- recent theme distribution
- recent narrative changes
- verified theme decay notes
- relevant constraints

Avoid:

- unrelated old token notes
- stale social hype
- full report history

### Evidence Grading

Possible context:

- current market metrics
- matching social signals
- relevant risk flags
- prior verification outcomes for similar patterns
- superseded thesis warnings

Avoid:

- old bullish notes that have been invalidated
- unrelated chain-level narratives
- raw memory without provenance

### Verifier

Possible context:

- original signal
- original confidence and reasoning
- later price, volume, liquidity, and social data
- human review labels
- regression memory for similar failures

Avoid:

- broad market commentary unrelated to the signal
- future-looking report drafts
- non-reviewed speculative notes

### Daily Report

Possible context:

- current top themes
- current top candidates
- selected evidence grades
- relevant verifier results
- recent human review notes
- explicit safety constraints

Avoid:

- all historical reports
- stale watchlists
- superseded conclusions

## 7. Safety Boundary

This architecture remains read-only.

It does not introduce:

- wallet connection
- private key handling
- trading logic
- signing
- swaps
- automated execution
- automated portfolio action

Alpha Hunter remains a market intelligence and research system. Human approval
is required before any future context-selection behavior affects production
scoring, alerts, reports, or workflow routing.

## 8. Roadmap Placement

This layer is:

- Future Architecture Reference Only
- not part of v1.1 Runtime
- not an immediate implementation task
- a candidate for future v1.2 / v2.0 planning

Suggested future progression:

```text
Memory assets
-> provenance and supersession metadata
-> relevance scoring
-> context packages per agent
-> verifier-aware context selection
-> human-reviewed context policy
```

Alpha Hunter should first stabilize observation, memory, and evaluation. Only
then should it introduce a Context Selection Layer.
