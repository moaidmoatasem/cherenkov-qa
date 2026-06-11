# Concepts

> **Navigation:** [Home](Home.md) · [Pipeline](Pipeline.md) · [Architecture](Architecture.md) · [CLI Reference](CLI-Reference.md) · [Configuration](Configuration.md) · **Concepts** · [FAQ](FAQ.md) · [Troubleshooting](Troubleshooting.md)

Core ideas behind CHERENKOV — what the terms mean and why the design is the way it is.

---

## Spec-Derived Oracle

Most test frameworks require you to hardcode expected values:

```typescript
// conventional: you decided 201, you wrote 201
expect(response.status()).toBe(201);
```

CHERENKOV derives expected values from your OpenAPI spec at runtime:

```typescript
// CHERENKOV-generated: 201 comes from the spec, not from someone's assumption
// spec: POST /pets → 201 Created
expect(response.status()).toBe(201);  // ← generated from openapi.paths['/pets'].post.responses
```

When the spec says `POST /users` returns `422` on a validation error and your server returns `400`, CHERENKOV flags it as a **conformance drift** — not because someone manually wrote the assertion, but because the spec is the source of truth.

The oracle is re-derived every run. If you update your spec, the expected values update automatically.

---

## The Pipeline

CHERENKOV runs a 5-stage pipeline for every validation:

```
Ingest → Plan → Generate → Review → Run
```

| Stage | Input | Output |
|-------|-------|--------|
| **Ingest** | OpenAPI 3.x YAML/JSON | Validated truth model |
| **Plan** | Truth model | Test scenarios (happy path, edge cases, auth, error branches) |
| **Generate** | Scenarios + local LLM | Typed Playwright `.spec.ts` files |
| **Review** | Generated tests | Reviewed tests (6 gates, see below) |
| **Run** | Reviewed tests + live server | Verdicts, findings, suggestions |

See [Pipeline](Pipeline.md) for the full deep-dive.

---

## The 6-Gate Review

Every generated test passes six gates before it can run. If a test fails any gate, it is discarded and regenerated — never run against your server.

| Gate | What It Checks |
|------|---------------|
| **1 Syntax** | Valid JavaScript/TypeScript — parses without error |
| **2 Structure** | Has `import`, `test()` block, `expect()` assertions — not just a stub |
| **3 AST** | Abstract syntax tree inspection — no forbidden patterns, correct imports |
| **4 Assertions** | At least one spec-derived assertion present — not vacuously true |
| **5 TypeScript** | Compiles with `tsc --noEmit` — type-safe API client calls |
| **6 Prism** | Runs against a local Prism mock server — passes before hitting your real server |

Gate 6 is particularly important: a test that fails against a Prism mock (which implements the spec exactly) is a bad test, not a bug in your server. It gets discarded before causing a false positive.

---

## Eject — The Zero Lock-In Guarantee

`cherenkov eject` exports all generated tests as a standalone Playwright project:

```bash
./bin/cherenkov eject --output ./my-tests
```

What you get:

```
my-tests/
├── package.json         # dependencies: @playwright/test, openapi-fetch — nothing else
├── playwright.config.ts
└── tests/
    ├── pets.spec.ts     # zero CHERENKOV imports
    ├── users.spec.ts    # zero CHERENKOV imports
    └── auth.spec.ts     # zero CHERENKOV imports
```

The ejected tests are standard Playwright. `npm install && npx playwright test` — that's it. CHERENKOV does not need to be on the PATH, installed, or even exist.

This invariant is enforced in CI by `smoke_test_eject.py`, which verifies that no ejected test file imports from `cherenkov`. That check never gets disabled.

---

## Suggest-Only Healing (Invariant D7)

When tests fail, CHERENKOV analyses the failure and produces a **suggestion** — never an auto-edit:

```
Tightening suggestions for happy_path:
  › assert response.headers['content-type'] includes 'application/json'
  › assert response.body.id is typeof 'number'
```

CHERENKOV never modifies your test files. Your working tree stays clean after every run. This is design invariant D7, enforced by `smoke_test_healing.py` in CI:

```
smoke_test_healing: verifies git status is clean after cherenkov heal runs
```

The reason: auto-edited test code creates hidden coupling between the tool and your codebase. Suggestions let you decide what to accept, reject, or adapt.

---

## Truth Model

The **truth model** is CHERENKOV's internal representation of what your API should do. It is built from:

- **OpenAPI spec** — the primary source: endpoints, parameters, request/response schemas, status codes, auth schemes
- **Traffic traces** — optional: real request/response pairs captured from your server
- **Database schema** — optional: inferred constraints from your data model

The truth model is immutable during a run. It cannot be modified by test results — a failing test never changes what the spec says.

---

## Knowledge Mesh

The knowledge mesh is a [GraphRAG](https://arxiv.org/abs/2404.16130)-powered memory that learns from your codebase over time. It stores:

- Test run history and verdicts
- Spec evolution (which endpoints changed, when)
- Healing suggestions accepted/rejected
- Team knowledge annotations

The mesh powers the chat agent and the divergence engine (which generates adversarial test scenarios by comparing spec versions). It runs entirely locally via a SQLite backend (upgradeable to Redis).

---

## LLM Tier Routing

CHERENKOV uses a local LLM for test generation and defaults to the safest tier:

| Tier | Provider | Use Case |
|------|---------|---------|
| **Local** (default) | Ollama + `qwen2.5-coder:7b` | All generation — your spec stays on your machine |
| **LocalAI** | LocalAI server | Docker-based alternative, compatible with OpenAI API |
| **Cloud** | OpenAI, Anthropic | Opt-in only — requires explicit `CHERENKOV_LLM_PROVIDER=openai` |

The router is a strategy pattern: you switch providers by setting an env var, not by changing code. The LLM is only used for generation (Stage 3) — all oracle logic is deterministic and spec-derived.

---

## VLM Visual Oracle

The **Visual Language Model (VLM) oracle** is used for web and mobile visual testing. It:

1. Takes a screenshot of the page/screen under test
2. Compares it to a reference image or to the spec-described expected state
3. Returns a verdict: `pass`, `drift`, or `fail` with a natural-language explanation

The VLM oracle is used for visual regression, not functional conformance — it catches layout breaks, missing elements, and rendering errors that functional tests can't see.

VLM is provided by LocalAI (default) or Ollama (with a multimodal model like `llava`).

---

## ConformanceCheck CRD (Kubernetes)

In a Kubernetes cluster, CHERENKOV can run as a native operator. The `ConformanceCheck` CRD triggers a test run:

```yaml
apiVersion: qa.cherenkov.io/v1alpha1
kind: ConformanceCheck
metadata:
  name: my-api-check
spec:
  target: http://my-api-service:8080
  spec: configmap/my-api-spec
  schedule: "0 * * * *"   # every hour
```

The operator reconciles the CRD, spins up a Job to run CHERENKOV, and writes results back to the CR status. This is Phase 8 — currently in progress.

---

## Design Invariants

These cannot be changed without an Architecture Decision Record:

| ID | Invariant | Enforced By |
|----|-----------|------------|
| **D7** | CHERENKOV never auto-edits test code | `smoke_test_healing.py` in CI |
| **D8** | Ejected tests have zero CHERENKOV imports | `smoke_test_eject.py` in CI |
| **D9** | Oracle derives expected status from spec, not hardcoded | Code review + ADR-003 |
| **D10** | LLM is used for generation only; oracle is deterministic | ADR-006 |
