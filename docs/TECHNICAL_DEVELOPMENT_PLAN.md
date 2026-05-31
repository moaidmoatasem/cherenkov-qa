# CHERENKOV Technical Development Plan

This document serves as the Single Source of Truth (SSOT) tracking the technical development phases, verification done-criteria, and milestones of the CHERENKOV validation engine.

---

## Phase 1: Generator Hardening (Week 0)
Satisfied during the Week 0 Validation Scaffold, where prompt styling, context limitations, and models were hardened.

- [x] **Prompt Optimization**: Enforced named imports and strict destructuring.
- [x] **Depth-Limited Slicing (V1 Check)**: Capped resolved schema depth at 1 to shrink context payload size by 100x (from 1MB to 10KB).
- [x] **RadixAttention Prefix Cache (Delta V1)**: Combined static rules at the start of raw text prompts for high-performance prefix cache hits (~3.5s generation).
- [x] **Semantic weight bias override**: Leveraged recency anchoring to neutralize pre-trained weights bias.

---

## Phase 2: Core Orchestration Skeleton & Stubbed Stages (Week 1)
Establishes the skeletal E2E pipeline, typed exception structures, retry ladders, and CLI progress monitors.

- [x] **Clean Repository Architecture**: Initialized clean `.gitignore` and step-by-step git commit discipline inside WSL Ubuntu.
- [x] **Legacy Repository Audit**: Cloned the legacy source separately and compiled `docs/MIGRATION_INVENTORY.md` to enforce tripwire imports.
- [x] **Pydantic Boundary Contracts**: Created robust, versioned stage payload validation interfaces.
- [x] **Typed Error Framework**: Added clean custom exceptions and structured JSONL logging.
- [x] **Retry Ladder & Circuit Breaker**: Added a stateful circuit breaker and stage-level retry ladders (3 attempts before falling back).
- [x] **Skeletal E2E Orchestrator**: Wired the mock INGEST → PLAN → GENERATE → REVIEW DAG, CLI execution status, and logged JSONL blocks.
- [x] **E2E Failure Safety Verification**: Proved that deliberately feeding malformed stage outputs successfully triggers the retry ladder, logs warnings, gracefully executes fallback data, and aborts the pipeline cleanly without crashing.
