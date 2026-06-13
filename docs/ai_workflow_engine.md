# AI Workflow Engine

The AI Workflow Engine is the human-in-the-loop operating model for Alpha
Hunter Market System. It describes how ChatGPT and Codex support the system
without turning it into a trading execution system.

## Roles

| Role | Responsibility |
| --- | --- |
| ChatGPT | Market reasoning, product direction, report interpretation, prompt-level research |
| Codex | Code implementation, local validation, repository maintenance, artifact generation |
| Human operator | Final judgment, publishing approval, risk review, roadmap decisions |

## Workflow

```text
Human objective
        |
        v
ChatGPT reasoning and product direction
        |
        v
Codex implementation and local verification
        |
        v
Alpha Hunter Market System runtime artifacts
        |
        +-- Market Intelligence
        +-- Memory Layer
        +-- Content Engine
        +-- Automation Layer
        +-- Future AI Trading Agent
        |
        v
Human review
```

## Boundaries

The AI Workflow Engine can:

- propose market intelligence improvements
- implement Market Intelligence, memory, dashboard, and content workflows
- generate research and draft content artifacts
- validate runtime behavior with local commands

The AI Workflow Engine cannot:

- connect wallets
- access private keys
- sign messages
- submit transactions
- execute swaps
- enable automated trading

## Operating Pattern

1. Translate system direction into a concrete repository change.
2. Keep the change aligned with one or more Market System layers.
3. Run local verification.
4. Write durable evidence into docs, manifest, memory, or dashboard artifacts.
5. Leave Future AI Trading Agent guarded until a separate safety model exists.
