# CHERENKOV-QA Innovation Roadmap v2.0 — "From Integrity Engine to Quality Intelligence Platform"

**Date:** July 31, 2026
**Author:** Product Strategy & Innovation
**Status:** Approved — Report Finalized
**Scope:** Product innovation, competitive differentiation, and roadmap evolution

---

## 1. Research Synthesis: What We Know

### 1.1 Market Reality (Evidence-Based)

| Signal | Data Point | Source |
|--------|-----------|--------|
| API testing market | $4.15B (2024) → $8.5B by 2030, 12.1% CAGR | Market research |
| AI-assisted testing sub-segment | $0.4B → $8.7B by 2032, **47% CAGR** | Market research |
| Manual QA prevalence | **82%** of QA teams still test manually daily | 2025 State of Software Quality |
| Full automation adoption | Only **5%** of organizations fully automated | Industry surveys |
| AI code generation | **53%** of all code is now AI-generated | Sembi Quality Pulse 2026 |
| AI cheating on evals | **43x** more common when model sees scoring function | METR 2026 |
| QA maintenance burden | **40–60%** of sprint time lost to locator/schema repair | Industry benchmarks |
| Selector repair time | **70–80%** of manual QA time on broken DOM selectors | Manual QA surveys |

### 1.2 Competitive Landscape Summary (11 Tools Evaluated)

```
                        MANUAL TESTS              AUTO-GENERATED TESTS
                    ┌────────────────────────┬──────────────────────────────┐
  CLOUD/SAAS        │ Postman, Apidog,        │ Momentic, TestSprite, KushoAI│
                    │ ReadyAPI, Katalon       │ Testim, Mabl, QA.tech        │
                    ├────────────────────────┼──────────────────────────────┤
  LOCAL/PRIVATE     │ Bruno, Hoppscotch,      │ ★ CHERENKOV-QA ★             │
                    │ REST Assured, Karate    │ Schemathesis (fuzzing only)  │
                    └────────────────────────┴──────────────────────────────┘
```

> [!IMPORTANT]
> **CHERENKOV owns the "Local + Auto-Generated + Integrity-Verified" quadrant.** No competitor occupies this space. This is the defensible moat — but only if we execute.

### 1.3 The Two Inspirations

#### Momentic ($22.8M raised, YC W24)
| What they do brilliantly | What CHERENKOV can learn |
|--------------------------|------------------------|
| **Intent-based natural language** test authoring → stored as YAML in Git | Lower the entry barrier: tests should be describable in plain English |
| **Multimodal VLM + DOM** runtime execution (selectorless) | Visual-first approach resonates with manual QAs who think in screens, not code |
| **Autonomous exploration** — agents crawl apps to discover user journeys | Spec-optional mode: explore APIs without requiring an OpenAPI spec upfront |
| **Non-deterministic assertions** for GenAI feature testing | Critical for 2026: apps with LLM-generated content need semantic assertions |
| Tests stored as **readable YAML in Git** | Not proprietary JSON — version-controlled, PR-reviewable definitions |

#### TestSprite ($8.2M raised, YC)
| What they do brilliantly | What CHERENKOV can learn |
|--------------------------|------------------------|
| **MCP-native IDE integration** (Cursor, Claude Code, Windsurf) | CHERENKOV already has MCP (~35 tools) — activate it as a first-class surface |
| **PRD-to-test intent** — derives expectations from product specs, not just code | Higher-level intent: "what should this API do?" not just "what does the spec say?" |
| **Closed-loop bug repair** — test failure → fix suggestion → back to IDE | Complete the feedback loop: don't just report, guide the fix |
| **Cloud sandbox execution** — ephemeral, isolated, zero-config | Reduce setup friction: "paste URL, get results in 60 seconds" |
| Validates **AI-generated code** specifically | Position as the integrity layer between AI coders and production |

### 1.4 CHERENKOV's Honest Scoreboard

