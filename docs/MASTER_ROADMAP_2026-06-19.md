# CHERENKOV QA — Master Roadmap & Implementation Plan

> **Authoritative synthesis of all agent sessions, 2026-06-19.**
> Sources: `docs/HANDOVER.md`, `docs/PHASE_PLAN.md`,
> `docs/PRODUCT_STRATEGY_ROADMAP.md`, `docs/INTEGRATION_STRATEGY.md`,
> live `git status`, live test suite run.
>
> This document does NOT replace those sources — it synthesises them into
> one executable sequence. If anything here conflicts with HANDOVER.md,
> HANDOVER.md wins; reconcile here.

---

## Part 1 — Confirmed Current State (Raw Evidence)

| Signal | Evidence |
|--------|----------|
| `main` HEAD | `0a23751b` — GitHub Pages landing page commit |
| Test suite | **867 passed · 4 skipped · 1 xpassed · 0 failed** (74.69s, 2026-06-19) |
| Ruff lint | ✅ 0 errors |
| Working tree | **Dirty** — 8 modified + 3 untracked files (Qwen Code session `55cfdcaf`) |
| `pyproject.toml` version | Already `"1.0.0"` |

### Phase completion (Phases -1 → 8) ✅

| Phase | Track | Status |
|-------|-------|--------|
| -1 | Planning & Prep | ✅ 6 ADRs, strategy docs |
| 0a | P0 Bug Fixes | ✅ 8 bugs fixed |
| 0b | Foundations | ✅ Ports, events, devices, config |
| 1 | Second Brain | ✅ GraphRAG, event bridges |
| 2 | VLM + LocalAI | ✅ Tier routing, doctor CLI |
| 3 | Desktop (Tauri 2) | ✅ `cargo check` green; 308MB debug binary |
| 4 | Chat Agents | ✅ Tool-calling, SSE streaming |
| 5 | Mobile Core | ✅ 232/232 unit tests pass |
| 6 | Mobile Execution | 🔧 Env ready (Maestro + ADB) — needs device/emulator |
| 7 | Dashboard | ✅ 9 screens built |
| 8 | K8s + Cloud | ✅ `make k3d-test` green |

### Gate G0 (EPIC #535)

| ID | Criterion | Status |
|----|-----------|--------|
| E0.1 | ≥2/3 real APIs yield ≥1 divergence | ✅ 3/3: Petstore (4), HTTPBin (1), GitHub (1) |
| E0.2 | Catch a real agent-cheat, reproducible | ✅ `demos/catch-the-ai-cheating/run_demo.py` |
| E0.3 | ≥3 QA practitioners complete quickstart | ❌ **Human task** — founder must recruit |
| E0.4 | Honest differentiation vs Schemathesis | ✅ `NORTH_STAR.md §8` |

> **E0.3 is the only open item in Gate G0.** Outreach templates:
> `docs/QA_OUTREACH_TEMPLATES.md`. Demo kit: `docs/QA_DEMO_KIT.md`.

---

## Part 2 — The Position

CHERENKOV owns the most defensible whitespace in API testing:

```
                    MANUAL TESTS          AUTO-GENERATED TESTS
                ┌──────────────────────┬─────────────────────────┐
  CLOUD/SAAS    │  Postman, APIfox,    │   (nobody here at scale)│
                ├──────────────────────┼─────────────────────────┤
  LOCAL/PRIVATE │  Dredd, Schemathesis │  ★ CHERENKOV ★          │
                └──────────────────────┴─────────────────────────┘
```

Differentiation sentence (E0.4, `NORTH_STAR.md §8`):

> *Schemathesis questions the server. CHERENKOV questions the test suite —
> catching the case where the AI wrote a test that can never fail.*

Market: $5B API testing → $41B by 2032 at 27% CAGR. No incumbent owns
local-first + auto-generated.

---

## Part 3 — Execution Plan

### Sprint 0 — Stabilise (Days 1-2, NOW)

> Prerequisite for everything. Do not start Phase 9 with a dirty tree.

#### S0.1 — Commit Qwen Code WIP

```bash
git checkout -b feat/qwen-code-federation-wip
git add benchmarks/qwen-code-vs-cherenkov.py \
  cherenkov/adapters/qwen_code_event_bus.py \
  cherenkov/stages/init_cmd.py \
  docs/QWEN_CODE_ALIGNMENT.md \
  qwen.json scripts/qwen-code-integration.sh \
  tools/qwen_code_mcp.py .gitignore \
  tests/unit/test_memory_sync.py \
  tests/unit/test_qwen_code_mcp.py \
  tests/unit/test_skill_sync.py
git commit -m "feat(qwen-code): federation adapter, MCP tools, unit tests (session 55cfdcaf)"
git push origin feat/qwen-code-federation-wip
```

