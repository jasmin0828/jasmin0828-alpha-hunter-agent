# Isolated Execution Workspace

Alpha Hunter supports one optional process-start environment variable:

```text
ALPHA_HUNTER_WORKSPACE=/absolute/path
```

When it is unset, all existing production paths remain unchanged beneath the
Alpha Hunter repository. PM2, the existing database, environment files, and
normal report, memory, content, and logging behavior require no migration.

When it is set, the value is normalized to an absolute path once during module
import. All mutable paths used by `main.run_agent()` derive from that root.
Missing isolated files do not fall back to production mutable state.

## Mutable path inventory

| Component | Default path | Workspace path | Access |
| --- | --- | --- | --- |
| SQLiteStore | `data/alpha_hunter.db` | `data/alpha_hunter.db` | read/write |
| AlphaTokenService | `data/alpha_tokens.csv` | `data/alpha_tokens.csv` | read/write fallback/output |
| MarketSystemManifestService | `data/market_system_manifest.json` | `data/market_system_manifest.json` | write |
| Execution summary | `data/aios_execution_summary.json` | `data/aios_execution_summary.json` | write |
| Telegram health state | `data/telegram_healthcheck_state.json` | `data/telegram_healthcheck_state.json` | conditional read/write |
| Report notification state | `data/telegram_report_state.json` | `data/telegram_report_state.json` | conditional read/write |
| Daily brief | `memory/daily/` | `memory/daily/` | write |
| Token notes | `memory/tokens/` | `memory/tokens/` | write |
| Narrative notes | `memory/narratives/` | `memory/narratives/` | write |
| Signal-quality note | `memory/signals/` | `memory/signals/` | write |
| Content drafts | `content/x/`, `content/notes/` | `content/x/`, `content/notes/` | write |
| Logging | `logs/app.log` | `logs/app.log` | write when logging is configured |
| Daily scan report | `reports/daily_scan_report.md` | `reports/daily_scan_report.md` | separate report command |
| Directory initialization | `labs/`, `content/threads/` | `labs/`, `content/threads/` | directory creation |

Every workspace path above is relative to the selected root. Source code,
static configuration, schemas, and dependency files remain read-only in the
application repository.

## Isolation semantics

Workspace mode uses a fresh SQLite path and does not read or write the
production database, CSV fallback, memory, or content directories. No database
copy or synchronization occurs.

Telegram remains controlled by the existing variables. A supervised Dogfood
invocation must set all three values explicitly:

```text
TELEGRAM_ENABLED=false
TELEGRAM_HEALTHCHECK_ENABLED=false
TELEGRAM_REPORTS_ENABLED=false
```

This disables message, health-check, and scheduled-report delivery while
retaining structured disabled delivery evidence.

DexScreener retains its existing request-level retry: at most three attempts
for one HTTP request with a three-second delay. Workspace support adds no
capability, Run, scheduler, process, or PM2 retry.

The AIOS Alpha Hunter adapter supplies and validates the workspace for Dogfood
mode. Alpha Hunter does not embed an AIOS path or Dogfood identity.
