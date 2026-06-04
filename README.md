# CHERENKOV QA

**API conformance test generator** — spec in, Playwright tests out, zero lock-in.

CHERENKOV reads your OpenAPI spec, generates typed Playwright API tests via a local LLM (Ollama/Qwen 2.5-coder:7b), and runs them against your real server to catch conformance drift. Your spec never leaves your machine.

---

## What It Does (30 seconds)

```
OpenAPI Spec → Local LLM → Playwright Tests → Run Against Real Server → Conformance Report
```

1. **Reads** your OpenAPI 3.x spec
2. **Generates** typed Playwright `.spec.ts` files with `openapi-fetch`
3. **Validates** against your live server, reports conformance drift
4. **Suggests** stronger assertions (never auto-edits your tests)
5. **Ejects** to vanilla Playwright — zero vendor dependency

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

# Validate — watch it catch a real bug
PYTHONPATH=. ./bin/cherenkov validate --target http://localhost:8000
```

**What you'll see:** `happy_path [PASSED]` with tightening suggestions, and `password_too_short [FAILED]` — the spec says 422 for validation errors, but the server returns 400. A real conformance bug caught by a test nobody wrote.

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

- **Never auto-edits tests** — validate and healing produce reports/suggestions only
- **Spec-derived** — expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions
- **Suggest-only healing** — failure diagnosis suggests fixes, never auto-commits
- **Zero lock-in** — `eject` strips all CHERENKOV metadata; tests run standalone

## Docs

- [Getting Started](docs/GETTING_STARTED.md) — full setup guide
- [CLI Demo](docs/CLI_DEMO.md) — terminal recording of the full flow
- [Technical Design](docs/TECHNICAL_DESIGN.md) — architecture overview
- [Development Plan](docs/TECHNICAL_DEVELOPMENT_PLAN.md) — phase-by-phase roadmap

## Project Status

**Track A (API conformance testing):** core engine built; design invariants proven by tests.
**The real blocker:** the 5-QA-user validation gate is **NOT passed** (a prior "passed" claim was fabricated — see [docs/HANDOVER.md](docs/HANDOVER.md)).
**What's next:** make one end-to-end human workflow real and frictionless, then validate it — see the [forward roadmap](docs/ROADMAP_NEXT.md) and the [golden-path workflow](docs/ROADMAP_NEXT.md#2-the-golden-path-the-meaningful-e2e-human-workflow).

See [AGENTS.md](AGENTS.md) for agent operating rules and [docs/SCOPE_LEDGER.md](docs/SCOPE_LEDGER.md) for the honest scope map.