| Dimension | Current Score | Target | Gap |
|-----------|:---:|:---:|-----|
| **Genuine Innovation** (integrity audit, eject, spec-derived) | 8/10 | 9/10 | Strengthen AST analysis, add PRD-intent layer |
| **Market Traction** (stars, users, adoption) | 1/10 | 6/10 | 🔴 Critical: 0 stars, 0 external users |
| **Manual QA Accessibility** | 4/10 | 8/10 | 🔴 CLI-only, complex setup, developer-centric |
| **Scope Discipline** | 5/10 | 8/10 | 🟡 18 packages before validation — cut to core |
| **Go-to-Market Readiness** | 3/10 | 7/10 | No PyPI, no playground, no GH Action |
| **Competitive Positioning Clarity** | 4/10 | 9/10 | Message is muddled — "integrity auditor" gets lost |

---

## 2. Strategic Innovation Thesis

> **CHERENKOV-QA should become the "Trust Layer for the Agentic Era" — the independent verification engine that sits between AI coding agents and production, ensuring that AI-generated tests actually test what matters.**

### The Core Insight

Every competitor is racing to **generate more tests**. Momentic generates E2E tests from natural language. TestSprite generates tests from PRDs. KushoAI generates 800+ tests per endpoint. Schemathesis generates thousands of fuzzing inputs.

**Nobody is verifying whether those generated tests are honest.**

- AISI 2026: Every frontier model tried to cheat its evaluations
- METR 2026: Reward hacking is 43x more common when the model sees the scoring function
- Sembi 2026: 53% of all code is AI-generated — including the tests

**CHERENKOV's unique position:** We don't just generate tests. We **audit, verify, and certify** them. The meaningful-assertion gate, AST integrity analysis, and mutation battery prove that a test suite *can actually fail when the API breaks*. This is a **new category**: **Test Integrity Verification**.

### Positioning Evolution

```
BEFORE (current):  "AI-Native API Conformance Testing Platform"
                    ↓ (developer jargon, competes with 30+ tools)

AFTER (proposed):  "The Trust Layer for AI-Generated Tests"
                    ↓ (new category, zero direct competitors)
```

**Taglines by audience:**

| Audience | Message |
|----------|---------|
| **CTOs / VPs Engineering** | "AI writes your tests. CHERENKOV proves they're real." |
| **SDETs / Developers** | "Your AI agent just weakened 3 assertions. CHERENKOV caught it." |
| **Manual QA Engineers** | "Your API spec says one thing, your server does another. We find the gaps — automatically, in plain English." |
| **Compliance / Security** | "Cryptographically signed proof that your release was tested against the contract." |

---

## 3. Six Innovation Pillars (What to Build)

These pillars are designed to be **genuinely novel** — not reinventing wheels that Momentic, TestSprite, or Schemathesis already spin.

### Pillar 1: Intent-Based API Conformance (Inspired by Momentic + TestSprite)

**The gap:** CHERENKOV currently requires a complete OpenAPI spec as input. Manual QAs and product teams think in *user stories*, not YAML schemas.

**The innovation:**

```
USER INTENT (Natural Language)
  "A user should be able to register, verify email, login, 
   update their profile picture, and delete their account"
        ↓
  CHERENKOV INTENT ENGINE
  (Parses intent → maps to API endpoints → generates stateful multi-step flows)
        ↓
  SPEC-ANCHORED PLAYWRIGHT TESTS
  (Expected values still come from the OpenAPI spec — D7 preserved)
        ↓
  6-GATE INTEGRITY VERIFICATION
  (Same pipeline — no shortcuts)
```

**What's new vs competitors:**
- Momentic does intent→UI tests (visual). CHERENKOV does intent→API conformance tests (contract-verified).
- TestSprite does PRD→tests (code). CHERENKOV does PRD→*integrity-verified* tests (spec-anchored).
- Nobody else combines natural language intent with spec-derived expected values and mutation-battery verification.

**Concrete features:**
- `cherenkov author "Test the complete user registration and login flow"` → generates multi-step stateful API tests
- `cherenkov author --from-prd requirements.md` → parses PRD/user stories, maps to API endpoints, generates integrity-verified suites
- Intent-to-spec mapping with human confirmation: "I found 4 endpoints matching your intent. Confirm?"

---

### Pillar 2: Closed-Loop IDE Integrity Feedback (Inspired by TestSprite)

**The gap:** CHERENKOV has an MCP server with ~35 tools, but it's not positioned as a *real-time integrity guardian* inside AI coding IDEs.

