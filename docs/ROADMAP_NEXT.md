# CHERENKOV — Forward Roadmap: "Validation-First" (Horizon V)

**Date:** 2026-06-05 (status snapshot refreshed 2026-06-06) · **Status:** Authoritative for *what's next* (supersedes the disputed
[ROADMAP_RECONCILIATION.md](ROADMAP_RECONCILIATION.md) for forward planning). Pairs with
[HANDOVER.md](HANDOVER.md) (status), [SCOPE_LEDGER.md](SCOPE_LEDGER.md) (scope), and
[process/VALIDATION_EVIDENCE_LEDGER.md](process/VALIDATION_EVIDENCE_LEDGER.md) (the gate).

---

## 0. Status snapshot (2026-06-06)

Where we actually stand against the phases below. Anchored to closed GitHub issues, not claims.

| Phase | State | Evidence |
|-------|-------|----------|
| **Phase 0 — Golden Path spike** | ✅ **Landed** | `cherenkov/web/api.py` wired to the real `HitlQueue`; `cherenkov.py review` launches API + serves prebuilt `cherenkov/web/ui/dist`. Tickets #173–#177 closed. |
| **Phase 1 — Friction kill** | 🔶 **In progress (~60%)** | Done: prebuilt dist (#178), `doctor` preflight (#179), no-Ollama demo mode (#181, #204), rejection-reason capture (#182), backend-offline overlay (#221), a11y labels (#225), responsive CTA (#226), Divergences triage drawer (#227, #236), packaging/Docker P-1…P-7 (#200–#206). **Remaining: the UI-only / one-click work — see §8 Wave 2/3.** |
| **Phase 2 — Real validation gate (5 QA users)** | ⛔ **Not started** | THE milestone. Still 0 attributable QA reviewers. Blocked on Phase 1 finishing the friction kill. |
| **Phase 3 — Earned expansion** | ⏸ **Deferred** | Gated on Phase 2 + the [SCOPE_LEDGER](SCOPE_LEDGER.md) fork. Spikes #193–#195 (chained journeys, DAST, RAG) already scoped. |

**Headline:** the golden path *works from the CLI*; the open frontier is making the **whole loop drivable
from the dashboard with no terminal** (EPIC [#241]) and **one-click install** — that is what unblocks the gate.

**Honesty debt still open (must close before the gate):** 10/17 dashboard surfaces still render `mockData.ts`
(#224/#239); silent `catch(console.warn)` instead of toasts (#222); "Initialize Pilot Run" not wired to
`POST /run` (#223). These make demos misleading and are gate-blockers, not polish.

---

## 1. Strategy in one paragraph

CHERENKOV's code surface is large; its *proven, used-by-a-human* surface is zero. The single
goal of this horizon is to make **one end-to-end workflow that a real QA engineer can run, enjoy,
and trust** — and then prove it with 5 real users. Every ticket below either (a) makes that
golden path real and frictionless, or (b) collects the human evidence that closes the validation
gate. We do **not** add new backend epochs. We *reuse* what's already built (a full FastAPI
backend + a React dashboard already exist — see §5) and wire it honestly to real data.

> **The reframe:** the existing dashboard/API are no longer "built-ahead debt." They become the
> **validation vehicle** — the friction-free face that gets us through the gate.

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

## 4. Roadmap phases

### Phase 0 — Golden Path spike *(make it real, ~1 wk)*
Wire the existing FastAPI review endpoints to the **real `HitlQueue`** and **real validate findings**
(delete mock data). Add `cherenkov review` to launch API + serve the prebuilt FE. Prove the full
path on the bundled petstore with **raw evidence (screen recording + terminal log)**.
**Exit:** init→generate→validate→**review (web, real data)**→eject works end to end, recorded.

### Phase 1 — Friction kill *(make it effortless, ~1–2 wk)*
Sub-10-minute first run. Prebuilt `dist/` in repo/CI. `doctor` preflight gates the path with
actionable fixes. No-Ollama demo mode. UI empty/error/loading states + guided first-run. Rejection-reason capture.
**Exit:** a fresh user, no prior context, reaches a real finding and a kept test in < 10 min on a laptop.

### Phase 2 — The real validation gate *(owner-led, agent-supported)*
Run **5 real QA practitioners** through the golden path (web UI) per
[QA_VALIDATION_RUNBOOK.md](process/QA_VALIDATION_RUNBOOK.md); record attributable evidence in the
[evidence ledger](process/VALIDATION_EVIDENCE_LEDGER.md). **This is THE milestone.** Nothing scales until ≥3 say yes.

### Phase 3 — Earned expansion *(only with demand signal)*
Resolve the [SCOPE_LEDGER](SCOPE_LEDGER.md) fork (re-quarantine vs adopt). Then build the *next adjacent*
the users actually asked for — likely **drift-watch** (Phase 1 nightly + dedup) or visual/perf — driven by
rejection-reason data, not a pre-written epoch list.

---

## 5. Reuse map (don't rebuild — wire)

| Need | Already exists | Action |
|------|----------------|--------|
| Review API (approve/reject/edit/validate/eject/ingest/run + WS) | `track-b-c-deferred/cherenkov/api/main.py` | Promote to supported `cherenkov/web/api.py`; wire to real `HitlQueue` |
| Durable review queue + `hitl/v1` envelope | `cherenkov/hitl/store.py` (live, tested) | Reuse as the single source of review truth |
| React/Vite review UI (App, components, hooks, dist) | `track-b-c-deferred/dashboard/` | Promote to `cherenkov/web/ui/`; replace `mockData.ts` with live API |
| AI "why flagged" explanation | `cherenkov/openclaw` Tier-3 / `copilot/triage` | Surface as the "Why?" button |
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

## 8. The full roadmap (tickets, by wave)

All tickets are filed as GitHub issues. Legend: ✅ closed · 🔶 open/in-flight · ⏸ deferred (post-gate).
`P0` = gate-blocker, `P1` = needed for a credible gate, `P2` = nice-to-have. Sequenced into delivery
**waves**: ship a wave, re-verify the golden path end to end with raw evidence, then start the next.

### Wave 0 — Golden Path spike ✅ (Phase 0, done)
| # | Ticket | State |
|---|--------|-------|
| #173 | Wire review API to the real `HitlQueue` | ✅ |
| #174 | Replace dashboard mock data with live API calls (review/divergences) | ✅ |
| #175 | `cherenkov review` — launch API + serve prebuilt FE | ✅ |
| #176 | Promote dashboard + review API to supported `cherenkov/web/` | ✅ |
| #177 | Golden-path E2E smoke with recorded evidence | ✅ |

### Wave 1 — Friction kill: foundations ✅ (Phase 1a, done)
| # | Ticket | Pri | State |
|---|--------|-----|-------|
| #178 | Ship prebuilt FE `dist/` so users need no `npm` | P1 | ✅ |
| #179 | `doctor` preflight gates the golden path with actionable fixes | P1 | ✅ |
| #181 / #204 | No-Ollama demo mode (cached run on bundled petstore) | P1 | ✅ |
| #182 | Capture rejection reasons in FE to seed the learning loop | P1 | ✅ |
| #221 | Backend-offline overlay + health-poll context | P1 | ✅ |
| #225 | a11y labels on autonomy toggle / help / KPI ring + focus roles | P1 | ✅ |
| #226 | Responsive: primary CTA renders off-screen below ~360px | P1 | ✅ |
| #227 / #236 | Divergences triage in UI (filters, detail drawer, act-with-feedback) | P1 | ✅ |
| #200–#206 | Packaging: Dockerfile, compose, Ollama+GPU profile, bundled UI, demo mode, quickstart, scaling spike | P1 | ✅ |
| #219 #220 #228 | Correctness: validate suggest-only violation, `review` crash, FastAPI lifespan | P0/chore | ✅ |

### Wave 2 — Honesty debt (Phase 1b, **DO FIRST — gate-blocking**) 🔶
The dashboard must never show fake data to a real QA reviewer. Close these before any new surface.
| # | Ticket | Pri | State |
|---|--------|-----|-------|
| #222 | Honest error/loading states — replace silent `catch(console.warn)` with toasts | P1 | 🔶 |
| #223 | Wire "Initialize Pilot Run" (Author-by-Intent) to `POST /api/v1/run` | P1 | 🔶 |
| #224 / #239 | Replace `mockData` on the 10/17 flagship screens (Overview/TruthMap/Signals/Governance/Memory/Explore/Author) with live endpoints **or** explicit `MOCK DATA` badges | P1 | 🔶 |

### Wave 3 — UI-only workflow loop (Phase 1c — EPIC #241, the heart of "one-click QA") 🔶
Goal: a non-technical QA engineer completes spec → generate → review → eject **without a terminal**.
| # | Ticket | Pri | State |
|---|--------|-----|-------|
| #234 | Full Setup→Run→Pipeline→Review loop driven entirely from the UI + live `WS /ws/live` progress | **P0** | 🔶 |
| #235 | Review Queue: complete HITL in UI + rejection-reason capture + "Why flagged?" AI explanation | P1 | 🔶 |
| #237 | Eject suite from the UI — in-browser folder picker / zip download, no terminal | P1 | 🔶 |
| #238 | Settings: real server-side persistence + editable engine config (target, model tier, egress) | P1 | 🔶 |
| #240 | Honest empty/loading/error states + 60-sec guided tour across all tabs | P2 | 🔶 |

### Wave 4 — One-click install & onboarding (Phase 1d — EPIC #241 Track A) 🔶
Goal: install in one click; never touch a package manager or CLI.
| # | Ticket | Pri | State |
|---|--------|-----|-------|
| #232 | First-run wizard in the UI (doctor-in-UI, engine/model detection, demo-vs-real, sample spec) | P1 | 🔶 |
| #233 | In-app engine + model manager (status, start/stop/restart, Ollama detect + pull progress, demo toggle) | P1 | 🔶 |
| #230 | Desktop launcher (one-file binary) — double-click starts engine + opens dashboard | P1 | 🔶 |
| #231 | Tauri desktop app + native installers (.msi/.dmg/.AppImage) — *needs-human signing/notarization* | P2 | 🔶 |

### Wave 5 — THE GATE (Phase 2, owner-led) ⛔
Run **5 real QA practitioners** through the UI golden path; record attributable evidence in the
[evidence ledger](process/VALIDATION_EVIDENCE_LEDGER.md). **Nothing in Wave 6 starts until ≥3 say yes.**
Runbook: [QA_VALIDATION_RUNBOOK.md](process/QA_VALIDATION_RUNBOOK.md). Recruiting: [QA_OUTREACH_TEMPLATES.md](QA_OUTREACH_TEMPLATES.md).

### Wave 6 — Earned expansion (Phase 3, post-gate, demand-driven) ⏸
Resolve the [SCOPE_LEDGER](SCOPE_LEDGER.md) fork (re-quarantine vs adopt §B built-ahead) **first**, then
build the *next adjacent* users actually asked for. Pre-scoped spikes ready to promote:
| # | Spike | Note |
|---|-------|------|
| #193 | Chained / stateful CRUD journeys (POST→capture id→PATCH→DELETE via OpenAPI links) | biggest "meaningful workflow" gap |
| #194 | Lightweight DAST mutation profile (OWASP payloads; assert safe-reject, no 500) | extends existing mutation testing |
| #195 | Semantic chunking / RAG for large specs (`nomic-embed-text`) | the 7.8 MB stripe spec is a real need |
| #196 | Security hardening: HITL auth + at-rest encryption | real, but over-prioritised pre-gate — backlog |

Further Phase 3+ bets (visual regression, perf baselines, diagnostics+RAG, Jira/compliance, auto-PR of
tightening suggestions, GraphQL/gRPC ingest) remain catalogued in §9c and gated on demand signal.

> **Anti-pattern guard (HANDOVER.md §2):** a ticket is "done" only with **raw evidence** (terminal output +
> screenshots from the running dashboard), never a summary. Phase 2 exits only on **attributable real-user** evidence.

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
