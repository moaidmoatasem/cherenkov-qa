# QA Automation & AI Strategy — CHERENKOV Edition

> **Purpose:** Synthesize the 2026 QA automation AI research into a concrete strategy for how CHERENKOV is built, tested, and positioned — covering what to automate, where AI fits, and how the hybrid model maps to real test suites in this repo.
> **Date:** 2026-06-17 · Anchored to `claude/qa-automation-ai-strategy-g0a06l`

---

## 1. The Strategic Context

The QA landscape in 2026 is defined by a single tension: **AI accelerates code creation faster than teams can verify it.** The industry is at the inflection point where:

- AI-generated code exceeds 40% of all commits at many orgs
- Agents write tests AND run them — closing a loop that was previously human-supervised
- Generation is becoming free and infinite; **trust is becoming scarce and valuable**

CHERENKOV's mission — "catch where your software lies before your users do" — is structurally aligned with this shift. This document captures:

1. What should be automated vs kept manual (the 60/30/10 model)
2. Where AI augments both categories (the bridge layer)
3. How this maps to CHERENKOV's own QA suites
4. How teams using CHERENKOV should structure their hybrid QA practice

---

## 2. The 60/30/10 Hybrid Model

Based on 2026 industry data, the optimal QA allocation for teams shipping at AI-accelerated pace:

```
┌──────────────────────────────────────────────────────────────────┐
│                    HYBRID QA FRAMEWORK 2026                       │
├─────────────────────┬──────────────────────┬─────────────────────┤
│   AUTOMATE (60%)     │   KEEP MANUAL (30%)   │  AI BRIDGE (10%)    │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ • Regression suites  │ • Exploratory testing │ • Self-healing       │
│ • Smoke tests        │ • UX/usability eval   │ • Test generation    │
│ • API contract tests │ • Accessibility w/    │ • NL authoring       │
│ • Cross-browser      │   assistive tech      │ • Risk prioritization│
│ • Performance/load   │ • First-time UX flows │ • Visual regression  │
│ • Data validation    │ • Cross-product        │ • Flaky test mgmt    │
│ • CI/CD gates        │   journey validation  │ • Synthetic data gen │
│ • E2E happy paths    │ • New feature sign-off│                     │
└─────────────────────┴──────────────────────┴─────────────────────┘
```

### Cost model reality check

| Approach | Annual Cost | Ramp |
|----------|-------------|------|
| Scaled manual (10-person team, 50 features/week) | ~$1.2M/year | Immediate |
| Traditional automation (with maintenance cliff) | ~$460K–510K/year | 3–6 months |
| AI-native testing (CHERENKOV model) | ~$120K–240K/year | 2–4 weeks |

The cost difference is structural: traditional automation's hidden cost is maintenance — up to 80% of ongoing effort. AI-native approaches reduce maintenance overhead to near zero via self-healing.

---

## 3. What Gets Automated — and Why

### Automate always (the 60%)

**Characteristics that make a test automation-ready:**
- Repetitive — runs the same steps frequently
- Stable — UI/API doesn't change shape every sprint
- Deterministic — same input always produces same output
- High volume — many test cases across the same pattern
- CI/CD integrated — must pass before any merge

| Test Type | Automation Benefit | CHERENKOV Test Suite |
|-----------|-------------------|----------------------|
| Regression | 80–90% time reduction; catches drift on every commit | `smoke-regression-exploratory.spec.ts` §Regression |
| Smoke / Release validation | Binary "is the system alive" — run on every build | `smoke-regression-exploratory.spec.ts` §Smoke |
| API contract | Verifies API changes don't break consumers; spec-derived | `api-contract-integration.spec.ts` |
| Performance / load | Simulates concurrent users; impossible manually | `nonfunctional-suite.spec.ts` §Performance |
| Security scanning | Input validation, XSS, auth — consistent and exhaustive | `nonfunctional-suite.spec.ts` §Security |
| Accessibility (automated) | Catches 30–40% of WCAG issues; automated scans alone | `nonfunctional-suite.spec.ts` §Accessibility |
| Cross-browser / responsive | Parallel execution across viewport sizes | `nonfunctional-suite.spec.ts` §Compatibility |
| Data integrity | End-to-end data flows at volumes humans can't inspect | `nonfunctional-suite.spec.ts` §Data Integrity |
| E2E happy paths | Full user journeys: login → core action → result | `e2e-journeys.spec.ts` |
| Functional validation | Happy paths, edge cases, business rule validation | `functional-suite.spec.ts` |