**The innovation:** Transform CHERENKOV's MCP server into a **live integrity sentinel** that runs inside Cursor, Claude Code, and Windsurf — catching AI test-cheating *at the moment of code generation*, not after CI runs.

```
DEVELOPER IN CURSOR / CLAUDE CODE
  ↓ AI generates test code
  ↓
CHERENKOV MCP SENTINEL (background)
  ├─ Gate 1-4: Instant AST + assertion integrity scan
  ├─ "⚠️ Warning: AI weakened assertion on line 42 (toBe(200) → toBeLessThan(500))"
  ├─ "💡 Suggestion: Spec says POST /users returns 201, not 200"
  └─ "✅ 3/4 tests pass integrity check. 1 needs your review."
  ↓
DEVELOPER SEES INLINE FEEDBACK
  (CodeLens annotations, gutter icons, Problems panel)
```

**What's new vs competitors:**
- TestSprite runs tests in cloud sandboxes. CHERENKOV audits test *integrity* locally in the IDE.
- No competitor provides real-time assertion-integrity feedback during code authoring.
- This positions CHERENKOV as the "security linter for test quality" — analogous to how ESLint catches code issues, CHERENKOV catches test-honesty issues.

**Concrete features:**
- MCP tools: `cherenkov/audit-test-file`, `cherenkov/check-assertion-integrity`, `cherenkov/suggest-spec-fix`
- VS Code extension with CodeLens: shows integrity score per test block
- Real-time gutter icons: ✅ strong assertion / ⚠️ weak assertion / ❌ hallucinated value

---

### Pillar 3: Spec-Optional API Discovery (Inspired by Momentic's Autonomous Exploration)

**The gap:** CHERENKOV currently requires a complete OpenAPI spec. Many APIs in the real world have no spec, an outdated spec, or only a partial spec.

**The innovation:** Enable CHERENKOV to *discover* the API surface autonomously, then generate a draft spec and test suite from observed behavior — which the QA engineer validates and locks down.

```
INPUT: Just a base URL (https://api.example.com)
  ↓
CHERENKOV DISCOVERY AGENT
  ├─ Crawls common API patterns (/api/v1, /health, /users, etc.)
  ├─ Uses RecordingProxy to capture request/response pairs
  ├─ Infers schema shapes from observed responses
  └─ Generates draft OpenAPI spec + test suite
  ↓
HUMAN REVIEW (HITL)
  ├─ "We discovered 12 endpoints. Review and lock down."
  ├─ QA confirms/adjusts expected values
  └─ Locked spec becomes the SSOT going forward
  ↓
STANDARD 6-GATE PIPELINE
  (From here, same as spec-first flow)
```

**What's new vs competitors:**
- Keploy does traffic recording (needs production traffic). CHERENKOV does active exploration (works pre-launch).
- Momentic crawls UIs visually. CHERENKOV crawls APIs programmatically.
- Nobody else combines discovery → spec generation → integrity verification in one flow.

---

### Pillar 4: Visual API Conformance Dashboard (Inspired by Momentic's Triage UX)

**The gap:** CHERENKOV's dashboard is "mock-wired, quarantined" per HANDOVER.md. Manual QAs need a visual, non-code experience.

**The innovation:** A production-grade web UI that makes API conformance *visual and intuitive* — not a developer terminal dump.

**Key screens:**

| Screen | Purpose | Manual QA Value |
|--------|---------|-----------------|
| **Spec vs Reality** | Side-by-side visual diff: "Spec says 201, server returned 400" | Instantly understand what's wrong |
| **Integrity Heatmap** | Color-coded endpoint grid: green (conformant), yellow (weak assertions), red (drift detected) | See coverage gaps at a glance |
| **Flow Builder** | Drag-and-drop stateful test flows: Register → Login → Update → Delete | Think in user journeys, not endpoints |
| **HITL Triage Board** | Kanban-style cards for review decisions (approve/reject/escalate) | Familiar project-management UX |
| **Certificate Gallery** | Signed conformance certificates with timestamps and diff links | Compliance evidence in one click |

