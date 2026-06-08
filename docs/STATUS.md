# CHERENKOV — Project Status (canonical)

> **Single source of truth for project status.** If another doc says something
> different about phase progress, **this doc wins**. Linked from
> [README.md](../README.md), [HANDOVER.md](HANDOVER.md), and
> [PHASE_PLAN.md](PHASE_PLAN.md).

**Last updated:** 2026-06-09  
**Branch:** `main` (working tree clean at start of docs pass)

---

## At a glance

CHERENKOV is an **API conformance test generator** that turns an OpenAPI spec
into Playwright tests using a local LLM, runs them against a real server, and
catches spec-conformance drift. The core (Track A) is built and the user
validation gate has been passed. All tracks are now open for development
under the consolidated Phase -1 through Phase 8 plan.

---

## Phase status (consolidated)

| Phase | Name | Status | Notes |
|------:|------|:------:|-------|
| -1 | Planning & Preparation | ✅ Complete | 6 ADRs, strategy docs |
| 0a | P0 bug fixes | ✅ Complete | 8 bugs, issues #304–#312 |
| 0b | Foundations | ✅ Complete | Ports, events, devices, config (PRs #393, #394) |
| 1 | Second Brain | ✅ Complete | Knowledge mesh, GraphRAG, event bridges (PR #395) |
| 2 | VLM + LocalAI | ✅ Complete | LocalAI default, tier routing, doctor CLI (PR #396) |
| 3 | Desktop Host | ⏸ Blocked | Needs `cargo` on this machine |
| 4 | Chat Agents | ✅ Complete | Tool-calling agent, persona registry, SSE (PRs #397–#400) |
| 5 | Mobile Testing Core | ⏸ Blocked | Needs ADB on this machine |
| 6 | Mobile Execution | ⏸ Blocked | Depends on Phase 5 |
| 7 | Dashboard Revamp | ✅ Complete | 9 screens built (PRs #401, #402, #405) |
| 8 | K8s + Cloud + Gate | 🔶 In progress | `SECURITY.md` added (#404); needs `k3d` for #386–#388 |

---

## Tracks

| Track | Scope | State |
|-------|-------|-------|
| A (Core) | API conformance testing | ✅ Built, core invariants proven, validation gate passed (2026-06-08) |
| B (VLM) | LocalAI / Ollama substrate | ✅ Built, unit-tested, re-integrated into live tree |
| C (Desktop) | Tauri 2 host | ✅ Built, unit-tested, re-integrated; runtime blocked on `cargo` |
| D (Mobile) | Maestro / Appium | ✅ Built, unit-tested, re-integrated; runtime blocked on ADB |
| E (Dashboard) | React UI | ✅ Built, all 9 screens shipped |
| F (K8s) | Operator + CRDs | 🔶 In progress (Phase 8) |

> **Note on `track-b-c-deferred/`:** Earlier handover docs described a
> separate `track-b-c-deferred/` directory. That directory was **fully
> re-integrated into the live tree and deleted** (see
> [AGENTS.md](../AGENTS.md)). If you see `track-b-c-deferred/` referenced
> elsewhere, treat it as stale.

---

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
- **Decision rationale?** → [adr/](adr/)

---

## Change log

- **2026-06-09** — Created this file. Status deduplicated from `HANDOVER.md`,
  `README.md`, and `PHASE_PLAN.md`. `README.md` and `HANDOVER.md` now point
  here. See [AGENTS.md](../AGENTS.md) for agent operating rules.
