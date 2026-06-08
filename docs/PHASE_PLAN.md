# CHERENKOV-QA: Consolidated Phase Plan

**Date:** 2026-06-08  
**Status:** Active  
**SSOT for:** All phases, tickets, integration plans, parallel tracks, architecture decisions, design patterns, agent guidance

---

## Executive Summary

This document is the **Single Source of Truth (SSOT)** for the CHERENKOV-QA consolidated plan. It covers all phases from planning (Phase -1) through validation gate (Phase 8), with detailed tickets, integration plans, parallel tracks, and agent guidance.

**Total Scope:**
- 10 phases (Phase -1 through Phase 8)
- ~105 GitHub issues
- 19 new documentation files
- 11 updated documentation files
- 7 new diagrams
- 15 new GitHub labels

---

## Architecture Overview

### Clean Architecture Per Module

Every new feature module follows the same structure:

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O, no external deps
│   └── models.py    # Pydantic models, enums, value objects
├── ports/           # Protocol interfaces (the "what", not the "how")
│   ├── repository.py
│   └── event_bus.py
├── adapters/        # I/O implementations
│   ├── sqlite_{module}.py   # Default adapter
│   └── redis_{module}.py     # Upgrade adapter
├── use_cases/       # Orchestration of domain + ports
│   └── {action}.py
└── api/             # Thin FastAPI routes / CLI commands
    └── routes.py
```

### Design Patterns Per Module

| Module | Primary Pattern | Secondary Pattern | Fallback Chain |
|--------|----------------|-------------------|-----------------|
| Second Brain | Repository | Event Observer | SQLite → Redis |
| VLM Substrate | Strategy | Circuit Breaker | LocalAI → Ollama → Demo |
| Chat Agent | Tool-Calling | CQRS-lite | In-memory → Redis |
| Desktop Host | Sidecar IPC | Observer | VLM auto-detect → Manual |
| Mobile Sources | Adapter | Factory | Maestro → Appium → Pixel Diff |
| Event Bus | Observer | Fan-out | asyncio.Queue → Redis Streams |

### Extension Points (Openness for Future Testing Types)

The Source Adapter SPI is the key extension mechanism:

```
Current: OpenAPI spec source → API conformance tests
Future: AccessibilitySource → WCAG audit tests
Future: SecuritySource → DAST/OWASP tests  
Future: PerformanceSource → Load/stress tests
Future: GraphQLSource → GraphQL conformance
Future: gRPCSource → gRPC conformance
Future: MobileSource → App/Device testing
```

Each new source type plugs in via:
1. Implement SourceAdapter protocol (parse, generate scenarios)
2. Add corresponding Stage (plan, generate, review)
3. Add corresponding Oracle (validation)
4. No core modifications needed

---

## Parallel Track Layout

```
TRACK A (Core):     Phase -1 → 0a → 0b → 1 (Second Brain) ----→ 4 (Chat)
                                                                      ↓
TRACK B (VLM):               ┌────── 2 (VLM+LocalAI) ──────────────┤
                              ↓                                      ↓
TRACK C (Desktop):                    ┌── 3 (Desktop) ──────────────┤
                                       ↓                            ↓
TRACK D (Mobile):                     5 (Mobile Core) → 6 (Mobile Exec) ↓
                                                                    ↓
TRACK E (Dashboard):                             7 (Dashboard Revamp) ↓
                                                                    ↓
TRACK F (K8s):                                8 (K8s + Cloud + Gate) ↓
```

### Parallel Execution Windows

| Week | Track A | Track B | Track C | Track D | Track E | Track F |
|------|---------|---------|---------|---------|---------|---------|
| 1-2 | Phase -1, 0a, 0b | - | - | - | - | - |
| 3-5 | Phase 1 (Second Brain) | Phase 2 (VLM) | - | - | - | - |
| 5-8 | Phase 4 (Chat) (starts Wk 9) | - | Phase 3 (Desktop) | Phase 5 (Mobile Core) | - | - |
| 9-10 | Phase 4 (Chat) | - | - | - | - | - |
| 11-14 | - | - | - | Phase 6 (Mobile Exec) | - | K8s fixes |
| 14-16 | - | - | - | - | Phase 7 (Dashboard) | - |
| 16-20 | - | - | - | - | - | Phase 8 (K8s+Gate) |

---

## Integration Plan

### Cross-Phase Dependencies (Hard)

```
Phase -1 ──→ Phase 0a ──→ Phase 0b ──┬──→ Phase 1 ──→ Phase 4
                                      ├──→ Phase 2 ──┬──→ Phase 3
                                      │              ├──→ Phase 5 ──→ Phase 6
                                      │              └──→ (VLM used by Phase 5)
                                      └──→ (Foundations used by all)
