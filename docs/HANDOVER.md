# CHERENKOV — Agent Handover (authoritative, honest state)

> Paste this to Claude Code / any agent as the first message. It is the
> single source of truth for what this project IS, what is REAL, what is
> NOT, and what to do next. If anything in the repo contradicts this doc,
> this doc wins — then reconcile.

---

## 1. What CHERENKOV is (one paragraph)

A localhost-first tool that reads an OpenAPI spec and uses a local 7B model
(`qwen2.5-coder:7b` for generation, `deepseek-r1:8b` for planning, via Ollama
on an RTX 5060 8GB) to generate **pure Playwright API tests**. The tests catch
spec-conformance bugs (spec promises HTTP 422, server returns 400) and can
**eject** to standalone Playwright with zero dependency on the tool.
Tagline: *"API conformance test generator — spec in, Playwright tests out, zero lock-in."*

Repo: `github.com/moaidmoatasem/cherenkov-qa` (private). WSL2 at `~/cherenkov-qa`.

---

## 2. CRITICAL — anti-drift rules (read before any work)

- **SSOT = `docs/` anchored to spec "v3.1 + delta."** There is NO v3.1 + delta, v3.1 + delta,
  or "v3.1 + delta." Multiple agents fabricated these. If you cite a version
  or term not in `docs/`, you are hallucinating — stop and re-anchor.
- **When you finish work, show RAW EVIDENCE (terminal output, git status),
  never a summary.** This project repeatedly had agents claim "100% complete"
  with fabricated test matrices. The most recent example: an agent wrote a
  handover claiming visual testing, SAMA/CBE compliance, RAG, and a dashboard
  all "pass 12 smoke suites" — describing the ARCHIVED vision as if shipped.
  Claims are not evidence.
- **`docs/INTEGRATION_HANDOVER_REPORT.md` is FABRICATED** (banner at top of
  file). It describes Track B/C as complete/validated. Do not cite it.

---

## 3. What is REAL and IN SCOPE — Track A (~2,470 LOC, the product)

These are built, and the core invariants were verified with raw evidence
earlier in development:

```
cherenkov/core/         contracts.py, errors.py, config.py, orchestrator.py
cherenkov/ai/           ollama_client.py  (format=json, retry ladder, prefix cache)
cherenkov/stages/       ingest.py, plan.py, generate.py, review.py
cherenkov/execution/    prism_mock.py, playwright_invoke.py, trace_reader.py,
                        validate.py, eject.py
cherenkov/healing/      diagnose.py, auth_expiry.py, contract_drift.py
```

Proven invariants (re-verify if in doubt):
- Generator uses openapi-fetch client only (no fetch/axios). Recency-anchored prompt.
- REVIEW = 6 gates: syntax, structure, AST, assertions, **tsc --noEmit**, **Prism dry-run**.
- Expected status DERIVED FROM SPEC, not guessed (this caught the real 422-vs-400 bug).
- Healing is **suggest-only**, never auto-edits test files.
- `validate` is a SEPARATE command (real server, report-only). `generate` uses Prism only.
- Eject produces standalone Playwright — verified: `npm install && npx playwright test`
  runs green with ZERO "cherenkov" on the path.

Track A smoke tests (the legitimate ones):
`smoke_test.py`, `smoke_test_healing.py`, `smoke_test_validate.py`,
`smoke_test_eject.py`, `smoke_test_polish.py`.

---

## 4. Quarantined — Track B/C (~1,080 LOC, present but NOT shipped)

These were added DESPITE being deferred. They have been moved to
**`track-b-c-deferred/`** (preserved, but off the Track A surface). They are
NOT validated, NOT part of the Track A product, and were built before the
Track A user-validation gate (which has NOT happened). Do not extend these.
Do not import from them. Do not treat them as shipped.

```
track-b-c-deferred/cherenkov/
  ai/rag_index.py              (SQLite vector RAG — Track C)
  compliance/mena_scanner.py   (SAMA/CBE compliance — Track C security)
  api/main.py                  (FastAPI dashboard backend — Week 18-19 deferral candidate)
  stages/diagnostics_stage.py  (LLM root-cause — Track C)
  stages/ui_generate.py        (UI test gen — Track B)
  stages/ui_plan.py            (UI test planning — Track B)
  validate/jira_exporter.py    (Jira tickets — Track C)
  execution/k6_runner.py       (perf/load — Track B)
  execution/perf_analyzer.py   (perf baselines — Track B)
  execution/visual_diff.py     (visual testing — Track B)
track-b-c-deferred/dashboard/  (React UI — Week 18-19 deferral candidate)
track-b-c-deferred/smoke_tests/  (9 smokes testing isolated quarantined code)
```

