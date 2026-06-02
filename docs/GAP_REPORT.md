# CHERENKOV — Technical Development Plan Gap Report
**SSOT / Authority:** v3.1 + delta · **For:** AI agents + Moaid

This document contains a comprehensive, raw-evidence-backed audit of the code under `cherenkov/` against the authoritative `docs/TECHNICAL_DEVELOPMENT_PLAN.md`. Each phase is critically evaluated and classified to establish the real, honest state of the product.

---

## Executive Summary

```
Total Development Phases: 12
WORKS / COMPLETED:         2  (Phase 6, Phase 11)
STRUCTURAL DIFFERENCE:     2  (Phase 9, Phase 10 - Both fully functional but consolidated)
PARTIAL / INCOMPLETE:      8  (Phases 1, 2, 3, 4, 5, 7, 8, 12)
```

The core CHERENKOV Track A API conformance engine is highly functional and cleanly structured, but several plan requirements are missing, incomplete, or consolidated. Key gaps include:
1. **No active DB integrations** (SQLite/Postgres) in the core pipeline for HITL queue storage.
2. **Missing LLM planners & gates** (Deterministic scenario selection instead of DeepSeek LLM; no Gate 4 Novelty embedding check, no Gate 6 LLM quality check).
3. **No test-content hashing** to detect modified test suites for healing snapshots.
4. **Structural consolidations** where eject/validate phases were moved directly under `cherenkov/execution/` to keep clean import seams.

---

## Detailed Gap Analysis by Phase

