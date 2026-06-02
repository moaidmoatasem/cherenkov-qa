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

- **SSOT = `docs/` anchored to spec "v3.1 + delta."** There is NO v4.x, v6.0,
  or "Meissner Shield." Multiple agents fabricated these. If you cite a version
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

```
Track A code:       BUILT and core invariants proven
Track A validation: NOT DONE  ← the real blocker
Track B/C code:     built prematurely, unvalidated, now quarantined
```

**The one remaining step for Track A is not code.** It is: show the tool to
**5 real QA professionals** (spec → generate tests → pass on correct API →
inject bug → tests catch it → eject), and ask *"Would you keep these in your
suite? What would make you keep more?"* **3 of 5 yes = Track A shipped.**

This gate has been repeatedly deferred. No agent can do it. It requires the
owner to recruit 5 QA people and run the demo.

---

## 6. What to do next (priority order)

### 6.1 — RECONCILE (DONE 2026-06-02, branch `chore/reconcile-to-track-a`)
- `docs/INTEGRATION_HANDOVER_REPORT.md` banner'd as fabricated.
- Track B/C modules moved to `track-b-c-deferred/`.
- `cherenkov.py`, `cherenkov/execution/validate.py`, `cherenkov/core/orchestrator.py`
  stripped of Track B/C call sites (--visual, --perf, dashboard, diagnostics, jira).
- Track A smokes re-run green after quarantine — see commit body for raw output.

### 6.2 — THE REAL FINISH LINE (owner task, not an agent)
Recruit 5 QA people. Run the demo from [QA_DEMO_KIT.md](QA_DEMO_KIT.md).
Count yeses. [QA_OUTREACH_TEMPLATES.md](QA_OUTREACH_TEMPLATES.md) exists to
help with recruiting.

### 6.3 — AFTER 3 yeses — plan Track B "build-over" (priority order)
Quarantined modules become the roadmap, ordered by demand signal not effort:

1. **B1 — Visual regression** (`visual_diff` + `ui_generate` + `ui_plan`):
   closest adjacent to API conformance, same Playwright runtime, easiest to
   layer on Track A's contracts. Highest likely "yes I'd use that" from QA.
2. **B2 — Perf baselines** (`k6_runner` + `perf_analyzer`): clear value, fully
   ejectable, but second because k6 isn't always in QA's existing stack.
3. **C1 — Diagnostics + RAG** (`diagnostics_stage` + `rag_index`): only worth
   doing once you have enough failure history to retrieve against.
4. **C2 — Jira export, compliance scanners, dashboard** (`jira_exporter`,
   `mena_scanner`, `api/`, `dashboard/`): integration surface. Build last,
   when you know which Jira fields / which compliance frameworks / which
   dashboard views actually get used.

Each module layers **on top of** validated Track A, reusing the same contracts —
never replaces it. Treat quarantined code as REFERENCE; rewrite cleanly on
top of Track A boundaries rather than re-importing wholesale.

---

## 7. Architecture (for any agent building on it)

```
OpenAPI spec → INGEST → PLAN → GENERATE → REVIEW → tests/
               (no LLM) (deepseek) (qwen)   (6 gates)

INGEST   parse + depth-1 slice per endpoint, openapi-fetch stub, mutation menu, richness
PLAN     deepseek selects mutation_id from menu (never invents), strips <think>
GENERATE qwen writes test w/ openapi-fetch, static system prompt (prefix cache)
REVIEW   syntax → structure → AST → assertions → tsc --noEmit → Prism dry-run
         verdict: auto_approve (>0.9) / hitl (0.7-0.9) / regenerate
                  dry-run fail → D2 loop back to PLAN, circuit-break at 2 fails/case
```

Stable core + pluggable capability layers. Track B/C build OVER this, never replace it.

## 8. Environment

WSL2 Ubuntu, RTX 5060 8GB, Ollama (`qwen2.5-coder:7b`, `deepseek-r1:8b`).
GPU confirmed: ~1.86s warm generation, 29/29 layers on GPU. Python 3.10+, Node
for openapi-typescript + Playwright, Docker for Prism. Keep the repo on the WSL
filesystem (~/cherenkov-qa), not /mnt/c.
