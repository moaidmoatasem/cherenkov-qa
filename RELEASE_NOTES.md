# CHERENKOV — Release Notes (v0.0.0-foundation)

We are proud to tag `foundation-v0`, the first stable release baseline of **CHERENKOV**. This release successfully anchors the **Track A** core conformance testing engine before carving the L0/L1 substrate router seam.

## 🚀 Core Capabilities

`foundation-v0` delivers a localhost-first, spec-driven API test generator and validator designed for deep spec-conformance check-ups with zero vendor lock-in.

### 1. Spec Ingestion & Slicing (`cherenkov/stages/ingest.py`)
- Programmatically ingests OpenAPI (v3.0/3.1) specifications.
- Implements depth-1 dependency slicing per endpoint to isolate test boundaries and fit compact 7B/8B local model context windows perfectly.

### 2. Planning & Generation Pipeline (`cherenkov/stages/plan.py`, `generate.py`)
- Integrates local LLM execution via Ollama (`qwen2.5-coder:7b` for code generation, `deepseek-r1:8b` for test scenario planning).
- Bulletproof JSON formatting enforcement and a robust retry ladder to heal LLM formatting errors gracefully.
- Reuses context prefixes via prefix caching for rapid, warm inference speeds (~1.8s/test).

### 3. Rigorous 6-Gate Review System (`cherenkov/stages/review.py`)
Every generated test runs through a strict local review matrix before approval:
1. **Syntax Validator**: Verifies complete AST parseability.
2. **Structure Guard**: Enforces standard Playwright structure.
3. **Assertion Guard**: Checks that assertions exist and targets correct variables.
4. **TypeScript Compiler (`tsc --noEmit`)**: Natively checks type safety.
5. **Prism Dry-run**: Fires tests against a local Prism mock server instance to confirm mock execution.
6. **Circuit Breaker**: Stops after 2 sequential replan failures to prevent infinite loops.

### 4. Suggest-Only Self-Healing Sandbox (`cherenkov/healing/`)
- Analyzes test trace records to isolate failure patterns.
- Classifies failures into `AUTH_EXPIRY` (JWT/token expiration) and `CONTRACT_DRIFT` (added or removed properties).
- Emits clear, copy-paste-ready healing suggestions (e.g. env variables, updated assertions).
- **Strict Invariant**: Enforces a suggest-only policy, never auto-modifying test code without explicit human consent.

### 5. Standalone Suite Ejection (`cherenkov/execution/eject.py`)
- Ejects generated suites to a standard directory layout.
- Natively strips all metadata, custom wrappers, and `cherenkov` imports.
- Generates standard `package.json`, `playwright.config.ts`, `tsconfig.json`, and `client.ts` (`openapi-fetch` client wrapper).
- **Invariant**: The ejected suite runs successfully natively using only standard `npx playwright test` with zero runtime dependency on the tool.

### 6. Spec-Derived Conformance Verification (`cherenkov/execution/validate.py`)
- The `validate` subcommand spins up testing against real, live target API servers.
- Compares live HTTP status responses against OpenAPI expectations to surface conformance bugs (e.g., server returning HTTP 400 when spec promises HTTP 422).

---

## 🛠️ Verification & Quality Assurance

All 5 core Track A verification smoke suites are fully automated and verified green in the target WSL2 environment:
- `smoke_test.py` (E2E Happy and malformed failure paths)
- `smoke_test_healing.py` (Trace diagnosis and suggest-only invariants)
- `smoke_test_validate.py` (Real target validation and conformance report output)
- `smoke_test_eject.py` (100% clean eject validation and green Native Playwright E2E execution)
- `smoke_test_polish.py` (CLI entry point, help commands, and documentation-drift checker)

---

## 📦 How to Revert to this Baseline

To fetch and reset your workspace to this verified foundation at any point:
```bash
git checkout tags/foundation-v0
```
