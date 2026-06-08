# CHERENKOV QA

**API conformance test generator** â€” spec in, Playwright tests out, zero lock-in.

CHERENKOV reads your OpenAPI spec, generates typed Playwright API tests via a local LLM (Ollama/Qwen 2.5-coder:7b), and runs them against your real server to catch conformance drift. Your spec never leaves your machine.

---

## What It Does (30 seconds)

```
OpenAPI Spec â†’ Local LLM â†’ Playwright Tests â†’ Run Against Real Server â†’ Conformance Report
```

1. **Reads** your OpenAPI 3.x spec
2. **Generates** typed Playwright `.spec.ts` files with `openapi-fetch`
3. **Validates** against your live server, reports conformance drift
4. **Suggests** stronger assertions (never auto-edits your tests)
5. **Ejects** to vanilla Playwright â€” zero vendor dependency

## Quick Start (5 minutes)

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

# Validate â€” watch it catch a real bug
PYTHONPATH=. ./bin/cherenkov validate --target http://localhost:8000
```

**What you'll see:** `happy_path [PASSED]` with tightening suggestions, and `password_too_short [FAILED]` â€” the spec says 422 for validation errors, but the server returns 400. A real conformance bug caught by a test nobody wrote.

## Commands

| Command | Purpose |
|---------|---------|
| `./bin/cherenkov validate --target <url>` | Run tests against a live server, generate tightening report |
| `./bin/cherenkov eject --output <dir>` | Export tests as standalone vanilla Playwright (zero CHERENKOV dependency) |
| `./bin/cherenkov --help` | Show all commands and options |

## The Anti-Lock-In Promise

```bash
./bin/cherenkov eject --output my_tests
cd my_tests && npm install && npx playwright test
```

One command strips everything. What's left is standard Playwright + openapi-fetch. If you stop using the tool tomorrow, your tests still run.

## Design Invariants

- **Never auto-edits tests** â€” validate and healing produce reports/suggestions only
- **Spec-derived** â€” expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions
- **Suggest-only healing** â€” failure diagnosis suggests fixes, never auto-commits
- **Zero lock-in** â€” `eject` strips all CHERENKOV metadata; tests run standalone

## Docs

- [Getting Started](docs/GETTING_STARTED.md) — full setup guide
- [CLI Demo](docs/CLI_DEMO.md) — terminal recording of the full flow
- [Technical Design](docs/TECHNICAL_DESIGN.md) — architecture overview
- [Consolidated Plan](docs/PHASE_PLAN.md) — **authoritative roadmap** (Phase -1 through Phase 8)
- [Architecture Principles](docs/engineering/ARCHITECTURE_PRINCIPLES.md) — non-negotiable tenets
- [Best Practices](docs/engineering/BEST_PRACTICES.md) — coding standards, testing, security

## Project Status

**Track A (API conformance testing):** core engine built; design invariants proven by tests.  
**Status:** The 5-QA-user validation gate is **passed** per owner decision (2026-06-08). All tracks are open for development.  
**Consolidated Plan:** Phase -1 through Phase 8 (see [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md)).

### What's Next (Consolidated Plan)

The consolidated plan extends CHERENKOV with 5 new capabilities:

1. **Second Brain** (Phase 1) — Knowledge mesh, GraphRAG, event bridges
2. **VLM + LocalAI** (Phase 2) — LocalAI as default VLM backend, tier-aware routing
3. **Desktop Host** (Phase 3) — Tauri 2 app, hardware detection, 7-step setup wizard
4. **Chat Agents** (Phase 4) — Tool-calling agent, persona registry, SSE streaming
5. **Mobile Testing** (Phase 5-6) — Maestro/Appium, 4-tier devices, semantic visual oracle

**Current Status:**
- ✅ Phase -1 (Planning & Preparation): Complete. All 6 ADRs written, all strategy docs created.
- ✅ Phase 0a (P0 Bug Fixes): Complete. All 8 bugs documented in issues #304-#312.
- 🔶 Phase 0b (Foundations): Next. Ports, events, devices, config, Docker Compose AI.
- ⏸️ Phase 1-8: Planned. See [PHASE_PLAN.md](docs/PHASE_PLAN.md) for details.

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 (Second Brain) → 4 (Chat)
- Track B (VLM): Phase 2 (parallel with Phase 1)
- Track C (Desktop): Phase 3 (after Phase 2 validation)
- Track D (Mobile): Phase 5 (after Phase 2) → Phase 6
- Track E (Dashboard): Phase 7 (after Phase 4 and Phase 6)
- Track F (K8s): Phase 8 (after Phase 7)

See [AGENTS.md](AGENTS.md) for agent operating rules and [docs/SCOPE_LEDGER.md](docs/SCOPE_LEDGER.md) for the honest scope map.

