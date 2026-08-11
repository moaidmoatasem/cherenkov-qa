# CHERENKOV-QA — Agentic Test Plan to Verified 100%

**Date:** 2026-08-11
**Measured against:** `claude/cherenkov-qa-agentic-tests-svs4yg`, HEAD `94de7bc`
**Status anchor:** `HANDOVER.md` (per `CLAUDE.md`). This document is a QA plan, not a roadmap —
where it disagrees with `HANDOVER.md` on *status*, `HANDOVER.md` wins.

---

## 1. Why this plan exists

CHERENKOV-QA's product thesis is *catch the AI cheating* — it exists to prove that
LLM-generated tests actually assert something. Its own suite does not currently meet that bar.

Every number below was **measured on this branch**, not carried forward from a prior session.
`§9 Appendix` gives the exact commands to reproduce each one.

| Fact | Measured | Source |
|---|---|---|
| Python line coverage | **64.78%** (21,530 / 33,238 stmts; 11,708 missing) | `pytest --cov` |
| Python files at 0% coverage | **86** (3,097 stmts) | `coverage json` |
| Branch coverage | **not measured at all** — no `branch = true` | `pyproject.toml:106` |
| Python tests collected | 2,658 across 213 files | `--collect-only -q` |
| Python tests failing | **1** — `test_saml_user_sync.py::test_saml_callback_syncs_user` | full run |
| **UI E2E tests collected** | **0 of 308 written** | `npx playwright test --list` |
| React component unit tests | **0** (no vitest/jest; 68 components, 11k LOC TSX) | grep, all `package.json` |
| CI coverage gate | `--cov-fail-under=55` — **10 pts below actual** | `.github/workflows/ci.yml:206` |
| Lint in CI | **none** — ruff configured but pre-commit only | 37 workflows grepped |

### Two load-bearing findings

**1 — The entire React E2E suite is dead.** `cherenkov/web/ui/tests/api_mocks.ts` does not
exist but is imported by 10 modules, including `tests/qa/page-objects.ts:2`, which 7 of the 9
live `e2e/*.spec.ts` files and `qa/headless-qa-user.spec.ts` (the one suite CI runs) depend on.
Playwright cannot resolve the module, so collection yields zero:

```
$ npx playwright test --list
Error: Cannot find module '.../tests/api_mocks' imported from .../tests/qa/page-objects.ts
Total: 0 tests in 0 files
```

A further 196 tests sit in `testIgnore` (`playwright.config.ts:14-22`), one entry of which
(`tests/dashboard_e2e.spec.ts`) names a file that no longer exists. `HANDOVER.md`'s
"260 headed, 0 failed" describes a suite that cannot presently run.

**2 — A live product bug is on the branch.** `UserStore.__init__` stores `db_path` unconverted
(`cherenkov/web/auth/store.py:53`), so `_connect` calls `.parent` on a `str` (`store.py:57`):

```
E   AttributeError: 'str' object has no attribute 'parent'
```