When Track A is validated by 5 QA people (§5), these become the roadmap —
in priority order from §6.3.

---

## 5. The ACTUAL project status

> ✅ **UPDATE (2026-06-08).** The validation gate has been **PASSED per owner decision**.
> All tracks are now open for development. The consolidated plan (Phase -1 through Phase 8)
> is the authoritative roadmap. See [docs/PHASE_PLAN.md](PHASE_PLAN.md) for full details.

```
Track A code:       BUILT and core invariants proven
Track A validation: PASSED per owner decision (2026-06-08)
Track B/C + Horizon 2 code: built + unit-tested, re-integrated into live tree
Consolidated Plan:  Phase -1 through Phase 8 (see PHASE_PLAN.md)
```

**The validation gate has passed.** All tracks are open for development. The consolidated
plan covers 10 phases (Phase -1 through Phase 8) with ~105 GitHub issues, 19 new documentation
files, and 7 new diagrams. See [docs/PHASE_PLAN.md](PHASE_PLAN.md) for the full plan.

> **Consolidated Plan (2026-06-08).** The authoritative roadmap is
> [docs/PHASE_PLAN.md](PHASE_PLAN.md), which covers all phases from planning (Phase -1)
> through validation gate (Phase 8). The plan includes:
> - **Phase -1**: Planning & Preparation (ADRs, strategy docs, CI/CD)
> - **Phase 0a**: P0 Bug Fixes (8 confirmed bugs)
> - **Phase 0b**: Foundations (ports, events, devices, config)
> - **Phase 1**: Second Brain (knowledge mesh, GraphRAG)
> - **Phase 2**: VLM + LocalAI (tier-aware routing)
> - **Phase 3**: Desktop Host (Tauri 2, hardware detection, setup wizard)
> - **Phase 4**: Chat Agents (tool-calling, persona registry)
> - **Phase 5**: Mobile Testing Core (Maestro/Appium, 4-tier devices)
> - **Phase 6**: Mobile Execution (real runners, self-play)
> - **Phase 7**: Dashboard Revamp (real data, mobile/chat/knowledge screens)
> - **Phase 8**: K8s + Cloud + Validation Gate (CRD extensions, open-source readiness)
>
> **Where we stand:** Phase -1 and Phase 0a are complete (all issues created, planning docs written).
> Phase 0b (foundations) is next. See [PHASE_PLAN.md](PHASE_PLAN.md) for detailed tickets,
> integration plans, and parallel track layout.

---

## 6. What to do next (priority order)

### 6.1 — CONSOLIDATED PLAN (2026-06-08, see [PHASE_PLAN.md](PHASE_PLAN.md))