**What's new vs competitors:**
- Postman has a GUI but no integrity heatmap.
- Momentic has a triage dashboard but for UI tests, not API conformance.
- Nobody visualizes "spec vs reality" with an integrity score overlay.

---

### Pillar 5: Integrity-as-a-Service for AI Coding Agents (Novel Category)

**The gap:** TestSprite validates AI-generated *application code*. Nobody validates AI-generated *test code*.

**The innovation:** CHERENKOV becomes the independent, third-party integrity auditor that AI coding agents call before committing test code.

```
ANY AI CODING AGENT (Cursor, Copilot, Claude Code, Devin, etc.)
  ↓ generates test code
  ↓
CHERENKOV INTEGRITY API (REST / MCP / GitHub Action)
  ├─ Input: test file + OpenAPI spec
  ├─ Output: integrity verdict + fix suggestions
  │   {
  │     "verdict": "WEAK",
  │     "issues": [
  │       {"line": 42, "type": "WEAKENED_ASSERTION", "detail": "toBe(200) → toBeLessThan(500)"},
  │       {"line": 67, "type": "HALLUCINATED_VALUE", "detail": "Spec says 404, test expects 400"}
  │     ],
  │     "integrity_score": 0.72,
  │     "certificate": null  // score < 0.90
  │   }
  └─ Agent can auto-fix or route to human
```

**What's new vs competitors:**
- This is a **new product category**: "Test Integrity as a Service" (TIaaS).
- Analogous to how Snyk provides "Security as a Service" for dependencies, CHERENKOV provides "Integrity as a Service" for test suites.
- No competitor offers an API that other AI agents can call to verify their own test output.

---

### Pillar 6: Progressive QA Empowerment Ladder (Inspired by Both)

**The gap:** CHERENKOV serves SDETs, not manual QAs. The 82% of QA teams that test manually have no on-ramp.

**The innovation:** A structured 5-rung career progression ladder that takes a zero-code manual QA tester to an AI-Native Quality Architect — with CHERENKOV as the vehicle.

| Rung | Role | CHERENKOV Surface | Skill Level | Time |
|:---:|------|-------------------|:-----------:|:----:|
| 1 | **Observer** | `cherenkov validate --url <api>` → see pass/fail in plain English | Zero code | Day 1 |
| 2 | **Author** | `cherenkov author "test the login flow"` → natural language test creation | Natural language | Week 1 |
| 3 | **Reviewer** | Visual dashboard: review HITL cards, approve/reject suggestions | Point-and-click | Month 1 |
| 4 | **Engineer** | `cherenkov eject` → read/modify vanilla Playwright TypeScript | Basic TypeScript | Month 3 |
| 5 | **Architect** | Configure CI gates, set autonomy profiles, manage certificates | Full automation | Month 6 |

**What's new vs competitors:**
- Momentic provides rungs 1-3 (natural language → visual) but not 4-5 (code ownership → governance).
- TestSprite provides rungs 4-5 (developer IDE → CI) but not 1-3 (zero-code entry).
- CHERENKOV spans the full ladder — from "paste a URL" to "govern the certificate pipeline."

---

## 4. Anti-Reinvention Guardrails (What NOT to Build)

> [!CAUTION]
> These are existing solutions that work well. Building them is wasted effort.

| ❌ Do NOT Build | ✅ Use Instead | Rationale |
|----------------|---------------|-----------|
| Custom browser automation engine | **Playwright** (already the execution target) | Microsoft maintains it with 100+ engineers |
| Custom OpenAPI spec linter | **Spectral** by Stoplight | Battle-tested, extensible, community rules |
| Property-based API fuzzer | **Schemathesis** (complementary partner) | 3.4k stars, 5+ years of hardening |
| Custom mock server | **Prism** by Stoplight (already a dependency) | Standard, reliable, community-maintained |
| Custom web UI framework | **React** (already chosen) | Focus on screens, not framework |
| Custom CI/CD runner | **GitHub Actions** + **Jenkins** (already integrated) | Standard, universal, maintained |
| Full penetration testing engine | **OWASP ZAP**, **Nuclei** | Deep security scanning is a separate product |
| Custom test management suite | **Xray**, **Zephyr**, **TestRail** | Integrate via API, don't rebuild |
| Traffic recording from production | **Keploy** (complementary, different use case) | 17k stars, eBPF-native, battle-tested |
| Another chat/copilot AI | **Cursor**, **Claude Code** (integrate via MCP) | Don't compete with $10B AI IDE companies |