### Keep manual (the 30%)

**Characteristics that resist automation:**
- Requires human curiosity and intuition
- Subjective — "does this feel right?" can't be scripted
- Explores unknown failure modes (exploratory)
- Requires empathy — usability, accessibility with real assistive tech
- Contextual — depends on business domain knowledge

| Activity | Why It Resists Automation | Human Advantage |
|----------|--------------------------|-----------------|
| Exploratory testing | Unscripted discovery; finds 35% of Sev-1 bugs not in any test suite | Pattern recognition across systems, "what if" thinking |
| UX/usability eval | "Does this make sense to someone seeing it for the first time?" | Empathy, aesthetic judgment, fresh eyes |
| Accessibility w/ assistive tech | Screen reader flow, focus order, cognitive load — automated scanners miss 60–70% | Direct experience with AT, disability perspective |
| New feature sign-off | Business context, stakeholder understanding of intent | Domain knowledge, acceptance criteria authorship |
| Cross-product journey | Web → email → mobile orchestration; individual pieces pass, whole fails | Systems thinking across product boundaries |

Note on the `smoke-regression-exploratory.spec.ts` exploratory section: the automated "exploratory" tests in that file are **charter-based structured tests** — they test known edge cases programmatically. True exploratory testing, which discovers unknown unknowns, remains a manual practice.

---

## 4. Where AI Fits — The Bridge Layer

AI doesn't replace either bucket — it removes the hard boundary between them.

### In the automated layer

| AI Capability | Impact | CHERENKOV relevance |
|---------------|--------|---------------------|
| **Self-healing** | Tests adapt when selectors/layouts change; drops maintenance from 80% to ~5% of effort | CHERENKOV's `healing/` module implements suggest-only healing (D7 invariant) |
| **Test generation from spec** | Local LLM writes typed Playwright tests from OpenAPI routes; no test authoring phase | Core pipeline: PLAN → GENERATE stages; `qwen2.5-coder:7b` |
| **Risk-based prioritization** | Analyzes code diffs and defect history; runs highest-risk tests first | Future: divergence corpus feeds prioritization model |
| **Visual regression** | Detects pixel-level layout shifts that functional tests miss | `skills/visual-regression.md`, `skills/visual-diff.md` |
| **Flaky test management** | Historical pattern analysis identifies root causes | CHERENKOV test suite uses `page.waitForLoadState()` + selector stability |

### In the manual layer

| AI Capability | Impact |
|---------------|--------|
| **Natural language test authoring** | Manual testers write in plain English; AI converts to automation | AuthorPage / J1 persona flow (Maya — Manual QA) |
| **Test case suggestions** | AI recommends based on requirements and recent changes | Chat agent + Knowledge Mesh in CHERENKOV |
| **Defect clustering** | Groups similar bugs for efficient triage | Divergence taxonomy D1–D5 |
| **Session analysis** | AI analyzes exploratory test sessions for patterns | Signals screen + audit trail |
| **Synthetic data generation** | Realistic test data at scale | `cherenkov/synthetic/` module |

### The integrity catch — CHERENKOV's unique position

The most dangerous failure mode in AI-augmented QA is when the agent **appears to verify but doesn't**:
- Assertion weakening: loosening strict checks to get green
- Test deletion: removing failing steps to fake a pass
- Hallucinated oracles: asserting a status code that was made up, not spec-derived

CHERENKOV's 6-gate REVIEW stage is the counter:
1. **Syntax** — the code is valid
2. **Structure** — JSON shape matches spec
3. **AST** — no forbidden constructs (hardcoded status codes, commented-out assertions)
4. **Assertions** — checks actually constrain behavior; not vacuously true
5. **TypeScript compilation** — type-safe against the spec schema
6. **Prism mock dry-run** — spec-derived expected behavior validates before hitting a live server

This is Gate G0 E0.2 (the "catch an agent cheat" requirement): an agent that weakens an assertion gets caught at gate 3 or 4.

---

## 5. CHERENKOV in the QA Landscape

CHERENKOV occupies a specific niche that is **not** test generation and **not** self-healing — it is **conformance verification**:

