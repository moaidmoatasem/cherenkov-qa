# CHERENKOV-QA — Comprehensive Project Review

**Reviewed:** 2026-06-15
**Reviewer:** AI Code Review Agent
**Project:** [cherenkov-qa](https://github.com/moaidmoatasem/cherenkov-qa)
**Version:** 0.1.0

---

## Executive Summary

CHERENKOV is an OpenAPI spec-to-Playwright test generation and conformance validation tool. It ingests an OpenAPI 3.x spec, generates typed Playwright tests via a local LLM (Ollama + qwen2.5-coder:7b), runs a 6-gate review pipeline, executes them against a live server, and reports where the implementation diverges from the spec. It enforces a "zero lock-in" eject invariant — generated tests can run without CHERENKOV.

**Core pipeline:** `INGEST → PLAN → GENERATE → REVIEW → RUN → REPORT`

**Overall Score: 6.8/10** — Strong architecture, weak operational discipline.

---

## Score Card

| Dimension | Score | Notes |
|-----------|:-----:|-------|
| **Architecture** | 8/10 | Strong foundations — contracts, hexagonal, circuit breaker |
| **Core Pipeline** | 8.5/10 | Well-engineered, typed, resilient |
| **AI Layer** | 7/10 | Good router, but latency/cost tracking is stubbed |
| **Healing System** | 7.5/10 | Solid classification, suggest-only invariant |
| **Divergence Engine** | 7/10 | Good taxonomy, thin implementation |
| **CLI** | 5/10 | Massive single file, mixed frameworks |
| **Tests** | 6.5/10 | Good breadth, thin e2e/eval, split execution |
| **CI/CD** | 5/10 | All jobs non-blocking, defeats CI purpose |
| **Docker** | 6/10 | Functional but outdated Python, no hardening |
| **Security** | 7/10 | Good foundations, missing headers + API key handling |
| **Code Hygiene** | 4/10 | Artifacts in git, root clutter, duplicate deps |
| **Documentation** | 8/10 | Extensive docs/wiki, ADRs, phase plans |

---

## Architecture Strengths

### 1. Typed Pipeline Contracts (contracts.py — 691 lines)

The Pydantic boundary contracts are the project's strongest architectural asset. Every stage emits a typed model (IngestOutput → PlanOutput → GenerateOutput → ReviewOutput) with schema versioning and a migration registry (`load_versioned()`). If a stage returns a raw dict, it fails loudly at the boundary.

### 2. Circuit Breaker + Retry Ladder (orchestrator.py)

The `CircuitBreaker` (trips after N failures) combined with `_execute_stage_with_retry()` (exponential backoff, 3 attempts, then fallback) is production-grade resilience. The D2 Planner Feedback loop is particularly clever — when Prism dry-run fails, it cycles through alternative mutations from the endpoint's menu before giving up.

### 3. 5-Way Divergence Space + Skeptic-Witness Pattern

The divergence engine's D1-D5 taxonomy (spec-code, code-prod, UI-spec, DB-code, spec-prod) is well-thought-out. The Skeptic generates hypotheses via the Substrate Router (never naming a model directly), and the Witness independently reproduces them. The Reflector's verdict-memory reranking (previously rejected hypotheses suppressed, confirmed idioms boosted) is a genuine learning loop.

### 4. 6-Gate Review Pipeline

The review stage is rigorous: syntax → structure → AST (forbidden keyword detection) → assertions (status code + body shape) → TSC compilation → Prism dynamic mock dry-run. Each gate is a clear pass/fail.

### 5. Substrate Router with Protocol-based Providers

The `ModelProvider` Protocol (generate + capabilities) with egress policy enforcement and fallback spill-over is clean. The `_enforce_egress()` method correctly blocks providers based on policy (`none | internal | github | external`).

### 6. Hexagonal Architecture

Ports/adapters pattern in `ports/` (device_registry, event_bus, knowledge_repository, vlm_provider) and clean separation of domain logic (divergence, knowledge, reasoning) from infrastructure (substrate, execution, web).

---

## Issues Found

### 🔴 P0 — Critical (Must Fix)

| # | Issue | File | Details |
|---|-------|------|---------|
| 1 | ~~CI `continue-on-error: true` on all jobs~~ | `.github/workflows/ci.yml` | ~~Fixed: removed from `docker-build-check`. `type-check` and `coverage` were already fixed.~~ ✅ Fixed |
| 2 | ~~Broken pyproject.toml entry point~~ | `cherenkov/__init__.py` | ~~`cherenkov = "cherenkov:main"` referenced non-existent `main` in `__init__.py`~~ ✅ Fixed |
| 3 | Thread-safety bug in `set_events_file()` | `cherenkov/core/orchestrator.py:294` | Module-level global shared across threads. Multiple concurrent pipelines will overwrite each other's events file. Needs `threading.local()`. |
| 4 | ~~Duplicate `jsonschema` in `requirements.txt`~~ | `requirements.txt` | ~~Already fixed in current file.~~ ✅ Already fixed |

### 🟡 P1 — High Priority

| # | Issue | File | Details |
|---|-------|------|---------|
| 5 | CLI is 1032 lines (God File) | `cherenkov.py` / `cherenkov/cli.py` | Uses argparse while Click is a dependency. Should be refactored to Click-based subcommands. |
| 6 | Appium, Redis as core deps | `pyproject.toml` | Should be optional extras (`[mobile]`, `[redis]`). |
| 7 | Docker uses Python 3.10 | `Dockerfile` | CI uses 3.12. Docker should match. |
| 8 | No non-root user in Docker | `Dockerfile` | Runs as root. |
| 9 | No HEALTHCHECK in Docker | `Dockerfile` | Missing container health check. |
| 10 | Git artifacts committed | Root dir | `cherenkov.egg-info/`, `__pycache__/`, `.coverage.*`, `nul`, log files. |
| 11 | `stripe_spec.json` (7.8MB) in git | Root dir | Large fixture should be gitignored or downloaded as test fixture. |
| 12 | 4 patch scripts at root | `patch_*.py` | Should be in `scripts/` or removed. |
| 13 | Config class-level mutable state | `cherenkov/core/config.py` | Class-level attributes read at import time. Fragile for testing and concurrent use. |

### 🟢 P2 — Medium Priority

| # | Issue | File | Details |
|---|-------|------|---------|
| 14 | Latency/cost stubbed at 0 | `cherenkov/substrate/provider.py` | `OllamaProvider.generate()` returns `latency_ms=0`. Should measure actual HTTP call time. |
| 15 | No HTTP security headers | `cherenkov/web/` | Missing CSP, X-Frame-Options, HSTS (per QA report). |
| 16 | Coverage threshold low | CI | Was 50%, now 70%. Could go higher. |
| 17 | `_load_system_prompt()` at import time | `cherenkov/stages/generate.py:62` | Makes module un-importable if file missing. |
| 18 | Duck-typing in AI router | `cherenkov/ai/router.py:28` | Uses `hasattr(client, "complete")` instead of Protocol. |
| 19 | `import hashlib as _hashlib` redundant | `cherenkov/healing/diagnose.py:23` | Already imported at line 10. |
| 20 | Missing `data-testid` attributes | React dashboard | No test IDs on interactive elements. |
| 21 | Missing `license` field | `pyproject.toml` | LICENSE file exists but not declared in metadata. |

---

## Subsystem Assessment

### Core Pipeline (orchestrator.py + stages/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Stage isolation | ✅ Excellent | Typed contracts, boundary validation |
| Resilience | ✅ Excellent | Circuit breaker + retry ladder + fallback |
| Thread safety | ⚠️ Needs work | `set_events_file()` is module-level global |
| Progress reporting | ⚠️ Needs work | ANSI escape codes break on Windows |
| D2 feedback loop | ✅ Excellent | Dynamic re-planning with mutation cycling |

### Generate Stage (stages/generate.py — 345 lines)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Prompt injection defense | ✅ Good | `_sanitize_prompt_input()` strips known markers |
| System prompt loading | ⚠️ Fragile | Called at import time, relative path resolution |
| Cache integration | ✅ Good | Prefix cache optimization (E1-5) |

### Review Stage (stages/review.py — 468 lines)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Gate rigor | ✅ Excellent | 6 gates, each with clear pass/fail |
| TSC filtering | ✅ Smart | Filters out pre-existing errors from other files |
| Prism integration | ✅ Good | Ephemeral Docker container, proper cleanup |
| Healing integration | ✅ Good | Diagnoser records snapshots on pass, classifies on fail |

### Substrate Router (substrate/router.py + provider.py)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Provider abstraction | ✅ Excellent | Protocol-based `ModelProvider` |
| Egress enforcement | ✅ Excellent | Policy-driven with clear error messages |
| Fallback spillover | ✅ Good | Automatic with same-provider detection |
| Latency tracking | ⚠️ Stub | `latency_ms=0` hardcoded |

### Healing System (healing/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Diagnoser classification | ✅ Good | 6 failure classes with clear logic |
| Snapshot diffing | ✅ Good | Stale snapshot detection |
| Suggest-only invariant | ✅ Critical | Never auto-edits user code |

### Divergence Engine (divergence/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Hypothesis generation | ✅ Good | Adversarial prompt, structured JSON schema |
| Reflector reranking | ✅ Good | Verdict memory suppresses/boosts |
| Parsing resilience | ✅ Good | Graceful handling of unparseable LLM output |

### MCP Server (mcp/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Protocol compliance | ✅ Good | MCP 2024-11-05 lifecycle, JSON-RPC 2.0 |
| No SDK dependency | ✅ Good | Custom implementation |
| Testability | ✅ Good | Injectable streams |

### Knowledge Mesh (knowledge/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| GraphRAG query | ✅ Basic | Multi-source parallel queries, confidence ranking |
| Depth | ⚠️ Shallow | 53 lines — minimal logic, mostly delegation |

### Web Dashboard (web/)

| Aspect | Rating | Notes |
|--------|:------:|-------|
| React SPA | ✅ Good | 9 screens, Vite build |
| Security headers | ❌ Missing | No CSP, X-Frame-Options, HSTS |
| Testability | ❌ Missing | No `data-testid` attributes |

---

## Test Infrastructure

| Tier | Count | Purpose | Quality |
|------|:-----:|---------|:-------:|
| `unit/` | ~45 files | Individual module tests | ✅ Good |
| `smoke/` | ~40 files | Quick integration checks | ✅ Good |
| `standalone/` | ~35 files | Environment-dependent | ⚠️ Split from pytest |
| `integration/` | ~5 files | API, K8s, Redis | ⚠️ Thin |
| `e2e/` | 1 file | Golden path | ⚠️ Very thin |
| `eval/` | 1 file | Generation quality | ⚠️ Very thin |

---

## CI/CD

### Fixed Issues
- ✅ `docker-build-check` no longer uses `continue-on-error: true`
- ✅ `type-check` (mypy) no longer uses `continue-on-error: true` or `|| true`
- ✅ Coverage threshold raised from 50% to 70%

### Remaining Issues
- ⚠️ ~15 jobs still use `continue-on-error: true` (smoke tests, standalone tests)
- ⚠️ These are acceptable for env-dependent tests but should be monitored

---

## Docker

| Aspect | Rating | Notes |
|--------|:------:|-------|
| Multi-stage build | ✅ Good | React UI + Python runtime |
| Python version | ⚠️ 3.10 | Should be 3.12 to match CI |
| Non-root user | ❌ Missing | Runs as root |
| HEALTHCHECK | ❌ Missing | No container health check |

---

## Priority Action Items

### P0 — Fixed ✅
1. ~~CI `continue-on-error: true` on `docker-build-check`~~
2. ~~`pyproject.toml` entry point (`cherenkov/__init__.py` now re-exports `main`)~~

### P0 — Remaining
3. Thread-safety: Replace `set_events_file()` global with `threading.local()`

### P1 — High Priority
4. Refactor CLI from 1032-line argparse to Click
5. Make Appium, Redis, desktop deps optional
6. Docker: Upgrade to Python 3.12, add non-root user, add HEALTHCHECK
7. Clean git artifacts (egg-info, __pycache__, coverage, logs, patch scripts)
8. Move `stripe_spec.json` (7.8MB) out of git
9. Fix Config class pattern for testability

### P2 — Medium Priority
10. Wire latency measurement into provider generate methods
11. Add HTTP security headers middleware to FastAPI
12. Make mypy non-optional in CI
13. Fix `_load_system_prompt()` import-time side effect
14. Add `data-testid` attributes to React dashboard
15. Add `license` field to pyproject.toml

---

## Conclusion

CHERENKOV has **exceptional architectural foundations** — the typed pipeline contracts, circuit breaker, D2 feedback loop, 5-way divergence taxonomy, and 6-gate review pipeline are genuinely well-engineered. The hexagonal architecture and Substrate Router with egress policy enforcement show real systems thinking.

The weaknesses are almost entirely in **operational discipline**: the CLI is a single massive file, the Config pattern creates testability and concurrency issues, and code hygiene needs attention. These are all fixable without architectural changes.

**The core product is strong. The packaging needs work.**
