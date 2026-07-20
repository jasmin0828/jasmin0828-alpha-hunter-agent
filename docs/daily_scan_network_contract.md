# Daily Scan Network Enforcement Contract

Status: Phase 4.7.3 implemented; no Dogfood execution performed

An isolated `main.run_agent()` execution is fail-closed unless
`ALPHA_HUNTER_NETWORK_POLICY` identifies a readable policy whose digest is
bound by the AIOS approved package. Normal production execution remains
compatible when both the workspace and policy variables are unset.

## Complete daily-scan endpoint inventory

| Endpoint ID | Origin / method / path | Query parameters | Caller | Purpose | Daily / read-only | Retry | Response parser |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `dexscreener.search_pairs` | `https://api.dexscreener.com` `GET /latest/dex/search` | required `q` only | `search_pairs()` from `find_and_save_top_tokens()` | search pairs for configured keywords | required / yes | request only, 3 attempts, 3 seconds | JSON object `pairs` list |
| `dexscreener.top_boosts` | `https://api.dexscreener.com` `GET /token-boosts/top/v1` | none | `get_top_boosted_token_addresses()` from `find_and_save_top_tokens()` | discover boosted-token addresses | required / yes | request only, 3 attempts, 3 seconds | JSON list of token descriptors |
| `dexscreener.token_batch` | `https://api.dexscreener.com` `GET /tokens/v1/{chain}/{addresses}` | none; path permits `ethereum`, `solana`, `bsc`, at most 30 unique format-validated addresses | `get_pairs_by_token_addresses()` from `find_and_save_top_tokens()` | fetch pair data for boosted tokens | required when boost addresses exist / yes | request only, 3 attempts, 3 seconds | JSON list of pairs |

No other origin, method, path, query parameter, chain, address shape, port, or
credential-bearing URL is authorized. The canonical machine-readable policy is
`config/daily_scan_network_policy.json`.

## Enforcement

Authorization occurs immediately before every request. Automatic redirects are
disabled; every redirect target is independently normalized and re-authorized,
with a maximum of five hops and loop rejection. A policy rejection is terminal
and is never retried. Existing retry semantics remain request-local: up to
three attempts, separated by three seconds, only after authorization succeeds.

Each decision is appended as one independent JSON line to
`data/network_requests.jsonl` in the selected workspace. Records contain a
microsecond UTC RFC 3339 `timestamp` with a `Z` suffix, Run correlation ID,
method, normalized origin and path, query-parameter names (never values),
decision, attempt, redirect index, and policy SHA-256. Request bodies, headers,
credentials, cookies, tokens, and raw query values are excluded.

The timestamp is generated at evidence emission: immediately before an allowed
attempt is transmitted, when a policy denial is recorded, and separately for
every retry and evaluated redirect target. The single foreground process
appends records in emission order without sorting or rewriting them. A
process-local lock keeps each JSON line intact; file order, attempt, and
redirect index remain the tie-breakers if two timestamps share clock resolution.

This contract adds no scheduler, queue, process retry, PM2 retry, Sandbox, or
new network destination.
