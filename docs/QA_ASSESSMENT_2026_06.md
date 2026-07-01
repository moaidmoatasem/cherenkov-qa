# CHERENKOV — Full QA Assessment Report
**Date:** 2026-06-05 · **Assessor:** Claude Code (claude-sonnet-4-6)
**Scope:** Business readiness · QA Engineer UX · Technical depth

---

## TL;DR

The core engine is **architecturally clean and technically solid**. The design invariants hold.
The blockers are not code — they are **human-facing friction** (first run requires a GPU, review is
terminal-only, no demo mode) and the still-open **5-user validation gate**. The built-ahead scope
(Horizon 2, Track B/C re-integrated into the live tree) creates a maintenance burden and a
credibility problem that must be resolved before any external launch.

**Verdict: Not production-ready. Close to demo-ready. One focused sprint away from the validation gate.**

---

## 1. Business Assessment

### 1.1 Value Proposition

**Strength:** The core tagline is defensible and differentiated:
*"Spec in, Playwright tests out, zero lock-in."*

The real innovation is the **triage wedge** — not "found a diff" but "this is a real bug vs an
intended change." No current open-source tool does this. The anti-lock-in eject is a meaningful
trust signal for risk-averse QA teams.

**Weakness:** The value is not demonstrated to any human yet. No QA practitioner outside the
project has run the tool and said "yes." The validation gate (5 attributable users) is wide open.
Without it, every business claim — market fit, pricing, launch readiness — is hypothesis, not fact.

### 1.2 Market Position

Nearest competitors: Optic, Schemathesis, Dredd, Portman.

| Tool | Approach | CHERENKOV difference |
|------|----------|----------------------|
| Schemathesis | Fuzzing | CHERENKOV generates human-readable Playwright tests, not random payloads |
| Optic | Diff-reporting | CHERENKOV generates executable conformance tests + ejects them |
| Dredd | Test runner | CHERENKOV writes the tests; Dredd requires you to |
| Portman | Newman-based | CHERENKOV targets Playwright (browser-native, trace-rich) |

The gap nobody owns: **spec→ejectable typed Playwright API test, localhost-first, no account**.
CHERENKOV is in that gap. The risk is that the gap is a niche, not a market — the validation gate
answers that question.

### 1.3 Monetization Readiness

**Not ready.** The monetization plan in the archived docs (Pro tier, Enterprise, SaaS) rests on
the fabricated "4/5 passed" gate. Do not plan pricing until ≥3 real QA practitioners confirm value.
The right sequence: validate → understand real pain points → price against the pain that matters.

### 1.4 Business Risks

| Risk | Severity | Status |
|------|----------|--------|
| Validation gate still open | **Critical** | No real users. Entire value claim is unproven. |
| Scope contradiction in live tree | High | Track B/C re-integrated without gate. Confuses agents + maintainers. |
| GPU dependency on first run | High | Kills demos on any machine without Ollama. |
| Fabricated prior claims in docs | Medium | HANDOVER §5 retracted the fake "4/5". Agents will hallucinate from old cached context. |
| Narrow spec support (JSON only) | Medium | Real-world APIs ship YAML. Blocks honest evaluation. |

---

## 2. QA Engineer UX Assessment

### 2.1 The Golden Path Today (honest audit)

Sam (QA engineer, has a spec and staging server, no GPU):

| Step | Command | State | Friction |
|------|---------|-------|----------|
| Install | `pip install` + `npm install` | ✅ works | Node + Python required. Not friction-free. |
| Onboard | `cherenkov init` + `cherenkov doctor` | ✅ works | Doctor flags missing Ollama clearly |
| **Generate** | `cherenkov generate` | ❌ **blocked** | **Requires Ollama + qwen2.5-coder:7b. No demo mode.** |
| Validate | `cherenkov validate --target <url>` | ✅ works | Good output. tightening suggestions useful. |
| Review | `cherenkov hitl approve <id>` | ⚠️ awkward | Terminal HITL is agent-friendly, human-hostile. No web UI wired. |
| Eject | `cherenkov eject --output <dir>` | ✅ works | Clean. The anti-lock-in promise holds. |

**First-run success rate without GPU: ~0%.** Generate is the core command and it hard-requires
Ollama. A no-Ollama demo mode that replays a cached generate run on the bundled petstore target is
the single highest-leverage UX fix.

### 2.2 Review Loop Friction

The HITL review loop (`hitl list / show / approve / reject`) is correct for CI/agent use.
For a human QA engineer it is hostile:
- Requires knowing `scenario_id` strings
- No visual representation of the generated test
- No "why was this flagged?" explanation surfaced inline
- No way to compare generate-vs-validate output without digging into files

