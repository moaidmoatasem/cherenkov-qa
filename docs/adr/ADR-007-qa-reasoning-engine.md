# ADR-007: QA Reasoning Engine — artifact-adaptive QA workflows

**Status:** Accepted
**Date:** 2026-06-11
**Deciders:** Owner + agent session (branch `claude/cherenkov-next-level-nb2uej`)

---

## Context

CHERENKOV today is an API-conformance pipeline: OpenAPI spec → INGEST →
PLAN → GENERATE → REVIEW → run. Its PLAN stage
(`cherenkov/stages/plan.py`) is **deterministic and mechanical**: every
endpoint is mapped to a fixed mutation menu and tagged P1/P2 by a
two-line rule. There is no analysis of intent, no review of the artifact
itself, no risk-based prioritization, and no notion of *which QA
activities are appropriate right now*.

The owner's direction (2026-06-11) is to take CHERENKOV to the next
level: **solid reasoning over QA activities — analysis, review,
designing plans, test cases, and execution** — over **heterogeneous
artifacts** (OpenAPI specs, PRDs/requirement docs, Figma designs,
codebases, live apps), where the workflow **varies by testing stage,
context, and product/feature/artifact maturity** rather than being one
fixed pipeline.

Constraints carried over from existing invariants:

- **D7** — never auto-edit test code. Reasoning outputs are plans,
  findings, and designs. Execution remains report-only.
- **Anti-lock-in** — generated/ejected tests stay vanilla Playwright.
- **Local-first** — reasoning must work at L0 (no Docker, no LLM)
  with a deterministic fallback, and improve with Ollama/LocalAI
  available (same fallback-chain pattern as the VLM substrate,
  ADR-003).
- **Clean Architecture** (ADR-004) — `domain/ports/adapters/use_cases`
  with a pure-Python domain.

## Decision

Introduce a **QA Reasoning Engine** as a new module
`cherenkov/reasoning/` that sits *above* the existing pipeline and
*selects + parameterizes* QA workflows instead of replacing Track A.

### 1. The QA context is an explicit, typed model

`QAContext` captures the three variation axes the owner named:

| Axis | Values | Effect |
|------|--------|--------|
| **Artifact kind** | `openapi_spec`, `requirements_doc`, `figma_design`, `codebase`, `live_app` | Which analyzers/oracles apply |
| **Maturity** | `concept`, `in_development`, `stabilizing`, `production` | Depth of review vs. breadth of execution |
| **Testing stage** | `static_review`, `exploratory`, `functional`, `regression`, `release_gate` | Which activities run and in what order |

### 2. Workflows are selected, not hardcoded

A pure-domain `WorkflowStrategy` maps `QAContext` → `WorkflowVariant`:
an ordered list of QA activities (`analyze`, `review`, `risk_assess`,
`plan`, `design_cases`, `execute`, `report`) plus depth and execution
mode. Examples of the variation rules (full matrix in
`docs/vision/19_QA_REASONING.md`):

- `concept` maturity → **no execution** (nothing runnable exists);
  deep ANALYZE + REVIEW of the artifact itself (gaps, contradictions,
  untestable requirements).
- `static_review` stage → critique-only regardless of maturity.
- `production` + `release_gate` → full chain with exhaustive depth and
  live execution.
- `exploratory` stage on a `live_app` → charter-based session design
  instead of scripted cases.
- Non-executable artifact kinds (PRD, Figma) never get `execute`
  unless paired with a runnable target.

### 3. Reasoning sits behind a port with a deterministic fallback

`ReasoningBackend` is a Protocol with four operations: `analyze`,
`review`, `assess_risks`, `design_cases`. Two adapters:

- **HeuristicReasoner** — deterministic, zero-I/O. Pattern-based
  analysis (requirement extraction, ambiguity markers, TODO/TBD
  density, missing error responses in specs). Always available; this
  is the L0/demo tier and the unit-test substrate.
- **OllamaReasoner** — wraps the existing
  `cherenkov/ai` inference client (`complete_json`), prompts derived
  from the heuristic schemas, **falls back to HeuristicReasoner on any
  failure**. Same chain shape as LocalAI → Ollama → Demo.

### 4. Outputs are typed and bridge into Track A

`QAPlan` is the engine's product: context + selected variant +
analysis + review findings + risk register + designed test cases (or
exploratory charters), every case traceable to a requirement and risk.
For `openapi_spec` artifacts, `QAPlan.to_scenarios()` converts designed
cases into core `Scenario` objects so the existing GENERATE → REVIEW →
run pipeline executes them unchanged. Other artifact kinds terminate at
a reviewed plan until their executors land (visual oracle for Figma,
explorer for live apps — both already exist as modules and get wired in
follow-up phases).

## Consequences

**Positive**
- QA activities adapt to context instead of one-size-fits-all; a
  concept-stage PRD gets a requirements critique, a production API gets
  a risk-ranked regression suite — from the same entry point.
- Risk-based prioritization replaces the P1/P2 two-liner; every test
  case carries a rationale and traceability (requirement → risk → case).
- Works at L0 with zero LLM; gets sharper with local models. No new
  mandatory dependencies.
- Track A is untouched: the engine *feeds* `PlanOutput`-compatible
  scenarios; D7 and eject invariants hold.

**Negative / risks**
- A second planning path exists alongside `stages/plan.py`; until the
  bridge is the default, the two must be kept consistent (mitigated:
  the bridge only ever *selects from* spec-derived expectations, never
  invents statuses — same rule as Delta "spec-derived").
- Heuristic reasoning is shallow by construction; its value is honesty
  at L0, not insight. LLM adapters carry the depth.

## Follow-ups

1. Wire `FigmaDesign` artifacts to the VLM visual oracle
   (`cherenkov/oracle`, vision doc 17) for executable visual cases.
2. Wire `live_app` charters to the autonomous explorer
   (`cherenkov/divergence/explorer.py`).
3. CLI surface: `cherenkov reason --artifact <path|url> [--stage <s>] [--maturity <m>]`.
4. Dashboard screen for the QA plan + risk register.
