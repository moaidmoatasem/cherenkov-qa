# CHERENKOV-QA Architecture Map

> Auto-generated from import analysis. Update when adding new modules.

## Module Dependency Layers

The codebase follows a clean layered architecture. Dependencies flow **downward only** — upper layers import lower layers, never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACES (web/ · mcp/ · chat/ · copilot/)                │
├─────────────────────────────────────────────────────────────┤
│  EXTENDED CAPABILITIES                                       │
│  governance/ · federation/ · divergence/ · compliance/      │
│  continuity/ · openclaw/ · sdet/ · rag/                     │
├─────────────────────────────────────────────────────────────┤
│  DOMAIN SERVICES                                            │
│  healing/ · coverage/ · reflector/ · hitl/ · truth/         │
│  knowledge/ · oracle/ · sources/ · validate/                │
├─────────────────────────────────────────────────────────────┤
│  PIPELINE STAGES                                            │
│  stages/ · execution/                                       │
├─────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                             │
│  ai/ · substrate/ · security/ · ports/ · dashboard/        │
├─────────────────────────────────────────────────────────────┤
│  CORE (no upstream deps)                                    │
│  core/contracts.py · core/config.py · core/orchestrator.py │
└─────────────────────────────────────────────────────────────┘
```

## Import Dependency Graph (from static analysis)

The table below was derived from `grep -r "from cherenkov\."` across all Python files.
Numbers in the **Imports** column indicate the import-frequency rank of that module as a dependency.

| Module | Imports from | Imported by |
|--------|-------------|-------------|
| `core/` | *(none — zero upstream deps)* | ai, substrate, oracle, stages, execution, healing, hitl, reflector, truth, chat, knowledge, mcp, web, governance, divergence, copilot, federation, rag, sources, coverage, validate, sdet, compliance, continuity, openclaw, ports, dashboard |
| `ai/` | core, reflector | stages, substrate, healing, mcp, web, coverage |
| `substrate/` | ai, core | oracle, stages, healing, divergence, copilot, openclaw |
| `oracle/` | core, oracle, substrate | stages |
| `stages/` | ai, copilot, core, divergence, execution, governance, healing, hitl, rag, reflector, sources, stages, substrate, truth, web | core/orchestrator, chat, web, continuity |
| `execution/` | core, hitl | stages, mcp, web |
| `reflector/` | core | ai, stages, chat, divergence, copilot, web |
| `truth/` | core, coverage, stages, truth | stages |
| `healing/` | ai, core, healing, oracle, substrate | stages, copilot |
| `hitl/` | hitl, openclaw | stages, execution, mcp, web |
| `chat/` | chat, core, knowledge, reflector, stages | mcp, web |
| `knowledge/` | *(self-contained)* | chat, web |
| `mcp/` | ai, chat, core, execution, hitl, mcp, validate | *(interface layer)* |
| `web/` | ai, chat, core, execution, hitl, knowledge, reflector, stages, web | *(interface layer)* |
| `governance/` | core, governance | stages, dashboard |
| `divergence/` | agents, core, divergence, reflector, sources, substrate | stages, sdet |
| `copilot/` | core, healing, reflector, substrate | stages |
| `federation/` | core, federation | *(extended capability)* |
| `rag/` | core, rag | stages |
| `sources/` | *(self-contained)* | stages, divergence |
| `coverage/` | ai, core, coverage | truth |
| `validate/` | core, validate | mcp |
| `sdet/` | core, divergence, sdet | *(extended capability)* |
| `compliance/` | compliance, core | *(extended capability)* |
| `continuity/` | core, stages | *(extended capability)* |
| `openclaw/` | core, hitl, openclaw, substrate | hitl |
| `ports/` | core, ports | *(infrastructure)* |
| `dashboard/` | core, governance | *(infrastructure)* |
| `agents/` | *(self-contained)* | divergence |

## Inter-Module Import Frequency

Top imported modules (import count from `grep` analysis — measures how central each module is):

| Rank | Module | Import count | Role |
|------|--------|-------------|------|
| 1 | `core` | 203 | Foundation — contracts, config, errors, orchestrator |
| 2 | `ai` | 34 | LLM client abstraction |
| 3 | `substrate` | 29 | Model routing and provider registry |
| 4 | `knowledge` | 25 | GraphRAG and knowledge mesh |
| 5 | `stages` | 23 | Pipeline stage definitions |
| 6 | `reflector` | 22 | Verdict memory and suppression |
| 7 | `truth` | 17 | Verdict model and emitters |
| 8 | `chat` | 17 | Chat agent and conversation memory |
| 9 | `hitl` | 15 | Human-in-the-loop review queue |
| 10 | `healing` | 15 | Test repair suggestions |
| 11 | `execution` | 15 | Playwright / validation runners |
| 12 | `openclaw` | 10 | Feedback loop contracts |
| 13 | `sources` | 9 | Traffic and event adapters |
| 14 | `oracle` | 9 | Spec/snapshot validation strategies |
| 15 | `validate` | 7 | Validation gate |
| 16 | `mcp` | 7 | MCP JSON-RPC server |
| 17 | `divergence` | 7 | Witness/skeptic/explorer loops |

## Circular Import Risk

`core/orchestrator.py` imports from `stages/` (ingest, plan, generate, review) and `ai/` — this is intentional:
`orchestrator` is the entry-point runner, not a passive contract module. The true "no upstream deps" modules
are `core/contracts.py`, `core/config.py`, and `core/errors.py`.

Modules that import themselves (internal sub-package references): `stages`, `hitl`, `healing`, `divergence`,
`chat`, `knowledge`, `reflector`, `truth`, `federation`, `openclaw`, `sdet`, `rag`, `compliance`, `sources`.
None of these create cross-module circular imports based on static analysis.

## Required Core (Track A — always needed)

These modules are required for the basic OpenAPI → Playwright pipeline:

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `core/contracts.py` | Versioned Pydantic stage contracts | All stage I/O models |
| `core/config.py` | Environment-based configuration | All config values |
| `core/errors.py` | Shared error types and logger | CherenkovError, get_logger |
| `core/orchestrator.py` | DAG pipeline execution | run_pipeline() |
| `stages/ingest.py` | OpenAPI spec ingestion | IngestStage |
| `stages/plan.py` | Test scenario planning | PlanStage |
| `stages/generate.py` | LLM test generation | GenerateStage |
| `stages/review.py` | Test review and validation | ReviewStage |
| `execution/eject.py` | Standalone test eject | EjectorEngine |
| `execution/validate.py` | Validation suite runner | ValidationSuite (heuristic-only suggestions) |
| `ai/ollama_client.py` | Ollama LLM client | OllamaClient |
| `substrate/router.py` | Tier-aware model routing | SubstrateRouter |
| `oracle/spec_prism.py` | Spec-derived oracle | SpecPrismOracle (status-code validation only) |

## Optional Extensions (plug in via SPI)

These modules extend the core but are not required for Track A:

| Module | Purpose | Status | SPI Interface |
|--------|---------|--------|---------------|
| `healing/` | Suggest-only test repair | PRODUCTION | `HealingProvider` base in `healing/providers/base.py` |
| `hitl/` | Human-in-the-loop review queue | PRODUCTION | — |
| `reflector/` | Verdict memory + suppression | PRODUCTION | — |
| `truth/` | Verdict model + emitters | PRODUCTION | `truth/emitters/interface.py`, `truth/sources/interface.py` |
| `chat/` | Chat agent + conversation memory | PRODUCTION | `chat/ports/memory.py` |
| `knowledge/` | GraphRAG + knowledge mesh | PARTIAL | `KnowledgeRepository` SPI in `knowledge/ports/repository.py` |
| `mcp/` | JSON-RPC MCP server | PRODUCTION | — |
| `web/` | FastAPI review API + React UI | PRODUCTION | — |
| `governance/` | KPI + compliance reporting | PARTIAL | — |
| `divergence/` | Witness/skeptic/explorer loops | PARTIAL | — |
| `copilot/` | Intent detection + autonomy | PARTIAL | — |
| `federation/` | Multi-node sync | PARTIAL | `federation/protocol.py` |
| `rag/` | Retrieval-augmented generation | PARTIAL | — |
| `sources/` | Traffic + event adapters | PARTIAL | `SourceAdapter` SPI |
| `oracle/prod_snapshot.py` | Prod snapshot oracle | PARTIAL | Oracle SPI in `oracle/interface.py` |
| `oracle/visual_oracle.py` | Visual regression oracle | PARTIAL | Oracle SPI in `oracle/interface.py` |
| `coverage/` | Coverage emission | PARTIAL | — |
| `sdet/` | Assertion gate + SDET helpers | PARTIAL | — |
| `openclaw/` | Feedback loop integration | PARTIAL | — |
| `continuity/` | PR diff action / CI integration | PARTIAL | — |
| `dashboard/` | KPI render layer | PARTIAL | — |
| `ports/` | Infrastructure port adapters | PARTIAL | — |
| `security/` | Policy / egress control | PARTIAL | — |
| `agents/` | Agent pilot | PARTIAL | — |
| `compliance/` | MENA compliance scanner | STUB | — |

## Stub Modules (not yet implemented)

See [MODULE_STATUS.md](MODULE_STATUS.md) for full stub details.

| Module | Blocker |
|--------|---------|
| `compliance/scanner.py` | MENA scanner not implemented |
| `governance/compliance/` | Stub |
| MCP `visual_diff` tool | Requires visual oracle infrastructure |
| MCP `run_perf` tool | Requires k6 >= 0.50 |
| MCP `export_jira` tool | JIRA API not wired |
| MCP `scan_mena` tool | MENA compliance scanner not implemented |

## Blocked Tracks

| Track | Module | Blocker |
|-------|--------|---------|
| Desktop (Phase 3) | `desktop/src-tauri/` | Requires `cargo` (Rust / Tauri 2) |
| Mobile (Phase 5–6) | `cherenkov/sources/mobile/` | Requires ADB + Maestro |
| K8s Operator (Phase 8) | `operator/` | In progress |

## Key SPI Extension Points

Add new capability by implementing one of these interfaces:

| SPI | Location | Implement to add |
|-----|----------|-----------------|
| `SourceAdapter` | `cherenkov/sources/` | New traffic / event / mobile source |
| `Oracle` | `cherenkov/oracle/interface.py` | New validation strategy |
| `ModelProvider` | `cherenkov/substrate/provider.py` + `providers/` | New LLM backend |
| `KnowledgeRepository` | `cherenkov/knowledge/ports/repository.py` | New storage backend |
| `HealingProvider` | `cherenkov/healing/providers/base.py` | New sandbox / repair environment |
| `TruthEmitter` | `cherenkov/truth/emitters/interface.py` | New verdict sink |
| `TruthSource` | `cherenkov/truth/sources/interface.py` | New ground-truth source |
| `ChatMemory` | `cherenkov/chat/ports/memory.py` | New conversation memory backend |

## Dependency Rules (enforced by convention)

1. `core/contracts.py`, `core/config.py`, and `core/errors.py` must not import from any other cherenkov module.
2. `core/orchestrator.py` may import `stages/` and `ai/` as the top-level entry-point (accepted exception to rule 1).
3. `stages/` may only import from `core/`, `ai/`, `substrate/`, `oracle/`, `execution/`, and domain services.
4. `web/` and `mcp/` are the only allowed import points for everything else (interface layer).
5. No circular imports between peer domain service modules (healing ↔ hitl ↔ reflector etc.).
6. `sources/` and `knowledge/` must remain self-contained to be independently replaceable via SPI.

## Module Count

- Total Python files: 217 across 31 submodules
- Required core (Track A): 13 files
- Optional extensions: ~190 files
- Smoke tests: 36+ (`smoke_test_*.py`)
- Unit / integration tests: 36+ (`test_*.py` + `tests/`)

---
*Last updated: 2026-06-09 | Run `pydeps cherenkov/ --max-bacon=2` to regenerate the import graph*
