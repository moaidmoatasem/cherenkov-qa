# CHERENKOV — Engineering Practice & Governance

How CHERENKOV is built and how its contributors — human and autonomous agents — behave. This is the **way of work** that keeps a multi-agent codebase coherent. Maps to **Epoch 8** (GitHub milestone).

| Doc | What it governs |
|---|---|
| [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) | The non-negotiable tenets every change is judged against. |
| [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) | Module layout, data stores, contracts, RCA/impact/traceability internals. |
| [WAYS_OF_WORKING.md](WAYS_OF_WORKING.md) | Branching, PRs, reviews, CI gates, definition of ready/done. |
| [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md) | How multiple coding agents work in parallel without colliding. |
| [BEST_PRACTICES.md](BEST_PRACTICES.md) | Coding, testing, error-handling, logging, security standards. |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Behaviour expected of all contributors and agents. |
| [../adr/](../adr/) | Architecture Decision Records — the log of *why*. |

**Reading order for a new contributor/agent:** ARCHITECTURE_PRINCIPLES → WAYS_OF_WORKING → AGENT_COLLABORATION_PROTOCOL → the relevant area in SYSTEM_DESIGN.

> The mission test for any change (from the Agent Workbook): *does this help the system detect, prove, or close a divergence between sources of truth?* If not, it's plumbing — keep it minimal.
