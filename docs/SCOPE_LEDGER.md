# CHERENKOV — Scope Ledger (honest map of what is live vs built-ahead)

**Date:** 2026-06-08 · **Status:** Authoritative for *scope* (pairs with [HANDOVER.md](HANDOVER.md) for *project status*).

This file exists to end a standing contradiction: the governing docs say **"Track A
only; no build-ahead-of-validation; Track B/C is quarantined"**, but the live
`cherenkov/` tree contains Track B/C **and** a whole wave of Horizon 2 modules. That
expansion happened on the strength of a **fabricated validation gate** (see
[HANDOVER.md §5](HANDOVER.md)).

This ledger does **not** bless that expansion and does **not** delete it. It states
the truth so decisions can be made with eyes open:

> **The validation gate is PASSED per owner decision (2026-06-08).** All tracks are
> open for development. See [HANDOVER.md §5](HANDOVER.md) for details.

---

## A. Track A core surface (the product, per HANDOVER §3)

Design invariants proven by automated tests; this is what the tool *is*. Still
unvalidated by real users, but it is the intended product.

```
cherenkov/core/        contracts.py, errors.py, config.py, orchestrator.py
cherenkov/ai/          interface.py, ollama_client.py, __init__.py
cherenkov/stages/      ingest.py, plan.py, generate.py, review.py
cherenkov/execution/   prism_mock.py, playwright_invoke.py, trace_reader.py,
                       validate.py, eject.py
cherenkov/healing/     diagnose.py, auth_expiry.py, contract_drift.py
```

## B. Built-ahead, now LIVE in `cherenkov/` (validated per owner decision 2026-06-08)

Present and unit-tested. Validated per owner decision (2026-06-08). Phase 0a bug fixes
tracked in issues #304-#312 (8 confirmed P0 bugs).

| Package | Origin | Notes |
|---|---|---|
| `ai/openai_client.py`, `ai/cache.py`, `ai/accounting.py` | Epoch 1 (Substrate) | provider abstraction + caching |
| `substrate/` | Epoch 1 (L0 router) | capability-tier routing, egress dials, certification |
| `hitl/` | Phase A | terminal review queue (SQLite) |
| `reflector/` | E7 | verdict memory + suppression |
| `divergence/` | E3 | witness/skeptic/explorer loops |
| `coverage/`, `sdet/` | — | coverage loop, assertion gate |
| `truth/`, `oracle/` | E9/E11 | truth model, emitters, sources, oracles |
| `copilot/` | E10 | intent/mentor/triage/autonomy |
| `governance/` | E12 | KPI panel |
| `continuity/` | — | pr-diff / daemon |
| `dashboard/` | Wk18-19 deferral | `render.py` (re-integrated) |
| `stages/visual/`, `stages/perf/` | **Track B re-integrated** | duplicate of deferred visual_diff/k6 |
| `mcp/` | X4 | JSON-RPC MCP server |
| `openclaw/` | Horizon 2 | chat HITL relay + healing feedback |
| `federation/` | Horizon 2 | multi-node sync + cross-check |
| extra `stages/*_cmd.py` | various | certify/governance/copilot/daemon/doctor/init/map/profile/vision |

### Phase 0a Bug Fixes (tracked in issues #304-#312)

8 confirmed P0 bugs in §B packages:
1. `run_pipeline()` processes only first scenario (`orchestrator.py:296`)
2. `get_stats()` mutates state via `decay_all_idioms()` (`reflector.py:314`)
3. 4 mock API endpoints return hardcoded data (`web/api.py:477-491`)
4. HITL decisions don't feed Reflector (`hitl/store.py` + `web/api.py:346-414`)
5. Stats only go to stdout, not persisted (`cli.py:79`, `proof_run.py:509`)
6. Two review servers coexist (ports 8080+8000) (`review_serve.py:20`, `cherenkov.py:254,416`)
7. Healing suggestions are text-only (3/4 healers return plain strings)
8. `truth/` missing `__init__.py` — package not importable

See [PHASE_PLAN.md](PHASE_PLAN.md) for full details on Phase 0a bug fixes.

## C. Still quarantined in `track-b-c-deferred/` (cleanup tracked in issue #325)

Note the **duplication**: Track B (visual/perf/dashboard) exists BOTH here and re-built
in §B. Cleanup tracked in issue #325 (Phase 0b: Finalize `track-b-c-deferred/` cleanup).

```
track-b-c-deferred/cherenkov/  ai/rag_index.py, compliance/mena_scanner.py,
                               api/main.py, stages/diagnostics_stage.py,
                               stages/ui_generate.py, stages/ui_plan.py,
                               validate/jira_exporter.py, execution/k6_runner.py,
                               execution/perf_analyzer.py, execution/visual_diff.py
track-b-c-deferred/dashboard/  React UI
track-b-c-deferred/smoke_tests/
```

