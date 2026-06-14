# CHERENKOV QA — Wiki

> **Spec in. Playwright tests out. Zero lock-in.**
> Source of truth lives in the repo. This wiki mirrors it. When in doubt, the repo wins.

CHERENKOV generates and runs conformance tests for **APIs, web UIs, and mobile apps** from your OpenAPI spec,
using a local LLM, with zero cloud dependency and zero vendor lock-in.

```
openapi.yaml  ──▶  cherenkov validate  ──▶  Playwright tests  ──▶  eject  ──▶  run anywhere
```

---

## New Here?

1. **[docs/GETTING_STARTED.md](../GETTING_STARTED.md)** — install and run your first test in 5 minutes
2. Run `./bin/cherenkov doctor` — verify Ollama, Node, and Playwright are wired up
3. Run `./bin/cherenkov validate --target http://localhost:8000` — catch your first conformance bug
4. Read **[Concepts](Concepts.md)** — understand spec-derived oracles, 6-gate review, and eject

---

## What Does It Test?

| Layer | How | Status |
|-------|-----|--------|
| **API** | REST endpoints vs OpenAPI spec — status codes, schemas, auth | ✅ Production ready |
| **Web** | Playwright browser flows — headed or headless, VLM visual regression | ✅ Playwright ready |
| **Mobile** | Maestro + Appium device flows, VLM visual oracle | ✅ Built · needs ADB |

---

## Wiki Pages

| Page | What's in it |
|------|-------------|
| [Concepts](Concepts.md) | Core ideas: spec-derived oracle, 6-gate review, eject, suggest-only healing |
| [Pipeline](Pipeline.md) | How the 5-stage ingest → plan → generate → review → run pipeline works |
| [Architecture](Architecture.md) | System design, directory map, Mermaid diagrams, ADR index |
| [CLI Reference](CLI-Reference.md) | Every command, flag, and option with examples |
| [Configuration](Configuration.md) | Env vars, config file, LLM tier setup |
| [Deployment](Deployment.md) | L0–L5 tiers, Docker, K8s, local dev setup |
| [Roadmap](Roadmap.md) | Phase timeline, track status, what's next |
| [FAQ](FAQ.md) | Common questions — including "how is this different from Dredd/Schemathesis?" |
| [Troubleshooting](Troubleshooting.md) | Fix guide for common problems |
| [Testing](Testing.md) | Running tests, writing tests, CI matrix explained |
| [Way-of-Work](Way-of-Work.md) | Contribution workflow — the full loop |
| [Contributing](Contributing.md) | First contribution, dev setup, code style, review process |
| [Security](Security.md) | Vulnerability reporting, security model, secure usage |

---

## Core Promises

| Promise | How It's Enforced |
|---------|-------------------|
| **Never auto-edits your code** | D7 invariant — `smoke_test_healing.py` runs in every CI build |
| **Zero lock-in** | Ejected tests contain zero CHERENKOV imports — `smoke_test_eject.py` in CI |
| **Local by default** | Ollama runs on your machine; your spec never leaves without explicit opt-in |
| **Spec-derived oracle** | Expected status codes come from the OpenAPI spec, never hardcoded |

---

## Key Links

| | |
|--|--|
| **[README.md](../../README.md)** | Project overview, quick start, feature table |
| **[docs/INDEX.md](../INDEX.md)** | Full documentation tree |
| **[docs/STATUS.md](../STATUS.md)** | Canonical project status (single source of truth) |
| **[docs/PHASE_PLAN.md](../PHASE_PLAN.md)** | Detailed phase plan — all phases, all tickets |
| **[CONTRIBUTING.md](../../CONTRIBUTING.md)** | How to contribute (humans and agents) |
| **[AGENTS.md](../../AGENTS.md)** | Rules for AI agents working on this project |
| **[docs/adr/](../adr/)** | Architecture Decision Records |