The web dashboard exists (deferred, `track-b-c-deferred/dashboard/`) and the backend is
partially wired (`cherenkov/web/api.py`). The one missing piece: replace mock data with real
`HitlQueue` and real validate findings. That is a wiring task, not a build task.

### 2.3 Documentation & Discoverability

| Item | State |
|------|-------|
| README.md | ✅ Honest, short, clear |
| GETTING_STARTED.md | ✅ Covers 14 commands; validated by CI docs-drift-gate |
| CLI `--help` | ✅ All 27 subcommands present |
| `doctor` preflight | ✅ Surfaces missing Ollama / Node / npm |
| "What does validate output mean?" | ⚠️ Tightening suggestions explained inline but no doc |
| "Why did this get flagged for HITL?" | ❌ Not surfaced to user |
| Demo / quickstart with no Ollama | ❌ Does not exist |

### 2.4 Windows / Cross-Platform

Two bugs fixed in this session (PR #212, merged):
- `npx` not found on Windows (was `FileNotFoundError` in subprocess)
- `←` character in `profile show` caused `UnicodeEncodeError` on cp1252/cp850 consoles

Remaining cross-platform risk: no Windows CI coverage. The validate/eject path is untested on
Windows. All CI runs on Ubuntu.

### 2.5 UX Summary Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| First-run (with GPU) | 7/10 | Works; init+doctor are good; generate succeeds |
| First-run (no GPU) | 1/10 | Blocked at generate with no fallback |
| Review UX | 4/10 | Terminal-only; no visual; no "why?" |
| Eject UX | 9/10 | Clean, works, anti-lock-in proven |
| Validate UX | 8/10 | Good output; tightening suggestions are useful |
| Docs | 7/10 | Honest and current; missing demo mode guidance |
| Cross-platform | 5/10 | Linux/Mac OK after PR #212; Windows untested |

---

## 3. Technical Assessment

### 3.1 Core Architecture (Track A)

**Strong.** The INGEST→PLAN→GENERATE→REVIEW pipeline is clean:
- Pydantic contracts at every boundary — no silent schema corruption
- Circuit breaker with configurable threshold
- Retry ladder (3 attempts per stage)
- D2 loop: Prism dry-run failure routes back to PLAN (not generate again blindly)
- 6-gate review (syntax → structure → AST → assertions → tsc → Prism)
- Design invariants enforced by automated tests (suggest-only healing, spec-derived status, anti-lock-in eject)

The orchestrator is the kind of code you can hand to a new engineer and they understand it.

### 3.2 Gap Between Plan and Reality

| Planned | Reality | Impact |
|---------|---------|--------|
| PLAN uses deepseek-r1:8b LLM | PLAN is deterministic Python | Medium — deterministic is fine for now; misleads doc readers |
| Gate 4: Novelty embedding (`nomic-embed-text`) | Not implemented | Low — deduplication gap, not a correctness gap |
| Gate 6: LLM quality review | Not implemented | Medium — manual HITL compensates; gap in automation |
| SQLite for HITL queue | SQLite exists in `hitl/store.py` but not wired into CI generate flow | Medium — terminal HITL works; CI generate doesn't persist |
| `json-schema-faker` for payloads | Not integrated (prompt-driven) | Low — works without it |
| YAML spec support | JSON only | **High — real APIs ship YAML** |

### 3.3 Scope Ledger Contradiction

The live `cherenkov/` tree contains ~18 packages that were added before the validation gate
(Horizon 2: `substrate/`, `reflector/`, `divergence/`, `copilot/`, `governance/`, `mcp/`,
`openclaw/`, `federation/`, `coverage/`, `sdet/`, `truth/`, `oracle/`, `continuity/`,
`stages/visual/`, `stages/perf/`, etc.). These are:
- Built and unit-tested
- **Not validated by any real user**
- In contradiction with the "Track A only" governing docs

This is not a code quality problem — the code is fine. It is a **project governance problem**:
working code in permanent contradiction with its own docs. Every agent touching the repo will
either over-count or under-count the product's scope depending on which doc they read first.

**Resolution required (owner decision):** Formally adopt the expanded scope (rewrite HANDOVER/AGENTS)
OR re-quarantine (move built-ahead packages back, resolve the Track B duplicate). Doing neither
is the actual problem.

### 3.4 Test Coverage Quality

- **41 smoke tests** cover every major module. All deterministic (no real Ollama dependency).
- **33+ unit tests** with mocked LLM. Fast, reliable.
- **1 live-LLM test** (opt-in, self-hosted GPU) — the real generate path is untested in standard CI.
- **Gap:** If the generator prompt drifts, no CI gate catches it until a human runs `generate`.
- **Gap:** Windows path never tested in CI.
- **Gap:** Smoke tests are standalone scripts, not in a pytest/unittest runner — hard to parallelize,
  no shared fixtures, no coverage reporting.

### 3.5 Dependency Health

```
Python core:   pydantic==2.7.1, requests, pyyaml     — minimal, good
Node dev:      @playwright/test ^1.60.0, typescript ^5, openapi-typescript ^7, openapi-fetch ^0.17
Optional:      fastapi, uvicorn, k6, docker/prism
```

Minimal for the core. The Node + Python dual-runtime is a setup friction point but unavoidable for
a tool that generates Playwright TypeScript.

### 3.6 Technical Debt Inventory

| Item | File(s) | Severity |
|------|---------|----------|
| YAML spec support missing | `cherenkov/stages/ingest.py` | High |
| `cherenkov_validate.py` reference now removed ✅ | smoke_test_validate.py | Fixed |
| PLAN doc says LLM, code is deterministic | `cherenkov/stages/plan.py`, docs | Medium |
| Gate 4 (novelty) + Gate 6 (LLM quality) absent | `cherenkov/stages/review.py` | Medium |
| Smoke tests not in pytest runner | root `smoke_test_*.py` | Low |
| No Windows CI | `.github/workflows/ci.yml` | Medium |
| CORS allow-all in web API | `cherenkov/web/api.py` | Low (localhost tool) |
| `track-b-c-deferred/` duplicates live tree | `stages/visual/`, `execution/perf*/` | Medium |

---

## 4. Roadmap Update

The existing `docs/ROADMAP_NEXT.md` is correct and well-reasoned. This assessment **confirms and
sharpens** its priorities. No new phases are added — the existing 4 phases are right.

### Confirmed Priority Order

**Phase 0 — Wire the review loop (1 week)**
The single action with the highest leverage: wire `cherenkov/web/api.py` to real `HitlQueue` +
real validate findings, and add `cherenkov review --web` to launch it. This turns the dashboard
from mock-wired dead code into the validation vehicle. Exit: screen-recorded golden path.

**Phase 1 — Kill first-run friction (1–2 weeks)**
1. YAML spec support (blocks real-world testing)
2. No-Ollama demo mode (runs cached petstore generate result; no GPU needed)
3. Prebuilt `dist/` for web UI (no `npm` for end user)
4. Windows CI coverage (prevents regression)

**Phase 2 — Validation gate (owner-led)**
5 real QA practitioners, attributable evidence. The only milestone that matters.

**Phase 3 — Earned expansion (post-gate only)**
Driven by rejection-reason data from the FE. Likely first: chained CRUD journeys and drift-watch.

### One Addition to the Roadmap

**Formally close the scope contradiction.** The owner must decide: adopt the expanded tree or
re-quarantine. This is a blocking prerequisite for Phase 3 expansion because you cannot build
confidently on a codebase where the governing docs and the code disagree.

---

## 5. Bugs Fixed in This Session

| # | Bug | File | Fix |
|---|-----|------|-----|
| 1 | `smoke_test_validate.py` called non-existent `cherenkov_validate.py` | `smoke_test_validate.py:46` | Changed to `cherenkov.py validate` |
| 2 | `self-test` and `report` commands undocumented → docs-drift CI failure | `docs/GETTING_STARTED.md` | Added Command 13 + 14 |
| 3 | REGRESSION_MODE BUG 2 returned 500 (FastAPI response_model) | `target/target_api.py` | Use `JSONResponse` directly |
| 4 | `get_queue()` ignored `CHERENKOV_HITL_DB` env var → broke test isolation | `cherenkov/web/api.py` | Read env var before constructing queue |
| 5 | `validate-smoke` job missing from CI | `.github/workflows/ci.yml` | Added job with Node.js + Playwright |
| 6 | `stub/*_tests/` gitignore blocked committed fixtures | `.gitignore` | Replaced with specific artefact ignores |
| 7 | Trace path only collected for failing tests | `cherenkov/execution/playwright_invoke.py` | Moved attachment collection outside status block |
| 8 | `behavioral-diff` job missing `permissions: pull-requests: write` | `.github/workflows/behavioral-diff.yml` | Added permission |
| 9 | `npx` not found on Windows (bare string, shell=False) | 6 files + new `cherenkov/core/compat.py` | `npx()` helper via `shutil.which` |
| 10 | `←` in `profile show` → UnicodeEncodeError on Windows consoles | `cherenkov/stages/profile_cmd.py` | Changed to ASCII `<-` |
