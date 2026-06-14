**Last updated:** 2026-06-10
**Branch:** `feat/sdd-cockpit`

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
| 3 | Desktop Host | 🔧 Env ready | `cargo` 1.96.0 installed (WSL + Windows); final build needs `sudo apt install libwebkit2gtk-4.1-dev pkg-config` in WSL |
| 4 | Chat Agents | ✅ Complete | Tool-calling agent, persona registry, SSE (PRs #397–#400) |
| 5 | Mobile Testing Core | 🔧 Env ready | 232/232 unit tests pass; real-device ADB needs `sudo apt install android-tools-adb` in WSL |
| 6 | Mobile Execution | 🔧 Env ready | Depends on Phase 5 ADB; Maestro install pending |
| 7 | Dashboard Revamp | ✅ Complete | 9 screens built (PRs #401, #402, #405) |
| 8 | K8s + Cloud + Gate | ✅ Complete | `make k3d-test` green (2026-06-09); all 6 issues closed |

---

## Tracks

| Track | Scope | State |
|-------|-------|-------|
| A (Core) | API conformance testing | ✅ Built; validation gate passed (2026-06-08); **258 tests passing, 0 failures** |
| B (VLM) | LocalAI / Ollama substrate | ✅ Built; MCP policy engine + Docker Model Runner adapter added |
| C (Desktop) | Tauri 2 host | 🔧 Shell complete; `cargo check` green, valid Tauri 2 config, icons; IPC bridge scaffolded but not integration-tested; full build blocked on `libwebkit2gtk-4.1-dev` + PyInstaller sidecar (`packaging/build.sh`) |
| D (Mobile) | Maestro / Appium | ✅ Built, unit-tested; E2E dashboard tests added; runtime blocked on ADB |
| E (Dashboard) | React UI | ✅ Built; all 9 screens shipped; E2E error-path + multi-viewport tests added; `data-testid` coverage in progress |
| F (K8s) | Operator + CRDs | ✅ Complete (Phase 8) |

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
- **Product strategy & market roadmap?** → [PRODUCT_STRATEGY_ROADMAP.md](PRODUCT_STRATEGY_ROADMAP.md) (Phases 9-16, market analysis, 10-year vision)
- **Integration & ecosystem plan?** → [INTEGRATION_STRATEGY.md](INTEGRATION_STRATEGY.md) (25 integrations, 6 sprints)

---

## Finish-unblock commands (2026-06-10)

Run these once in a WSL terminal to fully unblock Phases 3, 5, and 6:

```bash
# Unblocks Phase 3 (Tauri desktop build on Linux)
sudo apt install -y build-essential pkg-config libwebkit2gtk-4.1-dev \
  libssl-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev

# Unblocks Phase 5/6 (real-device ADB)
sudo apt install -y android-tools-adb

# Unblocks Phase 6 (Maestro mobile test runner)
curl -Ls https://get.maestro.mobile.dev | bash

# Verify Tauri build
cd ~/cherenkov-qa/desktop/src-tauri
CARGO_HTTP_CAINFO=/etc/ssl/certs/ca-certificates.crt ~/.cargo/bin/cargo build
```

`cargo` 1.96.0 is already installed in WSL (`~/.cargo/bin/`) and on Windows
(`rustup` via winget). The 232 Python unit tests (all phases) pass as of this
session.

---

## Change log

- **2026-06-11** — QA Reasoning Engine foundation added (`cherenkov/reasoning/`):
  artifact-adaptive QA workflows per [ADR-007](adr/ADR-007-qa-reasoning-engine.md)
  and [vision/19_QA_REASONING.md](vision/19_QA_REASONING.md). 29 unit tests passing.
- **2026-06-10** — Updated: test pass rate 16 failures → 258 passing; Track B/D/E state refreshed for priority rounds #419, #425, #442; Phase 8 notes updated.
- **2026-06-09** — Created this file. Status deduplicated from `HANDOVER.md`,
  `README.md`, and `PHASE_PLAN.md`. `README.md` and `HANDOVER.md` now point
  here. See [AGENTS.md](../AGENTS.md) for agent operating rules.
