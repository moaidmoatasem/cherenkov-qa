# CHERENKOV QA

**API conformance test generator** — spec in, Playwright tests out, zero lock-in.

CHERENKOV reads your OpenAPI spec, generates typed Playwright API tests via a
local LLM (Ollama, `qwen2.5-coder:7b` by default), and runs them against your
real server to catch conformance drift. Your spec never leaves your machine.

> **📍 New here?** Start with the **[Getting Started](docs/GETTING_STARTED.md)**
> guide (5 min) and the **[CLI demo](docs/CLI_DEMO.md)** walk-through.
> **Need the project state?** It's all in one place:
> **[docs/STATUS.md](docs/STATUS.md)**.

---

## What it does (30 seconds)

```
OpenAPI Spec → Local LLM → Playwright Tests → Run Against Real Server → Conformance Report
```

1. **Reads** your OpenAPI 3.x spec.
2. **Generates** typed Playwright `.spec.ts` files with `openapi-fetch`.
3. **Validates** against your live server, reports conformance drift.
4. **Suggests** stronger assertions (never auto-edits your tests).
5. **Ejects** to vanilla Playwright — zero vendor dependency.

---

## Quick start (5 minutes)

```bash
# Clone and install
git clone https://github.com/moaidmoatasem/cherenkov-qa.git
cd cherenkov-qa
python3 -m venv .venv && source .venv/bin/activate
pip install -r target/requirements.txt

# Install Playwright + Node deps
cd stub && npm install && npx playwright install && cd ..

# Start the target API
cd target && source ../.venv/bin/activate
uvicorn target_api:app --host 127.0.0.1 --port 8000 &
cd ..

# Validate — watch it catch a real bug
PYTHONPATH=. ./bin/cherenkov validate --target http://localhost:8000
```

**What you'll see:** `happy_path [PASSED]` with tightening suggestions, and
`password_too_short [FAILED]` — the spec says 422 for validation errors, but
the server returns 400. A real conformance bug caught by a test nobody wrote.

Full setup, prerequisites, and troubleshooting →
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

---

## Commands

| Command | Purpose |
|---------|---------|
| `./bin/cherenkov validate --target <url>` | Run tests against a live server, generate tightening report |
| `./bin/cherenkov eject --output <dir>` | Export tests as standalone vanilla Playwright (zero CHERENKOV dependency) |
| `./bin/cherenkov --help` | Show all commands and options |

The CLI exposes the full pipeline plus a `review --web` dashboard. See
[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for the complete reference.

---

## The anti-lock-in promise

```bash
./bin/cherenkov eject --output my_tests
cd my_tests && npm install && npx playwright test
```

One command strips everything. What's left is standard Playwright +
`openapi-fetch`. If you stop using the tool tomorrow, your tests still run.

---

## Design invariants (non-negotiable)

- **Never auto-edits tests** — validate and healing produce reports/suggestions only.
- **Spec-derived** — expected HTTP status comes from the OpenAPI spec, not hardcoded.
- **Suggest-only healing** — failure diagnosis suggests fixes, never auto-commits.
- **Zero lock-in** — `eject` strips all CHERENKOV metadata; tests run standalone.

These are codified as the project deltas (D7, anti-lock-in, suggest-only,
spec-derived). See [AGENTS.md](AGENTS.md) for the full list.

---

## Project status

**Current state:** Track A is **built** and the 5-QA user-validation gate has
been **passed per owner decision on 2026-06-08**. All six tracks (A core, B VLM,
C desktop, D mobile, E dashboard, F K8s) are open for development. The active
phase is **Phase 8 (K8s + Cloud + Gate)**; Phase 3 and Phase 5–6 are blocked
on `cargo` / ADB respectively.

For the canonical per-phase status table, design invariants, environment, and
cost tiers, read **[docs/STATUS.md](docs/STATUS.md)**.

The consolidated plan (10 phases, ~105 GitHub issues) is the authoritative
roadmap: **[docs/PHASE_PLAN.md](docs/PHASE_PLAN.md)**.

### What the consolidated plan delivers

1. **Second Brain** (Phase 1) — knowledge mesh, GraphRAG, event bridges.
2. **VLM + LocalAI** (Phase 2) — LocalAI as default VLM backend, tier-aware routing.
3. **Desktop Host** (Phase 3) — Tauri 2 app, hardware detection, 7-step setup wizard.
4. **Chat Agents** (Phase 4) — tool-calling agent, persona registry, SSE streaming.
5. **Mobile Testing** (Phase 5–6) — Maestro/Appium, 4-tier devices, semantic visual oracle.
6. **Dashboard Revamp** (Phase 7) — real data, mobile / chat / knowledge screens.
7. **K8s + Cloud** (Phase 8) — CRD extensions, operator, open-source readiness.

Phase -1, 0a, 0b, 1, 2, 4, and 7 are complete. Phase 8 is in progress
(`SECURITY.md` added; needs `k3d` for #386–#388). See
[docs/STATUS.md](docs/STATUS.md) for the canonical state.

---

## Documentation

**Start here:**

- **[docs/INDEX.md](docs/INDEX.md)** — the single entry point for the whole docs tree.
- **[docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)** — install + first test in 5 minutes.
- **[docs/CLI_DEMO.md](docs/CLI_DEMO.md)** — terminal walk-through of the full flow.

**For contributors and agents:**

- **[docs/STATUS.md](docs/STATUS.md)** — canonical project state.
- **[docs/HANDOVER.md](docs/HANDOVER.md)** — authoritative state for agents.
- **[docs/PHASE_PLAN.md](docs/PHASE_PLAN.md)** — consolidated Phase -1 → 8 plan.
- **[AGENTS.md](AGENTS.md)** — agent operating rules, deltas, track status.
- **[docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md)** — core architecture policy.

**Architecture and decisions:**

- **[docs/engineering/SYSTEM_DESIGN.md](docs/engineering/SYSTEM_DESIGN.md)** — system design.
- **[docs/engineering/ARCHITECTURE_PRINCIPLES.md](docs/engineering/ARCHITECTURE_PRINCIPLES.md)** — non-negotiable tenets.
- **[docs/engineering/BEST_PRACTICES.md](docs/engineering/BEST_PRACTICES.md)** — coding standards, testing, security.
- **[docs/adr/](docs/adr/)** — Architecture Decision Records.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md),
and [SECURITY.md](SECURITY.md). For agent work, read [AGENTS.md](AGENTS.md)
first.
