# ADR-010: Benchmark command and eval quality gate

**Status:** Accepted  
**Date:** 2026-06-18

## Context

The practitioner's brief (docs/QA_AUTOMATION_AI_STRATEGY.md) identifies the core
trust gap between a demo and a production tool: quality must be *measured*, not
asserted. Yuan et al. (FSE 2024) found raw LLM-generated tests compiled at only
39% and passed execution at 22.3%. Diffblue's commercial moat is a
compile-and-run guarantee backed by a reinforcement-learning validation loop.

Cherenkov's 6-gate REVIEW stage is the equivalent mechanism, but without a
benchmark command there is no reproducible way to measure what rate it achieves
or to detect regressions as the codebase evolves.

## Decision

### 1. `cherenkov bench` command (`cherenkov/bench/`)

A new CLI subcommand that runs the REVIEW stage against a corpus of `.spec.ts`
files and reports per-gate pass rates, average quality score, and verdict
distribution. The command:

- Defaults to the bundled **golden test fixtures** (`bench/fixtures/golden_tests/`)
- Accepts additional directories via `--dir`
- Fails with exit code 1 when thresholds are not met (compile ≥ 90%, quality ≥ 85%)
- Writes a machine-readable JSON report via `--output`
- Requires no external services for the static gates (1–4); tsc (Gate 5) and
  Prism (Gate 6) are skipped and reported as N/A when unavailable

The thresholds (compile ≥ 90%, quality ≥ 85%) come directly from Yuan et al.'s
ChatTester result (73.3% compile, 41.0% pass after repair loop vs 39%/22.3%
raw) and are the published bar that separates "AI slop" from a trusted tool.
They are configurable via `--threshold-compile` and `--threshold-quality`.

### 2. Golden test fixtures (`bench/fixtures/`)

Three hand-crafted Playwright `.spec.ts` files for the canonical Petstore API:

| Fixture | Gate 4 (assertion) | Expected verdict |
|---|---|---|
| `correct_petstore.spec.ts` | PASS | AUTO_APPROVE / HITL |
| `weakened_assertion_petstore.spec.ts` | FAIL | HITL / REGENERATE |
| `deleted_check_petstore.spec.ts` | FAIL | HITL / REGENERATE |

These fixtures are independent of the project's own stub spec so the benchmark
remains valid even if the stub spec changes.

### 3. CI eval gate (`tests/evals/test_review_integrity.py`)

Offline pytest tests (no LLM, no Docker, no network) that assert REVIEW stage
*correctness* — the gate classifies each fixture category as expected. Added to
the `tests/` tree so it runs on every PR via existing pytest discovery.

The tests cover both the `demos/catch-the-ai-cheating/fixtures/` (the E0.2
evidence) and the new golden bench fixtures.

### 4. Optional DeepEval dependency

`pip install cherenkov[bench]` installs DeepEval for LLM-as-judge metrics
(FAITHFULNESS, HALLUCINATION, ASSERTION_QUALITY, SPEC_ALIGNMENT, COMPLETENESS)
on top of the static gate metrics. DeepEval is not required for the base bench
or CI gate — it is opt-in so the tool stays offline-capable by default.

## Alternatives considered

**Run `cherenkov bench` against generated tests (full pipeline)**  
Requires Ollama running locally. The practitioner's guide calls for benchmarking
generation quality, which ultimately requires LLM access. This is the right
long-term direction but is gated on `--generate` (not yet implemented) to keep
the initial bench offline-capable.

**Use DeepEval as the primary eval framework**  
DeepEval is the right addition for LLM-based metrics; however, making it
mandatory would break offline/airgapped deployments. Optional dependency is the
correct pattern.

**Ship benchmark numbers in the README now**  
Cannot publish numbers until the bench command runs against a representative
corpus with a real LLM. The README will be updated once `cherenkov bench --generate`
is implemented and numbers are collected.

## Consequences

- `cherenkov bench` is a new CLI subcommand visible in `cherenkov --help`
- `tests/evals/test_review_integrity.py` runs in CI via pytest discovery
- `bench/fixtures/` is a new top-level directory alongside `stub/` and `demos/`
- `pyproject.toml` gains `bench` and `dev` optional dependency groups
- **Next step:** implement `cherenkov bench --generate` (Ollama-backed full
  pipeline mode) and publish compile/pass/mutation/flakiness numbers in README