Verify new tests:

```bash
python3 -m pytest tests/unit/test_memory_sync.py \
  tests/unit/test_qwen_code_mcp.py tests/unit/test_skill_sync.py -v
```

Open PR. Do NOT merge until green and reviewed.

#### S0.2 — Cut v1.0.0 GitHub Release

```bash
git tag -s v1.0.0 -m "CHERENKOV v1.0.0 — core engine complete"
git push origin v1.0.0
# release.yml fires → GitHub Release created automatically
```

Verify `CHANGELOG.md` has a v1.0.0 entry before tagging.

---

### Phase 9 — Market Launch (Weeks 1-4)

> Goal: Zero to public. First 100 real users.
> Exit: Product Hunt launched · docs site live · 100 GitHub stars.

| Task | Priority | Effort |
|------|----------|--------|
| **P9.1** Landing page live (verify `pages.yml` deploys `docs/index.html`) | P0 | 1 day |
| **P9.2** 90-second demo video (`spec → generate → violation caught → eject`) | P0 | 2 days |
| **P9.3** PyPI publish — activate `publish.yml`, add metadata to `pyproject.toml` | P0 | 1 day |
| **P9.4** npm thin wrapper `packages/cherenkov-cli` → `npx cherenkov-cli init` | P0 | 2 days |
| **P9.5** Docker Hub publish — add `docker-publish.yml` workflow | P0 | 1 day |
| **P9.6** README rewrite — conversion-focused, install commands, embed demo | P0 | 1 day |
| **P9.7** Discord community setup (`#general`, `#bugs`, `#showcase`, `#roadmap`) | P1 | 1 day |
| **P9.8** Product Hunt + HN launch kit (Tuesday 8AM PT) | P0 | 3 days |

#### Demo Video Arc (P9.2) — must show all 7 steps

```
1. Real OpenAPI spec (Petstore)
2. cherenkov generate → instant typed Playwright suite
3. 6-gate review (syntax → AST → tsc → Prism)
4. Tests run against real server
5. Violation: spec says 422, server returns 400
6. Healing suggestion (suggest-only, D7 invariant)
7. cherenkov eject → vanilla Playwright, zero CHERENKOV imports
```

#### npm Wrapper Design (P9.4)

Thin Node package — does not rewrite the CLI in Node:

```
packages/cherenkov-cli/
├── package.json          # name: "cherenkov-cli"
├── bin/cherenkov-init.js # checks Python ≥3.10, pip installs, delegates
└── README.md
```

Fix `npm-publish.yml` to also publish `packages/cherenkov-cli` on `v*` tags.

#### GitHub Actions — `action.yml` structure (P10, referenced from P9 README)

```yaml
name: CHERENKOV Conformance Check
inputs:
  spec: { required: true }
  target: { required: true }
  fail-on-drift: { default: 'true' }
  llm-provider: { default: 'openai' }
outputs:
  violations: {}
  report-path: {}
  sarif-path: {}
runs:
  using: docker
  image: ghcr.io/moaidmoatasem/cherenkov-qa:latest
```

---

### Phase 10 — CI/CD Native (Weeks 4-8)

> Goal: CHERENKOV runs in CI/CD for 50 projects.

| Task | Priority | Effort |
|------|----------|--------|
| **P10.1** GitHub Actions marketplace action (`action.yml` + self-test) | P0 | 3 days |
| **P10.2** SARIF output (`--format sarif` → GitHub Security tab) | P0 | 2 days |
| **P10.3** Fail-on-drift mode (`--fail-on-drift` → exit code 1) | P0 | 1 day |
| **P10.4** JUnit XML output (`--format junit`) | P1 | 1 day |
| **P10.5** Pre-commit hook (`.pre-commit-hooks.yaml`) | P1 | 1 day |
| **P10.6** Slack notifier adapter (`cherenkov/adapters/notifiers/slack.py`) | P1 | 1 week |
| **P10.7** Jira real integration (complete the stub in `jira_exporter.py`) | P1 | 1 week |
| **P10.8** GitLab CI template + CircleCI orb | P2 | 4 days |

---

### Phase 11 — VS Code Extension (Weeks 6-10)

> Goal: 1,000 VS Code installs. Test generation from within the editor.
> Note: Scaffold already exists in `vscode/`. Needs `npm install + vsce package + publish`.