The test that catches it arrived in the same PR that introduced the bug (`94de7bc`, #951).

**The problem this plan solves is therefore not "coverage is low".** It is that *coverage
numbers here are not currently trustworthy*. Raising them without first making them meaningful
would manufacture confidence. The intended outcome is a suite whose green is evidence.

---

## 2. What "100%" binds to

Pure line coverage is the wrong gate for an agent-driven campaign: a model can reach 100% with
assertion-free tests, and `demos/catch-the-ai-cheating/` exists to prove exactly that failure
mode. **100% binds to an eight-axis composite gate**, all eight of which must hold.

| Axis | Target | Enforced by |
|---|---|---|
| A1 — Branch coverage, core packages | **100%** | `coverage` with `branch = true` |
| A2 — Branch coverage, periphery | ≥90%, no file below 75% | same |
| A3 — Mutation kill rate | **≥80%** | `verdict/mutation_oracle.py` + `mutmut` |
| A4 — Surface coverage | **100%** of ~125 endpoints, 48 CLI commands, 7 routes, 6 journey steps | manifest-diff gates |
| A5 — Assertion integrity | **100%** of tests survive adversarial self-play | `sdet/assertion_gate.py` |
| A6 — Functional-claim coverage | **100%** of documented capabilities map to a passing test, or are marked `UNPROVEN` | claim→test traceability (§5) |
| A7 — UX task success | **100%** of persona tasks complete; scored, regressions block | persona harness + VLM oracle (§6) |
| A8 — Performance budgets | **100%** of budgeted operations within budget; no unexplained regression | baseline + anomaly detector (§7) |

A1–A5 answer *"is the code exercised, and are the tests real?"*
A6–A8 answer *"does the product do what it claims, feel usable, and stay fast?"*
The second group is what separates code coverage from the coverage a human QA team produces.

**Core packages (A1):** `core/`, `stages/`, `divergence/`, `verdict/`, `sdet/`, `journeys/`,
`substrate/`, `web/routes/`, `web/auth/`, `cli/commands/`.

### Model posture

**Frontier models author and review; every CI gate is deterministic and offline.** The
test-writing, contract-extraction and adversarial-review agents use the providers already
wired at `cherenkov/substrate/providers/`. Nothing on the CI critical path calls an LLM — A3
and A5 run on `mutation_oracle.py` and `assertion_gate.py`, which are offline by construction.
This avoids the failure shape the repo already hit once, where a shipped Action silently
depended on an LLM endpoint that wasn't there (`action.yml`, HANDOVER 2026-08-07).

One deliberate exception: the VLM visual assessment (§6.4) needs a vision model
(`CHERENKOV_TIER_VISION_*`, `settings.py:43`). It runs nightly and advisory-only, so a missing
vision provider degrades to "no visual opinion this run" rather than a red build.

---

## 3. Phase 0 — Repair the foundation

**Blocking. Nothing else is measurable until this lands.**

| # | Task | Files |
|---|---|---|
| 0.1 | Coerce `self._path = Path(db_path) if db_path else _db_path()` | `cherenkov/web/auth/store.py:53` |
| 0.2 | Reconstruct `api_mocks.ts` — export `setupApiMocks`, `INITIAL_PROJECTS`, `MOCK_ENDPOINTS`, `INITIAL_TESTS`, `INITIAL_FAILURES`, `MOCK_DIVERGENCES`. Derive route mocks from the live FastAPI schema, not by hand (see 4.4) | new `cherenkov/web/ui/tests/api_mocks.ts` |
| 0.3 | Triage the 7 `testIgnore` entries: delete the stale `dashboard_e2e.spec.ts` line; rewrite the 5 QA suites against the 5-hub IA in `src/journey/config.tsx:41-89`; un-ignore each as repaired | `cherenkov/web/ui/playwright.config.ts:14-22` |
| 0.4 | Retire legacy page objects (`SetupPage`, `PipelinePage`, `ReviewPage`, `HealingPage`, `EjectPage`, `TruthMapPage`) — those screens were deleted in the revamp | `tests/qa/page-objects.ts:133-235` |
| 0.5 | Fix `tests/unit/test_mcp_auth.py` collection (needs system `cffi`); add to the CI image so the file stops being invisible | CI image / `requirements.txt` |
| 0.6 | Make `tests/smoke/` (35 files) visible — named `smoke_test_*.py` while `python_files` is unset, so pytest has **never** collected them | `pyproject.toml:92` |
| 0.7 | Decide on `tests/standalone/` (44 files, excluded by `norecursedirs`) — adopt or delete. Do not leave 44 files pretending to be tests | `pyproject.toml:95` |

**Exit criteria:** `pytest tests/` green; `npx playwright test --list` reports >300 tests; every
directory under `tests/` is either collected or deleted.

---

## 4. Phase 1–3 — Instrumentation, the agent engine, surface campaigns

### 4.1 Instrumentation (build the measuring apparatus first)

- **Branch coverage on.** Add `branch = true` to `[tool.coverage.run]` and move `fail_under`
  into config. Ratchet `ci.yml:206` from 55 → the measured 64 immediately.
- **`scripts/coverage_ratchet.py`** — fails if any core file's branch coverage drops; raises
  the floor on green. Removes today's 10-point silent slack.
- **`scripts/mutation_gate.py`** — wraps the existing `MutationOracle` (STATUS_FLIP /
  FIELD_DROP / ENUM_BYPASS) and adds `mutmut`. Kill rate ≥0.80 — the same threshold the product
  asserts against its users' suites.
- **Surface manifests (A4)** — endpoints from `app.routes` (`web/api.py:23`), CLI from the
  Click tree (`cli/core.py:31`), UI routes from `App.tsx:300-334` and
  `journey/config.tsx:41-89`. Each with a drift test, mirroring the existing
  `tests/unit/test_manifest_matches_tools.py`.
- **`scripts/check_test_integrity.py` (A5)** — the anti-cheat. Rejects zero-assertion tests,
  `assert True`, bare `pytest.raises(Exception)`, newly added `# pragma: no cover`, newly added
  `@pytest.mark.skip`/`xfail`, `expect(true)` in TS, and any diff deleting assertions while
  adding coverage.
- **Reporters** — HTML + JUnit and `video: 'retain-on-failure'`; none of the 5 Playwright
  configs emits machine-readable results today.
- **Vitest** — `vitest` + `@testing-library/react` + V8 coverage. There is no frontend
  unit-test runner at all today.
- **Ruff in CI** — the missing lint job.
- **Baseline stores** — `docs/traceability/claims.yaml`, `docs/ux/baseline.json`, extended
  `bench/eval-baseline.json`. A baseline an agent can silently rewrite is not a baseline;
  updates require an explicit, human-reviewed commit.

**New dev dependencies:** `hypothesis`, `mutmut`, `schemathesis` (none installed today);
`vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/user-event`,
`msw`, `lighthouse`/`web-vitals`. k6 and axe are already present.

### 4.2 The agent engine

Mirrors the pipeline the repo already defines at `.agents/orchestrator/BRIEFING.md:12` —
`Survey → Decompose → Explorer → Worker → Reviewer → Challenger → Auditor → Gate`. Agents
follow the SDD protocol (`AGENTS.md:100-134`) and honour **D7** (`AGENTS.md:16`): agents write
*new* tests and never silently rewrite an existing test to make it pass.

| Agent | LLM? | Job |
|---|---|---|
| **Surveyor** | no | Rank work units by `uncovered_branches × blast_radius` (inbound import count) |
| **Decomposer** | no | One module per packet, with exact uncovered branch lines and real call sites |
| **Explorer** | yes | Writes a **behaviour contract** — what the module promises, its error modes, its invariants. **Does not write tests** |
| **Worker** | yes | Writes tests against the *contract*; the branch list is only a checklist |
| **Reviewer** | yes (different model) | Rejects tautologies, over-mocking, tests that assert the mock rather than the code |
| **Challenger** | **no** | Mutation + adversarial self-play against the new tests |
| **Auditor** | no | Verifies the branch-coverage delta is real and no integrity rule was violated |

**The Explorer/Worker split is what buys human-like coverage.** An agent told "cover line 214"
writes a test that reaches line 214. An agent told "this function promises X and fails in ways
Y and Z" writes the test a human would write, and line 214 is covered as a side effect. The
contract is committed alongside the tests so the next agent has no amnesia (`agent_memory/`).

**Challenger is the quality guarantee, and it is deliberately not an LLM.** Every
agent-authored test must (a) pass against correct code and (b) **fail** against a deliberately
broken variant — `AdversarialSelfPlay`'s `passed_correct and failed_broken` rule
(`sdet/assertion_gate.py:56`). A test passing both is tautological and is deleted, not merged.
This is the product's own guarantee turned on itself.

**Parallelism.** `CLAUDE.md` warns this tree is shared and volatile. Each Worker runs in its own
git worktree on `qa/coverage-<package>` and rebases before PR; agents never share a directory.

### 4.3 Python core → A1

Ordered by measured uncovered mass:

| Package | Covered | Missing | Note |
|---|---|---|---|
| `coverage/` | 17.5% | 344 | worst in repo |
| `security/` | 23.1% | 173 | highest risk per uncovered line |
| `openclaw/` | 23.8% | 278 | |
| `reflector/` | 26.3% | 306 | |
| `healing/` | 27.0% | 297 | suggest-only invariant untested |
| `agents/` | 41.8% | 223 | |
| `validate/` | 45.3% | 255 | |
| `oracle/` | 46.1% | 146 | |
| `stages/` | 47.3% | 1,330 | largest absolute gap |
| `execution/` | 54.3% | 470 | |
| `cli/` | 60.6% | 1,367 | 48 commands |
| `substrate/` | 63.0% | 706 | tri-furcated routing |
| `web/` | 66.2% | 1,044 | |

Two targets deserve tests that **document a defect** rather than pave over it:

- **Tri-furcated LLM routing.** `substrate/provider.py:234` routes only some providers to the
  new modules; `substrate/client_factory.py:10` is a third entry point; `agents/routing.py:10`
  a fourth. Assert all four resolve identically for a given `PROVIDER` — expect failure, file
  the issue.
- **`TIERS` omits vision.** `core/settings.py:261-276` exposes only small+deep.

Property-based tests (`hypothesis`) go where the input space is large: `stages/ingest.py` (the
richness heuristic that silently dropped endpoints twice), `journeys/crud_detect.py`,
`journeys/executor.py` JSON-pointer capture, `substrate/text_utils.py`.

### 4.4 API, CLI, UI, gated surfaces

- **API (A4):** ~125 endpoints across 31 routers; 23 have contract tests, and those are both
  `testIgnore`d and unloadable. Per endpoint: happy path, each documented error, authz
  (anonymous / wrong role / right role), schema conformance via `schemathesis` against the
  app's own `/openapi.json`. Plus `/ws/live` (`web/api.py:59`) and both SSE streams
  (`routes/push_notify.py:26`, `routes/agents.py:52`) incl. disconnect and reconnect.
- **CLI (A4):** 48 top-level commands + 20 sub-groups. `CliRunner` for logic, real `subprocess`
  for exit codes and stream discipline. **Assert on `result.stdout`, never `result.output`** —
  under Click 8.4 `result.output` is the combined stream and hides banner corruption; four
  tests were already wrong this way (HANDOVER 2026-08-08). Also fix the unreachable
  `cherenkov testerarmy projects list` (four groups at `commands/testerarmy.py:15-135` are
  never attached) and the competing root group at `cli/__init__.py:8`.
- **React UI:** vitest across all 68 components with MSW; Playwright across all 7 routes and
  every alias redirect. **Contract pinning** — extend the one good existing idea,
  `qa/fallback-journey-parity.spec.ts`, which pins `src/journey/fallback.ts` against
  `GET /api/v1/journeys`. Apply that pattern to every hand-written mock so `api_mocks.ts` can
  never again drift from the real API.
- **Gated surfaces** (desktop / VS Code / mobile / k8s): in scope but honestly gated — they
  need hardware, emulators or signing keys CI does not have. Pretending otherwise is how
  `tauri-build.yml` came to be red since 2026-07-01. `TAURI_SIGNING_PRIVATE_KEY` is an **owner
  action**.

---

## 5. Phase 4 — Functional coverage (A6)

Branch coverage proves code *ran*. It does not prove the product *does what it says*. This repo
has a recorded history of that gap — `CHANGELOG.md`'s "Corrected" note under `[1.2.0]`, the
fabricated gate results in `docs/_archive/ROADMAP_RECONCILIATION.md`, and the standing rule
"Claims are not evidence" (`AGENTS.md:10`). Functional coverage closes it.

### 5.1 The claim inventory

Harvest every externally-visible behavioural claim into `docs/traceability/claims.yaml`, each
with a stable ID, source `file:line`, and a `test` field. All sources are machine-readable:

| Source | Count | Yields |
|---|---|---|
| `cli/commands/docs_cmd.py:33+` | 10 topics | each topic's `summary`, `commands` list and `notes` list — every `notes` line is a testable claim |
| `skills/*/SKILL.md` | 24 skills | frontmatter `description`, `scope`, `invariants`, `related_contracts` + Purpose prose |
| `AGENTS.md:16-19` | 4 invariants | D7, anti-lock-in, suggest-only healing, spec-derived status |
| `manifest.json` / `mcp.json` / `server.json` / `cherenkov-mcp.yaml` | 44 MCP tools | declared inputSchema and behaviour |
| `README.md`, `docs-site/`, `CHANGELOG.md` | — | shipped-feature claims |
| Phases 13–16 (`HANDOVER.md:15-18`) | SAML, RBAC, GDPR, SOC2, Spec Guardian, SLM training, Public API, Plugin SDK | claimed "verified and operational" |

**The gate:** `scripts/check_claim_coverage.py` fails when a claim has no linked passing test.
A claim may be explicitly marked `status: UNPROVEN` with a reason — that is honest and allowed.
A claim silently lacking a test is not. This will find real drift on day one:
`cherenkov-mcp.yaml:38` advertises `run_qwen_code_agent`, which has no implementation anywhere,
while `AGENTS.md:140` instructs agents to call it.

### 5.2 The four invariants get adversarial suites

Each of the product's load-bearing promises needs a test that *tries to break it*:

- **D7 — never auto-edit test code.** Run `validate`, `verify`, every `healing/*` path and the
  full repair loop against a checksummed corpus; assert every checksum unchanged.
- **Anti-lock-in.** `eject` output: zero `cherenkov` imports, `npm install` clean,
  `playwright test --list` non-zero, **and `npx tsc --noEmit` pass** — a known live failure
  (HANDOVER 2026-07-30) that no CI job checks today.
- **Suggest-only healing.** Assert no auto-commit and no auto-apply on every healing path.
- **Spec-derived status.** Mutate the spec's declared status codes; assert expectations follow
  the spec rather than a hardcoded assumption.

### 5.3 Test-design techniques the agents must apply

This is where "almost the same as real human coverage" is actually won. A model told to raise
coverage writes one test per branch; a human QA engineer applies design techniques. Each
Explorer contract must specify these, and the Reviewer must verify them.

| Technique | Applied to |
|---|---|
| **Equivalence partitioning** | valid / invalid / boundary classes per input, not one arbitrary value |
| **Boundary value analysis** | min−1, min, min+1, max−1, max, max+1 — e.g. `MAX_CONCURRENT_SCENARIOS` (`settings.py:83`), petstore length/quantity constraints |
| **Decision tables** | `verify --fail-on-divergence --json --output`, `generate --repair/--no-repair`, tier×provider×egress in `SubstrateRouter.route()` |
| **State transition** | all 6 `StepStatus` values (`journeys/contracts.py:31`) and the illegal transitions between them; HITL queue lifecycle; run lifecycle incl. every terminal path |
| **Pairwise / combinatorial** | 8 providers × 3 tiers × egress × fallback — full cross-product is wasteful; pairwise is the human choice |
| **Error guessing / negative** | malformed specs, OpenAPI 2.0, 3.0.x/3.1.x/3.2.x, empty spec, cyclic `$ref`, unicode, 10 MB spec |
| **CRUD lifecycle** | `crud_detect` families end-to-end incl. guaranteed teardown on success, failure and exception (`journeys/executor.py:301`) |

### 5.4 Spec-corpus functional matrix

Run the whole pipeline across `specs/corpus/`, `demos/conformance_corpus/` and the 10-spec
corpus M0 closed against, asserting **zero silent endpoint drops** — the exact regression class
`stages/ingest.py`'s richness heuristic caused twice. Extend to the GraphQL, gRPC and AsyncAPI
planners, which have `plan_*.py` modules and near-zero coverage.

---

## 6. Phase 5 — Real user experience coverage and assessment (A7)

Two distinct things, both required: **coverage** (did we walk every path a user walks?) and
**assessment** (was it any good?). Assessment is scored, trended, and regression-gated — a
pass/fail-only UX suite cannot tell you the product got worse.

### 6.1 Persona harness

The repo already defines its QA personas as agent archetypes (`.agents/qa_practitioner`,
`usability_qa_1`, `accessibility_qa`, `security_qa`, `automation_qa`). Make them executable —
each a YAML profile of goal, prior knowledge, constraints, success condition.

| Persona | Entry point | Success condition |
|---|---|---|
| First-time developer | `session_a_zero_to_hero.md`, cold, no config | first conformance verdict, unaided |
| QA lead | `session_b_live_case.md`, dashboard | Stripe/Prism mock → repair loop → HITL → eject |
| Evaluating exec | `session_c_pitch_companion.md` | 5-QA gate answered in <5 min |
| CI engineer | GitHub Action + `--json` | machine-readable verdict, correct exit code |
| Screen-reader user | keyboard + AT only | complete the core loop without a mouse |
| Returning user | second session, existing project | resume without re-onboarding |

HANDOVER 2026-08-06 flags that session B was verified against the *previous* IA and must be
re-verified before M1. This harness makes that permanent instead of a one-off.

### 6.2 Assessment metrics (scored, not pass/fail)

Recorded per persona run into `docs/ux/baseline.json`, trended, regression-gated:

| Metric | Definition | Gate |
|---|---|---|
| Task success rate | completed unaided / attempted | 100%, no regression |
| Time-to-first-value | cold start → first real verdict | per-persona budget, ±20% |
| Steps-to-complete | actual UI actions ÷ optimal path | ≤1.5× optimal |
| Error-recovery rate | recoverable errors survived without restart | 100% |
| Dead-end rate | states with no forward action and no way back | **0** |
| Console/network cleanliness | uncaught errors, failed requests | 0 |
| Cognitive-load proxy | interactive elements per screen | flag regressions |

### 6.3 Known UX defects to encode as tests now

Prior audits recorded real findings that no test guards. Convert each into a failing test
first, then fix:

- **The offline overlay can trap the user.** `usability_report.md` §1 — "CHECKING…" with no
  timeout and no bypass to settings or cached data if the backend never answers. A dead-end
  state, which §6.2 gates at zero.
- **No HTTP security headers.** `5_QA_REPORT.md` §2 — CSP, X-Frame-Options,
  X-Content-Type-Options, HSTS, Referrer-Policy all absent. Add a middleware test.
- **No `<noscript>` fallback; placeholder favicon** (`5_QA_REPORT.md` §5) on an SPA.
- **Correction to the record:** `5_QA_REPORT.md` §3's "no `data-testid` anywhere" is **stale** —
  measured 107 across 38 files. The real gap is the **30 of 68 components with none**. Close
  that, since every page object depends on it.

### 6.4 Experience coverage

- **Exploratory charters.** 8 already written at
  `qa/smoke-regression-exploratory.spec.ts:261-404`, currently unrunnable. Restore them, and
  let an Explorer agent propose new charters from `divergence/explorer.py` findings — that
  module already "observes, does not judge" (`explorer.py:14-15`), the right posture.
- **Accessibility.** Axe WCAG 2.1 AA on all 7 routes × theme × density; keyboard-only traversal
  of `g d`/`g a`/`g t`/`g m`/`g s` and the command palette; focus-trap and accessible-name
  assertions. **Remove the blanket `color-contrast` suppression** (`tests/a11y.spec.ts:36-38`,
  "dashboard theme is intentionally low-contrast") — either the theme meets AA or each
  exception is recorded per-element with a reason. An a11y suite that excludes the most
  commonly failed criterion is not an a11y suite.
- **Resilience.** Backend 500s, 401 mid-session, slow-3G, offline, WebSocket drop/reconnect,
  SSE interruption. Assert a real error state with a forward action — never a blank hub.
- **Visual regression + VLM assessment.** `toHaveScreenshot()` baselines per route × theme ×
  density × reduced-motion (none exist today). Layer on `SemanticVisualOracle`
  (`oracle/visual_oracle_vlm.py:15`) to judge *"does this screen look broken to a human?"* —
  catching overlap, clipping, invisible text and empty states that pixel diffs miss.
  `AGENTS.md:98` already mandates VLM over DOM scraping for visual validation. Nightly and
  advisory-only: it files issues, it never blocks a PR.

---

## 7. Phase 6 — Performance evaluation (A8)

The perf machinery is largely **already built and entirely unwired**: `K6Runner` +
`export_k6_script` (`execution/k6_runner.py:21,31`), `PerformanceAnalyzer`
(`execution/perf_analyzer.py:16`), `LatencyAnomalyDetector` with MAD-based robust center/scale
(`stages/perf/anomaly.py:42,57`), `AnomalyVerdict` (`:28`), `CostAccountant`
(`substrate/accounting.py:25`), `bench/eval-baseline.json`, and `POST /api/v1/perf/run`.
**No CI workflow runs any of it.** This phase is mostly wiring, not building.

### 7.1 Four performance domains

**(a) Target-API performance** — what the product measures *for* users. k6 profiles per
endpoint: smoke, load, stress, spike, soak. Assert p50/p95/p99 against declared budgets and
feed results to `LatencyAnomalyDetector` so regressions are detected statistically rather than
by a hand-picked threshold.

**(b) CHERENKOV's own runtime performance** — what the product costs its users, and the domain
with a proven regression history. `cherenkov verify` once ran the full probe sweep **twice**
per invocation: 63s → 9s on an 81-path spec after the fix (HANDOVER 2026-07-29). Nothing today
would catch that recurring.

| Operation | Budget source |
|---|---|
| `generate` per scenario | `GEN_TIMEOUT_S=120` (`settings.py:33`) |
| `verify` full sweep, 81-path spec | measured baseline ±20%; **assert probe count, not just wall-clock** — count is the invariant that catches double-sweeps |
| `certify`, `audit`, `check-suite` | measured baselines |
| Substrate call | `SUBSTRATE_MAX_LATENCY_MS=120000` (`settings.py:72`) |
| Scenario fan-out | `MAX_CONCURRENT_SCENARIOS=4` (`settings.py:83`) — assert actual parallelism matches |
| tsc / Playwright gates | `TSC_TIMEOUT_SECONDS=60`, `PLAYWRIGHT_TIMEOUT_SECONDS=120` |

**(c) Cost and token performance** — an LLM product's real budget. Wire `CostAccountant` and
the `tokens report`/`breakdown` commands into the perf gate: tokens and USD per scenario per
provider, asserted against `SUBSTRATE_MAX_COST_USD_PER_RUN` (`settings.py:71`) and trended in
`bench/eval-baseline.json` (which already carries `metrics`/`model`/`total_scenarios`). **A
prompt change that quietly doubles token spend is a performance regression.**

**(d) Frontend performance** — render budgets already exist at
`nonfunctional-suite.spec.ts:127-188` (per-screen budgets, command palette <500 ms, DOM node
count <2× after rapid navigation, sidebar <100 ms) and are unrunnable. Restore them, then add
Core Web Vitals (LCP/CLS/INP), a Lighthouse budget, and a bundle-size ceiling on `vite build`.

### 7.2 Scalability and resource behaviour

- **Spec scale:** 1 → 10 → 81 → 500 endpoints; assert sub-quadratic growth in time and memory.
  Ingest is where silent drops happened twice; scale is where they hide.
- **Concurrency:** HITL queue and reflector store under parallel writers — smoke tests exist
  (`smoke_test_hitl_concurrency.py`, `smoke_test_reflector_store_concurrency.py`) and neither
  is collected today (Phase 0.6).
- **Known multi-replica defect, documented but untested:** the rate limiter and APScheduler are
  per-process, so N replicas means N× the rate and N× the routine firings (HANDOVER
  2026-08-06). Encode as a failing test, then decide with the maintainer.
- **Soak:** 1-hour daemon run; assert flat memory and no fd leak.

### 7.3 Methodology (so the numbers mean something)

Perf gates are the easiest to make useless. Rules: dedicated non-parallel job on a fixed
runner; ≥5 runs compared on **medians**, never a single sample; regressions gated on the
anomaly detector's robust z-score, not a raw threshold; baselines committed to `bench/` and
updated only by an explicit, reviewed commit. Perf blocks on the Standard gate **only** for the
small budgeted core set; everything else runs in Deep and files issues.

### 7.4 Eject performance

Ejected suites must not just run — they must run fast enough to adopt. Assert `npm install` +
full ejected suite within budget, alongside the §5.2 correctness assertions.

---

## 8. Phase 7 — CI topology

| Gate | Trigger | Content | Blocking |
|---|---|---|---|
| **Fast** (<5 min) | every push | ruff, mypy, unit tests, vitest, coverage ratchet, integrity linter, claim-coverage (A6) | yes |
| **Standard** (<20 min) | every PR | full pytest + branch gate, API contract + schemathesis, Playwright E2E + axe, invariant suites, persona task-success (A7), core perf budgets (A8) | yes |
| **Deep** | nightly | mutation (A3), adversarial self-play (A5), all viewports, visual baselines + VLM, full k6 load/stress/soak, cost/token trend, scalability, mobile, k8s | no — files issues |
| **Release** | tag | desktop, VS Code, clean-VM install, eject + `tsc --noEmit` + eject perf | yes |

A perf gate that flakes gets ignored, and an ignored gate is worse than no gate — this repo
already has several. The 37 existing workflows need **consolidating, not extending**:
`supply-chain.yml` schedules zero jobs, and `qa-headless.yml` is nightly + label-gated only, so
**no UI test blocks any PR today**.

---

## 9. Verification

Done when each is reproducible from a clean clone:

1. `pytest tests/` — 0 failures, 0 uncollectible files.
2. `pytest tests/ --cov=cherenkov --cov-branch --cov-report=json` → 100% branch on core
   packages, ≥90% elsewhere, no file <75%.
3. `python scripts/mutation_gate.py` → kill rate ≥0.80.
4. `python scripts/check_test_integrity.py --all` → exit 0.
5. `python scripts/surface_coverage.py` → every endpoint, CLI command, UI route and journey
   step maps to ≥1 covering test.
6. `cd cherenkov/web/ui && npx playwright test --list` → >300 tests, 0 resolution errors;
   `npx playwright test` green; `npm run test:unit -- --coverage` ≥90%.
7. `python scripts/check_claim_coverage.py` (A6) → every claim resolves to a passing test or an
   explicit `UNPROVEN` with a reason. Plus the four invariant suites green.
8. `python scripts/ux_assess.py --all-personas` (A7) → task success 100%, dead-end rate 0, all
   metrics within tolerance — including the keyboard/screen-reader persona completing the loop.
9. `python scripts/perf_gate.py` (A8) → all budgeted operations within budget across ≥5 runs on
   medians; no anomaly; token/USD within tolerance. Specifically assert `verify`'s **probe
   count** on the 81-path spec — that is what catches a returning double-sweep.
10. Cold start: fresh container, no network → `cherenkov init && cherenkov doctor && cherenkov
    generate --no-repair && cherenkov verify` completes with honest output.
11. **Non-vacuity proof — the one that matters.** Revert 0.1's fix and confirm the suite goes
    red. Repeat with deliberate defects across every axis: weakened assertion, dropped field
    check, flipped status code via `demos/catch-the-ai-cheating/` (A3/A5); an undocumented flag
    and a removed feature (A6); a 300 ms delay injected into the probe loop and a doubled
    prompt (A8); a removed skip-link and a trapped-focus modal (A7). **Every one must turn
    something red.** A gate that cannot fail is not a gate — and `check_cli_flags.py`,
    `gen_manifest.py` and `spec-drift.yml` all reported green while never having executed.

---

## 10. Risks

- **Agent gaming the metric.** Mitigated by A3/A5 being deterministic and non-LLM, and by the
  integrity linter refusing coverage deltas that arrive with assertion deletions.
- **Uncovered code that should be deleted.** `substrate/providers/vlm.py` is self-documented as
  dead (`providers/__init__.py:15-17`); `cherenkov-mcp.yaml:38` advertises a
  `run_qwen_code_agent` tool with no implementation. Deleting beats covering — every
  0%-coverage file gets a delete/cover decision *before* any test is written.
- **`journeys/` is deprecated** (`DeprecationWarning`, `contracts.py:62-64`) while the
  orchestrator still runs through it. Needs a maintainer call before it is tested to 100%.
- **Flake.** Any test failing 1× in 100 nightly reruns is quarantined and issue-filed, never
  retried into green. Note `retries: 2` is already set for CI
  (`cherenkov/web/ui/playwright.config.ts:25`) — that hides flake rather than surfacing it, so
  quarantine must key off first-attempt results, not final status.
- **Perf gates are the easiest to make useless.** Shared runners make wall-clock noisy.
  Mitigated by median-of-5, robust z-score, invariant counters (probe count, token count) that
  are noise-free by construction, and a small blocking set.
- **UX assessment can drift subjective.** Mitigated by keeping the blocking metrics objective
  and countable. The VLM oracle, genuinely a judgment call, stays nightly and advisory.
- **The claim inventory can rot.** Mitigated by a second check that fails when a docs topic,
  skill frontmatter or MCP tool exists with no corresponding claim ID — the same
  inventory-drift shape as `test_manifest_matches_tools.py`.
- **M1 is untouchable.** Gate G0's E0.3 requires ≥3 real external practitioners. Nothing here
  simulates or approximates it.

**Out of scope (owner actions):** stale remote `claude/*` branches, the expired PAT,
`TAURI_SIGNING_PRIVATE_KEY`, and the Docker Hub / release-please credential gates.

---

## 11. Appendix — reproducing the baseline

```bash
# Python coverage baseline (64.78%). test_mcp_auth.py needs system cffi to collect.
pytest tests/ \
  -m "not slow and not e2e and not integration and not k8s and not ollama and not mobile" \
  --ignore=tests/unit/test_mcp_auth.py \
  --cov=cherenkov --cov-report=json:cov.json

# Collected test count (2,658 across 213 files)
pytest tests/ -m "not slow and not e2e and not integration and not k8s and not ollama and not mobile" \
  --ignore=tests/unit/test_mcp_auth.py --collect-only -q

# UI E2E collection — currently "Total: 0 tests in 0 files"
cd cherenkov/web/ui && npx playwright test --list

# Written-but-uncollectible E2E count (308 across 19 spec files)
cd cherenkov/web/ui/tests && grep -rhcE "^\s*test\(" --include='*.spec.ts' . | paste -sd+ | bc

# Confirm no frontend unit-test runner exists
grep -rl "vitest\|jest" --include=package.json . | grep -v node_modules
```
