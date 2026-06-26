# Observation Upgrade

Alpha Hunter Market System v1.1 remains in Observation Phase. This upgrade
improves run visibility, reporting, and dashboard observability without changing
the system's safety boundary.

## Purpose

The goal is to make long-running Alpha Hunter scans easier to inspect.

This upgrade adds:

- scan run logging
- recent run health summary
- discovery-stage outcome placeholders
- dashboard Observation Summary
- daily brief Observation Summary

It does not add trading, wallet integration, private key handling, external LLM
calls, automated execution, or self-learning runtime.

## Run Log

The existing `scan_runs` table is reused and extended. No duplicate run-log
table is introduced.

Run-log fields:

- `run_id`
- `started_at`
- `finished_at`
- `status`
- `scanned_chains`
- `tokens_scanned`
- `signals_found`
- `errors`
- `duration_seconds`

The legacy `completed_at` and `token_count` fields remain for compatibility.

## Outcome Placeholders

Outcome placeholders are reserved on token and signal observation rows.

Fields:

- `price_at_discovery`
- `price_24h`
- `price_72h`
- `price_7d`
- `outcome_status`
- `outcome_checked_at`

Current behavior:

- write `price_at_discovery` during the discovery scan
- keep future 24h / 72h / 7d fields empty until later validation logic exists
- do not introduce a Verifier Agent runtime
- do not introduce Thesis Challenge runtime
- do not automatically re-score or learn from outcomes

## Dashboard Observation Summary

The dashboard now includes an Observation Summary for the most recent 7 days.

It shows:

- total run count
- successful run count
- failed run count
- scanned token count
- discovered signal count
- chain distribution
- latest run status
- latest run errors when present

This is an operator visibility panel only. It does not change scanner behavior.

## Daily Brief Observation Summary

The daily brief includes the latest run status:

- scan status
- started / finished time
- scanned chains
- token count
- signal count
- duration
- error summary

This helps confirm the system is healthy even when no Telegram alert is sent.

## Current Boundary

This is a v1.1 Observation Phase enhancement.

It is not:

- Learning Phase
- Evaluation Loop runtime
- Verifier Agent runtime
- Thesis Challenge Agent runtime
- Skill System runtime
- trading infrastructure

Safety boundary:

- read-only
- no trading
- no wallet connection
- no private key storage
- no signing
- no swaps
- no automated execution
- no external LLM calls
- no automated social publishing

## Future Use

These observation fields create a foundation for later review and evaluation,
but they do not implement those future layers yet.

Possible future uses:

- Reality Check Agent
- Evaluation Loop
- Verifier Agent
- Thesis Challenge Agent
- Skill System
- Context Selection Layer

Each future layer should require a separate design and approval step.
