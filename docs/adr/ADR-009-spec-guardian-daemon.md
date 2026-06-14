# ADR-009: Spec Guardian Daemon

**Date:** 2026-06-14  
**Status:** Accepted  

## Context

CHERENKOV QA (Track A) currently operates on a "push" model. Developers trigger it manually via the CLI or it runs sequentially as a step in a CI/CD pipeline. While this is effective for discrete validation, it does not achieve the 2027 vision of "Continuous Quality Assurance." 

The industry is moving toward fully autonomous QE loops where agents actively monitor repositories, observability telemetry, and specification drift, executing tests in the background and proposing fixes independently of human triggers. To remain at the forefront, CHERENKOV must evolve from an on-demand tool into a continuous daemon.

## Decision

We will build the **Spec Guardian Daemon** (Phase 14).

1. **Continuous Watcher Loop**: The daemon will run as a persistent background process (ideally within our Kubernetes deployment via the `ConformanceCheck` CRD Operator). It will monitor target repositories and live observability feeds (e.g., Datadog, OpenTelemetry).
2. **Autonomous Triggering**: When a change is detected (a commit modifying `openapi.yaml`, or a 5xx error spike in APM), the daemon will automatically orchestrate a targeted test generation and execution cycle.
3. **Strict Guardrails (The D7 Invariant)**: The daemon is explicitly forbidden from auto-merging code or loosening expected assertions. It may only submit PRs containing test suite updates or file detailed issue tickets containing execution traces and suggest-only healing verdicts.

## Consequences

### Positive
- **Zero-Touch QA**: Developers no longer need to remember to run tests or update suites when the spec changes; the guardian handles it continuously.
- **Shift-Right Synergies**: By tying into APM telemetry, CHERENKOV can generate new regression tests based on actual production failures, closing the loop between operations and QA.

### Negative
- **Compute Costs**: Running continuous LLM test generation in the background requires significant compute. (Mitigated by our Local-First LocalAI/Ollama architecture).
- **Concurrency Complexity**: The daemon must handle state and locks gracefully to avoid triggering duplicate parallel test generations for the same PR/commit.
