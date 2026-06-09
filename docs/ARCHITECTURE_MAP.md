# CHERENKOV-QA Architecture Map

> Auto-generated from import analysis. Update when adding new modules.

## Module Dependency Layers

The codebase follows a clean layered architecture. Dependencies flow **downward only** — upper layers import lower layers, never the reverse.

```
┌─────────────────────────────────────────────────────────────┐
│  INTERFACES (web/, mcp/, chat/, copilot/)                   │
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

## Import Frequency (grep-derived, descending)

The following counts reflect how many times each module is imported by other
cherenkov modules (i.e. demand on the module, not what it imports itself):

| Module | Import count | Role |
|--------|-------------|------|
| `core` | 203 | Foundation — most-imported module |
| `ai` | 34 | LLM clients — second most-imported |
| `substrate` | 29 | Model routing — third most-imported |
| `knowledge` | 25 | GraphRAG mesh |
| `stages` | 23 | Pipeline stage definitions |
| `reflector` | 22 | Verdict memory + suppression |
| `truth` | 17 | Verdict model + emitters |
| `chat` | 17 | Chat agent + conversation memory |
| `hitl` | 15 | Human-in-the-loop review |
| `healing` | 15 | Test repair suggestions |
| `execution` | 15 | Test execution engines |
| `openclaw` | 10 | OpenClaw test introspection |
| `oracle` | 9 | Validation oracle strategies |
| `sources` | 9 | Traffic + event source adapters |
| `validate` | 7 | Validation suite runner |
| `mcp` | 7 | MCP JSON-RPC server internals |
| `divergence` | 7 | Witness/skeptic/explorer loops |
| `coverage` | 5 | Coverage assertion + gating |
| `web` | 4 | FastAPI review API |
| `ports` | 4 | Hexagonal port definitions |
| `sdet` | 3 | SDET coverage loop |
| `rag` | 3 | Retrieval-augmented generation |
| `governance` | 3 | KPI + compliance reporting |
| `federation` | 3 | Multi-node sync |
| `copilot` | 3 | Intent detection + autonomy |
| `compliance` | 1 | MENA compliance scanner |
| `agents` | 1 | Agent pilot |

## Required Core (Track A — always needed)

These modules are required for the basic OpenAPI → Playwright pipeline:

| Module | Purpose | Key Files |
|--------|---------|-----------|
| `core/contracts.py` | Versioned Pydantic stage contracts | All stage I/O models |
| `core/config.py` | Environment-based configuration | All config values |
| `core/config_loader.py` | Config loading utilities | Config file parsing |
| `core/orchestrator.py` | DAG pipeline execution — imports stages + ai + reflector | `run_pipeline()` |
| `core/errors.py` | Shared error hierarchy | Exception base classes |
| `core/events.py` | Internal event bus types | Event data models |
| `core/truth_model.py` | Core verdict data model | `TruthRecord` |
| `stages/ingest.py` | OpenAPI spec ingestion | `IngestStage` |
| `stages/plan.py` | Test scenario planning | `PlanStage` |
| `stages/generate.py` | LLM test generation | `GenerateStage` |
| `stages/review.py` | Test review and validation | `ReviewStage` |
| `execution/eject.py` | Standalone test eject | `EjectorEngine` |
| `execution/validate.py` | Validation suite runner | `ValidationSuite` |
| `execution/playwright_invoke.py` | Playwright test runner | `PlaywrightRunner` |
| `ai/ollama_client.py` | Ollama LLM client | `OllamaClient` |
| `ai/openai_client.py` | OpenAI-compatible client | `OpenAIClient` |
| `ai/interface.py` | LLM provider interface | `AIInterface` |
| `substrate/router.py` | Tier-aware model routing | `SubstrateRouter` |
| `substrate/provider.py` | Provider abstraction | `ModelProvider` |
| `oracle/spec_prism.py` | Spec-derived oracle | `SpecPrismOracle` |
| `oracle/interface.py` | Oracle SPI definition | `Oracle` |

## Optional Extensions (plug in via SPI)

These modules extend the core but are not required for Track A:

| Module | Files | Purpose | Import deps | Status |
|--------|-------|---------|-------------|--------|
| `healing/` | 10 | Suggest-only test repair | `core`, `ai`, `oracle`, `substrate` | PRODUCTION |
| `hitl/` | 4 | Human-in-the-loop review | `openclaw`, `hitl` | PRODUCTION |
| `reflector/` | 6 | Verdict memory + suppression | `core`, `reflector` | PRODUCTION |
| `truth/` | 13 | Verdict model + emitters | `core`, `coverage`, `stages`, `truth` | PRODUCTION |
| `chat/` | 12 | Chat agent + conversation memory | `chat`, `knowledge`, `reflector`, `stages` | PRODUCTION |
| `knowledge/` | 16 | GraphRAG + knowledge mesh | `knowledge` (self-contained) | PARTIAL |
| `mcp/` | 6 | JSON-RPC MCP server | `ai`, `chat`, `core`, `execution`, `hitl`, `validate` | PRODUCTION |
| `web/` | 6 | FastAPI review API + React UI | `ai`, `chat`, `core`, `execution`, `hitl`, `reflector`, `stages`, `web` | PRODUCTION |
| `governance/` | 2 | KPI + compliance reporting | `core`, `governance` | PARTIAL |
| `divergence/` | 6 | Witness/skeptic/explorer loops | `agents`, `core`, `divergence`, `reflector`, `sources`, `substrate` | PARTIAL |
| `copilot/` | 6 | Intent detection + autonomy | `core`, `healing`, `reflector`, `substrate` | PARTIAL |
| `federation/` | 4 | Multi-node sync | `core`, `federation` | PARTIAL |
| `rag/` | 3 | Retrieval-augmented generation | `core`, `rag` | PARTIAL |
| `observability/` | — | Metrics collection + Prometheus | — | PRODUCTION |
| `sources/` | 5 | Traffic + event adapters | `sources` (self-contained) | PARTIAL |
| `coverage/` | 4 | Coverage assertion + gating | `ai`, `core`, `coverage` | PRODUCTION |
| `sdet/` | 3 | SDET coverage loop | `core`, `divergence`, `sdet` | PARTIAL |
| `openclaw/` | 5 | Test introspection | `core`, `hitl`, `openclaw`, `substrate` | PRODUCTION |
| `oracle/prod_snapshot.py` | 1 | Prod snapshot oracle | `core`, `oracle`, `substrate` | PARTIAL |
| `continuity/` | 1 | PR diff action | `core`, `stages` | PARTIAL |
| `validate/` | 5 | Validation gate + evidence | `core`, `validate` | PRODUCTION |
| `ports/` | 5 | Hexagonal port definitions | `core`, `ports` | PRODUCTION |
| `security/` | 1 | Snyk security bridge | (no cherenkov imports) | PRODUCTION |
| `dashboard/` | 2 | Terminal dashboard render | `core`, `governance` | PRODUCTION |
| `agents/` | 2 | Agent pilot | (consumed by divergence) | PARTIAL |

## Stub Modules (not yet implemented)

See [MODULE_STATUS.md](MODULE_STATUS.md) for full stub details.

| Module | Blocker |
|--------|---------|
| `sources/mobile/` | Requires ADB + Maestro (`sources/mobile/adapter.py`, `parsers.py`, `contracts.py` present but stub) |
| `compliance/mena_scanner.py` | MENA-specific compliance scanner not yet implemented |
| `governance/compliance/` | Stub — only `governance/kpi.py` is functional |

## Blocked Tracks

| Track | Module | Blocker |
|-------|--------|---------|
| Desktop (Phase 3) | `desktop/src-tauri/` | Requires `cargo` (Rust toolchain) |
| Mobile (Phase 5–6) | `cherenkov/sources/mobile/` | Requires ADB + Maestro |
| Mobile pipeline | `stages/mobile_cmd.py`, `stages/mobile_generate.py`, `stages/mobile_plan.py`, `stages/mobile_review.py` | Depend on `sources/mobile/` stubs |

## Key SPI Extension Points

Add new capability by implementing one of these interfaces:

| SPI | Location | Implement to add |
|-----|----------|-----------------|
| `SourceAdapter` | `cherenkov/sources/adapter.py` | New traffic/event/mobile source |
| `Oracle` | `cherenkov/oracle/interface.py` | New validation strategy |
| `ModelProvider` | `cherenkov/substrate/providers/` | New LLM backend (ollama, openai, localai, vlm) |
| `KnowledgeStore` | `cherenkov/knowledge/ports/repository.py` + `adapters/` | New storage backend (sqlite, redis) |
| `SandboxProvider` | `cherenkov/healing/providers/` | New test execution sandbox (docker, filesystem) |
| `TruthEmitter` | `cherenkov/truth/emitters/` | New verdict emission target (playwright, pr_comment, spec_patch) |

## Dependency Rules (enforced by convention)

1. `core/` must not import from any other cherenkov module **except** `core/orchestrator.py`, which is the one deliberate exception — it imports `stages/`, `ai/`, and optionally `reflector/` to wire the pipeline.
2. `stages/` may import from `core/`, `ai/`, `substrate/`, `execution/`, `oracle/`, `truth/`, `hitl/`, `healing/`, `divergence/`, `rag/`, `sources/`, `governance/`, `web/` (review serve), and `copilot/` — but not from `mcp/` or top-level `chat/`.
3. `web/` and `mcp/` are the primary consumer entry points that may import freely across layers.
4. `knowledge/` is self-contained — it imports only from itself (16 files, 0 external cherenkov deps detected).
5. `sources/` is self-contained — it imports only from itself.
6. No circular imports between domain service modules (`healing/`, `hitl/`, `reflector/`, `truth/`, `knowledge/`, `oracle/`).

## Actual Circular / Cross-Layer Risks Detected

The grep analysis revealed one notable cross-layer import:

- `core/orchestrator.py` imports `cherenkov.stages`, `cherenkov.ai`, `cherenkov.reflector` — intentional wiring point, not a true circular dep since `stages/` does not import back from `core.orchestrator`.
- `stages/` imports `cherenkov.web` (review serve path in `review_serve.py`) — minor upward leak; `web` should ideally not be a dep of `stages`.
- `truth/` imports `cherenkov.stages` (via `truth/sources/openapi.py`) — truth sources import stage contracts; acceptable but worth monitoring.

## Module Count

- Total Python files: 217 across 32 submodules
- Core module: 16 files
- Stages (including perf/ and visual/ subdirs): 29 files
- Optional extensions: ~172 files
- Tests: 200 unit + 108 smoke + 11 integration test files

---
*Last updated: 2026-06-09 | Run `pydeps cherenkov/ --max-bacon=2` to regenerate the graph*