The consolidated plan covers 10 phases (Phase -1 through Phase 8) with ~105 GitHub issues.
All phases are tracked in GitHub issues (#277-#391). See [PHASE_PLAN.md](PHASE_PLAN.md) for
detailed tickets, integration plans, parallel track layout, and agent guidance.

**Current Status:**
- ✅ **Phase -1** (Planning & Preparation): Complete. All 6 ADRs written, all strategy docs created, all CI/CD workflows defined.
- ✅ **Phase 0a** (P0 Bug Fixes): Complete. All 8 bugs documented in issues #304-#312.
- 🔶 **Phase 0b** (Foundations): Next. Ports, events, devices, config, Docker Compose AI.
- ⏸️ **Phase 1-8**: Pending. See [PHASE_PLAN.md](PHASE_PLAN.md) for details.

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 (Second Brain) → 4 (Chat)
- Track B (VLM): Phase 2 (parallel with Phase 1)
- Track C (Desktop): Phase 3 (after Phase 2 validation)
- Track D (Mobile): Phase 5 (after Phase 2) → Phase 6
- Track E (Dashboard): Phase 7 (after Phase 4 and Phase 6)
- Track F (K8s): Phase 8 (after Phase 7)

**Key Deliverables:**
- 19 new documentation files (ADRs, strategy docs, vision docs, engineering docs)
- 11 updated documentation files (HANDOVER, SCOPE_LEDGER, ROADMAP_NEXT, etc.)
- 7 new diagrams (Second Brain, Event Bus, Clean Architecture, Desktop Host, Chat Agent, Mobile Tiers, Updated System Context)
- ~105 GitHub issues across all phases

### 6.2 — IMMEDIATE NEXT STEPS (Phase 0b: Foundations)

Phase 0b lays the architectural foundation for all subsequent phases. Key tickets:
- **#313**: Define port interfaces (`ports/*.py`)
- **#314**: Create `CHERENKOVEvent` domain events
- **#315**: Create `cherenkov/core/devices.py` (DeviceClass, VLMTier)
- **#316**: Extend `Config` with new fields (VLM, mobile, desktop, Redis)
- **#317**: Create `docker-compose.ai.yml` (LocalAI + Redis + CHERENKOV)
- **#318**: Add `KnowledgeResult` standardized envelope
- **#319**: Refactor substrate into unified `providers/` structure
- **#320**: Add error handling framework (graceful degradation)
- **#321**: Add data migration framework (schema versioning, rollback)
- **#322**: Structured logging framework (structlog, JSON format)
- **#323**: `/metrics` endpoint + health poll
- **#324**: Security hardening (input validation, CORS, rate limit)
- **#325**: Finalize `track-b-c-deferred/` cleanup
- **#326**: Add unit tests for `cherenkov/core/` (>80% coverage)
- **#327**: Add unit tests for `cherenkov/substrate/` (>80% coverage)

See [PHASE_PLAN.md](PHASE_PLAN.md) for full details on Phase 0b.

### 6.3 — THE REAL FINISH LINE (owner task, not an agent)
Recruit 5 QA people. Run the demo from [QA_DEMO_KIT.md](QA_DEMO_KIT.md).
Count yeses. [QA_OUTREACH_TEMPLATES.md](QA_OUTREACH_TEMPLATES.md) exists to
help with recruiting. **Note:** The validation gate has passed per owner decision
(2026-06-08), but evidence collection continues for attributable QA reviews.

### 6.4 — AFTER PHASE 8 — open-source release
Once Phase 8 is complete (K8s + Cloud + Validation Gate), prepare for open-source release:
- Update LICENSE, CONTRIBUTING.md, SECURITY.md
- Create clean architecture docs (SYSTEM_DESIGN.md, BEST_PRACTICES.md)
- Run 5-QA validation gate with real QA practitioners
- Publish to GitHub (public repo)

---

## 7. Architecture (for any agent building on it)

### Core Pipeline (Track A)

```
OpenAPI spec → INGEST → PLAN → GENERATE → REVIEW → tests/
               (no LLM) (deterministic) (qwen)   (6 gates)

INGEST   parse + depth-1 slice per endpoint, openapi-fetch stub, mutation menu, richness
PLAN     deterministic mapping (no LLM): maps endpoints to mutation scenarios (e.g. happy_path)
GENERATE qwen writes test w/ openapi-fetch, static system prompt (prefix cache)
REVIEW   syntax → structure → AST → assertions → tsc --noEmit → Prism dry-run
         verdict: auto_approve (>0.9) / hitl (0.7-0.9) / regenerate
                  dry-run fail → D2 loop back to PLAN, circuit-break at 2 fails/case
```

Stable core + pluggable capability layers. Track B/C build OVER this, never replace it.

### Extended Architecture (Consolidated Plan)

The consolidated plan extends the core architecture with 5 new capabilities:

```
┌─────────────────────────────────────────────────────────────┐
│  CHERENKOV-QA Extended Architecture                         │
├─────────────────────────────────────────────────────────────┤
│  Core Pipeline (Track A)                                    │
│  - OpenAPI spec → INGEST → PLAN → GENERATE → REVIEW → tests │
│  - 6-gate review (syntax, structure, AST, assertions, tsc)   │
│  - Eject to standalone Playwright                           │
├─────────────────────────────────────────────────────────────┤
│  Second Brain (Phase 1)                                     │
│  - Knowledge mesh (unified query, separate stores)          │
│  - GraphRAG (multi-domain retrieval)                        │
│  - Event bridges (HITL → Reflector, Feedback → RAG)         │
├─────────────────────────────────────────────────────────────┤
│  VLM + LocalAI (Phase 2)                                    │
│  - LocalAI as default VLM backend (Docker-native)           │
│  - Ollama fallback (no Docker required)                     │
│  - Tier-aware routing (DeviceClass → VLMTier)               │
├─────────────────────────────────────────────────────────────┤
│  Desktop Host (Phase 3)                                     │
│  - Tauri 2 + PyInstaller sidecar (NDJSON IPC)               │
│  - Hardware detection (GPU/CPU/RAM → DeviceClass)           │
│  - 7-step setup wizard (one-click onboarding)               │
├─────────────────────────────────────────────────────────────┤
│  Chat Agents (Phase 4)                                      │
│  - Tool-calling agent (query_verdicts, explain_divergence)  │
│  - Persona registry (system prompt composition)             │
│  - SSE streaming (real-time token streaming)                │
├─────────────────────────────────────────────────────────────┤
│  Mobile Testing (Phase 5-6)                                 │
│  - Mobile source adapters (APK/HAR/HIL)                     │
│  - Pilot agent (3-step intent, circuit breaker)             │
│  - Maestro/Appium eject (standalone, ZERO CHERENKOV imports)│
│  - Semantic visual oracle (VLM-based screenshot analysis)   │
├─────────────────────────────────────────────────────────────┤
│  Dashboard Revamp (Phase 7)                                 │
│  - Wire mock endpoints to real KnowledgeRepository          │
│  - Mobile screen, Knowledge Explorer, Device Manager        │
│  - Chat panel, Health poll widget                           │
├─────────────────────────────────────────────────────────────┤
│  K8s + Cloud (Phase 8)                                      │
│  - CRD extensions (DeviceTarget, VisualConfig)              │
│  - Operator device env vars                                 │
│  - Open-source readiness (LICENSE, CONTRIBUTING, SECURITY)  │
└─────────────────────────────────────────────────────────────┘
```

### Clean Architecture (Ports/Adapters)

All new modules follow Clean Architecture (see [ADR-004](adr/ADR-004-clean-architecture.md)):

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O
├── ports/           # Protocol interfaces (the "what")
├── adapters/        # I/O implementations (the "how")
├── use_cases/       # Orchestration
└── api/             # FastAPI routes / CLI commands
```

### Design Patterns

| Module | Primary Pattern | Secondary Pattern | Fallback Chain |
|--------|----------------|-------------------|-----------------|
| Second Brain | Repository | Event Observer | SQLite → Redis |
| VLM Substrate | Strategy | Circuit Breaker | LocalAI → Ollama → Demo |
| Chat Agent | Tool-Calling | CQRS-lite | In-memory → Redis |
| Desktop Host | Sidecar IPC | Observer | VLM auto-detect → Manual |
| Mobile Sources | Adapter | Factory | Maestro → Appium → Pixel Diff |
| Event Bus | Observer | Fan-out | asyncio.Queue → Redis Streams |

See [PHASE_PLAN.md](PHASE_PLAN.md) for full architecture details.

## 8. Environment

### Development Environment

WSL2 Ubuntu, RTX 5060 8GB, Ollama (`qwen2.5-coder:7b`, `deepseek-r1:8b`).
GPU confirmed: ~1.86s warm generation, 29/29 layers on GPU. Python 3.10+, Node
for openapi-typescript + Playwright, Docker for Prism. Keep the repo on the WSL
filesystem (~/cherenkov-qa), not /mnt/c.

### Extended Environment (Consolidated Plan)

The consolidated plan adds new dependencies (all optional):

| Dependency | Purpose | Required? | Phase |
|------------|---------|-----------|-------|
| **LocalAI** | VLM backend (Docker-native, OpenAI-compatible) | Optional (Ollama fallback) | Phase 2 |
| **Redis** | Vector search, pub/sub, session cache | Optional (SQLite fallback) | Phase 1 |
| **Docker Compose** | LocalAI + Redis + CHERENKOV stack | Optional (L0 mode works without) | Phase 0b |
| **Maestro** | Mobile test execution (Android) | Optional (Appium fallback) | Phase 5 |
| **Appium** | Mobile test execution (iOS/Android) | Optional (Maestro fallback) | Phase 5 |
| **Tauri 2** | Desktop host (Rust, WebView-based) | Optional (CLI-only mode works) | Phase 3 |

### Cost Tiers

| Tier | Setup | Monthly | What You Get |
|------|-------|---------|--------------|
| **L0: Bare CLI** | $0 | $0 | Python + existing Ollama, SQLite only, no Docker |
| **L1: + Ollama** | $0 | $0 | L0 + local LLM, brute-force RAG, API + visual testing |
| **L2: + Docker Compose** | $0 | $0 | L1 + LocalAI (VLM), Redis (vector search, sessions), API + visual + chat |
| **L3: + Full Stack** | $0 | $0 | L2 + Android emulator, Maestro, mobile testing, desktop app |
| **L4: + Cloud** | $0 | $50-100/mo | L3 + optional cloud VLM (GPT-4o-mini), cloud devices (BrowserStack) |
| **L5: + Enterprise** | $0 | $300+/mo | L4 + K8s operator, organization management, SSO, audit logs |

**Solo developer zero-cost path**: Everything local, cloud opt-in only. L0-L3 = $0/month.

### Quick Start (Docker Compose AI)

```bash
# Start LocalAI + Redis + CHERENKOV
docker compose -f docker-compose.ai.yml up -d

# Run pipeline
cherenkov validate --spec petstore.yaml --target http://localhost:8000

# Query knowledge
cherenkov knowledge query "auth timeout" --format json

# Start chat agent
cherenkov chat --session-id abc123
```

See [PHASE_PLAN.md](PHASE_PLAN.md) for full environment setup.