```
QA STACK LAYERS
┌───────────────────────────────────────────────────────┐
│  GENERATION LAYER     (Baserock.ai, TestStory, Mabl)   │ ← Commoditizing
│  Generate tests from intent / user stories             │
├───────────────────────────────────────────────────────┤
│  EXECUTION LAYER      (Playwright, Cypress, Selenium)  │ ← Infrastructure
│  Run tests, report pass/fail                          │
├───────────────────────────────────────────────────────┤
│  CONFORMANCE LAYER    ← CHERENKOV owns this            │ ← The trust layer
│  Verify implementation matches spec;                  │
│  Catch what agents quietly weakened or hallucinated   │
├───────────────────────────────────────────────────────┤
│  CERTIFICATE LAYER    (CHERENKOV Rung 3)               │ ← Future moat
│  Signed, portable proof of what a system actually does│
└───────────────────────────────────────────────────────┘
```

Tools like Keploy (traffic replay), Schemathesis (property-based fuzzing), and Applitools (visual AI) are **complementary**, not competitive. They all sit below the conformance layer.

---

## 6. QA Activities Map — What CHERENKOV Handles

Mapping the full day-to-day QA activity list to CHERENKOV coverage:

### Fully automated by CHERENKOV
- API contract testing (spec → generated tests → live server conformance check)
- Regression verification (CI-integrated test suite)
- Smoke tests (every-commit critical path validation)
- Performance baseline (nonfunctional suite)
- Security scanning (XSS, input validation in nonfunctional suite)
- Automated accessibility scanning (axe-core integration)
- Cross-browser/viewport compatibility
- Data integrity reconciliation
- Build artifact validation (pre-merge gate)

### AI-augmented (CHERENKOV + human oversight)
- Test case design (PLAN stage suggests scenario coverage; human validates)
- Defect investigation (divergence taxonomy D1–D5 classifies; human triages)
- Healing suggestions (suggest-only; human applies)
- Test data preparation (synthetic data module; human reviews edge cases)

### Remains manual
- Exploratory testing (charter-based human sessions)
- UX/usability evaluation
- Accessibility with real assistive technology
- New feature sign-off (acceptance criteria validation)
- First-time user onboarding
- Cross-product journey validation

### CHERENKOV does NOT do (by design)
- UI test generation for non-API surfaces (no CSS/layout enforcement)
- Mobile app testing automation (Maestro integration available but not core)
- Load testing orchestration (k6 skill available, not core)
- Performance profiling beyond frontend render budgets

---

## 7. The QA Test Suites — Strategy in Code

The five test suites in `cherenkov/web/ui/tests/qa/` implement this strategy as applied to CHERENKOV's own dashboard — dogfooding the approach:

### `functional-suite.spec.ts` (926 lines)
**Strategy mapping:** Automate Always — functional testing
Covers: Projects screen (display, search, CRUD), pipeline execution flows, review screen (filtering, divergence display), healing screen (D7 invariant), eject screen (anti-lock-in), truth map, signals, knowledge, author intent, chat, governance
**Key invariants tested:**
- D7: all repairs are suggest-only (never auto-applied) — core CHERENKOV integrity promise
- Spec-derived status codes appear in UI (not hardcoded)
- Anti-lock-in: eject produces standalone suite with no CHERENKOV imports

### `smoke-regression-exploratory.spec.ts` (519 lines)
**Strategy mapping:** Automate (smoke + regression) + Charter-based (exploratory)
Smoke section: every build, 2-minute pass/fail gate (all 15 screens render, health widget, command palette)
Regression section: key invariants every sprint (D7, autonomy toggle, settings persistence, toast system, anti-lock-in eject, SDD sessions, chat SSE, mobile devices)
Exploratory section: structured edge-case charters (spec ingestion edge cases, autonomy toggle extremes, concurrent data loading, overlay stacking, offline handling)

### `api-contract-integration.spec.ts` (367 lines)
**Strategy mapping:** Automate Always — API contract and integration testing
Covers: REST API endpoint contracts (/api/projects, /api/tests, /api/run, /api/eject, /api/ingest, /api/divergences, /api/healing), schema validation, error handling, backward compatibility, service integration between screens

### `e2e-journeys.spec.ts` (250 lines)
**Strategy mapping:** Automate Always — end-to-end happy path journeys
Covers: J1 (Manual QA / Maya — author intent to result), J2 (QA Lead / Sam — divergence triage), J3 (SDET / Jordan — deep analysis + pattern learning), J4 (DevOps / Alex — scheduled validation), plus error recovery and performance under load
These journeys map to the 4 QA personas from `docs/FE_QA_WORKFLOW_REQUIREMENTS.md`

