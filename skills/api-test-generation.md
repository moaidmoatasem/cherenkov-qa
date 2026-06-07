---
scope: API Test Generation
invariants: [D7, Spec-derived, Anti-lock-in]
related_contracts: [Track A]
---

# API Test Generation Skill

## Purpose
Generate Playwright API tests from an OpenAPI spec using a local LLM. The pipeline is INGEST → PLAN → GENERATE → REVIEW. Each stage is deterministic or LLM-guided per design.

## When to Use
- You have an OpenAPI 3.x spec (JSON or YAML).
- You want typed Playwright API tests with zero lock-in.
- You need to catch spec-vs-server conformance drift (e.g., 422 vs 400).

## Workflow

### 1. INGEST (`cherenkov/stages/ingest.py`)
- Reads the OpenAPI spec file
- Performs depth-1 reference resolution on component schemas
- Generates a mutation menu per endpoint: happy_path, validation errors, edge cases, auth, security (DAST opt-in)
- Output: `EndpointSlice[]` with mutations + expected status codes derived FROM the spec

### 2. PLAN (`cherenkov/stages/plan.py`)
- Deterministic mapping (NO LLM involved)
- Prioritizes scenarios: P1 = happy_path + auth, P2 = validation + security
- Output: `Scenario[]` ready for generation

### 3. GENERATE (`cherenkov/stages/generate.py`)
- Invokes `qwen2.5-coder:7b` via Ollama (or configured LLM provider)
- Uses recency-anchored prompt: instruction rules placed at the absolute end
- Uses static system prompt from `prompts/generator_system.txt` (prefix-cache optimized)
- Enforces `openapi-fetch` client usage (no fetch/axios)
- Output: TypeScript test code per scenario

### 4. REVIEW (`cherenkov/stages/review.py`)
- Enforces 6 quality gates:
  1. **Syntax** — TS well-formed, no markdown fences
  2. **Structure** — correct imports (`@playwright/test`, `openapi-fetch` client)
  3. **AST** — only direct `openapi-fetch` client calls (no `fetch`/`axios`)
  4. **Assertions** — `expect()` statements present and meaningful
  5. **tsc --noEmit** — compiles without errors
  6. **Prism dry-run** — runs against Prism mock, checks expected status codes
- Produces a verdict: `auto_approve` (>0.9), `hitl` (0.7-0.9), `regenerate` (<0.7)
- Dry-run failure triggers D2 loop back to PLAN (circuit-break at 2 fails)

## D7 Invariant
The REVIEW stage **never auto-edits test code**. Recommendations are suggest-only. Test files are only written by explicit user action or the initial `generate` command.

## References
- `cherenkov/stages/ingest.py` — spec parsing + slicing
- `cherenkov/stages/plan.py` — deterministic scenario planning
- `cherenkov/stages/generate.py` — LLM test generation
- `cherenkov/stages/review.py` — 6-gate quality review
- `cherenkov/execution/prism_mock.py` — Prism mock server for dry-run
- `cherenkov/ai/ollama_client.py` — Ollama LLM client with retry ladder
- `prompts/generator_system.txt` — tuned system prompt
- `smoke_test_generate_live.py` — opt-in live LLM smoke test