| Feature | Effort |
|---------|--------|
| Right-click spec → "Generate conformance tests" | 1 week |
| Gutter icons: 🟢 passing · 🔴 drift · ⚪ untested | 1 week |
| CodeLens: `▶ 4 passing  ⚠ 1 drift  → Heal` | 3 days |
| Diagnostics panel (violations as warnings with file/line) | 3 days |
| Test Explorer integration | 1 week |
| Quick Fix (`Ctrl+.` → "Apply suggested assertion", suggest-only) | 3 days |

---

### Phase 12 — GraphQL + gRPC (Months 3-5)

> Goal: 3× addressable market.

| Feature | Effort |
|---------|--------|
| GraphQL schema ingest + test generator | 4 weeks |
| GraphQL conformance validator | 1 week |
| gRPC Protobuf ingest + test generator | 4 weeks |
| Buf schema registry integration | 1 week |
| AsyncAPI / WebSocket / Kafka | 3 weeks |

---

### Phase 13 — Enterprise Tier (Months 5-9)

> Goal: 5 paying enterprise accounts. $25K MRR.

SAML/SSO · multi-tenant RBAC · audit log · GDPR compliance · SOC2 templates ·
BYOLLM · SLA dashboard · enterprise support portal.

---

### Phase 14 — Spec Guardian (Months 9-15)

> Goal: Continuous conformance monitoring daemon.

Spec file watcher · PR-comment integration · conformance trend dashboard ·
alert policies · auto-regenerate on spec change · coverage heatmap ·
regression detection · spec change attribution.

---

### Phase 15 — Fine-Tuned Model (Months 12-18)

> Goal: `cherenkov-coder-7b` — best API test generation model.

Data pipeline → opt-in corpus → LoRA fine-tune (qwen2.5-coder-7b base) →
evaluation harness → HuggingFace + Ollama publish → enterprise model hosting.

---

### Phase 16 — Platform & Marketplace (Months 18-30)

> Goal: Partners build on CHERENKOV.

Public REST API + SDK · Plugin SDK · test template marketplace (HIPAA,
PCI-DSS, OWASP) · LLM provider marketplace · multi-org federation ·
CHERENKOV Certified · webhook ecosystem · Analytics API.

---

## Part 4 — Integration Strategy (25 Integrations Across 5 Tiers)

### Tier 0 — Where Developers Live

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 1 | GitHub Actions | ❌ | 3 days | P10 |
| 2 | VS Code Extension | 🔧 scaffold | 3-4 weeks | P11 |
| 3 | Pre-commit hooks | ❌ | 1 day | P10 |
| 4 | Docker Hub | ❌ | 1 day | P9 |
| 5 | npm / npx | ❌ | 2 days | P9 |

### Tier 1 — Where Teams Work

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 6 | Slack | ❌ declared, never wired | 1 week | P10 |
| 7 | Microsoft Teams | ❌ | 1 week | P10 |
| 8 | Jira | ⚠️ stub | 1 week | P10 |
| 9 | Linear | ❌ | 3 days | P10 |
| 10 | GitHub Issues | ❌ | 2 days | P10 |

### Tier 2 — Where Quality Lives

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 11 | Xray (Jira TM) | ❌ | 2 weeks | P13 |
| 12 | Zephyr Scale | ❌ | 1 week | P13 |
| 13 | Allure Report | ❌ | 3 days | P10 |
| 14 | Playwright Report | ✅ via eject | Done | — |

### Tier 3 — Where AI Lives

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 15 | MCP Server | ✅ 14 tools | Expand stubs | P10 |
| 16 | Qwen Code Federation | 🔧 WIP dirty tree | 1 week | Sprint 0 |
| 17 | LangChain / LlamaIndex | ❌ | 1 week | P12 |
| 18 | Claude / Cursor / Copilot | ✅ MCP | Publish registry | P9 |

### Tier 4 — Where Enterprise Lives

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 19 | K8s CRD Operator | ✅ | Done | — |
| 20 | ArgoCD / FluxCD | ❌ | 1 week | P13 |
| 21 | OpenTelemetry | ❌ | 1 week | P13 |
| 22 | Grafana Plugin | ❌ | 2 weeks | P14 |
| 23 | Datadog | ❌ | 1 week | P14 |

### Tier 5 — Market Expansion

| # | Integration | State | Effort | Phase |
|---|-------------|-------|--------|-------|
| 24 | GraphQL (Hive, Rover) | ❌ | 6 weeks | P12 |
| 25 | gRPC / Buf | ❌ | 6 weeks | P12 |

---

## Part 5 — Revenue Model