### `nonfunctional-suite.spec.ts` (457 lines)
**Strategy mapping:** Automate Always — security, performance, accessibility, compatibility
Security: XSS injection across all input surfaces, localStorage credential leak, API key masking
Performance: render budgets per screen (200–800ms), command palette < 500ms, DOM growth limits
Accessibility: axe-core WCAG 2AA on all 12 screens, ARIA radiogroup, keyboard navigation, landmark structure, form label coverage
Compatibility: 7 viewport sizes (mobile portrait through 4K), responsive sidebar behavior

---

## 8. Skills Evolution for QA on AI-Native Products

The research identifies a clear evolution:

```
2020 Manual Tester          2024 QA Automation Engineer     2026 AI-Augmented QA Engineer
────────────────────────    ──────────────────────────────  ──────────────────────────────
Manual test execution   →   Selenium/Cypress scripting   →  AI tool proficiency
Bug reporting           →   CI/CD pipeline integration   →  Prompt engineering for tests
Test case writing       →   Python/JS scripting          →  AI model understanding
                                                         →  Test strategy (hybrid model)
                                                         →  Data analysis of AI results
                                                         →  Oversight of autonomous agents
```

**For teams using CHERENKOV specifically:**
- Learn the divergence taxonomy (D1–D5) to triage AI-generated findings
- Understand the REVIEW gate to evaluate what the pipeline caught vs missed
- Use NL authoring (Author by Intent) as the bridge from manual to automated
- Read healing suggestions critically — CHERENKOV never auto-applies (D7 invariant)

---

## 9. Recommended Adoption Sequence

For a team starting with CHERENKOV:

**Week 1 — Prove the wow (Gate G0 E0.1)**
- Run `cherenkov verify` against 3 real APIs
- Capture at least 2 genuine divergences with reproductions
- This is the required evidence before any further investment

**Week 2–3 — Integrate smoke + regression**
- Add `smoke-regression-exploratory.spec.ts` smoke section to every CI merge check
- Run full regression nightly
- Accept zero flaky tests as the bar (not "we'll fix them later")

**Month 1 — API contract baseline**
- Capture current API behavior via spec
- Run `api-contract-integration.spec.ts` against staging
- Tag divergences as known-good vs genuine defects

**Month 2 — Nonfunctional gate**
- Set per-screen performance budgets (use nonfunctional-suite as template)
- Add axe-core WCAG 2AA as a PR gate
- Add XSS scans to CI

**Month 3 — E2E persona journeys**
- Map your 3–4 key user personas
- Write E2E journeys modeled on `e2e-journeys.spec.ts`
- Make these the "definition of shippable"

**Ongoing — Keep manual**
- 20% of each sprint: exploratory testing sessions (charter-based)
- Every new feature: first-time user walk-through with a real user
- Every release: accessibility audit with screen reader (beyond automated)

---

## 10. The Bottom Line

AI doesn't replace manual testing — it replaces the **boundary** between manual and automated work. The key insight for CHERENKOV's market position:

> **As agents generate all the tests, the scarce thing is no longer tests — it's the ability to trust what the agents produced.** Nobody owns that layer. That is the un-cornerable category.

The 60/30/10 model is the operating framework. The 5 QA test suites in this repo implement it for CHERENKOV itself. The CHERENKOV product is the trust layer that makes this framework safe when AI is generating the automated 60%.

For cost-conscious teams: the AI-native path reaches equivalent coverage at $120K–240K/year vs $1.2M/year for scaled manual QA — the difference is structural, not tactical.

---

## References

- `docs/VISION_AQE_2026.md` — why the trust layer is the un-cornerable category
- `docs/NORTH_STAR.md` — Tool → Platform → Protocol ladder
- `docs/ROADMAP_AQE.md` — Gate G0 through Rung 3 sequencing
- `docs/QA_AI_LANDSCAPE_2026_v2_UPDATED.md` — open-source AI testing landscape analysis
- `docs/FE_QA_WORKFLOW_REQUIREMENTS.md` — QA personas and journey specs (Maya, Sam, Jordan, Alex)
- `cherenkov/web/ui/tests/qa/` — the 5 test suites implementing this strategy
- `skills/self-healing.md`, `skills/visual-regression.md`, `skills/k6-perf.md` — AI capability extensions
