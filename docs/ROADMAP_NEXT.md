# CHERENKOV — Forward Roadmap: "Validation-First" (Horizon V)

**Date:** 2026-06-05 · **Status:** Authoritative for *what's next* (supersedes the disputed
[ROADMAP_RECONCILIATION.md](ROADMAP_RECONCILIATION.md) for forward planning). Pairs with
[HANDOVER.md](HANDOVER.md) (status), [SCOPE_LEDGER.md](SCOPE_LEDGER.md) (scope), and
[process/VALIDATION_EVIDENCE_LEDGER.md](process/VALIDATION_EVIDENCE_LEDGER.md) (the gate).

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

## 8. Tickets

Phase 0 / Phase 1 tickets are filed as GitHub issues labelled `agent-ready` and reference this doc.
See the milestone "Horizon V — Validation-First."