Phase 4 ──→ Phase 7 ──→ Phase 8
Phase 6 ──→ Phase 7 (mobile screen needs mobile core)
Phase 3 ──→ Phase 7 (desktop needs to exist for dashboard)
```

### Cross-Phase Integration Points

| From | To | Integration | Test |
|------|-----|-------------|------|
| Phase 0b (Events) | Phase 1 (Second Brain) | `CHERENKOVEvent` published from HITL → consumed by KnowledgeRepository | Event publish + subscribe round-trip test |
| Phase 0b (Ports) | Phase 2 (VLM) | `VLMProvider` port defined in Phase 0b, implemented in Phase 2 | Port contract test passes for both adapters |
| Phase 1 (Knowledge) | Phase 4 (Chat) | Chat agent calls `KnowledgeRepository.query()` | `query_verdicts` tool returns real results |
| Phase 2 (VLM) | Phase 5 (Mobile) | Semantic visual oracle uses VLM for mobile screenshots | VLMProvider can analyze mobile screenshots |
| Phase 1 (Knowledge) | Phase 7 (Dashboard) | Dashboard shows real knowledge data | `/overview`, `/truth-map` return non-mock data |
| Phase 4 (Chat) | Phase 7 (Dashboard) | ChatPanel shows streaming chat | SSE endpoint works with ChatAgent |
| Phase 5 (Mobile) | Phase 7 (Dashboard) | MobileScreen shows pilot traces | Mobile traces appear in dashboard |
| Phase 0a (Bug fix) | All | All 8 bugs must be fixed before foundations merge | `pytest tests/unit/` + `pytest tests/smoke/` green |
| Phase 8 (K8s) | All | CRD extensions don't break existing deployment | `make k3d-test` green |

### Integration Testing Strategy

For every cross-phase integration point:
1. **Contract test**: Both sides agree on the Protocol interface
2. **Adapter test**: Each adapter (SQLite, Redis) passes the same contract
3. **Smoke test**: End-to-end happy path
4. **Degradation test**: Remove one dependency, verify graceful fallback

---

## Phase-by-Phase Summary

### Phase -1: Planning & Preparation (Days 1-2)

**EPIC:** #277  
**Tickets:** #290-#303 (14 issues)  
**Goals:** Establish architectural foundation, strategy documents, CI/CD pipeline  
**Kill Criteria:**
- All 6 ADRs exist in `docs/adr/`
- All 4 strategy docs exist in `docs/`
- CI/CD workflows exist in `.github/workflows/`
- HANDOVER.md, SCOPE_LEDGER.md, ROADMAP_NEXT.md updated
- Gate status consistent across all 5 governing docs

**Key Deliverables:**
- ADR-001: Seam-widening architecture (#290)
- ADR-002: Tauri 2 + PyInstaller sidecar (#291)
- ADR-003: LocalAI as default LLM (#292)
- ADR-004: Clean Architecture ports/adapters (#293)
- ADR-005: Event-driven architecture (#294)
- ADR-006: Knowledge mesh (#295)
- Testing strategy (#296)
- Migration strategy (#297)
- Error handling strategy (#298)
- Assumptions (#299)
- CI/CD workflows (#300)
- Logging strategy (#301)
- Gate reconciliation (#302)
- Performance baselines (#303)

### Phase 0a: P0 Bug Fixes (Days 3-5)

**EPIC:** #278  
**Tickets:** #304-#312 (9 issues)  
**Goals:** Fix all 8 confirmed P0 bugs before any new features land  
**Kill Criteria:**
- `pytest tests/unit/` passes
- `pytest tests/smoke/` passes
- All 8 bugs verified fixed with raw evidence
- No new features added (bug fixes only)

**P0 Bugs:**
1. `run_pipeline()` processes only first scenario (#304)
2. `get_stats()` mutates state via `decay_all_idioms()` (#305)
3. 4 mock API endpoints return hardcoded data (#306)
4. HITL decisions don't feed Reflector (#307)
5. Stats only go to stdout, not persisted (#308)
6. Two review servers coexist (ports 8080+8000) (#309)
7. Healing suggestions are text-only (#310)
8. `truth/` missing `__init__.py` — package not importable (#311)
9. Backwards compatibility smoke test for CLI commands (#312)

### Phase 0b: Foundations (Week 2)

**EPIC:** #279  
**Tickets:** #313-#327 (15 issues)  
**Goals:** Lay architectural foundation for all subsequent phases  
**Kill Criteria:**
- `pytest tests/unit/` passes
- `pytest tests/contracts/` passes
- All port interfaces defined and type-check
- Docker Compose AI stack starts successfully
- `/healthz` and `/metrics` endpoints working

**Key Deliverables:**
- Port interfaces (#313)
- Domain events (#314)
- Device classes (#315)
- Config extensions (#316)
- Docker Compose AI (#317)
- KnowledgeResult envelope (#318)
- Substrate refactor (#319)
- Error handling framework (#320)
- Migration framework (#321)
- Structured logging (#322)
- `/metrics` endpoint (#323)
- Security hardening (#324)
- Deferred cleanup (#325)
- Core unit tests (#326)
- Substrate unit tests (#327)

### Phase 1: Second Brain (Weeks 3-5)

**EPIC:** #280  
**Tickets:** #328-#337 (10 issues)  
**Goals:** Build knowledge mesh that powers all subsequent phases  
**Kill Criteria:**
- `pytest tests/unit/test_knowledge_repository.py` passes
- `pytest tests/contracts/` passes for both SQLite and Redis adapters
- `cherenkov knowledge query "auth timeout"` returns real results
- Truth Model survives app restart

**Key Deliverables:**
- Knowledge domain models (#328)
- KnowledgeRepository port (#329)
- SQLite adapter (#330)
- Redis adapter (#331)
- GraphRAG (#332)
- HITL → Reflector bridge (#333)
- Feedback → RAG bridge (#334)
- agent_memory → RAG bridge (#335)
- Knowledge query CLI (#336)
- Truth Model persistence (#337)

### Phase 2: VLM + LocalAI (Weeks 3-4, parallel with Phase 1)

**EPIC:** #281  
**Tickets:** #338-#344 (7 issues)  
**Goals:** Integrate LocalAI as default VLM backend, add tier-aware routing  
**Kill Criteria:**
- Tauri 2 prototype opens on Windows + macOS + Linux
- LocalAI VLM request returns result in <10s on 1280×720 PNG
- Router selects correct provider for each device class
- `cherenkov doctor --vlm --localai` shows tier recommendation

**Key Deliverables:**
- Tauri 2 validation sprint (#338)
- LocalAI adapter (#339)
- Tier-aware routing (#340)
- LocalAI Docker integration (#341)
- `/healthz` endpoint (#342)
- Launcher extensions (#343)
- Doctor --vlm --localai (#344)

### Phase 3: Desktop Host (Weeks 5-8)

**EPIC:** #282  
**Tickets:** #345-#353 (9 issues)  
**Goals:** Build desktop host for one-click onboarding  
**Kill Criteria:**
- Desktop app opens on Windows + macOS + Linux
- Setup wizard completes in <10 clicks, <5 minutes
- Hardware detection returns correct DeviceClass on each OS
- Settings persist to `cherenkov.toml`

**Key Deliverables:**
- Tauri 2 prototype validation (#345)
- Full main.rs rewrite (#346)
- Hardware detection (#347)
- OS-specific setup (#348)
- 7-step setup wizard (#349)
- DeviceManager screen (#350)
- Settings screen (#351)
- Desktop packaging (#352)
- Tauri IPC protocol (#353)

### Phase 4: Chat Agents (Weeks 9-10)

**EPIC:** #283  
**Tickets:** #354-#361 (8 issues)  
**Goals:** Build chat agent with tool-calling for knowledge access  
**Kill Criteria:**
- `pytest tests/unit/test_chat_agent.py` passes
- Chat agent answers "why was this test rejected?" using Reflector idioms
- SSE client receives incremental tokens
- Rate limiting returns 429 when exceeded

**Key Deliverables:**
- ConversationMemory (#354)
- PersonaRegistry (#355)
- QAChatAgent (#356)
- CHERENKOV tools (#357)
- SSE streaming (#358)
- Rate limiting (#359)
- ChatPanel React component (#360)
- MCP knowledge tools (#361)

### Phase 5: Mobile Testing Core (Weeks 5-10, parallel tail)

**EPIC:** #284  
**Tickets:** #362-#370 (9 issues)  
**Goals:** Build mobile testing core (sources, pilot, stages, eject)  
**Kill Criteria:**
- `pytest tests/unit/test_mobile_source_adapter.py` passes
- Pilot agent completes 3-step intent with terminal DONE
- Maestro YAML generation produces valid format with ZERO CHERENKOV imports
- Semantic visual oracle passes anti-reward-hacking gate

**Key Deliverables:**
- Mobile source adapters (#362)
- Ingest mobile dispatch (#363)
- Pilot agent stub (#364)
- Mobile stages (#365)
- Mobile RAG index (#366)
- SemanticVisualOracle (#367)
- Maestro eject (#368)
- Appium eject (#369)
- MobilePilotScreen (#370)

### Phase 6: Mobile Execution (Weeks 11-14)

**EPIC:** #285  
**Tickets:** #371-#376 (6 issues)  
**Goals:** Replace stubs with real execution, self-play validation  
**Kill Criteria:**
- `make mobile-smoke` passes with Android emulator
- ADB commands work, screenshots captured
- Mobile failures classified correctly (mobile_bug, mobile_flaky, mobile_env)
- Self-play gate works for mobile screenshots

**Key Deliverables:**
- Real MaestroRunner (#371)
- AppiumRunner (#372)
- Mobile Reflector extensions (#373)
- Mobile skeptic hypothesizer (#374)
- Mobile self-play gate (#375)
- Mobile smoke tests (#376)

### Phase 7: Dashboard Revamp (Weeks 14-16)

**EPIC:** #286  
**Tickets:** #377-#385 (9 issues)  
**Goals:** Wire dashboard to real data, add mobile/chat/knowledge screens  
**Kill Criteria:**
- `npx playwright test tests/e2e/` passes on all screens
- `/overview`, `/truth-map`, `/failures`, `/metrics` return real data
- No screen shows mock data without a MOCK DATA badge
- "Initialize Pilot Run" triggers `POST /api/v1/run` end-to-end
- 0 instances of `console.warn` in production code

**Key Deliverables:**
- Wire mock endpoints (#377)
- MOCK DATA badges (#378)
- Pilot Run button (#379)
- Toast notifications (#380)
- MobileScreen (#381)
- KnowledgeExplorer (#382)
- DeviceManagerScreen (#383)
- ReviewScreen mobile+chat (#384)
- Health poll widget (#385)

### Phase 8: K8s + Cloud + Validation Gate (Weeks 16-20)

**EPIC:** #287  
**Tickets:** #386-#391 (6 issues)  
**Goals:** Fix K8s, extend CRDs, open-source readiness, 5-QA validation gate  
**Kill Criteria:**
- `make k3d-up && make k3d-test` green
- kubectl apply succeeds with device_target in spec
- LICENSE, CONTRIBUTING.md, SECURITY.md present and current
- ≥5 attributable "yes" verdicts in evidence ledger (including ≥1 mobile and ≥1 chat)
- New contributor can add an adapter in <30 minutes using docs alone

**Key Deliverables:**
- K8s Phase 0 fixes (#386)
- CRD extensions (#387)
- Operator device env vars (#388)
- Open-source readiness (#389)
- 5-QA validation gate (#390)
- Clean architecture docs (#391)

---

## Documentation Plan

### New Documents to Create (19 files)

| # | File | Content Summary |
|---|------|-----------------|
| 1 | `docs/adr/ADR-001-seam-widening.md` | Decision: extend Substrate/Stages/Oracle, not separate mobile/ module |
| 2 | `docs/adr/ADR-002-tauri2-sidecar.md` | Decision: Tauri 2 + PyInstaller sidecar with NDJSON IPC |
| 3 | `docs/adr/ADR-003-localai-default.md` | Decision: LocalAI default, Ollama fallback, demo mode |
| 4 | `docs/adr/ADR-004-clean-architecture.md` | Decision: Protocol interfaces, domain/ports/adapters layout |
| 5 | `docs/adr/ADR-005-event-driven.md` | Decision: asyncio.Queue → Redis Streams, not Airflow |
| 6 | `docs/adr/ADR-006-knowledge-mesh.md` | Decision: unified query, separate stores, KnowledgeResult envelope |
| 7 | `docs/TESTING.md` | Testing pyramid, kill criteria per phase, auto-skip rules |
| 8 | `docs/MIGRATION.md` | Schema versioning, v1→v2 scripts, idempotent rules |
| 9 | `docs/ERROR_HANDLING.md` | Degradation matrix, /healthz, structured errors |
| 10 | `docs/ASSUMPTIONS.md` | Team size, hardware, OS, cost, deps |
| 11 | `docs/INTEGRATION_PLAN.md` | Cross-phase dependencies, integration testing, parallel tracks |
| 12 | `docs/PHASE_PLAN.md` | SSOT for all phases, tickets, acceptance criteria, design patterns |
| 13 | `docs/vision/15_SECOND_BRAIN.md` | Second Brain architecture, GraphRAG, knowledge mesh |
| 14 | `docs/vision/16_CHAT_AGENT.md` | Chat agent architecture, tool-calling, persona registry |
| 15 | `docs/vision/17_MOBILE_TESTING.md` | Mobile testing architecture, 4-tier devices, Maestro-first |
| 16 | `docs/vision/18_DESKTOP_HOST.md` | Tauri 2 host architecture, setup wizard, hardware detection |
| 17 | `docs/engineering/SYSTEM_DESIGN.md` | (Fill missing) System layout, data stores, contracts, RCA |
| 18 | `docs/engineering/BEST_PRACTICES.md` | (Fill missing) Coding, testing, error-handling, logging, security |
| 19 | `docs/LOGGING.md` | Logging strategy, structured logs, correlation IDs |

### Existing Documents to Update (11 files)

| # | File | Update |
|---|------|--------|
| 1 | `docs/HANDOVER.md` | Update §5 (project status with Phase -1 through 8), §6 (consolidated next steps), §7 (expand architecture for all new modules), §8 (update environment for Docker+LocalAI) |
| 2 | `docs/SCOPE_LEDGER.md` | Add §D (new packages: knowledge/, chat/, sources/mobile/, substrate/providers/vlm.py, devices.py). Update §B for Phase 0a bug fixes. |
| 3 | `docs/ROADMAP_NEXT.md` | Add Phase -1 (Planning), Phase 0a (Bug Fixes), Phase 0b (Foundations). Restructure Waves 2-5 into Phases 1-8. |
| 4 | `docs/diagrams/DIAGRAMS.md` | Add 7 diagrams: Second Brain, Event Bus, Clean Architecture, Desktop Host, Chat Agent, Mobile Tiers, Updated System Context |
| 5 | `docs/vision/01_ARCHITECTURE.md` | Add L0.5 (Knowledge), L1.5 (Chat Agent), L3.5 (Mobile) layers. Update system context for new capabilities. |
| 6 | `docs/vision/09_WIRING_SCHEMA.md` | Add new seams: knowledge/v1, chat/v1, mobile/eject/v1, vlm/v1. Update dependency matrix. |
| 7 | `docs/engineering/README.md` | Add links to ADR-001→006, TESTING.md, MIGRATION.md, ERROR_HANDLING.md, ASSUMPTIONS.md. |
| 8 | `docs/engineering/ARCHITECTURE_PRINCIPLES.md` | Add principle #11 (Graceful Degradation), #12 (Open for Extension), #13 (Knowledge Mesh). |
| 9 | `README.md` | Update "What's Next" section with consolidated plan. Add Second Brain, Chat, Mobile sections. |
| 10 | `AGENTS.md` | Update Track Status with Phase -1→8 structure. |
| 11 | `docs/LOGGING.md` | Add logging strategy (log levels, JSON format, correlation IDs) |

---

## Diagram Plan

### 7 New Diagrams to Add to `docs/diagrams/DIAGRAMS.md`

1. **Second Brain Architecture** — KnowledgeRepository + EventBus + GraphRAG + 5 stores
2. **Event Bus Flow** — asyncio.Queue → Redis Streams, event types, subscribers
3. **Clean Architecture Module** — domain/ports/adapters/use_cases/api structure
4. **Desktop Host IPC** — Tauri 2 window ← NDJSON → PyInstaller sidecar → CHERENKOV CLI
5. **Chat Agent Flow** — QAChatAgent ← tool calls → KnowledgeRepository, SSE → UI
6. **Mobile Testing Tiers** — Browser Emulation → Android Emulator → iOS Simulator → Physical Device
7. **Updated System Context** — All new capabilities (Desktop, Mobile, Chat, Second Brain, VLM, K8s)

---

## GitHub Labels Created (17 labels)

| Label | Color | Description |
|-------|-------|-------------|
| `phase--1` | `bfd4f2` | Phase -1: Planning and preparation |
| `phase-0a` | `e99695` | Phase 0a: Critical bug fixes |
| `phase-0b` | `fef2c0` | Phase 0b: Clean architecture foundations |
| `phase-1` | `c5def5` | Phase 1: Second Brain |
| `phase-2` | `bfd4f2` | Phase 2: VLM + LocalAI |
| `phase-3` | `d4c5f9` | Phase 3: Desktop Host |
| `phase-4` | `5319e7` | Phase 4: Chat Agents |
| `phase-5` | `fbca04` | Phase 5: Mobile Testing Core |
| `phase-6` | `f9d0c4` | Phase 6: Mobile Execution |
| `phase-7` | `006b75` | Phase 7: Dashboard Revamp |
| `phase-8` | `0e8a16` | Phase 8: K8s + Cloud + Gate |
| `second-brain` | `1d76db` | Second Brain / Knowledge Repository |
| `chat-agent` | `5319e7` | Chat Agent and tool calling |
| `desktop-host` | `0e8a16` | Tauri 2 desktop host |
| `vlm` | `d93f0b` | Vision Language Model integration |
| `mobile-testing` | `fbca04` | Mobile testing (Maestro/Appium) |
| `p0-bug` | `b60205` | Confirmed P0 bug from audit |

---

## Agent Guidance

### For Agents Picking Up Tickets

1. **Read this document first** (PHASE_PLAN.md)
2. **Read the relevant ADR** for architectural decisions
3. **Read the EPIC issue** for phase context
4. **Read the detailed issue** for specific acceptance criteria
5. **Check dependencies** before starting (don't start Phase 1 before Phase 0b is complete)
6. **Follow Clean Architecture** (domain/ports/adapters/use_cases/api)
7. **Write tests first** (TDD: write failing test, then implement)
8. **Update documentation** as you go (don't leave it for later)
9. **Show raw evidence** (terminal output, screenshots, not summaries)
10. **Respect D7 invariant** (never auto-edit test code, suggest-only healing)

### Design Invariants (Non-Negotiable)

- **D7**: Never auto-edit test code. Validate and healing produce reports/suggestions only.
- **Anti-lock-in**: Tests must run without CHERENKOV (`eject` strips all imports).
- **Suggest-only healing**: Healing never auto-commits or auto-applies.
- **Spec-derived**: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions.

### Code Quality Standards

- **Type hints**: All functions must have type hints
- **Docstrings**: All public functions must have docstrings
- **Unit tests**: All new code must have unit tests
- **Coverage**: Maintain >80% coverage
- **Clean Architecture**: Follow domain/ports/adapters/use_cases/api structure
- **No circular imports**: Domain never imports from adapters or api

---

## Total Deliverables Summary

| Category | Count |
|----------|-------|
| GitHub Issues (EPICs) | 10 |
| GitHub Issues (Detailed) | ~95 |
| GitHub Issues (Total) | ~105 |
| New Documents | 19 |
| Updated Documents | 11 |
| New Diagrams | 7 |
| New Labels | 17 |
| P0 Bugs | 8 |

---

## Next Steps

1. **Immediate (Days 1-2):** Phase -1 (planning docs, ADRs, CI/CD)
2. **Days 3-5:** Phase 0a (fix 8 P0 bugs)
3. **Week 2:** Phase 0b (foundations: ports, events, devices, config)
4. **Weeks 3-5:** Phase 1 (Second Brain) + Phase 2 (VLM+LocalAI) in parallel
5. **Weeks 5-8:** Phase 3 (Desktop) + Phase 5 (Mobile Core) in parallel
6. **Weeks 9-10:** Phase 4 (Chat Agents)
7. **Weeks 11-14:** Phase 6 (Mobile Execution)
8. **Weeks 14-16:** Phase 7 (Dashboard Revamp)
9. **Weeks 16-20:** Phase 8 (K8s + Validation Gate)

---

**This document is the SSOT. All agents should reference it when picking up tickets.**
