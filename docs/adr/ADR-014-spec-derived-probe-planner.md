# ADR-014: Spec-Derived Probe Planner (offline hypothesis synthesis)

**Date:** 2026-07-07
**Status:** Proposed
**Phase:** AQE Gate G0 / E0.3 (blocks the human validation gate)
**Deciders:** Core maintainer (moaid); anyone owning `cherenkov/divergence/`

## Context

`cherenkov verify` promises a truthful answer to "does this live API match its spec?" for **any** OpenAPI spec the user points it at. Today it does not deliver that for arbitrary APIs, and the gap sits directly on the critical path.

What the code actually does now (verified 2026-07-07):

- `run_proof()` chooses probes with:
  `probes = PROOF_RUN_PROBES if spec is PETSTORE_SPEC_SUBSET else _derive_probes_from_spec(spec)` — [proof_run.py:336](../../cherenkov/divergence/proof_run.py).
- `_derive_probes_from_spec()` ([proof_run.py:286](../../cherenkov/divergence/proof_run.py)) already walks an arbitrary spec and returns up to 5 `(path, method, operation, context)` tuples. So **endpoint selection for arbitrary specs is solved.**
- The two probe→hypothesis paths diverge:
  - **LLM path** (`use_llm=True`): the `SkepticAgent` synthesises hypotheses from the operation fragment — works for arbitrary specs, but is non-deterministic, costs tokens, and needs a model/provider.
  - **Offline path** (`use_llm=False`): `_offline_hypotheses(endpoint, method)` ([proof_run.py:375](../../cherenkov/divergence/proof_run.py)) only returns hypotheses when the endpoint literally matches Petstore paths (`/pet/findByStatus`, etc.). For any other spec it returns an **empty list** → zero probes → a green verdict that means "we didn't test anything," not "the API conforms."

This is the real remaining defect behind HANDOVER's P0 "R1 — Spec-derived probe planner." The honest framing: **offline `verify` against a non-Petstore API silently no-ops.** That is a *false-negative machine*, which is the one failure mode a trust/integrity tool cannot ship with. It also blocks **E0.3** (three practitioners complete the quickstart unaided) — practitioners point `verify` at their own API and, in demo/offline mode, get a meaningless PASS.

Constraints shaping the decision:
- **Determinism required.** The offline path exists precisely so CI and first-run/demo mode work with no model, no network to a provider, and reproducible output. Whatever we build must be deterministic.
- **Differentiation (E0.4).** Our wedge vs Schemathesis is *integrity / reality checking*, not input fuzzing. A solution that reduces us to "a Schemathesis wrapper" erodes the positioning in `docs/NORTH_STAR.md §8`.
- **Reuse over rebuild.** `coverage.py:_extract_endpoints()` ([coverage.py:47](../../cherenkov/divergence/coverage.py)) already walks paths/methods/operationIds; the hypothesis contract (`DivergenceHypothesis`, `DivergenceClass.D1_SPEC_CODE`) is stable ([contracts.py:294](../../cherenkov/core/contracts.py)).
- **Surface freeze in effect** — this is a bug-class fix inside `cherenkov/divergence/`, which is allowed; no new surfaces.

## Decision

Build a **deterministic Spec-Derived Probe Planner** that turns OpenAPI *constraints* into falsifiable `DivergenceHypothesis` objects, and make it the offline path's hypothesis source (replacing the Petstore-only `_offline_hypotheses`). The LLM `SkepticAgent` becomes an *enrichment* layer on top of the same planner, not a separate code path.

The planner emits one hypothesis per **checkable spec constraint** on each selected endpoint. v1 constraint rules (all `D1_SPEC_CODE` unless noted):

1. **Enum bypass** — for each `enum` param/property: predict the API accepts an off-enum value and returns 2xx instead of 400.
2. **Required-field omission** — for each `required` request field: predict the API returns 2xx when it is omitted.
3. **Documented-error reachability** — for each documented 4xx (e.g. 400/404/422): predict the trigger condition does *not* actually produce that status (`D5_SPEC_PROD` when the code path is absent).
4. **Response-schema drift** — for a documented 200 schema with `required` response fields: predict a field is missing/renamed in the live payload (`D2_CODE_PROD`).
5. **Type/format constraints** — `format`, `minimum`/`maximum`, `maxLength`: predict the constraint is unenforced.

Each rule is a small pure function `(endpoint, method, operation, spec) -> list[DivergenceHypothesis]` with a concrete `predicted_evidence` and `repro_steps`, so the existing `WitnessAgent.reproduce()` loop confirms or rejects it unchanged. When no constraint yields a hypothesis for an endpoint, the planner records an **explicit "no checkable constraint" note** so the verdict can say *"nothing to test here"* rather than emitting a hollow PASS.

Layering:

```
_extract_endpoints (reuse)  →  planner rules (deterministic)  →  hypotheses
                                        │
                          SkepticAgent enrichment (optional, when use_llm)
                                        │
                             Reflector.rerank (existing)  →  WitnessAgent (existing)
```

## Options Considered

### Option A: Deterministic spec-constraint rule engine (chosen)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium — a handful of pure rule functions over the spec dict |
| Cost | $0 runtime; no model/provider needed |
| Determinism | Full — same spec → same hypotheses |
| Scalability | Bounded by endpoint cap (5) × rule count; cheap |
| Team familiarity | High — mirrors existing `_offline_hypotheses` shape and `coverage.py` walker |
| Differentiation | Reinforces the integrity wedge (spec-*claim* checking, not fuzzing) |

