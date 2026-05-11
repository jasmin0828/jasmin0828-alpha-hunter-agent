# Alpha Hunter Agent v0.5 Architecture

Alpha Hunter Agent is designed as a lightweight productized AI agent. It does
one job end to end: collect public market data, filter it, analyze it, and push
the result to human-facing surfaces.

It is intentionally read-only. There is no wallet connector, no private-key
handling, and no trading execution path.

## Agent Workflow

```text
1. main.py starts the agent.
2. schedule runs the scanner immediately and then every 10 minutes.
3. DexScreenerClient fetches Solana hot token candidates.
4. AlphaTokenService fetches pair metrics and applies market filters.
5. AlphaAnalyzer adds alpha score, risk score, and AI Summary.
6. Top 10 tokens are saved to data/alpha_tokens.csv.
7. TelegramNotifier sends the Top token intelligence to Telegram.
8. Streamlit dashboard reads the CSV and refreshes every 30 seconds.
```

## Data Flow

```text
DexScreener public API
        |
        v
src/api/dexscreener_client.py
        |
        v
Raw Solana token and pair metrics
        |
        v
src/services/alpha_token_service.py
        |
        v
Market filters:
  - liquidity_usd > 50000
  - volume_24h > 100000
  - price_change_24h between -30 and 200
  - fdv < 50000000
        |
        v
src/ai/alpha_analyzer.py
        |
        v
Enriched Top 10 output:
  - alpha_score
  - risk_score
  - ai_summary
        |
        +--------------------+
        |                    |
        v                    v
data/alpha_tokens.csv   Telegram Bot API
        |
        v
dashboard/streamlit_app.py
```

## AI Analysis Flow

The AI Intelligence Layer is deterministic and explainable. It does not call a
black-box model. This keeps the demo stable and makes the scoring logic easy to
inspect.

For each token:

1. Normalize numeric fields from DexScreener.
2. Estimate liquidity quality.
3. Estimate attention from 24h volume.
4. Penalize or reward FDV range.
5. Score momentum from 24h price change.
6. Estimate pair age from `pair_created_at`.
7. Create `alpha_score` from opportunity signals.
8. Create `risk_score` from liquidity risk, suspicious volume, very new pairs,
   extreme price moves, and low-FDV manipulation risk.
9. Convert the result into `ai_summary`.

## Product Surfaces

### Dashboard

The Streamlit dashboard is the live operator view:

- Top AI Candidate panel
- KPI strip
- AI Summary cards
- Ranked token intelligence table
- Alpha Score and Risk Score color highlighting

### Telegram Alert

Telegram is the background alert channel. It receives the same intelligence that
appears on the dashboard, including the DexScreener URL for human verification.

## Safety Boundaries

Alpha Hunter Agent does not:

- connect wallets
- request seed phrases or private keys
- sign messages
- submit transactions
- execute swaps
- automate trading

The agent only reads public data, creates analysis, saves CSV output, and sends
notifications.
