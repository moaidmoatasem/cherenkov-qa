# CHERENKOV — Engineering Practice & Governance

How CHERENKOV is built and how its contributors — human and autonomous agents — behave. This is the **way of work** that keeps a multi-agent codebase coherent. Maps to **Epoch 8** (GitHub milestone).

## Core Engineering Docs

| Doc | What it governs |
|---|---|
| [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) | The non-negotiable tenets every change is judged against. |
| [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) | Module layout, data stores, contracts, RCA/impact/traceability internals. |
| [WAYS_OF_WORKING.md](WAYS_OF_WORKING.md) | Branching, PRs, reviews, CI gates, definition of ready/done. |
| [AGENT_COLLABORATION_PROTOCOL.md](AGENT_COLLABORATION_PROTOCOL.md) | How multiple coding agents work in parallel without colliding. |
| [BEST_PRACTICES.md](BEST_PRACTICES.md) | Coding, testing, error-handling, logging, security standards. |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Behaviour expected of all contributors and agents. |

## Consolidated Plan Docs (Phase -1 through Phase 8)

The consolidated plan (see [../PHASE_PLAN.md](../PHASE_PLAN.md)) adds 5 new capabilities across Phase 1-8. All new modules follow Clean Architecture (Ports/Adapters).

### Architecture Decision Records (ADRs)

| ADR | Decision | Phase |
|-----|----------|-------|
| [ADR-001: Seam-Widening](../adr/ADR-001-seam-widening.md) | Extend Substrate/Stages/Oracle, not separate modules | Phase -1 |
| [ADR-002: Tauri 2 + PyInstaller Sidecar](../adr/ADR-002-tauri2-sidecar.md) | Desktop host architecture | Phase -1 |
| [ADR-003: LocalAI as Default LLM](../adr/ADR-003-localai-default.md) | LocalAI default, Ollama fallback | Phase -1 |
| [ADR-004: Clean Architecture](../adr/ADR-004-clean-architecture.md) | Ports/Adapters for all new modules | Phase -1 |
| [ADR-005: Event-Driven Architecture](../adr/ADR-005-event-driven.md) | asyncio.Queue → Redis Streams | Phase -1 |
| [ADR-006: Knowledge Mesh](../adr/ADR-006-knowledge-mesh.md) | Unified query, separate stores | Phase -1 |

### Strategy Docs

| Doc | What it governs | Phase |
|-----|-----------------|-------|
| [../TESTING.md](../TESTING.md) | Testing pyramid, performance baselines, kill criteria | Phase -1 |
| [../MIGRATION.md](../MIGRATION.md) | Schema versioning, rollback strategy, v1→v2 migrations | Phase -1 |
| [../ERROR_HANDLING.md](../ERROR_HANDLING.md) | Graceful degradation, /healthz, error response format | Phase -1 |
| [../ASSUMPTIONS.md](../ASSUMPTIONS.md) | Team size, hardware, OS, cost, dependencies | Phase -1 |
| [../LOGGING.md](../LOGGING.md) | Structured logging, correlation IDs, log levels | Phase -1 |

### Vision Docs (New Capabilities)

| Doc | What it governs | Phase |
|-----|-----------------|-------|
| [../vision/15_SECOND_BRAIN.md](../vision/15_SECOND_BRAIN.md) | Knowledge mesh, GraphRAG, event bridges | Phase 1 |
| [../vision/16_CHAT_AGENT.md](../vision/16_CHAT_AGENT.md) | Tool-calling agent, persona registry, SSE streaming | Phase 4 |
| [../vision/17_MOBILE_TESTING.md](../vision/17_MOBILE_TESTING.md) | Maestro/Appium, 4-tier devices, semantic visual oracle | Phase 5-6 |
| [../vision/18_DESKTOP_HOST.md](../vision/18_DESKTOP_HOST.md) | Tauri 2, hardware detection, setup wizard | Phase 3 |

**Reading order for a new contributor/agent:** 
1. [../PHASE_PLAN.md](../PHASE_PLAN.md) (consolidated plan overview)
2. [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) (non-negotiable tenets)
3. [../adr/ADR-004-clean-architecture.md](../adr/ADR-004-clean-architecture.md) (Clean Architecture pattern)
4. [BEST_PRACTICES.md](BEST_PRACTICES.md) (coding standards)
5. The relevant vision doc for your phase (15-18)

> The mission test for any change (from the Agent Workbook): *does this help the system detect, prove, or close a divergence between sources of truth?* If not, it's plumbing — keep it minimal.
