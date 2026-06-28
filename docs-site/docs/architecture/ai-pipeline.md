---
title: AI Pipeline
description: CHERENKOV-QA AI pipeline — LLM-powered test generation, 6-gate review, divergence detection.
---

# AI Pipeline

CHERENKOV's core pipeline takes an OpenAPI spec and produces conformance-tested Playwright tests through a 5-stage LLM-powered process.

---

## Pipeline Stages

```
OpenAPI Spec
     │
     ▼
┌─────────────┐
│   INGEST    │  Parse spec, extract endpoint slices, build mutation menu
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    PLAN     │  deepseek-r1:8b selects test scenarios (never invents endpoints)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  GENERATE   │  qwen2.5-coder:7b writes typed Playwright test with openapi-fetch
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   REVIEW    │  6-gate automated review (see below)
└──────┬──────┘
       │
  ┌────┴────┐
  │         │
  ▼         ▼
WRITE    LOOP BACK
test      to Plan
```

---

## Stage 1: INGEST

- Parses OpenAPI spec (3.x YAML/JSON)
- Creates depth-1 slices per endpoint
- Generates `openapi-fetch` type stubs
- Builds mutation menu (mutation IDs from spec — never invented)

---

## Stage 2: PLAN

Model: `deepseek-r1:8b` (reasoning/planning)

- Selects mutation scenarios from the menu
- Never invents endpoint paths or methods
- Strips `<think>` reasoning tokens from output

---

## Stage 3: GENERATE

Model: `qwen2.5-coder:7b` (code generation)

- Writes a typed Playwright test using `openapi-fetch`
- Uses static system prompt (enables prefix caching)
- Produces TypeScript with strict type safety

---

## Stage 4: REVIEW (6 Gates)

Every generated test passes 6 sequential gates before being written to disk:

| Gate | Check | Fail Action |
|------|-------|-------------|
| 1 — Syntax | Valid TypeScript syntax | Loop back to Generate |
| 2 — Structure | Required test blocks present | Loop back to Generate |
| 3 — AST | No forbidden patterns | Loop back to Generate |
| 4 — Assertions | Assertions are present and meaningful | Loop back to Generate |
| 5 — `tsc --noEmit` | Passes TypeScript compiler | Loop back to Generate |
| 6 — Prism dry-run | Validates against OpenAPI spec | Loop back to Generate |

After 2 consecutive failures per case, the circuit breaks (stops retrying).

**Verdict thresholds:**
- Score `> 0.9` → auto-approve, write test
- Score `0.7–0.9` → human review (HITL queue)
- Score `< 0.7` → reject, loop back

---

## Stage 5: EXECUTE

- Runs approved tests via Playwright against the target server
- Captures HTTP responses, timing, body assertions
- Writes JUnit XML + SARIF report
- Persists `VerdictRecord` to `verdicts.db`

---

## Divergence Detection

When a test fails against the live server, CHERENKOV runs the **divergence loop**:

1. **Skeptic** forms a hypothesis about the discrepancy (spec claim vs. reality)
2. **Witness** fires a minimal real HTTP request to verify
3. If reproduced → **Scribe** records confirmed divergence with evidence
4. If not reproduced → rejected as tautology/noise

See [Diagrams — Divergence Loop](diagrams.md#divergence-loop--the-core-capability) for the sequence diagram.

---

## LLM Substrate Router

CHERENKOV routes model calls based on task type:

| Task | Default Model | Tier |
|------|--------------|------|
| Code generation | `qwen2.5-coder:7b` | Small |
| Reasoning / planning | `deepseek-r1:8b` | Deep |
| Vision / screenshot analysis | LocalAI VLM | Vision |
| Cloud fallback | OpenAI / Anthropic | Cloud |

Configure via `cherenkov.toml`:

```toml
[substrate]
default_tier = "small"
small_model = "qwen2.5-coder:7b"
deep_model = "deepseek-r1:8b"
vision_model = "localai/llava"
```