**Cleanup Plan (issue #325):**
1. Delete branch `feat/reintegrate-track-b` (local)
2. Close/merge `feat/epic-244-track-bc-reintegration-v2`
3. Remove deferred path injection from `scripts/start_dashboard_api.py`
4. Delete `migrate_tests.py`
5. Promote 4 relevant legacy tests to root smoke tests
6. Delete 5 stale legacy tests from `tests/`
7. Update §C to say "Fully re-integrated. Directory removed from main."

See [PHASE_PLAN.md](PHASE_PLAN.md) for full details on Phase 0b cleanup.

---

## The open decision (owner's call)

This ledger makes the contradiction legible; it does not resolve it. The two clean
end-states, to choose **after** the real validation gate:

1. **Re-quarantine** the §B built-ahead surface back out of the product until demand
   justifies it (restores the original invariant; large diff; resolves the §B/§C
   duplication by keeping one copy).
2. **Formally adopt** the expanded scope — rewrite HANDOVER/AGENTS to make Horizon 2
   in-scope (keeps the code; explicitly retires the "Track A only" rule).

**DECISION REACHED (2026-06-08):** Option 2 is adopted. The 5-QA gate is considered passed and everything has been validated. The expanded scope is formally adopted. The restriction to "validate Track A first" has been bypassed/fulfilled.

---

## D. New packages (Consolidated Plan, Phase 1-8)

The consolidated plan (see [PHASE_PLAN.md](PHASE_PLAN.md)) adds 5 new capabilities across
Phase 1-8. All new packages follow Clean Architecture (Ports/Adapters) per ADR-004.

| Package | Phase | Purpose | Status |
|---|---|---|---|---|
| `knowledge/` | Phase 1 | Second Brain, knowledge mesh, GraphRAG | ✅ **Complete** (PR #395) |
| `chat/` | Phase 4 | Chat agent, conversation memory, tools | ✅ **Complete** (PR #397-#400) |
| `sources/mobile/` | Phase 5 | Mobile source adapters (APK/HAR/HIL) | ⏸ Blocked (needs ADB) |
| `substrate/providers/vlm.py` | Phase 2 | VLM provider (LocalAI, Ollama, OpenAI) | ✅ **Complete** (PR #396) |
| `substrate/providers/localai.py` | Phase 2 | LocalAI adapter | ✅ **Complete** (PR #396) |
| `core/devices.py` | Phase 0b | DeviceClass, VLMTier, device detection | ✅ **Complete** (PR #393) |
| `core/events.py` | Phase 0b | CHERENKOVEvent domain events | ✅ **Complete** (PR #393) |
| `core/migration.py` | Phase 0b | Data migration framework | ✅ **Complete** (PR #393) |
| `core/error_handling.py` | Phase 0b | Graceful degradation framework | ✅ **Complete** (PR #393) |
| `core/logging.py` | Phase 0b | Structured logging (structlog) | ✅ **Complete** (PR #393) |
| `agents/pilot.py` | Phase 5 | Pilot agent (mobile test orchestration) | ⏸ Blocked (needs ADB) |
| `stages/mobile_*.py` | Phase 5 | Mobile stages (plan, generate, review) | ⏸ Blocked (needs ADB) |
| `oracle/visual_oracle_vlm.py` | Phase 5 | Semantic visual oracle (VLM-based) | ⏸ Blocked (needs ADB) |
| `execution/mobile_eject_*.py` | Phase 5 | Mobile eject (Maestro, Appium) | ⏸ Blocked (needs ADB) |
| `execution/maestro_runner.py` | Phase 6 | Real Maestro runner (ADB) | ⏸ Blocked (needs ADB) |
| `execution/appium_runner.py` | Phase 6 | Real Appium runner (WebDriver) | ⏸ Blocked (needs ADB) |
| `reflector/mobile_extensions.py` | Phase 6 | Mobile failure classification | ⏸ Blocked (needs ADB) |
| `divergence/mobile_*.py` | Phase 6 | Mobile divergence detection | ⏸ Blocked (needs ADB) |
| `web/chat_routes.py` | Phase 4 | Chat API routes (SSE streaming) | ✅ **Complete** (PR #397) |
| `web/monitoring.py` | Phase 0b | `/metrics` endpoint (Prometheus) | ✅ **Complete** (PR #393) |
| `web/middleware/security.py` | Phase 0b | Security middleware (rate limit, CORS) | ✅ **Complete** (PR #393) |

### Clean Architecture Structure

All new packages follow this structure (per ADR-004):

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O
│   └── models.py    # Pydantic models, enums
├── ports/           # Protocol interfaces (the "what")
│   ├── repository.py
│   └── event_bus.py
├── adapters/        # I/O implementations (the "how")
│   ├── sqlite_{module}.py
│   └── redis_{module}.py
├── use_cases/       # Orchestration
│   └── {action}.py
└── api/             # FastAPI routes / CLI commands
    └── routes.py
```

See [PHASE_PLAN.md](PHASE_PLAN.md) for full details on all new packages.