### Phase 1 — Week 1 — Generator Hardening
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** `SYSTEM_PROMPT` is defined inside [cherenkov/stages/generate.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/stages/generate.py#L16-L45) as a static constant to ensure prefix-cache optimization on Ollama (Delta D10 / V1).
  - **Incomplete/Missing:** The plan states: *"The tuned prompt is committed to `prompts/generator_system.txt`"*. The `prompts/` directory and `generator_system.txt` file are entirely missing from the repository. The prompt remains embedded in the Python generation stage code.

### Phase 2 — Weeks 2-3 — Core Infrastructure
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** Type-safe, versioned Pydantic contracts exist for every boundary (`IngestOutput`, `PlanOutput`, `GenerateOutput`, `ReviewOutput`) in [cherenkov/core/contracts.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/core/contracts.py). Structured logger emitting JSONL to stderr exists in [cherenkov/core/errors.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/core/errors.py#L40-L70). Ollama client with format constraint is implemented in [cherenkov/ai/ollama_client.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/ai/ollama_client.py#L45-L93).
  - **Structural Difference:** There is no separate `core/logging.py` or `ai/strip_think.py` file. Logging was consolidated into `core/errors.py`, and `strip_think` was inline-defined in `ai/ollama_client.py`.
  - **Incomplete/Missing:** The plan states: *"SQLite default; `--engine postgres` switch via `DATABASE_URL`"* and *"SQLite DB created on first run with zero config."* The core Track A pipeline contains no SQLite schema, database initialization, or Postgres adapter. Database capability is exclusively found inside the quarantined Track B performance metric stage.

### Phase 3 — Weeks 4-5 — Pipeline Skeleton
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** `core/orchestrator.py` correctly links the INGEST, PLAN, GENERATE, and REVIEW stages with Pydantic contract boundaries. A circuit breaker correctly records failures, and drops scenario execution when error thresholds are exceeded.
  - **Structural Difference:** There is no separate `cli/progress.py` file. CLI progress spinners and dynamic carriage returns are directly printed inside [cherenkov/core/orchestrator.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/core/orchestrator.py#L204-L210) using terminal escape formatting.

### Phase 4 — Weeks 6-7 — INGEST (real)
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** [cherenkov/stages/ingest.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/stages/ingest.py) parses specs, resolves `$ref` with a depth constraint (`SCHEMA_DEPTH`), calculates richness scores, and builds a deterministic mutation menu (missing fields, extreme strings, numeric boundaries).
  - **Structural Difference:** Type generation is handled out-of-band via command line commands (documented in `RUN_ORDER.md`) instead of running `openapi-typescript` programmatically inside `ingest.py`.
  - **Incomplete/Missing:** The plan states: *"`json-schema-faker` for missing payloads"*. This javascript library is completely missing and not integrated into the python ingestion stage. Payload structure instructions are entirely textual LLM prompt-driven rather than faker synthetics.

### Phase 5 — Weeks 8-9 — PLAN + GENERATE (real)
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** `stages/generate.py` correctly coordinates scenario data and invokes Ollama `qwen2.5-coder` to generate compile-ready TypeScript tests.
  - **Incomplete/Missing:** The plan states: *"`stages/plan.py` (deepseek-r1:8b): emit scenarios... SELECT from the menu"*. The actual [cherenkov/stages/plan.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/stages/plan.py) is simple, deterministic Python code that maps the Ingest mutation menu straight into `Scenario` contracts. No LLM connection or planning inference is executed in the PLAN stage.

### Phase 6 — Weeks 10-11 — EXECUTE + PRISM
* **Status:** `WORKS`
* **Raw Evidence & Code References:**
  - **Works:** [cherenkov/execution/prism_mock.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/execution/prism_mock.py) successfully spins stoplight/prism in dynamic mode inside Docker containers. [cherenkov/execution/playwright_invoke.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/execution/playwright_invoke.py) executes pure `npx playwright test`. [cherenkov/execution/trace_reader.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/execution/trace_reader.py) successfully programmatically parses `trace.zip` binary outputs to retrieve HTTP request/response payloads.

### Phase 7 — Weeks 12-13 — REVIEW Gates
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** [cherenkov/stages/review.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/stages/review.py) executes cheap-first static gates: Syntax (markdown strip), Structure (imports verification), AST-validate (zero axios/fetch bleed), TSC compile (`tsc --noEmit`), and Prism dynamic mock server dry-run. Threshold verdicts (Auto-Approve / HITL / Regenerate) are strictly enforced.
  - **Incomplete/Missing:** Gate 4 Novelty (using `nomic-embed-text` embeddings to block redundant duplicates) and Gate 6 Quality (LLM review) are entirely missing. The HITL queue is not stored in SQLite (only returned as a Pydantic enum verdict).

### Phase 8 — Weeks 14-15 — HEALING (2 types, suggest-only)
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** [cherenkov/healing/diagnose.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/healing/diagnose.py) reads/writes passing snapshots under `.cherenkov/snapshots/`, classifies failure classes (`AUTH_EXPIRY`, `CONTRACT_DRIFT`), and prints suggestions without auto-committing code alterations. Isolated sandbox healer is supported.
  - **Incomplete/Missing:** The plan states: *"Test-content hash detects a modified test -> stale snapshot flagged, not auto-diffed."* There is no hashing or stale snapshot validation logic implemented.

### Phase 9 — Week 16 — VALIDATE Command
* **Status:** `STRUCTURAL DIFFERENCE / WORKS`
* **Raw Evidence & Code References:**
  - **Works:** `cherenkov validate --target <url>` successfully runs generated spec suites against a real server target, extracts trace files, and dynamically prints value assertion tightening suggestions (suggest-only).
  - **Structural Difference:** Consolidated directly inside [cherenkov/execution/validate.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/execution/validate.py) instead of separating into `validate/real_server.py` and `validate/value_tightening.py`.

### Phase 10 — Week 17 — EJECT + Harden
* **Status:** `STRUCTURAL DIFFERENCE / WORKS`
* **Raw Evidence & Code References:**
  - **Works:** Ejects a standalone, zero-dependency Playwright TypeScript suite containing a clean `client.ts`, standard `playwright.config.ts`, `package.json`, and `tsconfig.json`. (Verified eject runs green in isolated environments).
  - **Structural Difference:** Implemented in [cherenkov/execution/eject.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/cherenkov/execution/eject.py) instead of `eject/exporter.py` to keep internal module boundaries cohesive.

### Phase 11 — Weeks 18-19 — Dashboard (defer-first)
* **Status:** `WORKS / DEFERRED`
* **Raw Evidence & Code References:**
  - **Works:** React Dashboard E2E components (review screen, healing screen, WS integration) exist inside [track-b-c-deferred/dashboard](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/track-b-c-deferred/dashboard) and [track-b-c-deferred/cherenkov/api/main.py](file:///wsl.localhost/Ubuntu-24.04/home/moaid/cherenkov-qa/track-b-c-deferred/cherenkov/api/main.py). They are cleanly quarantined off the active Track A runtime surface.

### Phase 12 — Weeks 20-22 — Polish, Docs, Ship
* **Status:** `PARTIAL`
* **Raw Evidence & Code References:**
  - **Works:** Getting started instructions exist under `docs/GETTING_STARTED.md` and CLI documentation drift checkers are validated in CI.
  - **Incomplete/Missing:** The 5-partner QA demo signoff gate has not been reached.