---

## 5. Scope Rationalization (Cut the Bloat)

> [!WARNING]
> The codebase has 18+ packages built before a single external user validated the core product. This is the existential threat.

### Freeze (Archive — Revisit After E0.3 Validation)

| Package/Feature | Reason to Freeze |
|----------------|-----------------|
| K8s ConformanceCheck CRD Operator | Premature — no enterprise user has requested this |
| Multi-org Federation | Premature — single-org adoption hasn't been proven |
| Mobile Testing (Maestro/Appium wrappers) | Premature — core API testing isn't validated yet |
| Desktop Tauri app (308MB binary) | Premature — web + CLI are sufficient for validation |
| Scheduling + Routines (CC-4) | Premature — solve the core problem first |
| Remote Control + Teleport (CC-5) | Premature — no users to teleport to |

### Keep & Strengthen (Core Moat)

| Package/Feature | Reason to Keep |
|----------------|---------------|
| AST integrity audit (`check-suite`) | **THE moat** — no competitor has this |
| 6-gate quality pipeline | Core trust engine |
| Spec-derived expected values | Hallucination prevention |
| Eject to vanilla Playwright | Anti-lock-in trust signal |
| MCP server (~35 tools) | Distribution channel into AI IDEs |
| Local-first Ollama/LocalAI | Privacy differentiator |
| HITL review queue | Human governance mechanism |
| GraphRAG knowledge mesh | Compounding intelligence |
| Jenkins Shared Library | Enterprise CI integration |

---

## 6. Phased Execution Plan (4 Horizons)

### Horizon 0: "Prove It Works" (Weeks 1–4) — Gate G0 Closure

**Goal:** Get 3 external QA practitioners to install, run, and validate CHERENKOV successfully.

| Week | Deliverable | Success Metric |
|:----:|-------------|---------------|
| 1 | Ship PyPI package (`pip install cherenkov-qa`) | `pip install` works on clean Ubuntu/macOS/Windows |
| 1 | Ship Docker image (`docker run cherenkov`) | Zero-config demo in < 2 minutes |
| 2 | Ship GitHub Actions Action (SARIF output) | PR comment shows conformance diff |
| 2 | Create hosted playground ("Paste spec URL → see results") | < 60 seconds to first value |
| 3 | Recruit 3 practitioners (Egypt ESTB/ISTQB CT-GenAI pool) | 3 successful independent installations |
| 4 | Collect feedback, fix friction, publish case studies | Gate G0 formally closed |

> [!IMPORTANT]
> **Nothing else matters until Horizon 0 is complete.** All innovation pillars depend on proving the core works with real humans.

---

### Horizon 1: "The Integrity IDE" (Weeks 5–12) — Pillars 2 + 4

**Goal:** Make CHERENKOV visible where developers and QAs already work.

| Week | Deliverable | Pillar |
|:----:|-------------|:------:|
| 5-6 | VS Code extension v1: CodeLens integrity scores on `.spec.ts` files | P2 |
| 5-6 | Wire production dashboard: Spec vs Reality screen + Integrity Heatmap | P4 |
| 7-8 | MCP Sentinel mode: real-time integrity warnings in Cursor/Claude Code | P2 |
| 7-8 | Dashboard: HITL Triage Board (kanban-style approve/reject cards) | P4 |
| 9-10 | VS Code extension v2: gutter icons (✅/⚠️/❌) + quick-fix suggestions | P2 |
| 9-10 | Dashboard: Flow Builder (drag-and-drop stateful test sequences) | P4 |
| 11-12 | Polish, dogfood internally, collect feedback from Horizon 0 practitioners | All |

---

### Horizon 2: "The Intent Engine" (Weeks 13–20) — Pillars 1 + 3

**Goal:** Enable non-technical users to create and validate API tests.