```
FREE (OSS CLI)          PRO ($99/mo)              ENTERPRISE ($2K-10K/mo)
──────────────────      ──────────────────────    ─────────────────────────
Core test generation    Everything in Free        Everything in Pro
Conformance validation  Cloud-hosted runs         On-prem K8s operator
Eject to Playwright     Team dashboard            SAML/SSO
Local LLM (Ollama)      Shared knowledge mesh     RBAC + audit logs
Suggest-only healing    Slack/Teams alerts        Compliance reports
OWASP mutations         CI/CD analytics           SLA (99.9%)
K8s CRD (basic)         GitHub/Linear integ.      Dedicated support
React dashboard         5-user seats              Custom fine-tuning
```

### Projections

| Milestone | Timeline | MRR |
|-----------|----------|-----|
| 10 Pro teams | Month 9 | $990 |
| 50 Pro teams | Month 15 | $4,950 |
| 5 Enterprise accounts | Month 18 | $25,000 |
| 200 Pro + 20 Enterprise | Month 24 | $60,000+ |
| Established platform | Month 36 | $500K+ ARR |

---

## Part 6 — KPI Targets

| Metric | M3 | M6 | M12 | M24 |
|--------|-----|-----|------|------|
| GitHub Stars | 1,000 | 3,000 | 8,000 | 20,000 |
| CLI installs/month | 500 | 2,000 | 8,000 | 30,000 |
| GitHub Actions uses | 50 | 500 | 3,000 | 15,000 |
| VS Code installs | — | 1,000 | 5,000 | 20,000 |
| Discord members | 100 | 500 | 2,000 | 8,000 |
| Pro accounts | 0 | 5 | 50 | 200 |
| Enterprise accounts | 0 | 0 | 5 | 25 |
| MRR | $0 | $500 | $25K | $150K |

---

## Part 7 — Design Invariants (Non-Negotiable)

| Invariant | Rule |
|-----------|------|
| D7 | Never auto-edit test code. Healing = suggest-only, reports only. |
| Anti-lock-in | Tests must run without CHERENKOV (`eject` strips all imports). |
| Spec-derived | Expected HTTP status from the OpenAPI spec, not LLM assumption. |
| Structural neutrality | Model-agnostic, vendor-neutral, local-first. |
| Suggest-only healing | Healing never auto-commits or auto-applies. |

---

## Part 8 — Open Questions (Founder Decisions Required)

1. **PyPI credentials** — Does `PYPI_API_TOKEN` exist as a GitHub Actions secret?
2. **Docker Hub** — Is the `cherenkov` namespace claimed? `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` secrets needed.
3. **E0.3** — Who are the first 3 QA practitioners? (`docs/QA_OUTREACH_TEMPLATES.md`)
4. **Mobile (Track D)** — Physical device or emulator available to unblock Phase 6?
5. **Desktop (Track C)** — Auto-setup wizard now (2 weeks) or defer to after Phase 11?
6. **MCP Registry** — Publish to official Anthropic MCP registry now (1 day) for Cursor/Windsurf/Claude Desktop?

---

## Part 9 — The Single Most Important Thing

**Ship the demo that converts skeptics in 90 seconds.**

```
spec → generate → 6-gate review → violation caught → eject → vanilla Playwright
```

Every adoption metric compounds from that demo existing.

---

## Part 10 — Handover Checklist (Next Agent)

> Read `docs/HANDOVER.md` first. This is the plan; HANDOVER.md is the live
> state. If they conflict, HANDOVER.md wins.

- [ ] S0.1 — Commit 8 dirty Qwen Code files to `feat/qwen-code-federation-wip`
- [ ] S0.1 — Run 3 new unit tests, confirm green
- [ ] S0.2 — Cut `v1.0.0` tag → `release.yml` fires
- [ ] P9.1 — Verify `pages.yml` deploys `docs/index.html` to GitHub Pages
- [ ] P9.2 — Record 90-second demo video
- [ ] P9.3 — Activate `publish.yml` → `pip install cherenkov-qa` works
- [ ] P9.4 — Create `packages/cherenkov-cli` → `npx cherenkov-cli init` works
- [ ] P9.5 — Add `docker-publish.yml` → `docker pull cherenkov/cli:latest` works
- [ ] P9.6 — Rewrite README to be conversion-focused
- [ ] P9.7 — Create Discord server
- [ ] P9.8 — Launch on Product Hunt + HN
- [ ] Founder — Recruit 3 QA practitioners for E0.3

---

*Synthesised: 2026-06-19 · Antigravity (Claude Sonnet 4.6 Thinking)*
*SSOT: HANDOVER.md · PHASE_PLAN.md · PRODUCT_STRATEGY_ROADMAP.md · INTEGRATION_STRATEGY.md*
*Evidence: `git status`, pytest (867 passed, 0 failed), `git log --oneline -10`*
