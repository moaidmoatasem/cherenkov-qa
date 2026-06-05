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

> ⚠️ **CORRECTION (2026-06-05).** This section was previously rewritten to claim
> the validation gate "PASSED (4/5 YES) ← SHIPPED." **That was fabricated** — see
> §2. The only backing artifact was an untracked, anonymous JSON; there were no
> real, attributable QA reviewers. The claim is retracted below. §4 above is also
> now **stale**: Track B/C was re-integrated into the live `cherenkov/` tree and a
> wave of Horizon 2 modules was added on the strength of that fake gate. The
> honest map of what is actually live vs built-ahead is
> [docs/SCOPE_LEDGER.md](SCOPE_LEDGER.md).

```
Track A code:       BUILT and core invariants proven
Track A validation: NOT PASSED  ← the real, still-open blocker (no real QA evidence)
Track B/C + Horizon 2 code: built + unit-tested, NOT validated, and (contrary to §4)
                    largely re-integrated into the live tree. See SCOPE_LEDGER.md.
```

**The validation gate has NOT passed.** Nothing has been validated by real QA
practitioners. The gate requires 5 reachable QA people to use the tool and leave
attributable evidence — tracked in
[docs/process/VALIDATION_EVIDENCE_LEDGER.md](process/VALIDATION_EVIDENCE_LEDGER.md).
Until that happens, no part of the product — Track A or the built-ahead Horizon 2
surface — counts as shipped or validated.

> **Forward plan (2026-06-06).** The authoritative forward roadmap is
> [docs/ROADMAP_NEXT.md](ROADMAP_NEXT.md) ("Validation-First / Horizon V"), with a full
> wave-by-wave ticket breakdown in its §8 and a current status snapshot in its §0.
> **Where we stand:** the golden path (init→generate→validate→review→eject) works
> **from the CLI**; Phase 0 spike + Phase 1a friction foundations are landed. The open
> frontier is making the **whole loop drivable from the dashboard with no terminal**
> (EPIC #241) and **one-click install** — this is what unblocks the 5-QA gate. Immediate
> next work, in order: **Wave 2 honesty debt** (#222 toasts, #223 wire Pilot Run, #224/#239
> kill mock screens / add MOCK badges) → **Wave 3 UI-only loop** (#234 P0, #235, #237, #238,
> #240) → **Wave 4 one-click install** (#232, #233, #230, #231) → **Wave 5 the gate.**

---

## 6. What to do next (priority order)

### 6.1 — RECONCILE & STABILISE CI (DONE 2026-06-02, branches `chore/reconcile-to-track-a` and `epoch0/stabilise-ci-green-on-main`)
- `docs/INTEGRATION_HANDOVER_REPORT.md` banner'd as fabricated.
- Track B/C modules moved to `track-b-c-deferred/`.
- `cherenkov.py`, `cherenkov/execution/validate.py`, `cherenkov/core/orchestrator.py`
  stripped of Track B/C call sites (--visual, --perf, dashboard, diagnostics, jira).
- Track A smokes re-run green after quarantine.
- **E0-2 Stabilise CI**: Added standard dependency installation steps to the `.github/workflows/ci.yml` file, refactored `smoke_test_healing.py` to prevent local change pollution, and implemented auto-restoration in `smoke_test_polish.py` (ALL tests verified fully green).

- **Epoch 1 (L0 Substrate Router) Complete**: Implemented core SPI for model providers, integrated OpenAI alongside Ollama, developed routing logic matching capability tiers with egress policies, created response caching, cost/latency accounting, and enforced sovereignty dials (`none`/`internal`/`any`). Fully covered by unit tests and smoke tests.

- **Phase A Validation Gate Complete (Issues #109-#115)**:
  - **A1/A2 (#109, #110)**: Built `cherenkov hitl list|show|approve|reject` terminal CLI & REVIEW stage bridge to enqueue Verdict.HITL items.
  - **A3 (#111)**: Documented HITL flow in GETTING_STARTED.md & CLI_DEMO.md.
  - **A4 (#112)**: Implemented `cherenkov/validate/` Validation Gate criteria and evidence collection contracts.
  - **A5 (#115)**: Created the 5-QA validation runbook and standalone scripts/collect_evidence.py script.
  - **A6/A7 (#113, #114)**: Wired Reflector reranking into proof_run loop & created E7 behavioral exit demo proving fingerprint-based suppression.
  - **Epoch 10 Explorer & Copilot (Issues #123-#125)**: Created the `smoke_test_copilot_e10.py` exit demo verifying C8 (Explorer crawl/hypotheses), C9 (NL intent to ejectable role-locator Playwright TS), and C10 (SecondPairOfEyes pre-session digest & triage UX).

- **Horizon V — Golden Path + Friction Kill (2026-06 in progress)**: Phase 0 spike landed
  (review API wired to real `HitlQueue`; `cherenkov.py review` serves prebuilt
  `cherenkov/web/ui/dist` — #173–#177). Phase 1a foundations landed: prebuilt dist (#178),
  `doctor` preflight (#179), no-Ollama demo mode (#181/#204), rejection-reason capture (#182),
  offline overlay (#221), a11y (#225), responsive CTA (#226), Divergences triage drawer
  (#227/#236), Docker packaging (#200–#206), correctness fixes (#219/#220/#228). **Open frontier:**
  Wave 2 honesty debt (#222–#224/#239), Wave 3 UI-only loop + Wave 4 one-click install under
  EPIC #241. See [ROADMAP_NEXT.md §0/§8](ROADMAP_NEXT.md).



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
               (no LLM) (deterministic) (qwen)   (6 gates)

INGEST   parse + depth-1 slice per endpoint, openapi-fetch stub, mutation menu, richness
PLAN     deterministic mapping (no LLM): maps endpoints to mutation scenarios (e.g. happy_path)
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
