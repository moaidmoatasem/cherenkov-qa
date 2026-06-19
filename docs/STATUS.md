**Last updated:** 2026-06-19
**Branch:** `main`

---

## At a glance

CHERENKOV is an **AI-native API conformance testing platform** that reads an OpenAPI spec, uses a local LLM to generate typed Playwright tests, executes them against a real server, and delivers conformance violation reports — all with zero vendor lock-in. The core pipeline (Track A) is built, validated, and tagged as `v1.0.0`. The full extended roadmap (Phases 9-16) is largely implemented across GraphQL, gRPC, AsyncAPI, enterprise tier, VS Code extension, CI/CD integrations, and more.

---

## Phase status (consolidated)

| Phase | Name | Status | Notes |
|------:|------|:------:|-------|
| -1 | Planning & Preparation | ✅ Complete | 6 ADRs, strategy docs |
| 0a | P0 bug fixes | ✅ Complete | 8 bugs, issues #304–#312 |
| 0b | Foundations | ✅ Complete | Ports, events, devices, config (PRs #393, #394) |
| 1 | Second Brain | ✅ Complete | Knowledge mesh, GraphRAG, event bridges (PR #395) |
| 2 | VLM + LocalAI | ✅ Complete | LocalAI default, tier routing, doctor CLI (PR #396) |
| 3 | Desktop Host | ✅ Complete | `libwebkit2gtk-4.1-dev` installed; `cargo check` passes; 308MB debug binary builds |
| 4 | Chat Agents | ✅ Complete | Tool-calling agent, persona registry, SSE (PRs #397–#400) |
| 5 | Mobile Testing Core | ✅ Complete | ADB at `~/.local/bin/adb`; Maestro 2.6.1 at `~/.maestro/bin/maestro` |
| 6 | Mobile Execution | 🔧 Env ready | Maestro + ADB installed; needs physical device/emulator for live runs |
| 7 | Dashboard Revamp | ✅ Complete | 9 screens built (PRs #401, #402, #405) |
| 8 | K8s + Cloud + Gate | ✅ Complete | `make k3d-test` green (2026-06-09); all 6 issues closed |
| 9 | Market Launch | ✅ Complete | `docs/launch/` (Discord setup, Product Hunt kit, demo script), `npx cherenkov init`, v1.0.0 release notes |
| 10 | CI/CD Native | ✅ Complete | GitHub Action (`.github/workflows/`), GitLab CI template, CircleCI orb, JUnit XML, SARIF, Jira exporter |
| 11 | VS Code Extension | ✅ Complete | `vscode/` with gutter icons, CodeLens, TestExplorer, QuickFix — packaged as `.vsix` |
| 12 | GraphQL + gRPC + AsyncAPI | ✅ Complete | `cherenkov/sources/graphql/`, `grpc/`, `asyncapi/` adapters + templates |
| 13 | Enterprise Tier | ✅ Complete | `cherenkov/enterprise/` — SAML, GDPR, SOC2, RBAC, org mgmt, audit, BYO-LLM (Azure OpenAI, Bedrock) |
| 14 | Spec Guardian | ✅ Complete | `cherenkov/spec_guardian/` — daemon, detector, store |
| 15 | Fine-Tuned Model | 🔧 Scaffolded | `cherenkov/training/` — dataset collector, trainer pipeline; needs opt-in corpus |
| 16 | Platform & Marketplace | 🔧 Scaffolded | `cherenkov/federation/` — corpus sync; MCP registry not yet published |

---

## Tracks

| Track | Scope | State |
|-------|-------|-------|
| A (Core) | API conformance testing | ✅ Built; v1.0.0 tagged; validation gate passed (2026-06-08) |
| B (VLM) | LocalAI / Ollama substrate | ✅ Built; MCP policy engine + Docker Model Runner adapter |
| C (Desktop) | Tauri 2 host | ✅ Built; `cargo check` green, 308MB debug binary |
| D (Mobile) | Maestro / Appium | ✅ Built, unit-tested; E2E dashboard tests added; runtime blocked on physical device/emulator |
| E (Dashboard) | React UI | ✅ Built; all 9 screens shipped; E2E error-path + multi-viewport tests |
| F (K8s) | Operator + CRDs | ✅ Complete (Phase 8) |
| G (Protocols) | GraphQL, gRPC, AsyncAPI | ✅ Built; adapters + templates + eject paths |
| H (Enterprise) | SAML, GDPR, SOC2, RBAC | ✅ Built with CLI + integration tests |
| I (IDE) | VS Code extension | ✅ Built; `.vsix` packaged, ready for marketplace publish |
| J (CI/CD) | GitHub Actions, GitLab, CircleCI | ✅ Built; templates + SARIF + JUnit |

---

## Gate G0 (EPIC #535) — 3/4 complete

| ID | Criteria | Status | Evidence |
|----|----------|--------|----------|
| E0.1 | Real divergence proof: ≥2/3 APIs yield ≥1 divergence | ✅ DONE | 3/3 APIs: Petstore (4), HTTPBin (1), GitHub (1) — `docs/evidence/e0.1_divergences.md` |
| E0.2 | Catch a real agent-cheat, reproducible | ✅ DONE | `demos/catch-the-ai-cheating/run_demo.py` + TypeScript checker |
| E0.3 | ≥3 QA practitioners complete quickstart | ❌ HUMAN | Needs real users |
| E0.4 | Honest differentiation vs Schemathesis | ✅ DONE | `NORTH_STAR.md` §8 |

**Blocking state:** Only E0.3 (human recruitment) remains. All code gates passed.

## Design invariants (deltas — non-negotiable)

- **D7 — never auto-edit test code.** Validate and healing produce
  reports/suggestions only. No test files are touched by automation.
- **Anti-lock-in.** `cherenkov eject` strips all CHERENKOV imports so tests
  run with vanilla Playwright + `openapi-fetch`.
- **Suggest-only healing.** Healing never auto-commits or auto-applies.
- **Spec-derived.** Expected HTTP status comes from the OpenAPI spec, not
  from hardcoded assumptions in test code.

---

## Environment

- **Host:** WSL2 Ubuntu, RTX 5060 8GB
- **LLMs:** Ollama — `qwen2.5-coder:7b` (generation), `deepseek-r1:8b` (planning)
- **Python:** 3.10+
- **Node:** for `openapi-typescript` + Playwright
- **Docker:** for Prism (and optional LocalAI/Redis via `docker-compose.ai.yml`)

### Cost tiers

| Tier | Setup | Monthly | What you get |
|------|------:|--------:|--------------|
| L0 Bare CLI | $0 | $0 | Python + SQLite, no Docker |
| L1 + Ollama | $0 | $0 | L0 + local LLM, API + visual testing |
| L2 + Docker Compose | $0 | $0 | L1 + LocalAI (VLM), Redis (vector/sessions) |
| L3 + Full stack | $0 | $0 | L2 + Android emulator, Maestro, mobile, desktop |
| L4 + Cloud | $0 | ~$50–100 | L3 + optional cloud VLM/devices |
| L5 + Enterprise | $0 | $300+ | L4 + K8s operator, SSO, audit logs |

Solo developer zero-cost path: L0–L3 = $0/month.

---

## What to read next

- **New user?** → [GETTING_STARTED.md](GETTING_STARTED.md)
- **Want a CLI walk-through?** → [CLI_DEMO.md](CLI_DEMO.md)
- **Agent / contributor?** → [HANDOVER.md](HANDOVER.md) then [PHASE_PLAN.md](PHASE_PLAN.md)
- **Architect?** → [engineering/SYSTEM_DESIGN.md](engineering/SYSTEM_DESIGN.md)
- **Launch materials?** → [docs/launch/](launch/) (Product Hunt kit, Demo script, Discord setup)
- **Decision rationale?** → [adr/](adr/)
- **Product strategy & market roadmap?** → [PRODUCT_STRATEGY_ROADMAP.md](PRODUCT_STRATEGY_ROADMAP.md)
- **Integration & ecosystem plan?** → [INTEGRATION_STRATEGY.md](INTEGRATION_STRATEGY.md)

---

## Environment dependencies

This WSL environment has:
- `libwebkit2gtk-4.1-dev` ✅ — Tauri Desktop
- `android-tools-adb` ✅ — ADB at `~/.local/bin/adb` (needs physical device/emulator)
- Maestro 2.6.1 ✅ — at `~/.maestro/bin/maestro`
- `cargo` 1.96.0 ✅ — at `~/.cargo/bin/`

For a fresh environment setup, see `docs/HANDOVER.md` §8.

---

## Change log

- **2026-06-19** — Updated to reflect Phase 9-16 implementation status (most tracks built/scaffolded). v1.0.0 release tagged.
- **2026-06-11** — QA Reasoning Engine foundation added (`cherenkov/reasoning/`):
  artifact-adaptive QA workflows per [ADR-007](adr/ADR-007-qa-reasoning-engine.md).
- **2026-06-10** — Updated: test pass rate 16 failures → 258 passing; Track B/D/E state refreshed.
- **2026-06-09** — Created this file. Status deduplicated from `HANDOVER.md`,
  `README.md`, and `PHASE_PLAN.md`.
