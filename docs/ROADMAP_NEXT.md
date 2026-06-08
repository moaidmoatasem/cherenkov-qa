# CHERENKOV — Forward Roadmap: "Consolidated Plan" (Horizon V)

**Date:** 2026-06-08 (consolidated plan) · **Status:** Authoritative for *what's next* (supersedes the disputed
[ROADMAP_RECONCILIATION.md](ROADMAP_RECONCILIATION.md) for forward planning). Pairs with
[HANDOVER.md](HANDOVER.md) (status), [SCOPE_LEDGER.md](SCOPE_LEDGER.md) (scope),
[PHASE_PLAN.md](PHASE_PLAN.md) (consolidated plan), and
[process/VALIDATION_EVIDENCE_LEDGER.md](process/VALIDATION_EVIDENCE_LEDGER.md) (the gate).

---

## 0. Status snapshot (2026-06-08)

Where we actually stand against the phases below. Anchored to closed GitHub issues, not claims.

| Phase | State | Evidence |
|-------|-------|----------|
| **Phase -1 — Planning & Preparation** | ✅ **Complete** | All 6 ADRs written (#290-#295), all strategy docs created (#296-#300), all CI/CD workflows defined (#301-#303). See [PHASE_PLAN.md](PHASE_PLAN.md). |
| **Phase 0a — P0 Bug Fixes** | ✅ **Complete** | All 8 P0 bugs documented in issues #304-#312. See [PHASE_PLAN.md](PHASE_PLAN.md). |
| **Phase 0b — Foundations** | ✅ **Complete** | Ports, events, devices, config, Docker Compose AI. Merged PR #393, #394. 66 assertions across 10 modules. |
| **Phase 1 — Second Brain** | ✅ **Complete** | Knowledge mesh, GraphRAG, event bridges. Merged PR #395. 20 files, 38 tests. |
| **Phase 2 — VLM + LocalAI** | ✅ **Complete** | LocalAI adapter, tier-aware routing, doctor CLI. Merged PR #396. 6 files, 29 tests. |
| **Phase 3 — Desktop Host** | ⏸ **Blocked** | Tauri 2, hardware detection, setup wizard. Needs `cargo` on this machine. |
| **Phase 4 — Chat Agents** | ✅ **Complete** | Tool-calling agent, persona registry, SSE streaming. Merged PR #397, #398, #399, #400. 57 tests. |
| **Phase 5 — Mobile Testing Core** | ⏸ **Blocked** | Maestro/Appium, 4-tier devices. Needs ADB/Maestro. |
| **Phase 6 — Mobile Execution** | ⏸ **Blocked** | Real runners, self-play. Depends on Phase 5. |
| **Phase 7 — Dashboard Revamp** | ✅ **Complete** | All 9 screens: DeviceManager, KnowledgeExplorer, HealthWidget, MobileScreen, ChatPanel, wire-up, badges, Pilot Run, Toast. Merged PR #401, #402, #405. |
| **Phase 8 — K8s + Cloud + Gate** | 🔶 **In Progress** | SECURITY.md added (#404). Remaining: #386-#388 (needs k3d), #390 (gate), #391 (docs). |

**Headline:** The consolidated plan (Phase -1 through Phase 8) is the authoritative roadmap.
All phases are tracked in GitHub issues (#277-#391). See [PHASE_PLAN.md](PHASE_PLAN.md) for
detailed tickets, integration plans, parallel track layout, and agent guidance.

**Validation gate:** PASSED per owner decision (2026-06-08). Evidence collection continues for
attributable QA reviews. See [HANDOVER.md §5](HANDOVER.md) for details.

---

## 1. Strategy in one paragraph

The consolidated plan (see [PHASE_PLAN.md](PHASE_PLAN.md)) extends CHERENKOV with 5 new
capabilities: Second Brain (knowledge mesh), VLM + LocalAI (tier-aware routing), Desktop Host
(Tauri 2, hardware detection), Chat Agents (tool-calling), and Mobile Testing (Maestro/Appium).
All new modules follow Clean Architecture (Ports/Adapters) per ADR-004. The plan covers 10 phases
(Phase -1 through Phase 8) with ~105 GitHub issues, 19 new documentation files, and 7 new diagrams.

> **The reframe:** CHERENKOV is no longer just an API conformance test generator. It's a full
> QA platform with knowledge mesh, chat agents, mobile testing, and desktop host — all built
> on the same Clean Architecture foundation.

---

## 2. The Golden Path (the meaningful E2E human workflow)

**Persona — "Sam", a QA/automation engineer.** Has an OpenAPI spec and a running staging server.
Lives in PRs and dashboards, not a Python REPL. Wants to catch API↔spec drift without hand-writing
tests, and to keep whatever tests are good — in *their* repo, no lock-in.

**Sam's 6-step journey (target: zero → first real finding in < 10 minutes):**

| # | Step | Command / surface | State today |
|---|------|-------------------|-------------|
| 1 | **Onboard** | `cherenkov init` + `cherenkov doctor` | ✅ exists; needs preflight polish |
| 2 | **Generate** | `cherenkov generate` (local LLM → Playwright) | ✅ pipeline exists |
| 3 | **Find drift** | `cherenkov validate --target <url>` | ✅ exists (the 422-vs-400 bug) |
| 4 | **Review (FE)** | `cherenkov review` → local web UI: approve / reject / classify / "why?" | ⚠️ backend+FE exist but mock-wired, quarantined |
| 5 | **Keep / own** | `cherenkov eject --output` (zero lock-in) | ✅ exists |
| 6 | **Watch drift** | nightly/CI re-run → deduped queue, no spam | ⚠️ daemon exists; needs honest wiring + reflector dedup |

**Friction audit (why it isn't "meaningful" yet):**
- **Review is terminal-only.** `cherenkov hitl approve <id>` is fine for an agent, hostile for a human.
  → **Fix:** the web review loop (step 4) is the heart of this horizon.
- **First run needs a GPU + Ollama.** Kills the demo on a laptop/Mac.
  → **Fix:** a no-Ollama demo mode (cached run on the bundled petstore target).
- **FE needs `npm install`.** A QA user shouldn't build a frontend.
  → **Fix:** ship a prebuilt `dist/`; `cherenkov review` serves it.
- **No empty/error/loading states** in the UI; mock data masks reality.
  → **Fix:** wire to the real `HitlQueue` + real validate findings; design honest states.

---

## 3. FE plan — "ease of work" (explicit)

**Decision (taken, justifiable):** a **local web review UI**, not an enhanced TUI or IDE plugin.
Reasons: the assets already exist (React/Vite dashboard + FastAPI), real QA users click rather than
type, and it demos far better in the validation gate. TUI stays as the agent/CI interface (`hitl`).

Principles:
- **No build step for the user.** Ship prebuilt `dist/`; `cherenkov review --web` launches API + serves it. `npm` only for FE *developers*.
- **One screen that matters:** the **Findings queue** — each card shows endpoint+method, the failing gate, confidence + plain-language reason, the generated test, and big Approve / Reject / Classify buttons + a "Why was this flagged?" (AI explanation, Tier-3, already built).
- **Honest states:** empty ("no findings — run validate"), loading, error (API down, target unreachable), and a 60-second guided first-run.
- **Capture rejection reasons** ("intended change", "too noisy", "wrong assertion") — this is both UX and the seed of the learning loop (§6).
- **Ejectable/optional:** the UI is a convenience over the `hitl/v1` API; the CLI path always works without it (anti-lock-in preserved).

---

## 4. Roadmap phases (Consolidated Plan)

The consolidated plan covers 10 phases (Phase -1 through Phase 8). See [PHASE_PLAN.md](PHASE_PLAN.md)
for detailed tickets, integration plans, parallel track layout, and agent guidance.

### Phase -1 — Planning & Preparation *(Days 1-2, complete)*
Establish architectural foundation, strategy documents, CI/CD pipeline. All 6 ADRs written,
all strategy docs created, all CI/CD workflows defined.
**Exit:** All planning docs exist, all ADRs accepted, CI/CD workflows pass.
**Issues:** #290-#303 (14 issues)

### Phase 0a — P0 Bug Fixes *(Days 3-5, complete)*
Fix all 8 confirmed P0 bugs before any new features land. All bugs documented in issues.
**Exit:** All 8 bugs fixed, `pytest tests/unit/` + `pytest tests/smoke/` green.
**Issues:** #304-#312 (9 issues)

### Phase 0b — Foundations *(Week 2, complete)*
Lay architectural foundation for all subsequent phases. Ports, events, devices, config,
Docker Compose AI, error handling, migration, logging, security.
**Exit:** All port interfaces defined, Docker Compose AI stack starts, `/healthz` and `/metrics` working.
**Issues:** #313-#327 (15 issues) · **Merged PR #393, #394**

### Phase 1 — Second Brain *(Weeks 3-5, complete)*
Build knowledge mesh that powers all subsequent phases. KnowledgeRepository, GraphRAG,
event bridges (HITL → Reflector, Feedback → RAG, agent_memory → RAG).
**Exit:** `cherenkov knowledge query "auth timeout"` returns real results, Truth Model persists.
**Issues:** #328-#337 (10 issues) · **Merged PR #395**

### Phase 2 — VLM + LocalAI *(Weeks 3-4, parallel with Phase 1, complete)*
Integrate LocalAI as default VLM backend, add tier-aware routing to SubstrateRouter.
**Exit:** LocalAI VLM request returns result in <10s, router selects correct provider for each device class.
**Issues:** #338-#344 (7 issues) · **Merged PR #396**

### Phase 3 — Desktop Host *(Weeks 5-8, blocked)*
Build desktop host for one-click onboarding. Tauri 2, hardware detection, 7-step setup wizard,
device manager, settings UI.
**Exit:** Desktop app opens on Windows + macOS + Linux, setup wizard completes in <5 minutes.
**Issues:** #345-#353 (9 issues) · **Blocked: needs `cargo`**

### Phase 4 — Chat Agents *(Weeks 9-10, complete)*
Build chat agent with tool-calling for knowledge access. ConversationMemory, PersonaRegistry,
QAChatAgent, CHERENKOV tools, SSE streaming, ChatPanel React component.
**Exit:** Chat agent answers "why was this test rejected?" using Reflector idioms, SSE streaming works.
**Issues:** #354-#361 (8 issues) · **Merged PR #397, #398, #399, #400**

### Phase 5 — Mobile Testing Core *(Weeks 5-10, parallel tail, blocked)*
Build mobile testing core. Mobile source adapters (APK/HAR/HIL), Pilot agent, mobile stages,
SemanticVisualOracle, Maestro/Appium eject.
**Exit:** Maestro YAML generation produces valid format with ZERO CHERENKOV imports.
**Issues:** #362-#370 (9 issues) · **Blocked: needs ADB/Maestro**

### Phase 6 — Mobile Execution *(Weeks 11-14, blocked)*
Replace stubs with real execution. MaestroRunner, AppiumRunner, mobile Reflector extensions,
mobile divergence detection, mobile smoke tests.
**Exit:** `make mobile-smoke` passes with Android emulator.
**Issues:** #371-#376 (6 issues) · **Blocked: depends on Phase 5**

### Phase 7 — Dashboard Revamp *(Weeks 14-16, complete)*
Wire dashboard to real data, add mobile/chat/knowledge screens. Mock endpoints → real data,
MOCK DATA badges, MobileScreen, KnowledgeExplorer, DeviceManagerScreen, ChatPanel, Pilot Run, Toast.
**Exit:** All 9 screens built and wired into Navigation sidebar.
**Issues:** #377-#385 (9 issues) · **Merged PR #401, #402, #405**

### Phase 8 — K8s + Cloud + Validation Gate *(Weeks 16-20, in progress)*
Fix K8s, extend CRDs, open-source readiness, 5-QA validation gate. CRD extensions (DeviceTarget,
VisualConfig), operator device env vars, LICENSE/CONTRIBUTING/SECURITY, clean architecture docs.
**Exit:** `make k3d-test` green, ≥5 attributable "yes" verdicts in evidence ledger.
**Issues:** #386-#391 (6 issues) · **SECURITY.md added (#404). Remaining: #386-#388 (needs k3d), #390-#391**

---

## 5. Reuse map (don't rebuild — wire)

| Need | Already exists | Action |
|------|----------------|--------|
| Review API (approve/reject/edit/validate/eject/ingest/run) | `cherenkov/web/api.py` (extended live) | Fully wired — HitlQueue integration live |
| Durable review queue + `hitl/v1` envelope | `cherenkov/hitl/store.py` (live, tested) | Reuse as the single source of review truth |
| React/Vite dashboard (App, 19 screens, components, hooks) | `cherenkov/web/ui/` | All 9 Phase 7 screens built — real API wiring live |
| AI "why flagged" explanation | Chat agent + MCP tools (#361) | SSE streaming chat panel in ReviewScreen (#384) |
| Noise dedup for nightly runs | `cherenkov/reflector` (fingerprint suppression) | Wire into drift-watch (Phase 3) |

## 6. Innovation bets (KEEP INNOVATING — woven into the path, not bolted on)

1. **Bug-vs-intended triage as the headline.** The hard part of conformance testing isn't finding
   diffs — it's deciding which matter. Lead the FE with a confidence-ranked "real bug vs intended
   change" verdict + plain-language reason (Tier-3 exists). This is the defensible differentiator.
2. **The "keep more tests" learning loop.** The gate question is *"what would make you keep more?"*
   Capture every rejection reason in the FE and feed it back into the generator prompt / assertion
   gate. A user-grounded improvement loop — not autonomy for its own sake.
3. **Zero-spam drift-watch.** Nightly re-runs deduped by reflector fingerprint so repeat failures
   don't re-enqueue — directly kills the "alert fatigue → abandonment" death predicted in the premortem.

## 7. Risks & guardrails

- **Anti-pattern to avoid:** treating this doc as "done" by writing code without a human running it.
  Every phase exits on **raw evidence**, and Phase 2 exits only on **attributable real-user** evidence.
- **Anti-lock-in invariant holds:** the web UI is optional sugar over the `hitl/v1` API + CLI; eject still produces standalone Playwright.
- **No new scope** until Phase 2 passes. Promoting the dashboard/API is *wiring existing code into the product*, not new build-ahead — and it's explicitly in service of the gate.

## 8. The full roadmap (tickets, by phase)

All tickets are filed as GitHub issues (#277-#391). Legend: ✅ closed · 🔶 open/in-flight · ⏸ planned.
`P0` = gate-blocker, `P1` = needed for credible release, `P2` = nice-to-have. Sequenced into phases:
complete a phase, re-verify with raw evidence, then start the next.

### Phase -1 — Planning & Preparation ✅ (complete)
| # | Ticket | State |
|---|--------|-------|
| #277 | [EPIC] Phase -1: Planning, ADRs, Strategy, CI/CD | ✅ |
| #290 | ADR-001: Seam-widening architecture decision | ✅ |
| #291 | ADR-002: Tauri 2 + PyInstaller sidecar desktop | ✅ |
| #292 | ADR-003: LocalAI as default LLM backend | ✅ |
| #293 | ADR-004: Clean Architecture ports/adapters | ✅ |
| #294 | ADR-005: Event-driven architecture | ✅ |
| #295 | ADR-006: Knowledge mesh | ✅ |
| #296 | Testing strategy and pyramid documentation | ✅ |
| #297 | Data migration strategy documentation | ✅ |
| #298 | Error handling and graceful degradation strategy | ✅ |
| #299 | Team and infrastructure assumptions documentation | ✅ |
| #300 | CI/CD workflows (integration + release) | ✅ |
| #301 | Create LOGGING.md (logging strategy) | ✅ |
| #302 | Reconcile gate status across all docs | ✅ |
| #303 | Performance baseline smoke tests | ✅ |

### Phase 0a — P0 Bug Fixes ✅ (complete)
| # | Ticket | State |
|---|--------|-------|
| #278 | [EPIC] Phase 0a: P0 Bug Fixes | ✅ |
| #304 | Fix: `run_pipeline()` processes only first scenario | ✅ |
| #305 | Fix: `get_stats()` mutates state via `decay_all_idioms()` | ✅ |
| #306 | Fix: 4 mock API endpoints return hardcoded data | ✅ |
| #307 | Fix: HITL decisions don't feed Reflector | ✅ |
| #308 | Fix: Stats only go to stdout, not persisted | ✅ |
| #309 | Fix: Two review servers coexist (ports 8080+8000) | ✅ |
| #310 | Fix: Healing suggestions are text-only | ✅ |
| #311 | Fix: `truth/` missing `__init__.py` — package not importable | ✅ |
| #312 | Backwards compatibility smoke test for CLI commands | ✅ |

### Phase 0b — Foundations 🔶 (next)
| # | Ticket | Pri | State |
|---|--------|-----|-------|
| #279 | [EPIC] Phase 0b: Foundations — Ports, Events, Devices, Config | 🔶 |
| #313 | Define port interfaces (`ports/*.py`) | P1 | 🔶 |
| #314 | Create `CHERENKOVEvent` domain events | P1 | 🔶 |
| #315 | Create `cherenkov/core/devices.py` | P1 | 🔶 |
| #316 | Extend `Config` with new fields | P1 | 🔶 |
| #317 | Create `docker-compose.ai.yml` | P1 | 🔶 |
| #318 | Add `KnowledgeResult` standardized envelope | P1 | 🔶 |
| #319 | Refactor substrate into unified `providers/` structure | P1 | 🔶 |
| #320 | Add error handling framework | P1 | 🔶 |
| #321 | Add data migration framework | P1 | 🔶 |
| #322 | Structured logging framework | P1 | 🔶 |
| #323 | `/metrics` endpoint + health poll | P1 | 🔶 |
| #324 | Security hardening (input validation, CORS, rate limit) | P1 | 🔶 |
| #325 | Finalize `track-b-c-deferred/` cleanup | P1 | 🔶 |
| #326 | Add unit tests for `cherenkov/core/` | P0 | 🔶 |
| #327 | Add unit tests for `cherenkov/substrate/` | P1 | 🔶 |

### Phase 1-8 — See [PHASE_PLAN.md](PHASE_PLAN.md)

All Phase 1-8 tickets are documented in [PHASE_PLAN.md](PHASE_PLAN.md) with detailed acceptance
criteria, file references, D7 checks, and kill criteria. GitHub issues #328-#391 track all tickets.

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 (Second Brain) → 4 (Chat)
- Track B (VLM): Phase 2 (parallel with Phase 1)
- Track C (Desktop): Phase 3 (after Phase 2 validation)
- Track D (Mobile): Phase 5 (after Phase 2) → Phase 6
- Track E (Dashboard): Phase 7 (after Phase 4 and Phase 6)
- Track F (K8s): Phase 8 (after Phase 7)

See [PHASE_PLAN.md](PHASE_PLAN.md) for full parallel track layout and integration plan.

---

## 9. Triaged backlog from teammate-agent reviews (2026-06-05)

Three teammate-agent reviews were assessed (archived in [reviews/](reviews/README.md)). Strong
corroboration: one independently recommended a **lightweight local HITL triage UI** — exactly the
golden-path FE in §2/§3. Triage rule: **validation-first** — adopt what makes the golden path real,
frictionless, or credible; defer anything that assumes the (still-unpassed) gate.

### 9a. Already done this session
TS `^6.0.3`→`^5.0.0` and LICENSE (#165); live-LLM CI smoke (#167); client memoization / state fix
(#168); HITL web review UI (#173–#177); rejection-reason feedback loop (#182, WIP `cherenkov/core/feedback_store.py`).
**Note:** a teammate has begun Phase 0 — untracked WIP `cherenkov/web/api.py` (wired to the *real*
`HitlQueue`, not mock) + `cherenkov/web/divergences.py`. Land it via its own reviewed PR.

### 9b. Adopt now — credibility & golden-path hardening (tickets #183+)
| Item | Source | Why now |
|------|--------|---------|
| **YAML spec support** (`yaml.safe_load` for `.yaml/.yml`) | F4 | real bug — ingest is JSON-only today; blocks real specs |
| **`cherenkov report --output report.json`** (+ `--diff`) | F3 | structured results enable CI, diffing, the review UI |
| **`cherenkov self-test`** (mini-spec → generate → tsc) | F1 | proves the core claim on demand; complements #167 |
| **Per-run `events.jsonl` + `--verbose/--quiet`** | E10/E11 | observability; separates logs from user output |
| **Generation timeout + retry-on-non-compiling-output** | E7/E8 | directly kills the premortem's silent-fail mode |
| **Golden-output snapshot test for `generate`** | E9 | catches prompt drift in CI |
| **Consolidate validate entrypoints** (drop `cherenkov_validate.py`) | E3 | one CLI surface |
| **Spec coverage-gap report** (skipped endpoints / response codes) | F8 | answers "did it cover my API?" |
| **Document PlanStage as deterministic-by-design** (or ticket the LLM planner) | E4 | ends a spec-vs-reality gap |
| **Mutation test for the validation engine** (break a test → validate catches it) | E13 | proves the detector works E2E |

### 9c. Meaningful-workflow innovation — Phase 3+ (the "real human workflows" the owner asked for)
These make the tool matter for *real* APIs, but they widen scope, so they land **after** the gate.
| Bet | Source | Note |
|-----|--------|------|
| **Chained / stateful CRUD journeys** (POST→capture id→PATCH→DELETE via OpenAPI links) | Doc3 A, F-stateful | the biggest "meaningful workflow" gap; spike ticket now, build post-gate |
| **Robust test-data management** (unique-constraint / 409 handling, fixtures) | Doc3 | pairs with chained tests |
| **Lightweight DAST** (OWASP payloads in the mutation menu; assert safe-reject, no 500) | Doc3 B, F7 | natural extension of existing mutation testing |
| **Semantic chunking / RAG for huge specs** (`nomic-embed-text`, keep prefix cache hot) | Doc3 #3 | the bundled `stripe_spec.json` is 7.8 MB — real need |
| **Auto-PR of tightening suggestions** (GitHub/GitLab one-click) | Doc3 | closes the suggest→apply loop without violating D7 (human merges) |
| **Advanced Auth Vault** (OAuth2 code flow, mTLS, multi-tenant JWT) | Doc3 C | unblocks real enterprise specs |
| **GraphQL / gRPC / WebSocket** ingestion | Doc1, Doc3 | long-horizon market expansion |
| **Novelty Gate 4 + LLM Quality Gate 6** | dev plan | complete the 6-gate design |
| ⚠️ **Safe-list opt-in auto-healing** | Doc3 #2 | **tension with invariant D7** (suggest-only). Only as a strict, user-opt-in policy engine, carefully gated — do NOT erode D7 by default |

### 9d. Rejected / deferred (predicated on the fabricated gate)
**Do not action until the real gate passes.** "Ready to ship / open-source launch now", the B+ 88.5
score, **un-quarantining Track B/C now**, and all pricing / Pro / Enterprise / SaaS / monetization
plans (Doc2 §2.3–2.5) rest on the fabricated "4/5 passed" claim. Security items Doc2 marks **P0**
(HITL auth, SQLite encryption) are real but **over-prioritised for a localhost-first, single-user,
pre-validation tool** — captured as a security backlog ticket, not a launch blocker.
