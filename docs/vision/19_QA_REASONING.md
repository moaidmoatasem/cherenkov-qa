# Vision 19 — QA Reasoning Engine

> Companion to [ADR-007](../adr/ADR-007-qa-reasoning-engine.md).
> Status: foundation built (domain + ports + heuristic adapter + bridge),
> LLM adapter and artifact executors land in follow-up phases.

---

## 1. The problem in one sentence

CHERENKOV can *generate and run* tests mechanically, but it cannot yet
*think like a QA engineer*: it does not analyze an artifact's intent,
review it for gaps, weigh risk, choose a strategy appropriate to the
moment, or design test cases with a rationale.

## 2. The shape of the solution

One entry point, many workflows. The engine receives an **artifact**
and a **context**, then *selects* the right QA workflow variant:

```
            ┌─────────────────────────────────────────────┐
 artifact ─▶│  classify ─▶ QAContext ─▶ WorkflowStrategy  │
 (spec/PRD/ │                 │                │          │
  figma/    │                 ▼                ▼          │
  code/app) │   ┌──────────────────────────────────────┐  │
            │   │ WorkflowVariant (selected activities) │  │
            │   │ analyze → review → risk → plan →      │  │
            │   │ design_cases → [execute] → report     │  │
            │   └──────────────────────────────────────┘  │
            │                 │                           │
            │                 ▼                           │
            │   QAPlan (findings, risks, cases, charters) │
            │                 │                           │
            │                 ▼ (openapi only, today)     │
            │   Scenario[] ─▶ existing GENERATE→REVIEW→run│
            └─────────────────────────────────────────────┘
```

## 3. The variation matrix

The owner's requirement: *"keep the variations based on the testing
stage, context, product/feature/artifact maturity."* The strategy is a
pure-domain rule table — deterministic, unit-tested, no LLM involved in
*selecting* the workflow (the LLM reasons *within* activities).

### 3.1 By maturity

| Maturity | Emphasis | Execute? | Depth |
|----------|----------|:--:|-------|
| `concept` | Critique the artifact: gaps, contradictions, untestable requirements | ✗ | deep review, shallow case design |
| `in_development` | Risk assessment + smoke-level case design | mock only | medium |
| `stabilizing` | Full case design, functional execution | ✓ | medium-deep |
| `production` | Regression breadth, conformance drift, release evidence | ✓ | exhaustive at `release_gate` |

### 3.2 By testing stage

| Stage | Activities |
|-------|-----------|
| `static_review` | analyze → review → report (never executes) |
| `exploratory` | analyze → risk_assess → charters → execute (session-based) |
| `functional` | analyze → review → risk_assess → plan → design_cases → execute → report |
| `regression` | risk_assess → plan → design_cases (breadth-first) → execute → report |
| `release_gate` | full chain, exhaustive depth, evidence-grade report |

### 3.3 By artifact kind

| Kind | Analyzer | Oracle / executor | Today |
|------|----------|-------------------|-------|
| `openapi_spec` | spec slicer (reuses INGEST) + heuristic/LLM analysis | conformance pipeline (Track A) | **executable end-to-end** |
| `requirements_doc` | requirement extraction, ambiguity detection | — (plan/critique output) | reviewed plan |
| `figma_design` | screen/flow inventory | VLM visual oracle (vision 17) | reviewed plan; executor follow-up |
| `codebase` | route/test-gap inventory | unit/E2E runners | reviewed plan; executor follow-up |
| `live_app` | endpoint/UI probe | autonomous explorer (`divergence/explorer.py`) | charters; executor follow-up |

Composite inputs are explicit: a PRD **plus** a live target URL makes
`execute` legal for the derived cases; a PRD alone never executes.

## 4. Traceability — the non-negotiable

Every designed test case carries:

- `requirement_ref` — which extracted requirement it covers
- `risk_refs` — which risk register entries it mitigates
- `rationale` — one sentence: why this case exists
- `priority` — derived from risk score (likelihood × impact), not
  from a hardcoded case-type rule

A `QAPlan` with cases that cannot be traced back to a requirement or
risk fails its own contract validation.

## 5. Invariants preserved

- **D7**: the engine emits plans/findings/designs. It never edits test
  files. Execution stays report-only.
- **Spec-derived**: `to_scenarios()` only selects from spec-derived
  mutation menus and expected statuses. The reasoner can *prioritize*
  and *drop*; it can never *invent* an expected status.
- **Local-first**: HeuristicReasoner makes every workflow runnable at
  L0. LLM adapters are an upgrade, not a dependency.

## 6. Module layout

```
cherenkov/reasoning/
├── domain/
│   ├── models.py       # Artifact, QAContext, QAPlan, findings, risks, cases
│   ├── classifier.py   # artifact kind + maturity inference (pure)
│   └── strategy.py     # QAContext → WorkflowVariant (pure rule table)
├── ports/
│   └── reasoner.py     # ReasoningBackend Protocol
├── adapters/
│   └── heuristic.py    # deterministic L0 reasoner (no I/O)
└── use_cases/
    └── run_workflow.py # orchestrates activities → QAPlan → Scenario bridge
```

## 7. Roadmap

| Step | Deliverable | Status |
|------|------------|--------|
| 1 | Domain + strategy + heuristic adapter + scenario bridge + unit tests | ✅ this branch |
| 2 | `OllamaReasoner` adapter (complete_json, fallback to heuristic) | next |
| 3 | CLI: `cherenkov reason --artifact <path|url> --stage <s> --maturity <m>` | next |
| 4 | Figma artifact → VLM visual oracle execution | follow-up |
| 5 | Live-app charters → autonomous explorer execution | follow-up |
| 6 | Dashboard: QA plan + risk register screen | follow-up |
