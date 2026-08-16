# Release Notes: CHERENKOV-QA v1.4.0

**Date:** 2026-08-05
**Tag:** `v1.4.0`

## Version Evolution (v1.2 → v1.3 → v1.4)

```mermaid
flowchart TD
  subgraph V12["Version 1.2.0 (Foundation)"]
    direction TB
    A1["Core API Conformance Engine"]
    A2["Playwright Test Generation"]
    A3["SQLite Storage (verdicts.db)"]
    A4["D7 Non-Negotiable Invariants"]
    A5["CLI Baseline (run, validate, eject)"]
  end

  subgraph V13["Version 1.3.0 (Autonomous Extensions)"]
    direction TB
    B1["Second Brain (Knowledge Mesh / RAG)"]
    B2["VLM + LocalAI Backend Routing"]
    B3["Tauri 2 Desktop Host App"]
    B4["Chat Agent + Persona SSE"]
    B5["Mobile Engine (Maestro/ADB)"]
    B6["Kubernetes Operator & CRDs"]
  end

  subgraph V14["Version 1.4.0 (Consolidated Release - CURRENT)"]
    direction TB
    C1["Unified 1.4 Diátaxis Documentation Hub"]
    C2["Clean Architecture Ports & Adapters (ADR-004)"]
    C3["MemSearch Semantic Memory & SDD Protocol"]
    C4["Multi-Agent Conductor & CC-1..CC-6 Suite"]
    C5["Native CI/CD & Jenkins Shared Library"]
    C6["Spec Guardian & Portable Test Certificates"]
    C7["Continuous Conformance Trend & Coverage Maps"]
  end

  V12 ==>|"Added Background Daemons, Enterprise SAML, MCP"| V13
  V13 ==>|"Added Coverage Analytics, Regression Engine, CI Bots"| V14

  classDef v12 fill:#1e293b,stroke:#64748b,stroke-width:2px,color:#f8fafc;
  classDef v13 fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#f8fafc;
  classDef v14 fill:#0c4a6e,stroke:#38bdf8,stroke-width:2.5px,color:#f8fafc;

  class A1,A2,A3,A4,A5 v12;
  class B1,B2,B3,B4,B5,B6 v13;
  class C1,C2,C3,C4,C5,C6,C7 v14;
```

![Version Evolution Diagram](assets/version_diff.png)
*Figure: Architectural evolution across CHERENKOV-QA minor versions.*

## What's New Since v1.3.0

### Features

- **Coverage map** (Phase 14): `build_coverage_map()` in
  `cherenkov/web/coverage_map.py` computes per-endpoint conformance coverage from the
  in-process `divergences` corpus. Registered as
  `GET /api/v1/coverage/map`, returning endpoint tuples
  `(method, path, status, last_run_id, last_verdict)`.
- **Continuous conformance trend** (Phase 14): `conformance_trend()` and
  `conformance_summary()` stream verdict/divergence/coverage time-series from RunStore
  records. Registered as `GET /api/v1/coverage/conformance-trend` and
  `GET /api/v1/coverage/conformance-summary` (#767).
- **Regression detection** (Phase 14): `detect_regressions()` compares consecutive
  runs *per target_url*, flagging `verdict_downgrade` (PASS→FAIL), `coverage_regression`
  (pct drop), and `divergence_spike` (climb). Registered as
  `GET /api/v1/coverage/regressions` (#771).
- **PR-comment integration** (Phase 14): `format_coverage_comment()` + GitHub client
  post a coverage-diff comment on `opened`/`synchronize`/`reopened`/`ready_for_review`
  events. Best-effort background task; never 5xxes the webhook (#766).

### Design Notes

- **Spec-derived (D7):** verdict ranks are read from
  `cherenkov/verdict/models.py` (`OverallVerdict`: CERTIFIED/DIVERGENT/
  SUSPECT/INCONCLUSIVE), not hardcoded. Records sourced from RunStore
  (`persistence/run_store.py`); coverage map from the `divergences` corpus.
- **Eject-safe:** coverage/conformance routes read only the public `divergences` and
  `RunStore` ports — `eject` strips CHERENKOV imports without breaking the contract.
- **Suggest-only healing:** regression results are reports/suggestions; no auto-commit
  or auto-apply (D7 invariant maintained).

### Certification

- **Conformance gate green at push:** commit `4c5b4f2e` —
  `Automated Golden Path Validation Gate` ✅ and `CHERENKOV Conformance Tests` ✅ both
  `success`.
- **New unit tests:** 26 tests in `tests/unit/test_coverage_map.py` (including new
  `TestDetectRegressions` + `TestRegressionsRoute`), 26 passed in 2.66s.
- **Type check:** `mypy cherenkov/web/coverage_map.py cherenkov/web/routes/coverage_routes.py cherenkov/web/pr_comments.py cherenkov/web/routes/webhooks_github.py` clean (no errors).
- **Pre-existing failures NOT introduced by this release** (documented in
  `docs/evidence/baseline-recert-2026-08-04.md`): `supply-chain.yml` and `spec-drift.yml`
  continue to fail on `main` from `sqlite.py:235`, `airllm_client.py:87,97`, and
  `InferenceRouter` import errors — tracked separately, out of scope for Phase 14.


