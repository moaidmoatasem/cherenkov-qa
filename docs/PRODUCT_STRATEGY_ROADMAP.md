# CHERENKOV-QA: Product Strategy & Market Roadmap

> **Think big. Innovate. Deliver value. Change the market.**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Where We Stand — Current State Audit](#2-where-we-stand)
3. [Market Analysis](#3-market-analysis)
4. [Competitive Landscape](#4-competitive-landscape)
5. [Pain Points We Uniquely Solve](#5-pain-points-we-uniquely-solve)
6. [Open Source Integration Opportunities](#6-open-source-integration-opportunities)
7. [Growth Strategy](#7-growth-strategy)
8. [Scaling Architecture](#8-scaling-architecture)
9. [Revenue Model](#9-revenue-model)
10. [Next Phases — Detailed Roadmap](#10-next-phases-detailed-roadmap)
11. [The 10-Year Vision](#11-the-10-year-vision)
12. [Recommended Immediate Next Steps](#12-recommended-immediate-next-steps)

---

## 1. Executive Summary

**CHERENKOV-QA** is an AI-native API conformance testing platform. It ingests OpenAPI specifications, uses a local LLM to generate typed Playwright API tests, executes them against real servers, and delivers conformance violation reports — all with zero vendor lock-in (tests eject to vanilla Playwright on demand).

The product is **production-ready** at its core (Track A complete, validated 2026-06-08). Six parallel tracks span API testing, mobile testing, a React dashboard, a chat agent, a K8s operator, and a VLM layer.

**The opportunity is asymmetric.** The API testing market is $5B and growing at 27% CAGR toward $41B by 2032. Every existing tool requires manual test writing. CHERENKOV is the first to automate the full loop: *spec → tests → conformance report → tightening suggestions* — locally, privately, at zero incremental cost per test.

The recommended play: **open core + community flywheel → enterprise K8s tier → AI testing platform**. The window to define the "AI-native API testing" category is now.

---

## 2. Where We Stand

### 2.1 Delivered (Production-Ready)

| Track | Capability | Status |
|-------|-----------|--------|
| A — Core | OpenAPI ingest → LLM → typed Playwright tests | ✅ Complete, validated |
| A — Core | 6-gate review (syntax, AST, tsc, Prism) | ✅ Complete |
| A — Core | Conformance validation against real server | ✅ Complete |
| A — Core | Value-assertion tightening engine | ✅ Complete |
| A — Core | Suggest-only healing (never auto-edits) | ✅ Complete |
| A — Core | Eject to vanilla Playwright (zero lock-in) | ✅ Complete |
| A — Core | OWASP mutation payloads (DAST lite) | ✅ Complete |
| B — VLM | LocalAI/Ollama tier routing (small/deep/vision) | ✅ Complete |
| B — VLM | Offline-first LLM (qwen2.5-coder:7b default) | ✅ Complete |
| B — VLM | Visual oracle (VLM-powered screenshot analysis) | ✅ Complete |
| A — Knowledge | GraphRAG second brain (verdicts, idioms, incidents) | ✅ Complete |
| A — Chat | Chat agent with tool-calling + SSE streaming | ✅ Complete |
| E — Dashboard | React dashboard (9 screens) | ✅ Complete |
| F — K8s | ConformanceCheck CRD + Go operator | 🔶 In Progress |
| C — Desktop | Tauri 2 desktop app | ⏸ Blocked (needs cargo) |
| D — Mobile | Maestro/Appium mobile execution | ⏸ Blocked (needs ADB) |

### 2.2 Technical Moat (What Makes This Hard to Copy)

1. **Spec-derived expected values** — LLM generates test *structure*, spec provides expected *values*. Hallucination-resistant by design.
2. **Suggest-only healing invariant** — A safety-first constraint that builds deep developer trust. Baked into architecture, not bolted on.
3. **Clean architecture throughout** — Ports/adapters pattern; every data store, LLM provider, and test format is swappable.
4. **6-gate review pipeline** — Tests must pass syntax, structure, AST, assertion, tsc, and Prism mock gates before touching a real server.
5. **Anti-lock-in eject** — One command strips all CHERENKOV imports. This is a trust-builder that competitors won't copy (it's against their business model).
6. **K8s operator with CRD** — First-class Kubernetes citizen. `ConformanceCheck` as a native resource.

### 2.3 What's Missing Before Market Launch

| Gap | Priority | Effort |
|----|---------|--------|
| Public documentation site (docs.cherenkov.dev) | P0 | 1 week |
| Frictionless quickstart (single `npx cherenkov init`) | P0 | 2 days |
| GitHub Actions marketplace action | P0 | 3 days |
| Demo video (2-min product tour) | P0 | 2 days |
| Landing page (cherenkov.dev) | P0 | 1 week |
| VS Code extension | P1 | 2 weeks |
| Hosted demo (no install required) | P1 | 1 week |
| Changelog + versioning policy | P1 | 1 day |

---

## 3. Market Analysis

### 3.1 Market Size & Growth

| Segment | 2024 Size | 2032 Projection | CAGR |
|---------|-----------|-----------------|------|
| API Management (broad) | $7.4B | $41.2B | 27% |
| API Testing Tools (focused) | $1.8B | $9.2B | 22% |
| AI-Assisted Testing (nascent) | $0.4B | $8.7B | 47% |
| Developer Tools / DevTools SaaS | $12B | $38B | 15% |

**The CHERENKOV opportunity sits at the intersection of AI-Assisted Testing and API Testing** — the fastest-growing sub-segment, with no dominant incumbent.

### 3.2 Macro Tailwinds

1. **API explosion**: Every modern product is API-first. 90% of developer activity touches APIs daily.
2. **AI-native tooling wave**: GitHub Copilot proved developers will adopt AI assistants. The next frontier is AI-native *verification*, not just generation.
3. **Spec drift is endemic**: As teams scale, OpenAPI specs and server implementations diverge silently. No existing tool catches this automatically.
4. **Privacy-first cloud fatigue**: Enterprises increasingly reject SaaS-only tools. Local LLM (Ollama) is a massive enterprise differentiator.
5. **K8s as default runtime**: 78% of cloud workloads run on Kubernetes. Native K8s operator = zero integration friction for enterprise.
6. **Developer-led buying**: Bottom-up SaaS wins. Engineers discover, use, and champion tools. Then procurement follows.

### 3.3 ICP (Ideal Customer Profile)

**Primary ICP: Backend/Platform Engineer at a 50-500 person tech company**
- Maintains 5-50 microservices, each with OpenAPI specs
- Writes some API tests but coverage is thin
- Hates the ceremony of test maintenance when specs change
- Loves tools that "just work" from the terminal
- Will try an open source tool before advocating internally

**Secondary ICP: QA Lead / SDET at enterprise (500+ eng)**
- Responsible for API coverage across dozens of services
- Has a CI/CD pipeline and wants tests to run there
- Needs audit trails, compliance, RBAC
- Will champion enterprise licensing if the open tier wins them

**Tertiary ICP: DevOps/Platform Eng building internal developer platforms**
- Wants to standardize API testing across all teams
- Loves K8s operators (native to their mental model)
- Will deploy the ConformanceCheck CRD cluster-wide

---

## 4. Competitive Landscape

### 4.1 Direct Competitors

| Tool | Strength | Weakness | CHERENKOV Advantage |
|------|---------|---------|---------------------|
| **Postman** | Ubiquitous, great UX, huge community | Manual test writing, SaaS lock-in, no LLM generation, $29-99/mo | LLM generation, local-first, zero lock-in, free |
| **Dredd** | CLI, OpenAPI-to-test, simple | Deprecated/slow, no LLM, no healing, no mobile | Active development, LLM-native, full pipeline |
| **Schemathesis** | Property-based, Hypothesis-powered, good CLI | Python only, random-ish, no LLM, no mobile, no dashboard | Typed generated tests, spec-derived values, multi-platform |
| **Pact** | True contract testing, language-native | Requires both consumer AND provider, complex setup | One-sided (spec-only), zero setup, no coordination needed |
| **Keploy** | Traffic replay, record & playback | Needs live traffic, no spec-first, Go-only native | Spec-first (no traffic needed), multi-language |
| **OWASP ZAP** | Security scanning, DAST | UI/web only, not API-type-safe, complex | API-specific, typed, embedded OWASP payloads |
| **Stoplight Spectral** | Spec linting, rules engine | Linting only, not test execution, no LLM | Full execution, healing, generation |
| **APIfox** | All-in-one Chinese tool, good UX | SaaS, China-hosted, limited enterprise features | Local-first, privacy-safe, K8s native |
| **k6** | Performance testing, JS DSL, great OSS | Performance only, not conformance, manual scripts | Conformance focus, LLM-generated, zero-script |

### 4.2 Indirect Competitors (Adjacent)

- **GitHub Copilot** — Generates test code but doesn't run it, validate it, or tie it to specs
- **TestRigor** — English-language test generation, SaaS, UI focused
- **Katalon** — All-in-one, SaaS, heavy
- **ReadyAPI (SmartBear)** — Enterprise, expensive, not AI-native

### 4.3 Whitespace Map

```
                    MANUAL TESTS          AUTO-GENERATED TESTS
                ┌──────────────────────┬─────────────────────────┐
  CLOUD/SAAS    │  Postman, APIfox,     │    (nobody owns this    │
                │  ReadyAPI, Katalon    │     space at scale)     │
                ├──────────────────────┼─────────────────────────┤
  LOCAL/PRIVATE │  Dredd, Schemathesis, │  ★ CHERENKOV-QA ★       │
                │  Pact, RestAssured   │    (unique position)    │
                └──────────────────────┴─────────────────────────┘
```

**CHERENKOV owns the most defensible quadrant: local-first + auto-generated.** No competitor is in this space. The only threat is a well-funded player (Postman, SmartBear) pivoting here — which takes 12-18 months minimum.

---

## 5. Pain Points We Uniquely Solve

### Pain 1: "Spec drift kills us in production"
**Who:** Every team that maintains OpenAPI specs + backend services
**Symptom:** Spec says `422`, server returns `400`. Spec says field is required, server accepts null. These divergences are invisible until a client breaks.
**CHERENKOV Fix:** Runs your spec through LLM-generated tests against your real server. Every run is a conformance audit. Caught before commit, not after incident.

### Pain 2: "Writing API tests is tedious and never happens"
**Who:** Backend engineers, QA teams
**Symptom:** Coverage is always "coming soon". Engineers ship features faster than they write tests.
**CHERENKOV Fix:** `cherenkov generate --spec api.yaml` → instant typed Playwright suite. Generated tests pass the 6-gate review before you ever read them.

### Pain 3: "We can't trust auto-generated tests — they hallucinate"
**Who:** Quality-conscious engineers who tried AI testing tools and got burned
**Symptom:** LLM generates plausible-looking tests that pass because they assert the wrong thing.
**CHERENKOV Fix:** Expected HTTP status and schema come from the OpenAPI spec — not the LLM. The LLM writes structure; the spec provides truth. Hallucination-resistant by architecture.

### Pain 4: "Tool lock-in. If we adopt this, we're stuck."
**Who:** Engineering leads, architects
**Symptom:** Adoption hesitation because proprietary test format = migration cost later.
**CHERENKOV Fix:** `cherenkov eject --output ./tests` strips all CHERENKOV imports. Tests run standalone with only Playwright + openapi-fetch. You can stop using CHERENKOV tomorrow. Tests still work.

### Pain 5: "Our LLM-powered tools send our internal specs to OpenAI"
**Who:** Enterprise security, regulated industries (fintech, healthtech, govtech)
**Symptom:** Blocked from AI tools because of data privacy requirements.
**CHERENKOV Fix:** Default provider is Ollama (local). `qwen2.5-coder:7b` runs on your laptop or K8s cluster. Zero data leaves your environment. OpenAI is an opt-in fallback with cost accounting.

### Pain 6: "Our tests break every time the spec changes"
**Who:** Teams running frequent spec updates
**Symptom:** Test maintenance overhead kills velocity. Tests become stale or disabled.
**CHERENKOV Fix:** Regenerate from updated spec. Knowledge mesh remembers past patterns. Suggest-only healing proposes targeted fixes. No auto-edits, no surprises.

### Pain 7: "Mobile API testing is a different world we don't touch"
**Who:** Mobile teams, full-stack teams
**Symptom:** API tests exist for web but mobile surfaces are untested.
**CHERENKOV Fix:** Maestro + Appium bridges with semantic VLM oracles. Same spec → mobile test flows. Same conformance report format.

---

## 6. Open Source Integration Opportunities

### Tier 1 — Immediate (High Impact, Low Effort)

| Integration | Why It Matters | Implementation |
|-------------|----------------|----------------|
| **GitHub Actions** | CI/CD is where teams live. A marketplace action means `uses: cherenkov/action@v1` in every workflow | 3-day effort; YAML wrapper + Docker image |
| **VS Code Extension** | Spec files open in VS Code daily. Right-click → "Generate tests" is instant viral loop | 2-week effort; Language Server + sidebar |
| **OpenAPI Generator** | Largest OSS spec-to-code tool. Plugin means automatic discovery | 1-week effort; generator plugin |
| **Swagger UI** | Millions view specs here daily. "Generate Tests" button is a conversion funnel | 1-week effort; Swagger UI plugin |
| **Pre-commit hooks** | `cherenkov check` as a pre-commit gate catches drift before push | 1-day effort; `.pre-commit-hooks.yaml` |
| **Docker Hub** | Official image means `docker run cherenkov/cli` zero-install demo | Already has Dockerfile; 1-day publish |

### Tier 2 — High Value Ecosystem (1-3 months)

| Integration | Why It Matters | Notes |
|-------------|----------------|-------|
| **Pact Broker** | Export CHERENKOV verdicts as Pact contracts — bridges contract testing ecosystem | Pact has 3K+ GitHub stars; taps existing user base |
| **Stoplight Spectral** | Import Spectral linting rules → CHERENKOV mutations; export violations as Spectral violations | Cross-pollination of both audiences |
| **OpenTelemetry** | Export test traces as OTEL spans — integrates into Datadog, Jaeger, Grafana | Enterprise must-have; OTEL is the standard |
| **Testcontainers** | Spin up the target API in a container for self-contained test runs | Popular in Java/Go/Node ecosystems |
| **ArgoCD / FluxCD** | GitOps: ConformanceCheck CRD applied via Argo app; tests run on every deploy | K8s-native CI/CD integration |
| **Keploy** | Import traffic recordings as test seeds; CHERENKOV validates them against spec | Complementary tools; co-marketing potential |
| **k6 / Artillery** | Route CHERENKOV test scenarios to k6 for performance baseline testing | "Same test, performance mode" is a powerful pitch |
| **Wiremock / Prism** | Already uses Prism; deepen with Wiremock for Java ecosystem | Expands to Java shops |

### Tier 3 — Platform Bets (3-12 months)

| Integration | Why It Matters | Notes |
|-------------|----------------|-------|
| **MCP (Model Context Protocol)** | AI assistants (Claude, Cursor, Copilot) can call CHERENKOV tools directly | Already has `.mcp.json`; expand to full MCP server |
| **LangChain / LlamaIndex** | Agents can invoke CHERENKOV as a tool in multi-agent pipelines | AI agent ecosystem is exploding |
| **Backstage** | Spotify's dev portal plugin means enterprise adoption via existing tooling | 600+ companies use Backstage |
| **Grafana** | Dashboard plugin for conformance trend visualization | Enterprises already have Grafana; zero new tooling |
| **Slack / Teams** | Conformance alerts in engineering channels | Where engineers live; drives engagement loop |
| **Linear / Jira** | Auto-create issues from conformance failures | Closes the loop from test failure → fix ticket |
| **Buf (gRPC/Protobuf)** | Extend from OpenAPI to Protobuf/gRPC — massive market | Same core pipeline; different spec parser |
| **GraphQL (Hive, Rover)** | OpenAPI + GraphQL = 80%+ of API surface covered | Same LLM-generation approach, new spec format |

---

## 7. Growth Strategy

### 7.1 The Flywheel

```
                    ┌─────────────────────┐
                    │   OSS Community     │
                    │   (GitHub Stars,    │
                    │    HN, Dev.to)      │
                    └─────────┬───────────┘
                              │ discovers
                              ▼
┌──────────────┐    tries    ┌─────────────────────┐    shares
│  Enterprise  │◄────────────│   Individual Devs   │──────────────┐
│   Accounts   │             │   (CLI users)       │              │
└──────┬───────┘             └─────────────────────┘              │
       │                              ▲                           ▼
       │ licenses K8s operator        │ finds via           ┌──────────┐
       │ + enterprise support         │ integrations        │  Virality │
       ▼                              │                     │  (VS Code,│
┌──────────────┐             ┌────────┴────────────┐        │  GH Actions│
│   Revenue    │             │  Ecosystem Plugins  │        │  Backstage)│
│   ($$$)      │             │  (VS Code, Actions, │        └──────────┘
└──────────────┘             │   Backstage, MCP)   │
                             └─────────────────────┘
```

### 7.2 Go-to-Market Phases

#### Phase 1 — Community Seeding (Months 1-3)

**Goal:** 1,000 GitHub stars, 200 active CLI users, 10 testimonials.

- Launch on **Product Hunt** (Tuesday morning, 8AM PT)
- Submit to **Hacker News** "Show HN" (Sunday evening)
- Post on **r/devops**, **r/QualityAssurance**, **r/node**, **r/python**
- Write a technical blog: *"We built an AI that reads your OpenAPI spec and writes your tests — here's what we learned"*
- Post on **Dev.to**, **Medium Engineering**, **Substack**
- Record a **2-min demo video** (quickstart to conformance report)
- Create a **Changelog** (important for dev credibility)
- Set up **Discord** community with #general, #bugs, #showcase channels

**Distribution Amplifiers:**
- Sponsor **API Craft** newsletter (5K subscribers)
- Guest post in **The Pragmatic Engineer** (500K subscribers)
- Submit to **awesome-testing**, **awesome-openapi** GitHub lists
- Contribute detection of CHERENKOV to popular **OpenAPI spec validators**

#### Phase 2 — Ecosystem Integration (Months 3-6)

**Goal:** 50 GitHub Actions users, VS Code extension installed 1,000 times, 3 co-marketing partnerships.

- Publish **GitHub Actions marketplace** action
- Launch **VS Code extension** on marketplace
- Publish to **npm** as `npx cherenkov` zero-install runner
- Reach out to Dredd maintainers (migration guide: "Dredd is deprecated, use CHERENKOV")
- Partner with **Keploy**, **Schemathesis** for cross-promotion
- Apply for **GitHub Accelerator** (open source program)
- Talk at **APIDays**, **QA Fest**, **EuroPython**
- Write: *"CHERENKOV vs Postman: Why local-first AI testing wins"*

#### Phase 3 — Enterprise Pipeline (Months 6-12)

**Goal:** 10 paid enterprise pilots ($1K-5K/month), K8s operator in production at 3 companies.

- Launch **enterprise landing page** with security/compliance focus
- Create **SOC2 readiness checklist** (publish it; it's free marketing to enterprises)
- **"Bring Your Own LLM"** mode for regulated industries (Azure OpenAI, AWS Bedrock)
- Build a **Slack app** for conformance alerts
- Publish **case study #1**: "How [Company] reduced API incidents by N% with CHERENKOV"
- Enterprise sales: outbound to **Platform Engineering leads** at Series B-D companies
- Attend **KubeCon** with a demo pod

---

## 8. Scaling Architecture

### 8.1 From CLI to Platform — The Evolution

```
TODAY                    6 MONTHS                  18 MONTHS
────────────────────     ────────────────────────   ────────────────────────
Local CLI                CI/CD-native runner        Multi-tenant SaaS platform
↓                        ↓                          ↓
Single user              Team shared runs           Org-wide conformance dashboard
↓                        ↓                          ↓
Ollama local             Cloud LLM (opt-in)         Dedicated model endpoints
↓                        ↓                          ↓
SQLite verdicts          Postgres + Redis           Distributed verdict store
↓                        ↓                          ↓
Single spec              Multiple services          Service mesh coverage map
↓                        ↓                          ↓
Manual trigger           Git hook + CI gate         Continuous spec guardian
```

### 8.2 Infrastructure Scaling Strategy

#### Tier 0 — Open Source (Now)
- **Deploy**: `docker compose up`
- **State**: SQLite
- **LLM**: Ollama local
- **Users**: 1-5 devs per project
- **Cost to user**: $0

#### Tier 1 — Team (6 months)
- **Deploy**: K8s (ConformanceCheck CRD)
- **State**: PostgreSQL + Redis
- **LLM**: Ollama cluster or Azure OpenAI (BYOK)
- **Users**: 10-100 per org
- **Cost to user**: $50-200/mo (self-hosted)

#### Tier 2 — Enterprise SaaS (12 months)
- **Deploy**: Fully managed (cherenkov.dev cloud)
- **State**: Distributed, multi-tenant
- **LLM**: CHERENKOV-hosted fine-tuned model
- **Users**: Unlimited per org
- **Cost to user**: $500-5000/mo (metered + seats)

#### Tier 3 — Platform (18-24 months)
- **Deploy**: Any (cloud, on-prem, hybrid)
- **State**: Federated knowledge mesh
- **LLM**: CHERENKOV fine-tuned + customer BYOK
- **Users**: Multi-org federation
- **Cost to user**: Enterprise contract

### 8.3 The LLM Strategy

**Phase 1 — Use existing models (now)**
- `qwen2.5-coder:7b` via Ollama (free, local, fast)
- `deepseek-r1:8b` for deep analysis
- OpenAI GPT-4o as fallback (cost-metered)

**Phase 2 — Fine-tune for domain (6-12 months)**
- Collect anonymized (opt-in) verdict data: (spec_slice, generated_test, verdict_outcome)
- Fine-tune a `cherenkov-coder-7b` on this corpus
- Dramatically better test generation quality than base models
- **Moat**: A fine-tuned model on real API conformance data is unreproducible without the data.

**Phase 3 — Spec Guardian Model (12-24 months)**
- Continuous fine-tuning as the corpus grows
- Model specializes in: API test generation, conformance checking, healing suggestions
- License to enterprises as a private deployment
- **This becomes the core IP asset**

### 8.4 Knowledge Mesh as a Network Effect

The GraphRAG knowledge base is not just a feature — it's a **network effect moat**:

```
More specs indexed → Better pattern recognition
→ Better test generation → More verdicts collected
→ Better healing suggestions → More teams adopt
→ More specs indexed (cycle)
```

In federated mode (opt-in), the knowledge mesh compounds across customers. The more organizations use CHERENKOV, the smarter every organization's test generation becomes. **This is the Grammarly model applied to API testing.**

---

## 9. Revenue Model

### 9.1 Open Core Model

```
FREE (Open Source CLI)          PRO (SaaS/Self-hosted)          ENTERPRISE
────────────────────────────    ────────────────────────────    ─────────────────────
✅ Core test generation         ✅ Everything in Free           ✅ Everything in Pro
✅ Conformance validation       ✅ Cloud-hosted runs            ✅ On-prem K8s operator
✅ Eject to Playwright          ✅ Team dashboard               ✅ SAML/SSO
✅ Local LLM (Ollama)           ✅ Shared knowledge mesh        ✅ RBAC + audit logs
✅ Suggest-only healing         ✅ Slack/Teams alerts           ✅ Compliance reports
✅ OWASP mutations              ✅ CI/CD analytics              ✅ SLA (99.9%)
✅ K8s CRD (basic)              ✅ GitHub/Linear integration    ✅ Dedicated support
✅ React dashboard              ✅ API rate limits (high)       ✅ Custom fine-tuning
                                ✅ 5-user seats included        ✅ Federation corpus
                                💰 $99/mo (up to 10 users)     💰 $2,000-10,000/mo
```

### 9.2 Revenue Projections (Conservative)

| Milestone | Timeline | Monthly Revenue |
|-----------|----------|-----------------|
| 10 Pro teams | Month 9 | $990/mo |
| 50 Pro teams | Month 15 | $4,950/mo |
| 5 Enterprise accounts | Month 18 | $25,000/mo |
| 200 Pro teams + 20 Enterprise | Month 24 | $60,000+/mo |
| Established platform | Month 36 | $500K+/mo ARR |

### 9.3 Unit Economics

- **CAC (Community → Paid)**: ~$0-50 (organic, content-driven)
- **CAC (Outbound Enterprise)**: ~$500-2,000
- **LTV (Pro)**: $99/mo × 24 months avg = $2,376
- **LTV (Enterprise)**: $3,000/mo × 36 months = $108,000
- **Gross Margin (SaaS cloud)**: ~75% (LLM inference is low cost with local models)
- **Payback period**: 1-2 months for Pro, 3-6 months for Enterprise

### 9.4 Alternative Revenue Streams

1. **Marketplace**: Premium test templates (HIPAA, PCI-DSS, OWASP Top 10 suites) — $29-99 one-time
2. **Training & Certification**: "CHERENKOV Certified API Quality Engineer" — $199/person
3. **Consulting**: Enterprise onboarding, custom integrations — $200-500/hr
4. **Data (anonymized, opt-in)**: API conformance benchmark reports — $5,000/report to analysts
5. **Fine-tuned model licensing**: `cherenkov-coder` sold as a private deployment — $10,000+/yr

---

## 10. Next Phases — Detailed Roadmap

### Phase 9 — Market Launch (Weeks 1-4)

> **Goal: Zero to public. First 100 real users.**

| Task | Owner | Effort | Priority |
|------|-------|--------|----------|
| Landing page (cherenkov.dev or subdomain) | Frontend | 1 week | P0 |
| `npx cherenkov init` quickstart (zero install) | Backend | 3 days | P0 |
| 2-min demo video (Loom/YouTube) | Founder | 2 days | P0 |
| Public docs site (Docusaurus / Mintlify) | Docs | 1 week | P0 |
| Product Hunt launch kit | Marketing | 3 days | P0 |
| GitHub README rewrite (convert-focused) | Docs | 1 day | P0 |
| Changelog v1.0.0 release notes | Docs | 1 day | P0 |
| Docker Hub official image publish | DevOps | 1 day | P0 |
| npm package publish | Backend | 1 day | P1 |
| Discord community setup | Community | 1 day | P1 |

**Exit Criteria:** Product Hunt launched. Docs site live. 100 GitHub stars.

---

### Phase 10 — CI/CD Native (Weeks 4-8)

> **Goal: CHERENKOV runs in CI/CD for 50 projects.**

| Task | Details | Effort |
|------|---------|--------|
| GitHub Actions action | `uses: cherenkov-qa/action@v1` | 3 days |
| GitLab CI template | `.gitlab-ci.yml` include | 2 days |
| CircleCI orb | Published to CircleCI registry | 2 days |
| Jenkins plugin or shared library | Groovy wrapper | 3 days |
| Pre-commit hook | `.pre-commit-hooks.yaml` | 1 day |
| Fail-on-drift mode | Exit code 1 on conformance violation | 1 day |
| SARIF output | For GitHub Security tab integration | 2 days |
| Junit XML output | For CI test result parsing | 1 day |

**Exit Criteria:** GitHub Actions action with 50+ installs. "CHERENKOV in CI" blog post.

---

### Phase 11 — VS Code Extension (Weeks 6-10)

> **Goal: 1,000 VS Code installs. Test generation from within the editor.**

| Feature | Details | Effort |
|---------|---------|--------|
| "Generate tests for this spec" command | Right-click `.yaml`/`.json` → generate | 1 week |
| Inline conformance indicators | Gutter icons: ✅ passing / ❌ drift detected | 1 week |
| Inline healing suggestions | Code lens shows tightening suggestions | 3 days |
| Spec drift detection on save | Runs fast validation on file save | 3 days |
| Test explorer integration | Shows CHERENKOV tests in VS Code test panel | 1 week |
| Quick fix (suggest-only) | Light bulb → "Apply suggested assertion" | 3 days |

**Exit Criteria:** 1,000 VS Code installs. Extension rating ≥ 4.5 stars.

---

### Phase 12 — GraphQL + gRPC Expansion (Months 3-5)

> **Goal: 3x addressable market by supporting GraphQL and gRPC specs.**

| Feature | Details | Effort |
|---------|---------|--------|
| GraphQL schema ingest | Parse `.graphql`/introspection → scenarios | 2 weeks |
| GraphQL test generator | LLM writes Apollo/urql test code | 2 weeks |
| GraphQL conformance validator | Response validates against schema | 1 week |
| gRPC Protobuf ingest | Parse `.proto` → endpoint slices | 2 weeks |
| gRPC test generator | LLM writes gRPC client tests | 2 weeks |
| Buf schema registry integration | Pull schemas from Buf | 1 week |
| AsyncAPI support | WebSocket + event-driven APIs | 3 weeks |

**Exit Criteria:** CHERENKOV tests a real GraphQL API end-to-end. gRPC demo.

---

### Phase 13 — Enterprise Tier (Months 5-9)

> **Goal: 5 paying enterprise accounts. $25K MRR.**

| Feature | Details | Effort |
|---------|---------|--------|
| SAML 2.0 / SSO | Okta, Azure AD, Google Workspace | 2 weeks |
| Multi-tenant org management | Teams, projects, roles | 2 weeks |
| RBAC | Admin, Developer, Viewer roles | 1 week |
| Audit log | Every action logged, exportable | 1 week |
| GDPR compliance mode | Data residency, right-to-delete | 1 week |
| Compliance report templates | SOC2, ISO27001, HIPAA-ready | 2 weeks |
| Bring-Your-Own-LLM | Azure OpenAI, AWS Bedrock, private Ollama | 1 week |
| SLA dashboard | Uptime, response time, incident history | 1 week |
| Enterprise support portal | Ticketing, dedicated Slack channel | 1 week |

**Exit Criteria:** 3 enterprise accounts signed. SOC2 Type I audit initiated.

---

### Phase 14 — Spec Guardian (Months 9-15)

> **Goal: Continuous conformance monitoring. CHERENKOV becomes the "always-on" spec watcher.**

This is the category-defining move. Rather than a tool you run, CHERENKOV becomes a **daemon that watches your spec and server continuously**.

| Feature | Details | Effort |
|---------|---------|--------|
| Spec Guardian daemon | Watches spec file for changes; auto-triggers generation | 1 week |
| PR-comment integration | Posts conformance diff as PR comment on spec change | 1 week |
| Continuous conformance trend | Dashboard shows drift over time, by endpoint | 2 weeks |
| Alert policies | "Notify on any new violation", "Alert if coverage drops below X%" | 1 week |
| Auto-regenerate mode | On spec change → regenerate affected test cases only | 2 weeks |
| Coverage map | Visual heatmap of tested vs untested endpoints | 2 weeks |
| Regression detection | "This test passed yesterday, fails today — server changed" | 2 weeks |
| Spec change attribution | Links conformance violations to specific spec commits | 1 week |

**Vision**: *Every OpenAPI spec file has a living test suite that validates itself on every push.*

---

### Phase 15 — Fine-Tuned Model (Months 12-18)

> **Goal: Ship `cherenkov-coder-7b` — the best API test generation model.**

| Step | Details | Effort |
|------|---------|--------|
| Data pipeline design | Collect (spec_slice, scenario, test, verdict) tuples | 2 weeks |
| Opt-in corpus collection | Users opt in to contribute anonymized pairs | 1 month (ongoing) |
| Dataset curation | Filter, deduplicate, quality-score | 2 weeks |
| Fine-tuning run | LoRA fine-tune on qwen2.5-coder-7b base | 1 week (compute) |
| Evaluation harness | Benchmark: compile rate, conformance hit rate, assertion quality | 2 weeks |
| Model release | Hugging Face + Ollama registry | 1 week |
| Enterprise model hosting | Private deployment option for regulated industries | 2 weeks |

**Exit Criteria:** `cherenkov-coder-7b` outperforms base model by ≥20% on all benchmarks. Published on HuggingFace.

---

### Phase 16 — Platform & Marketplace (Months 18-30)

> **Goal: CHERENKOV becomes the testing platform layer. Partners build on it.**

| Feature | Details | Effort |
|---------|---------|--------|
| Public API (REST + SDK) | Programmatic test generation and verdict retrieval | 3 weeks |
| Plugin SDK | Third-party test generators, healers, reporters | 4 weeks |
| Test template marketplace | Community publishes: HIPAA suite, PCI-DSS suite, OWASP Top10 | 2 weeks |
| LLM provider marketplace | Bring your own LLM (Mistral, Cohere, etc.) as plugins | 2 weeks |
| Multi-org federation | Share knowledge mesh across trusted organizations | 4 weeks |
| CHERENKOV Certified | Test quality certification for API products | 2 weeks |
| Webhook ecosystem | Notify Slack, Linear, PagerDuty on drift events | 2 weeks |
| Analytics API | Export conformance metrics to Datadog, Grafana | 2 weeks |

---

## 11. The 10-Year Vision

### What CHERENKOV Can Become

> *"Every API has a spec. Every spec has a guardian. Every guardian is CHERENKOV."*

**Year 1-2: Category Creation**
"The AI-native API conformance tool." Engineers discover it via CLI, adopt it in CI/CD. The category didn't exist before — CHERENKOV defines it.

**Year 3-5: Developer Standard**
Like ESLint for JavaScript, CHERENKOV becomes the de facto standard for API quality gates. Every new microservice gets `cherenkov init` as part of scaffolding. The GitHub Actions action is used in 10K+ repos.

**Year 5-7: Enterprise Platform**
The K8s operator is deployed across enterprise API estates. The knowledge mesh has indexed millions of OpenAPI specs. `cherenkov-coder` is the most accurate API test generation model in existence, trained on opt-in corpus from thousands of organizations.

**Year 7-10: API Intelligence Layer**
CHERENKOV evolves beyond testing into the **API intelligence layer** — real-time monitoring, predictive drift detection, cross-API dependency mapping, automatic spec evolution suggestions. It becomes the observability platform for the API contract layer of every distributed system.

### The Market Endgame

API contracts are the nervous system of modern software. Today they're invisible, undocumented, untested, and drift silently. CHERENKOV makes them observable, validated, and self-defending.

**The 10-year bet:** API contracts become as important as database schemas — and every serious engineering org has a tool that validates them continuously. CHERENKOV is that tool.

### Comparable Trajectories

| Company | Category | Path | Outcome |
|---------|---------|------|---------|
| **ESLint** | JS linting | OSS → standard → ecosystem | ~$150M ARR ecosystem |
| **Postman** | API testing (manual) | Dev tool → platform | $1B+ unicorn |
| **Snyk** | Security scanning | OSS → enterprise | $8.5B peak valuation |
| **Datadog** | Observability | Agent → platform | $30B+ market cap |
| **CHERENKOV** | API conformance | OSS CLI → K8s operator → AI platform | TBD |

The path is proven. The category is new. The timing is right.

---

## 12. Recommended Immediate Next Steps

### This Week (Days 1-7)

- [ ] **Fix the `cargo` blocker** — Tauri 3 desktop app doesn't need Rust locally; use `tauri-action` in CI instead. Unblock Phase 3.
- [ ] **Complete Phase 8** — Ship the K8s operator (CRDs are done). This is the enterprise proof point.
- [ ] **Write the landing page copy** — Focus on the 3 core pains: spec drift, manual tests, tool lock-in.
- [ ] **Record the demo video** — Show: `cherenkov generate → 6-gate review → conformance violation caught → eject`. 90 seconds. No voiceover needed.
- [ ] **Cut v1.0.0** — Semantic version, GitHub Release, CHANGELOG.md. Signal stability.
- [ ] **Push Docker Hub image** — `docker pull cherenkov/cli:latest` works publicly.

### This Month (Weeks 2-4)

- [ ] **Ship `npx cherenkov init`** — Zero install. 30-second quickstart. The demo must run without reading docs.
- [ ] **Launch docs site** — Mintlify or Docusaurus. Getting Started, CLI Reference, Architecture. 10 pages.
- [ ] **GitHub Actions action** — `uses: cherenkov-qa/action@v1` in 3-step quickstart. This is viral.
- [ ] **Product Hunt launch** — Coordinate upvotes from network. Tuesday 8AM PT.
- [ ] **HackerNews Show HN** — Write the honest technical story. Hackers respect honesty + depth.
- [ ] **Add to `awesome-testing` list** — Free discovery.

### This Quarter (Months 2-3)

- [ ] **VS Code extension beta** — Get 100 beta testers from Discord.
- [ ] **First 3 integration guides** — Postman migration, GitHub Actions setup, K8s deployment. Docs that rank on Google.
- [ ] **Community office hours** — Weekly 30-min video call. Build the core community.
- [ ] **3 case studies** — Even internal: "We tested our own Petstore API with CHERENKOV and found these 4 conformance bugs."
- [ ] **Reach out to Dredd users** — Dredd is deprecated. A "migrating from Dredd" guide + HN post can convert 1,000+ users instantly.
- [ ] **Apply to Y Combinator** — The product is real. The market is big. The timing is right. Apply.

### The Single Most Important Thing

**Ship the demo that converts skeptics in 90 seconds.**

The demo must show: a real OpenAPI spec → CHERENKOV generates tests → tests run → a conformance violation is caught (spec says 422, server returns 400) → suggested fix → eject produces vanilla Playwright. That arc, in under 2 minutes, closes every objection a developer has.

Everything else compounds from there.

---

## Appendix: KPIs & Success Metrics

| Metric | Month 3 | Month 6 | Month 12 | Month 24 |
|--------|---------|---------|----------|----------|
| GitHub Stars | 1,000 | 3,000 | 8,000 | 20,000 |
| CLI installs (monthly) | 500 | 2,000 | 8,000 | 30,000 |
| GitHub Actions uses | 50 | 500 | 3,000 | 15,000 |
| VS Code installs | — | 1,000 | 5,000 | 20,000 |
| Discord members | 100 | 500 | 2,000 | 8,000 |
| Pro team accounts | 0 | 5 | 50 | 200 |
| Enterprise accounts | 0 | 0 | 5 | 25 |
| MRR | $0 | $500 | $25K | $150K |
| ARR | — | — | $300K | $1.8M |

---

*Document authored: 2026-06-09*
*Revision cycle: Quarterly*
*Owner: Product / Strategy*