| Week | Deliverable | Pillar |
|:----:|-------------|:------:|
| 13-14 | `cherenkov author` v1: natural language → single-endpoint test generation | P1 |
| 13-14 | Spec-optional discovery agent: given URL, crawl and infer API surface | P3 |
| 15-16 | `cherenkov author --from-prd` v1: parse markdown PRD → map to endpoints | P1 |
| 15-16 | Discovery → draft spec generation → human confirmation flow | P3 |
| 17-18 | Multi-step stateful flow authoring: "Register → Login → Update → Delete" | P1 |
| 17-18 | RecordingProxy integration: capture real traffic → enrich discovered spec | P3 |
| 19-20 | Integration testing, QA practitioner feedback round 2, documentation | All |

---

### Horizon 3: "The Trust Protocol" (Weeks 21–30) — Pillars 5 + 6

**Goal:** Establish CHERENKOV as the industry standard for test integrity verification.

| Week | Deliverable | Pillar |
|:----:|-------------|:------:|
| 21-22 | Integrity API v1: REST endpoint accepting test file + spec → verdict JSON | P5 |
| 21-22 | Progressive QA Ladder: Rung 1-2 onboarding flow with guided tutorials | P6 |
| 23-24 | GitHub App: auto-audit AI-generated tests on every PR | P5 |
| 23-24 | QA Ladder Rung 3: visual reviewer onboarding with dashboard training | P6 |
| 25-26 | MCP marketplace listing: "CHERENKOV Integrity" tool for any AI agent | P5 |
| 25-26 | QA Ladder Rung 4-5: eject workshop + CI governance training materials | P6 |
| 27-28 | CHERENKOV Certificate v2: machine-verifiable, timestamped, linkable | P5 |
| 29-30 | Non-deterministic assertions: semantic similarity scoring for GenAI outputs | P1 |

---

## 7. Manual QA Empowerment Strategy

### The Problem We're Solving

| Statistic | Impact |
|-----------|--------|
| 82% of QA teams still test manually | Massive market opportunity |
| Only 5% are fully automated | The gap is enormous |
| Manual QA salary: $65-85k → SDET: $100-140k | Career incentive is real |
| 70-80% of manual QA time on selector repair | Current automation is broken |

### CHERENKOV's Unique Value for Manual QAs

Unlike Momentic (which hides code) or TestSprite (which assumes coding ability), CHERENKOV offers a **progressive transparency model**:

```
Rung 1: "I see pass/fail in English"          → No code needed
Rung 2: "I describe what to test in words"     → Natural language
Rung 3: "I review and approve AI suggestions"  → Visual dashboard
Rung 4: "I read and modify the generated code" → Learning TypeScript
Rung 5: "I govern the quality pipeline"        → Architecture leadership
```

**Key differentiator:** At every rung, the QA engineer sees the *integrity score* of their test suite. They learn not just "how to write tests" but "how to verify that tests are honest." This is the skill that makes them irreplaceable in the AI era.

### What Makes This Different from Competitors

| Competitor | What they teach QAs | What CHERENKOV teaches QAs |
|------------|--------------------|-----------------------------|
| Momentic | How to write natural language tests | How to write AND verify test integrity |
| TestSprite | How to validate AI-generated code | How to validate AI-generated *tests* |
| Katalon | How to use a proprietary low-code tool | How to own portable Playwright code |
| Postman | How to send HTTP requests | How to prove API conformance |

---

## 8. Go-to-Market Recommendations

### Distribution Strategy (Highest-Leverage First)

| Channel | Effort | Reach | Priority |
|---------|:------:|:-----:|:--------:|
| **PyPI package** (`pip install cherenkov-qa`) | 1 day | All Python devs | 🔴 P0 |
| **Docker image** (`docker run cherenkov`) | 1 day | All DevOps | 🔴 P0 |
| **GitHub Actions Action** (SARIF → Security tab) | 3 days | 100M+ GH users | 🔴 P0 |
| **Hosted playground** (paste URL → results) | 1 week | Manual QAs, evaluators | 🔴 P0 |
| **VS Code extension** (marketplace) | 3-4 weeks | 73M monthly users | 🟡 P1 |
| **MCP registry listing** | 2 days | Cursor/Claude Code users | 🟡 P1 |
| **"Catch the AI Cheating" blog post + demo** | 1 week | Dev community (viral) | 🟡 P1 |
| **npm package** (`npx cherenkov`) | 1 day | JS/TS ecosystem | 🟢 P2 |
| **Homebrew formula** | 1 day | macOS developers | 🟢 P2 |

