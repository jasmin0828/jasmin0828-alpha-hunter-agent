# Future Skill Self-Improvement Loop

> Future Architecture Reference Only  
> Not part of the v1.1 Runtime

This document records a future Alpha Hunter architecture for Inner Loop / Outer
Loop self-improvement.

It is documentation only. Alpha Hunter v1.1 remains in Observation Phase:
read-only, no trading, no wallet integration, no private key handling, and no
automated execution.

This document does not modify `main.py`, `src/`, dashboard behavior, database
schema, GitHub Actions, dependencies, scheduling logic, Telegram behavior, or
the current agent execution flow.

## 1. Future Self-Improvement Loop

The long-term direction is to move Alpha Hunter from:

```text
Discover Alpha
-> Remember Alpha
-> Evaluate Alpha
-> Learn Alpha
```

This is not automatic trading and not autonomous self-modification. It is a
future research-quality loop that helps Alpha Hunter improve its own market
intelligence methods through reviewed evidence.

The key idea:

- the Inner Loop performs research and creates outputs
- the Outer Loop reviews those outputs over time
- improvement proposals are written as Skill Diffs
- humans approve any adopted skill change

## 2. Inner Loop

The Inner Loop is the current operational research workflow:

```text
Market Scan
-> Theme Scanner
-> Social Signal
-> Evidence Grading
-> Daily Report
-> Memory Archive
```

Definition:

The Inner Loop performs research and generates outputs.

It discovers market candidates, identifies themes, adds social context, grades
evidence, produces daily reports, and archives memory. The Inner Loop is the
system's observation and reporting path.

Current boundaries:

- read-only
- no wallet access
- no private key handling
- no trading
- no automated execution

## 3. Outer Loop

The Outer Loop is a future architecture layer.

It does not replace the Inner Loop. It reviews the Inner Loop's historical
outputs and proposes improvements to the reasoning process.

### Inputs

The Outer Loop may use:

- historical reports
- memory archives
- human review feedback
- outcome observations
- evaluation records

### Responsibilities

The Outer Loop should:

- review past decisions
- identify successful and failed patterns
- detect recurring themes
- analyze evidence quality
- find repeated false positives
- identify missed opportunities
- generate improvement suggestions

### Outputs

The Outer Loop should produce:

- Skill Diff
- Skill Changelog
- Improvement Proposals

These outputs are recommendations. They do not automatically modify production
logic.

## 4. Skill Files

Skill files are a future concept for storing reasoning heuristics and evaluation
rules in version-controlled documents.

Example skill files:

- `theme_scanner_skill.md`
- `evidence_grading_skill.md`
- `social_signal_skill.md`

Purpose:

- make agent heuristics explicit
- keep evaluation rules reviewable
- preserve why a reasoning method exists
- allow small, inspectable improvements
- support future regression testing

Skill files should be treated as durable research method documents. They are
not runtime trading rules.

## 5. Skill Diff

A Skill Diff is a proposed change to a skill file.

It should explain:

- which skill should change
- what exact heuristic or rule should change
- why the change is proposed
- which reports or evaluations support the change
- what expected impact the change should have
- what risk or uncertainty remains

Skill Diffs should be easy for a human reviewer to approve, reject, or revise.

## 6. Skill Changelog

The Skill Changelog records adopted changes.

Purpose:

Track:

- what changed
- why it changed
- evidence supporting the change
- expected impact
- approval status
- date of adoption

The changelog makes Alpha Hunter's learning history auditable. It should show
how research methods changed over time and why.

## 7. Research Improvement Agent

Research Improvement Agent is a future specialist agent.

Responsibilities:

- analyze report history
- review human feedback
- compare observations with later outcomes
- identify recurring mistakes
- identify useful recurring patterns
- generate proposed skill improvements
- write Skill Diff recommendations

Important boundary:

The Research Improvement Agent must not automatically modify production logic.
It only produces recommendations.

It should not:

- edit runtime code
- change scoring behavior automatically
- rewrite prompts automatically
- mutate workflows automatically
- trigger trading behavior
- change alerts without human approval

## 8. Human Approval Layer

All generated Skill Diffs require human review before adoption.

There is no autonomous self-modification.

Human reviewers decide:

- whether the evidence is strong enough
- whether the proposed change is too broad
- whether the change should be tested first
- whether the skill should be updated
- whether the change should remain parked as a hypothesis

The Human Approval Layer is part of the safety model. Alpha Hunter can propose
improvements, but humans approve system changes.

## 9. Relationship to Existing Future Architecture

This document aligns with and complements:

- `docs/future_self_improving_architecture.md`
- `docs/future_architecture_evaluation_loop.md`
- `docs/harnessx_inspired_architecture.md`

### STATE Store

The STATE Store can preserve run context, thesis state, evaluation records, and
review labels. The Outer Loop can use STATE to identify recurring patterns and
evidence quality changes.

### Skill System

The Skill System stores the reasoning heuristics and evaluation rules that the
Outer Loop may propose to improve.

### Verifier Agent

The Verifier Agent checks whether prior observations matched later reality. Its
results become input to the Outer Loop.

### Thesis Challenge Agent

The Thesis Challenge Agent identifies weak assumptions and failure conditions.
Its output can reveal where skill rules need to become sharper.

### Dynamic Workflow Router

The Dynamic Workflow Router may eventually use approved skills to choose the
right workflow for a market situation. It should only use human-approved skill
changes.

## 10. Conceptual Flow

Future self-improvement flow:

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

This flow is future architecture only. It is not implemented in v1.1.

## 11. Safety Boundary

Alpha Hunter remains:

- read-only
- no trading
- no wallet integration
- no private key handling
- no automated execution

This document introduces no trading engine, no wallet integration, no private
key flow, no automated execution path, and no autonomous self-modification.

Any future adoption of skill changes must be human-approved and separately
implemented.

## 12. Roadmap Placement

This layer is:

- not part of v1.1 runtime
- planning only
- a candidate for v1.2 / v2.0 architecture
- dependent on enough memory, evaluation records, and human feedback

The immediate goal is architectural clarity, not code changes.
