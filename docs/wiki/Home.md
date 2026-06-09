# CHERENKOV QA — Wiki

> **Source of truth lives in the repo.** This wiki mirrors it. When in doubt, the repo wins.

CHERENKOV generates and runs conformance tests for **APIs, web UIs, and mobile apps** — from your OpenAPI spec, using a local LLM, with zero cloud dependency and zero vendor lock-in.

---

## What Does It Test?

| Layer | How | Status |
|-------|-----|--------|
| **API** | REST endpoints vs OpenAPI spec — status codes, schemas, auth | ✅ Fully working |
| **Web** | Playwright browser flows — headed or headless, visual regression via VLM | ✅ Playwright ready |
| **Mobile** | Maestro + Appium device flows, VLM visual oracle | ✅ Built · needs ADB |

All modes support **headed** (visible window) and **headless** (CI mode).

---

## Wiki Pages

| Page | What's in it |
|------|-------------|
| [Pipeline](Pipeline.md) | How the 5-stage pipeline works |
| [Architecture](Architecture.md) | System design and Mermaid diagrams |
| [CLI Reference](CLI-Reference.md) | Every command, flag, and option |
| [Configuration](Configuration.md) | Env vars, config file, LLM setup |
| [Deployment](Deployment.md) | Docker, K8s, local dev (L1–L5) |
| [Roadmap](Roadmap.md) | Phase timeline, track status |
| [FAQ](FAQ.md) | Common questions |
| [Troubleshooting](Troubleshooting.md) | Fix guide for common problems |
| [Way-of-Work](Way-of-Work.md) | Contribution workflow |

---

## New Here?

1. Read [docs/GETTING_STARTED.md](../GETTING_STARTED.md) — install in 5 minutes
2. Run `./bin/cherenkov doctor` — check everything is installed
3. Run `./bin/cherenkov validate --target http://localhost:8000` — catch your first bug

---

## Core Promises

| Promise | Enforcement |
|---------|------------|
| **Never auto-edits your code** | D7 invariant — `smoke_test_healing.py` in CI |
| **Zero lock-in** | `eject` produces vanilla Playwright — `smoke_test_eject.py` in CI |
| **Local by default** | Ollama runs on your machine |
| **Spec-derived oracle** | Expected status from OpenAPI spec, never hardcoded |

---

## Key Links

- **[README.md](../../README.md)** — project overview and quick start
- **[docs/INDEX.md](../INDEX.md)** — full documentation tree
- **[docs/STATUS.md](../STATUS.md)** — canonical project status (single source of truth)
- **[CONTRIBUTING.md](../../CONTRIBUTING.md)** — how to contribute
- **[AGENTS.md](../../AGENTS.md)** — rules for AI agents working on this project