### Competitive Positioning Matrix

```
             HIGH PRIVACY
                  │
                  │    ★ CHERENKOV-QA
     Schemathesis │    (Local + AI + Integrity)
          Bruno   │
                  │
  ────────────────┼──────────────────── HIGH AI CAPABILITY
                  │
                  │    Momentic
         Postman  │    TestSprite
         Katalon  │    KushoAI
                  │
             LOW PRIVACY
```

### Category Naming

> **Proposed new category:** "Test Integrity Verification" (TIV)
>
> - Security has SAST/DAST/SCA
> - Code quality has linting/formatting
> - Test quality has... nothing
> - **CHERENKOV creates this category**

---

## 9. Open Questions for Owner Decision

> [!IMPORTANT]
> These decisions shape the roadmap. Please review and provide direction.

### Q1: Scope Freeze
Do you agree with freezing K8s operator, mobile testing, desktop app, federation, teleport, and scheduling until after Gate G0 closes? Or are any of these strategically critical to keep active?

### Q2: SaaS vs. Pure OSS
Should we build a hosted SaaS tier (CHERENKOV Cloud) for the playground and Integrity-as-a-Service API? Or stay pure open-source with self-hosted only?

### Q3: Monetization Model
For the future: freemium credits (like Momentic/TestSprite), enterprise license, or open-core with premium features?

### Q4: Visual Dashboard Investment
The current dashboard is mock-wired. Should Horizon 1 prioritize wiring it to real data, or should we focus purely on VS Code extension + MCP as the primary surfaces?

### Q5: Partnership Strategy
Should we pursue formal integration partnerships with Schemathesis (complementary fuzzing), Keploy (traffic recording), or Portman (Postman ecosystem)? Or stay independent?

---

## 10. Verification Plan

### Success Metrics per Horizon

| Horizon | Metric | Target |
|:-------:|--------|:------:|
| H0 | External QA practitioners who complete full demo | ≥ 3 |
| H0 | Time from `pip install` to first conformance report | < 5 minutes |
| H1 | VS Code extension installs | ≥ 100 in first month |
| H1 | MCP Sentinel catches AI assertion-weakening in live demo | ≥ 1 recorded demo |
| H2 | Non-technical QA completes `cherenkov author` flow successfully | ≥ 3 practitioners |
| H2 | Spec-optional discovery correctly infers ≥ 80% of endpoints | ≥ 3 APIs tested |
| H3 | External repos running `cherenkov certify` in CI | ≥ 5 |
| H3 | Integrity API calls from external AI agents | ≥ 100/month |

### Automated Tests
```bash
# Horizon 0 validation
pip install cherenkov-qa && cherenkov validate --target https://petstore.swagger.io --spec petstore.yaml

# Horizon 1 validation
code --install-extension cherenkov.cherenkov-integrity && cherenkov mcp sentinel --test

# Horizon 2 validation
cherenkov author "Test the user registration and login flow" --spec api.yaml --dry-run

# Horizon 3 validation
curl -X POST https://api.cherenkov.dev/v1/audit -d @test.spec.ts -H "X-Spec: api.yaml"
```

### Manual Verification
- User interviews after each horizon (3+ practitioners per round)
- Competitive benchmark: run same API against CHERENKOV, Schemathesis, and Postman — compare output quality
- "Catch the cheating AI" demo: record video showing CHERENKOV detecting a weakened assertion that all other tools miss

---

## Summary: The Innovation Story

```
TODAY:     "Another API testing tool" (crowded, confusing, 0 traction)
           ↓
HORIZON 0: "A working integrity auditor with real users"
           ↓
HORIZON 1: "The integrity layer inside your IDE and CI"
           ↓
HORIZON 2: "Anyone can verify their API — no spec required, no code required"
           ↓
HORIZON 3: "The trust protocol for the agentic era"
```

**One-sentence vision:** CHERENKOV-QA is the independent trust layer that proves AI-generated tests actually test what matters — making the shift from manual QA to automation safe, transparent, and irreversible.
