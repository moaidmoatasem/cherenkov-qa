# Spec — CHERENKOV MCP Verification Server

> **Status:** DRAFT (design-ready, build-gated on G0). Owner: TBD.
> **Why:** the highest-leverage interoperability bet — make CHERENKOV the *verify* step every coding agent reaches for before claiming "done." See [../NORTH_STAR.md](../NORTH_STAR.md) §6, [../ROADMAP_AQE.md](../ROADMAP_AQE.md) E2.1.
> **Date:** 2026-06-16

## 1. Goal
Expose CHERENKOV's verification engine as a Model Context Protocol (MCP) server so any agent (Claude, Cursor, an OSS test-gen agent, a CI bot) can call it to:
1. **verify a test suite** an agent just generated (catch weakened/hallucinated/deleted checks), and
2. **verify a running system** against its sources of truth (conformance/drift).

The server is the machine-facing twin of the `cherenkov verify` CLI. **Local-first:** runs on the user's machine over stdio by default; nothing leaves the host unless the user opts into a remote transport.

## 2. Non-goals
- Not a generator. It never writes tests; it judges them. (Healing stays *suggest-only*.)
- Not a model. It is model-agnostic and never favors a vendor.
- No telemetry exfiltration. No cloud dependency for core verify.

## 3. Transport & deployment
- **Default:** stdio MCP server, launched by the agent host (e.g. `cherenkov mcp`).
- **Optional:** streamable-HTTP for team/CI use, behind local auth.
- Stateless per call where possible; optional workspace handle for incremental runs.

## 4. Tools exposed (MCP `tools`)

### 4.1 `verify_suite`
Judge an existing/just-generated test suite for integrity and meaningfulness.
- **Input:** `{ suite_path | suite_inline, language, target_ref?, baseline_ref?, spec_source? }`
- **Checks (the 6 gates + integrity):** assertion-meaningfulness (does each test actually constrain behavior?), assertion-weakening vs baseline, deleted/skipped check detection, hallucinated-oracle detection (asserts against nonexistent fields/endpoints), coverage-vs-claim, flake/non-determinism smell.
- **Output:** `VerificationReport` (see §5).

### 4.2 `verify_system`
Conformance/drift of a running system against its sources of truth.
- **Input:** `{ base_url | adapter_config, spec_source (openapi|asyncapi|postman|graphql|grpc|traffic), depth }`
- **Output:** `VerificationReport` with divergences (spec-vs-reality), each with a reproduction.

### 4.3 `explain_finding`
- **Input:** `{ finding_id }` → human + machine rationale, minimal repro, suggested (not applied) fix.

### 4.4 `issue_certificate` (Phase 3 hook)
- **Input:** `{ report_id, signer_ref }` → a signed CHERENKOV Certificate (see [CHERENKOV_CERTIFICATE.md](CHERENKOV_CERTIFICATE.md)). Disabled until Phase 3.

## 5. `VerificationReport` schema (shared with CLI)
```json
{
  "report_id": "string",
  "schema_version": "1.0",
  "target": { "kind": "suite|system", "ref": "string", "hash": "sha256" },
  "verdict": "pass|fail|warn",
  "integrity": {
    "weakened_assertions": [ { "test": "", "before": "", "after": "", "evidence": "" } ],
    "deleted_checks": [ { "test": "", "evidence": "" } ],
    "hallucinated_oracles": [ { "test": "", "missing_target": "" } ]
  },
  "findings": [
    { "id": "", "severity": "high|med|low", "category": "",
      "title": "", "evidence": "", "reproduction": "", "suggested_fix": "" }
  ],
  "coverage": { "claimed": 0.0, "verified": 0.0 },
  "meta": { "engine_version": "", "model_used": "string|none", "duration_ms": 0, "local_only": true }
}
```
Stable, versioned, JSON-schema-published so other tools can consume it.

## 6. Resources & prompts (MCP)
- **Resource** `cherenkov://report/{id}` — fetch a prior report.
- **Resource** `cherenkov://gates` — machine-readable description of the gates (so agents self-correct).
- **Prompt** `verify-before-done` — a ready prompt instructing an agent to call `verify_suite` and not report success until `verdict != fail`.

## 7. The integrity contract (the moat, enforced here)
- The server's verdict is **independent** of the agent that produced the suite — it re-derives oracles from the spec/system, not from the suite's own claims.
- Gates are **declarative and signed**; an agent cannot pass arguments that weaken them. Any attempt to disable a gate is recorded in the report.
- `verify_suite` always diffs against a baseline when available, so silent assertion-weakening is caught structurally, not heuristically.

## 8. Security
- Default local stdio; no network egress for core verify.
- Remote/HTTP mode requires explicit token; redact secrets from reports.
- Reports are reproducible: same inputs + engine version → same `report_id` payload hash.

## 9. Open questions
- Incremental verify (workspace handle) vs stateless per call — perf vs simplicity.
- How much of the gate set runs without an LLM (deterministic core) vs LLM-assisted — keep a deterministic floor so verdicts don't depend on a model.
- Packaging: ship inside the main CLI (`cherenkov mcp`) vs a thin separate dist.

## 10. Acceptance (for the build, post-G0)
1. An OSS agent generates a suite, calls `verify_suite`, and the report flags an injected weakened assertion.
2. `verify_system` reproduces a real divergence on a third-party API.
3. Same inputs → identical report hash (determinism floor).
4. Runs fully offline by default.
