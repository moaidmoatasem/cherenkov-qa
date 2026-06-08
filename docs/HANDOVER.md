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

## 4. Status of Track B/C and Horizon 2 (~1,080 LOC, re-integrated into the live tree)

> **⚠️ Superseded by [docs/STATUS.md](STATUS.md).** This section is kept for
> historical context. For the **current** status of every track and phase,
> read [docs/STATUS.md](STATUS.md) — that file is the single source of truth.

These modules were originally added under a separate `track-b-c-deferred/`
directory and quarantined. That directory has since been **fully
re-integrated into the live tree and deleted** (see
[AGENTS.md](../AGENTS.md)). All code now lives under `cherenkov/` and the
relevant subfolders.

**Current state of those modules:**
- Built, unit-tested, and re-integrated into the live tree.
- Rely on the Track A core pipeline; do not replace it.
- The 5-QA user-validation gate has been **passed per owner decision on
  2026-06-08** (see [docs/STATUS.md](STATUS.md) → "Phase status" and "Tracks"
  tables for the canonical state).

If you encounter references to `track-b-c-deferred/` elsewhere in the repo
(README, vision/, ROADMAP_*.md, etc.), treat them as **stale** and link
to [docs/STATUS.md](STATUS.md) instead.

---

## 5. The ACTUAL project status

> **Canonical status lives in [docs/STATUS.md](STATUS.md).** This file does
> not duplicate it; if the two disagree, [STATUS.md](STATUS.md) wins.

**Summary:**
- Track A code: **built** and core invariants proven.
- Track A 5-QA user-validation gate: **passed per owner decision on 2026-06-08.**
- Track B/C + Horizon 2: **built, unit-tested, re-integrated** into the live tree
  (`track-b-c-deferred/` was deleted; see [AGENTS.md](../AGENTS.md)).
- Active tracks: A (core), B (VLM), C (desktop), D (mobile), E (dashboard), F (K8s).
- Active phase work: Phase 8 (K8s + Cloud + Gate) is in progress; Phase 3
  (Desktop) and Phase 5–6 (Mobile) are blocked on `cargo` / ADB.
- The consolidated Phase -1 → 8 plan with tickets, parallel tracks, and
  agent guidance lives in [docs/PHASE_PLAN.md](PHASE_PLAN.md).
- All tickets (#277–#391) are tracked in GitHub.

For the full per-phase status table, the per-track state, and the
design invariants, read [docs/STATUS.md](STATUS.md).

---

## 6. What to do next (priority order)

> The per-phase status table and per-track state live in
> [docs/STATUS.md](STATUS.md). This section lists what to read first and
> where to focus next; it does not duplicate the status table.

### 6.1 — Read first

1. **[docs/STATUS.md](STATUS.md)** — canonical state of every phase and track.
2. **[docs/PHASE_PLAN.md](PHASE_PLAN.md)** — the consolidated Phase -1 → 8
   plan, parallel tracks, dependencies, and all ~105 GitHub issues (#277–#391).
3. **[docs/HANDOVER.md](HANDOVER.md)** — this file.
4. The relevant [ADR](adr/) before touching a module.
5. [engineering/BEST_PRACTICES.md](engineering/BEST_PRACTICES.md) before writing code.

**The plan in one sentence:** 10 phases (Phase -1 through Phase 8), 6 parallel
tracks (A core, B VLM, C desktop, D mobile, E dashboard, F K8s), ~105 GitHub
issues, 19 new docs, 7 new diagrams. Track A and Phase -1, 0a, 0b, 1, 2, 4, 7
are complete; Phase 8 is in progress; Phase 3 and 5–6 are blocked on `cargo` / ADB.

### 6.2 — IMMEDIATE NEXT STEPS (Phase 8: K8s + Cloud + Gate)

The active phase is **Phase 8**. Phase 0b, 1, 2, 4, and 7 are complete
(see [STATUS.md](STATUS.md) for the canonical state). Phase 8 needs `k3d`
on this host for tickets #386–#388. Tickets in flight:

- **#389 / #404**: `SECURITY.md` added.
- **#386–#388**: K8s CRD extensions + operator device env vars (needs `k3d`).
- **#390**: Final validation gate.
- **#391**: Open-source readiness docs.

See [PHASE_PLAN.md](PHASE_PLAN.md) for the full ticket list, dependencies,
and parallel-track layout.

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