**Pros:** deterministic, offline, free, testable rule-by-rule, reuses the Witness loop and contracts, unifies both paths.
**Cons:** rule coverage is only as good as the rules we write; won't catch semantic divergences an LLM might infer; up-front effort to author + test each rule.

### Option B: Adopt Schemathesis / Hypothesis property-based fuzzing
| Dimension | Assessment |
|-----------|------------|
| Complexity | Medium-high — new heavy dependency, output-model impedance mismatch |
| Cost | $0 runtime but adds a large dep + slower runs |
| Determinism | Configurable seed, but stateful/flaky in practice |
| Scalability | Good breadth on inputs |
| Team familiarity | Low — foreign failure model |
| Differentiation | **Negative** — collapses us into "a Schemathesis wrapper" (violates E0.4) |

**Pros:** mature input generation; broad schema coverage for free.
**Cons:** blurs the differentiation we're gated on; fuzzing finds "500 on weird input," not spec-vs-reality *claims*; mapping its findings back into `DivergenceReport`/`DivergenceClass` is real glue work. **We can still borrow Hypothesis-style value generation *inside* Option A's rules without adopting the framework's verdict model.**

### Option C: Require the LLM Skeptic always (drop the offline path)
| Dimension | Assessment |
|-----------|------------|
| Complexity | Low (delete code) |
| Cost | Tokens + provider dependency on every run |
| Determinism | **None** — breaks CI reproducibility, demo mode, air-gapped use |
| Team familiarity | High |
| Differentiation | Neutral |

**Pros:** least code; already works for arbitrary specs.
**Cons:** kills deterministic CI (`--demo`/offline first-run is an E1.5 install-friction feature), makes every `verify` cost money and need network to a model. Non-starter for a tool whose value proposition is *trustworthy, repeatable* verdicts.

### Option D: Hybrid — deterministic planner as backbone + LLM enrichment (the chosen path's stance)
This is Option A with the explicit rule that the `SkepticAgent` *adds to* the planner's hypotheses when `use_llm=True`, rather than replacing them. Captured in the Decision above; recorded here so the enrichment relationship is a deliberate choice, not an accident.

## Trade-off Analysis

The core tension is **coverage vs. differentiation + determinism.** Option B maximises raw input coverage but at the cost of the exact positioning (E0.4) and reproducibility (CI/demo) the project is gated on. Option C maximises coverage-per-line-of-code but sacrifices determinism entirely. Option A/D trades some breadth for a deterministic, free, on-brand core that we can grow rule by rule — and it strictly *unifies* the two existing paths instead of maintaining a Petstore-only fork. The LLM path stops being a parallel implementation and becomes enrichment over the same hypothesis stream, which shrinks the surface that can silently no-op.

Key risk: rule coverage. Mitigation — the planner is the *floor*, not the ceiling: each rule is independently unit-tested against a mutant fixture (mirroring `tests/unit/test_mutation_validation.py`), and LLM enrichment covers the semantic long tail when a provider is available.

## Consequences

**Easier**
- Offline `verify` against any spec produces real probes → E0.3 practitioners get honest verdicts.
- CI/demo mode gains genuine coverage with zero model dependency.
- One hypothesis source feeds both paths; `_offline_hypotheses`' Petstore special-casing is retired.
- Coverage report (`--coverage-report`) becomes meaningful for arbitrary specs, since probes now touch real endpoints.

**Harder**
- We own a growing library of constraint rules and their tests.
- Must guard against **hollow PASS**: absence of a rule match must render as "not tested," never as "conforms." This needs an explicit verdict state, not silent emptiness.

**To revisit**
- The 5-endpoint cap in `_derive_probes_from_spec` becomes the coverage bottleneck once hypotheses are real — likely raise/paginate it, or prioritise endpoints by constraint density.
- Whether `PETSTORE_SPEC_SUBSET` / `PROOF_RUN_PROBES` / `_offline_hypotheses` can be deleted entirely once rule parity with the hand-crafted Petstore hypotheses is proven.

## Action Items

1. [ ] Add `cherenkov/divergence/probe_planner.py` — `plan_probes(spec, endpoints) -> list[DivergenceHypothesis]` with the 5 v1 rules as pure functions; reuse `coverage.py:_extract_endpoints`.
2. [ ] Introduce an explicit "no checkable constraint / not tested" verdict state so empty ≠ PASS.
3. [ ] Rewire `run_proof()` offline branch to call the planner instead of `_offline_hypotheses`; make `SkepticAgent` output *extend* planner hypotheses when `use_llm=True`.
4. [ ] Unit-test each rule against conformant + mutant fixtures (extend `tests/unit/test_mutation_validation.py` pattern); prove the planner fires on a non-Petstore spec.
5. [ ] Prove rule parity with the Petstore hand-crafted hypotheses, then delete `_offline_hypotheses` (and, if clean, `PROOF_RUN_PROBES`).
6. [ ] Fix the sibling truth bug noted in HANDOVER: `OrchestrationEngine.run_pipeline()` returns success on a missing spec file — a truth tool must hard-fail on missing input. (Same "empty ≠ pass" principle; file as its own issue.)
