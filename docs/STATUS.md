**Last updated:** 2026-07-05
**Branch:** `main`

---

## At a glance

CHERENKOV is an **API Integrity Auditor** that uses pure AST static analysis to mathematically prove that your test suites actually enforce your OpenAPI contract (catching Weakened, Deleted, and Hallucinated assertions). It also generates Playwright tests from an OpenAPI spec using a local LLM, runs them against a real server, and catches spec-conformance drift. All tracks are now open for development under the consolidated Phase -1 through Phase 16 plan.

---

## Phase status (consolidated)

| Phase | Name | Status | Notes |
|------:|------|:------:|-------|
| -1 | Planning & Preparation | ✅ Complete | 6 ADRs, strategy docs |
| 0a | P0 bug fixes | ✅ Complete | 8 bugs, issues #304–#312 |
| 0b | Foundations | ✅ Complete | Ports, events, devices, config (PRs #393, #394) |
| 1 | Second Brain | ✅ Complete | Knowledge mesh, GraphRAG, event bridges (PR #395) |
| 2 | VLM + LocalAI | ✅ Complete | LocalAI default, tier routing, doctor CLI (PR #396) |
| 3 | Desktop Host | ✅ Complete | 308MB debug binary builds; needs signing key |
| 4 | Chat Agents | ✅ Complete | Tool-calling agent, persona registry, SSE (PRs #397–#400) |
| 5 | Mobile Testing Core | ✅ Complete | Unit tests pass; ADB installed |
| 6 | Mobile Execution | 🔧 Env ready | Maestro 2.6.1 installed; needs physical device |
| 7 | Dashboard Revamp | ✅ Complete | 9 screens built (PRs #401, #402, #405) |
| 8 | K8s + Cloud + Gate | ✅ Complete | `make k3d-test` green; security headers wired |
| CC-1| Auto-Memory + Hooks | ✅ Complete | SQLite FTS5, HookRegistry, 32 tests |
| CC-2| Multi-Agent Conductor | ✅ Complete | Fan-out/fan-in on MCP mesh |
| CC-3–6| MCP Expansion, Scheduling, Remote, CLI | ✅ Complete | All shipped |
| 9 | Semantic Memory | ✅ Complete | MemSearch + SDD protocol |
| 10 | CI/CD Native | ✅ Complete | Jenkins Shared Library |
| 11 | VS Code Extension | ✅ Complete | Test Explorer, inline indicators |
| 12 | GraphQL + gRPC | ✅ Complete | Schema ingest, API generation |
| 13 | Enterprise Tier | ✅ Complete | SAML 2.0, RBAC, org management |
| 14 | Spec Guardian | ✅ Complete | Conformance monitoring daemon |
| 15 | Fine-Tuned Model | ✅ Complete | Data pipeline, dataset curation |
| 16 | Platform & Marketplace | ✅ Complete | Webhooks, Analytics API, Plugin SDK |

---

## AQE Rungs (Mission-Critical)

- **Rung 1 (The Tool):** ✅ Complete — `verify`, `check-suite`, `certify`, `eject`, `install.sh`
- **Rung 2 (The Platform):** ✅ Complete — MCP server (~35 tools), continuous daemon, gRPC/GraphQL adapters
- **Rung 3 (The Protocol):** ✅ Complete — Certificate STABLE v1.0, compliance mapping

---

## Tracks

| Track | Scope | State |
|-------|-------|-------|
| A (Core) | API conformance testing | ✅ Built; validation gate passed; **788+ unit tests passing, 0 failures** |
| B (VLM) | LocalAI / Ollama substrate | ✅ Built; MCP policy engine + Docker Model Runner adapter added |
| C (Desktop) | Tauri 2 host | ✅ Complete | `cargo check` green, full debug binary builds |
| D (Mobile) | Maestro / Appium | ✅ Built, unit-tested; runtime blocked on physical device |
| E (Dashboard) | React UI | ✅ Built; 5-workspace UI live; `data-testid` coverage complete; 25 workspace E2E tests + 23 headless QA tests green |
| F (K8s) | Operator + CRDs | ✅ Complete (Phase 8) |

---

## Gate G0 (EPIC #535) — 3/4 complete

| ID | Criteria | Status | Evidence |
|----|----------|--------|----------|
| E0.1 | Real divergence proof: ≥2/3 APIs yield ≥1 divergence | ✅ DONE | 3/3 APIs: Petstore (4), HTTPBin (1), GitHub (1) |
| E0.2 | Catch a real agent-cheat, reproducible | ✅ DONE | `demos/catch-the-ai-cheating/run_demo.py` + AST checker |
| E0.3 | ≥3 QA practitioners complete quickstart | ❌ HUMAN | Needs real users; spec-derived probe planner fixed (PR #R1) |
| E0.4 | Honest differentiation vs Schemathesis | ✅ DONE | `NORTH_STAR.md` §8 |

**Blocking state:** Only E0.3 (human recruitment) remains.

## Design invariants (deltas — non-negotiable)

- **D7 — never auto-edit test code.** Validate and healing produce reports/suggestions only. No test files are touched by automation.
- **Anti-lock-in.** `cherenkov eject` strips all CHERENKOV imports so tests run with vanilla Playwright + `openapi-fetch`.
- **Suggest-only healing.** Healing never auto-commits or auto-applies.
- **Spec-derived.** Expected HTTP status comes from the OpenAPI spec, not from hardcoded assumptions in test code.

---

## What to read next

1. `HANDOVER.md` — The authoritative source of truth for current tasks.
2. `docs/reviews/STRATEGY_REVIEW_2026-07-05.md` — The latest strategic review.
3. `docs/NORTH_STAR.md` — 10-year vision.
4. `docs/recordings/` — 8 Loom recording scripts for onboarding, demos, and pitching (live evidence captured 2026-07-06).
