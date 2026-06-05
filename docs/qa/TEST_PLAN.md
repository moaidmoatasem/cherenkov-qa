# CHERENKOV QA — Comprehensive Test Plan

**Date:** 2026-06-05
**Status:** Draft for review
**Scope:** Track A core surface + built-ahead modules (see SCOPE_LEDGER.md)
**Gate dependency:** Track A validation gate (3/5 QA) is NOT passed — nothing is "shipped"

---

## 1. Introduction & Scope

### 1.1 What This Document Covers

| Dimension | Coverage |
|-----------|----------|
| Existing smoke tests | All 37 `smoke_test_*.py` files mapped to features |
| Unit tests | All `test_*.py` files in repo root and `tests/` |
| Business scenarios | ~75 scenarios extracted from HANDOVER.md, SCOPE_LEDGER.md, QA_DEMO_KIT.md |
| Regression gaps | Modules/branches with NO test coverage |
| QA cycles | Smoke → Integration → Regression → Acceptance → Exploratory |
| UX issues | Dashboard UI code inspection of `cherenkov/web/ui/` |
| Recommendations | Tooling, CI, test data, process improvements |

### 1.2 Not In Scope

- `track-b-c-deferred/` code (reference only — must not be tested as shipped)
- Performance benchmarking (Track B — no baseline established)
- Visual regression (Track B — re-integrated but not validated)
- Federation cross-node testing (Horizon 2 — no multi-node environment)

### 1.3 Current State Summary

| Metric | Count |
|--------|-------|
| Smoke tests (root) | 32 files |
| Smoke tests (test_*.py) | 25 files |
| Unit tests (tests/) | 5 files |
| Business scenarios documented | ~75 |
| Modules with ZERO tests | See §3.2 |
| Validation gate completions | 0/5 (no real QA evidence collected) |

---

## 2. Existing Test Coverage Matrix

### 2.1 Smoke Tests — Feature Mapping

| # | Smoke Test | Module/Package | Track | What It Proves |
|---|-----------|---------------|-------|---------------|
| 1 | `smoke_test.py` | `core/orchestrator.py` | A | Full E2E pipeline: happy path + circuit breaker recovery |
| 2 | `smoke_test_healing.py` | `healing/` | A | Contract drift + auth expiry detection |
| 3 | `smoke_test_validate.py` | `execution/validate.py` | A | Validation engine: real server conformance checks |
| 4 | `smoke_test_eject.py` | `execution/eject.py` | A | Anti-lock-in: standalone Playwright output |
| 5 | `smoke_test_polish.py` | `core/` | A | Polish/presentation layer |
| 6 | `smoke_test_hitl_cli.py` | `hitl/` | A | HITL CLI commands (list, show, approve, reject) |
| 7 | `smoke_test_hitl_race.py` | `hitl/` | A | Thread-safety under concurrent writes |
| 8 | `smoke_test_hitl_concurrency.py` | `hitl/` | A | Isolated HITL streams, no cross-corruption |
| 9 | `smoke_test_generate_live.py` | `stages/generate.py` | A | Live LLM test generation |
| 10 | `smoke_test_golden_path.py` | `core/orchestrator.py` | A | Golden path pipeline (regression) |
| 11 | `smoke_test_autonomy.py` | `copilot/` | Horizon 2 | Autonomous agent loop |
| 12 | `smoke_test_cache.py` | `ai/cache.py` | Epoch 1 | Response caching correctness |
| 13 | `smoke_test_certification.py` | `substrate/` | Epoch 1 | Provider certification |
| 14 | `smoke_test_copilot_e10.py` | `copilot/` | E10 | Copilot E10 exit demo |
| 15 | `smoke_test_e7_behavioral.py` | `reflector/` | E7 | Behavioral fingerprint suppression |
| 16 | `smoke_test_emitters_unit.py` | `truth/emitters/` | E9/E11 | Truth model emitter unit tests |
| 17 | `smoke_test_epoch5.py` | various | Epoch 5 | Epoch 5 integration |
| 18 | `smoke_test_federation_sync.py` | `federation/` | Horizon 2 | Multi-node sync |
| 19 | `smoke_test_governance.py` | `governance/` | E12 | Governance KPI panel |
| 20 | `smoke_test_mcp.py` | `mcp/` | X4 | MCP JSON-RPC server |
| 21 | `smoke_test_mentor.py` | `copilot/` | E10 | Copilot mentor role |
| 22 | `smoke_test_openclaw.py` | `openclaw/` | Horizon 2 | Chat HITL relay + healing feedback |
| 23 | `smoke_test_perf.py` | `stages/perf/` | B | Performance baseline (re-integrated) |
| 24 | `smoke_test_perf_anomaly.py` | `stages/perf/` | B | Performance anomaly detection |
| 25 | `smoke_test_perf_intelligence.py` | `stages/perf/` | B | Perf intelligence analysis |
| 26 | `smoke_test_provider.py` | `ai/` | Epoch 1 | Provider abstraction |
| 27 | `smoke_test_reflector_cli.py` | `reflector/` | E7 | Reflector CLI commands |
| 28 | `smoke_test_reflector_introspect.py` | `reflector/` | E7 | Reflector introspection |
| 29 | `smoke_test_reflector_store_concurrency.py` | `reflector/` | E7 | Concurrent store access |
| 30 | `smoke_test_reflector_suppression.py` | `reflector/` | E7 | Verdict suppression |
| 31 | `smoke_test_validate_gate.py` | `execution/validate.py` | A | Validation gate criteria |
| 32 | `smoke_test_vision_e9.py` | `stages/vision/` | E9 | Vision stage (re-integrated Track B) |
| 33 | `smoke_test_visual.py` | `stages/visual/` | B | Visual regression (re-integrated) |

### 2.2 Unit Tests (`test_*.py`) — Feature Mapping

| # | Test File | Module | What It Tests |
|---|----------|--------|-------------|
| 1 | `test_hitl_review_bridge.py` | `hitl/` | HITL review bridge |
| 2 | `test_emitters.py` | `truth/emitters/` | Emitter correctness |
| 3 | `test_egress_policy.py` | `substrate/` | Egress network policy enforcement |
| 4 | `test_validate_gate.py` | `execution/validate.py` | Validate gate logic |
| 5 | `test_sources_db_schema.py` | `truth/sources/` | Sources DB schema |
| 6 | `test_embedding_index.py` | `truth/` | Embedding index operations |
| 7 | `test_pr_diff_action.py` | `continuity/` | PR diff action |
| 8 | `test_hitl_cli.py` | `hitl/` | HITL CLI unit tests |
| 9 | `test_openclaw_t3.py` | `openclaw/` | OpenClaw protocol |
| 10 | `test_truth_model.py` | `truth/` | Truth model |
| 11 | `test_perf_enhancements.py` | `perf/` | Performance enhancements |
| 12 | `test_epoch11_coverage.py` | `coverage/` | Epoch 11 coverage loop |
| 13 | `test_e7_behavioral.py` | `reflector/` | E7 behavioral exit |
| 14 | `test_daemon_cmd.py` | `continuity/` | Daemon command |
| 15 | `test_proof_run_reflector.py` | `reflector/` | Proof-run with reflector |
| 16 | `test_sources_traffic.py` | `truth/sources/` | Traffic source ingestion |
| 17 | `test_oracle.py` | `oracle/` | Oracle engine |
| 18 | `test_inference_client.py` | `ai/` | Inference client |
| 19 | `test_federation_protocol.py` | `federation/` | Federation protocol |
| 20 | `test_certification_mentor.py` | `substrate/` | Certification + mentor |
| 21 | `test_federation_corpus.py` | `federation/` | Federation corpus sync |
| 22 | `test_map_cmd.py` | `stages/` | Map command |
| 23 | `test_source_adapter.py` | `truth/sources/` | Source adapter |
| 24 | `test_divergence_engine.py` | `divergence/` | Divergence engine |
| 25 | `test_epoch9_vision.py` | `stages/vision/` | Epoch 9 vision |

### 2.3 Tests/ Directory Unit Tests

| # | Test File | What It Tests |
|---|----------|-------------|
| 1 | `tests/test_dast_mutation.py` | DAST mutation engine |
| 2 | `tests/test_golden_snapshot.py` | Golden snapshot comparisons |
| 3 | `tests/test_hitl_auth.py` | HITL authentication |
| 4 | `tests/test_mutation_validate.py` | Mutation validation |
| 5 | `tests/test_rag_schema_index.py` | RAG schema index |

---

## 3. Regression Coverage Analysis

### 3.1 Coverage by Module

| Module | Smoke Tests | Unit Tests | Coverage Level |
|--------|------------|------------|---------------|
| `core/orchestrator.py` | `smoke_test.py`, `smoke_test_golden_path.py` | None | Functional |
| `stages/ingest.py` | None (covered by E2E only) | None | **GAP** |
| `stages/plan.py` | None (covered by E2E only) | None | **GAP** |
| `stages/generate.py` | `smoke_test_generate_live.py` | None | Partial |
| `stages/review.py` | None (covered by E2E only) | None | **GAP** |
| `execution/validate.py` | `smoke_test_validate.py`, `smoke_test_validate_gate.py` | `test_validate_gate.py` | Good |
| `execution/eject.py` | `smoke_test_eject.py` | None | Functional |
| `execution/prism_mock.py` | None | None | **GAP** |
| `execution/playwright_invoke.py` | None | None | **GAP** |
| `execution/trace_reader.py` | None | None | **GAP** |
| `healing/` | `smoke_test_healing.py` | None | Partial |
| `hitl/` | 3 smoke tests | 2 unit tests | Good |
| `reflector/` | 4 smoke tests | 2 unit tests | Good |
| `divergence/` | None | `test_divergence_engine.py` | Partial |
| `ai/` | `smoke_test_cache.py`, `smoke_test_provider.py` | `test_inference_client.py` | Good |
| `substrate/` | `smoke_test_certification.py` | `test_certification_mentor.py`, `test_egress_policy.py` | Good |
| `truth/` | `smoke_test_emitters_unit.py` | `test_truth_model.py`, `test_emitters.py`, `test_embedding_index.py` | Good |
| `oracle/` | None | `test_oracle.py` | Partial |
| `coverage/` | None | `test_epoch11_coverage.py` | Partial |
| `sdet/` | None | None | **GAP** |
| `governance/` | `smoke_test_governance.py` | None | Partial |
| `continuity/` | None | `test_daemon_cmd.py`, `test_pr_diff_action.py` | Partial |
| `copilot/` | 2 smoke tests | None | Partial |
| `mcp/` | `smoke_test_mcp.py` | None | Minimal |
| `openclaw/` | `smoke_test_openclaw.py` | `test_openclaw_t3.py` | Partial |
| `federation/` | `smoke_test_federation_sync.py` | 2 unit tests | Partial |
| `stages/perf/` | 3 smoke tests | None | Minimal (re-integrated B) |
| `stages/visual/` | `smoke_test_visual.py`, `smoke_test_vision_e9.py` | `test_epoch9_vision.py` | Minimal (re-integrated B) |
| `web/ui/` (dashboard) | None | None | **ZERO GAP** |
| `dashboard/render.py` | None | None | **ZERO GAP** |
| `cherenkov/stages/*_cmd.py` | None | None | **ZERO GAP** for most cmd modules |

### 3.2 Critical Regression Gaps

| Gap | Module | Risk | Impact |
|-----|--------|------|--------|
| **No ingest unit tests** | `stages/ingest.py` | High | Spec parsing errors silent; regression unnoticed |
| **No plan unit tests** | `stages/plan.py` | High | Deterministic mapping logic changes undetected |
| **No review gate unit tests** | `stages/review.py` | High | 6-gate verdict logic wrong = wrong tests |
| **No Prism mock tests** | `execution/prism_mock.py` | High | CDC mock drift = false passes/failures |
| **No Playwright invoke tests** | `execution/playwright_invoke.py` | Medium | WSL bridge regression undetected |
| **No trace reader tests** | `execution/trace_reader.py` | Medium | Trace parsing errors mask test results |
| **No SDET tests** | `sdet/` | Medium | Assertion generation unverified |
| **No dashboard tests** | `web/ui/` | High | React components have zero tests |
| **No render.py tests** | `dashboard/render.py` | Medium | Dashboard rendering unverified |
| **No cmd module tests** | Most `stages/*_cmd.py` | Medium | CLI command regressions undetected |
| **No coverage loop tests** | `coverage/` beyond E11 | Medium | Coverage loop integrity unverified |

### 3.3 Test Duplication

The following are tested by both smoke AND unit tests — consider consolidating:

- HITL CLI: `smoke_test_hitl_cli.py` + `test_hitl_cli.py` + `test_hitl_review_bridge.py`
- Validate gate: `smoke_test_validate_gate.py` + `test_validate_gate.py`
- Federation: `smoke_test_federation_sync.py` + `test_federation_protocol.py` + `test_federation_corpus.py`
- OpenClaw: `smoke_test_openclaw.py` + `test_openclaw_t3.py`

---

## 4. Business Scenario — Test Case Mapping

### 4.1 Track A Core (Product Surface)

| ID | Business Scenario | Feature | Existing Test(s) | Test Coverage | Test Case |
|----|------------------|---------|-----------------|---------------|-----------|
| BS-A1 | User provides OpenAPI spec → tool parses & validates it | INGEST | E2E only | Partial | TC-INGEST-001 to TC-INGEST-010 |
| BS-A2 | Tool generates mutation scenarios from endpoint list | PLAN | E2E only | Partial | TC-PLAN-001 to TC-PLAN-008 |
| BS-A3 | LLM generates Playwright tests from plan | GENERATE | `smoke_test_generate_live.py` | Functional | TC-GEN-001 to TC-GEN-008 |
| BS-A4 | Tests pass 6 review gates (syntax→dry-run) | REVIEW | E2E only | Partial | TC-REVIEW-001 to TC-REVIEW-012 |
| BS-A5 | Approved tests land in tests/ output directory | GENERATE→REVIEW | E2E only | Implicit | TC-GEN-009, TC-REVIEW-013 |
| BS-A6 | HITL items are queued for human review | HITL | `smoke_test_hitl_cli.py` | Good | TC-HITL-001 to TC-HITL-020 |
| BS-A7 | Human approves/rejects tests via CLI | HITL | 3 smokes + 2 unit | Good | TC-HITL-021 to TC-HITL-030 |
| BS-A8 | Concurrent HITL operations are thread-safe | HITL | `smoke_test_hitl_race.py`, `smoke_test_hitl_concurrency.py` | Good | TC-HITL-031 to TC-HITL-040 |
| BS-A9 | Tool runs tests against live server (validate) | VALIDATE | `smoke_test_validate.py` | Good | TC-VAL-001 to TC-VAL-012 |
| BS-A10 | Expected HTTP status from spec vs actual response | VALIDATE | `smoke_test_validate.py` | Good | TC-VAL-013 to TC-VAL-018 |
| BS-A11 | Healing detects contract drift | HEALING | `smoke_test_healing.py` | Partial | TC-HEAL-001 to TC-HEAL-010 |
| BS-A12 | Healing detects auth expiry | HEALING | `smoke_test_healing.py` | Partial | TC-HEAL-011 to TC-HEAL-015 |
| BS-A13 | Healing is suggest-only — never auto-edits | HEALING | `smoke_test_healing.py` | Good | TC-HEAL-016 to TC-HEAL-020 |
| BS-A14 | Eject produces standalone Playwright tests | EJECT | `smoke_test_eject.py` | Good | TC-EJECT-001 to TC-EJECT-012 |
| BS-A15 | Ejected tests run with zero tool dependency | EJECT | `smoke_test_eject.py` | Good | TC-EJECT-013 to TC-EJECT-018 |
| BS-A16 | Circuit breaker trips after 2 plan→generate failures | CORE | `smoke_test.py` | Good | TC-CORE-001 to TC-CORE-005 |
| BS-A17 | Circuit breaker recovers cleanly | CORE | `smoke_test.py` | Good | TC-CORE-006 to TC-CORE-008 |
| BS-A18 | Prism mock server starts & responds | PRISM | None | **GAP** | TC-PRISM-001 to TC-PRISM-006 |
| BS-A19 | Playwright tests execute via runner | PLAYWRIGHT | None | **GAP** | TC-PW-001 to TC-PW-006 |
| BS-A20 | WSL bridge works for UNC paths | PLAYWRIGHT | None | **GAP** | TC-PW-007 to TC-PW-010 |

### 4.2 Epoch 1 — Substrate Provider Router

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-EP1 | User selects local model → routed to Ollama | Substrate | `smoke_test_provider.py` | Good | TC-SUB-001 to TC-SUB-005 |
| BS-EP2 | User selects cloud model → routed to OpenAI | Substrate | `smoke_test_provider.py` | Good | TC-SUB-006 to TC-SUB-010 |
| BS-EP3 | Egress policy enforcement (none/internal/any) | Substrate | `test_egress_policy.py` | Good | TC-SUB-011 to TC-SUB-018 |
| BS-EP4 | Response caching with TTL | Cache | `smoke_test_cache.py` | Functional | TC-CACHE-001 to TC-CACHE-008 |
| BS-EP5 | Cost/latency accounting | Substrate | None | Partial | TC-SUB-019 to TC-SUB-025 |
| BS-EP6 | Provider certification | Substrate | `smoke_test_certification.py` | Functional | TC-CERT-001 to TC-CERT-006 |

### 4.3 Phase A — HITL + Validation + Evidence

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-PA1 | HITL queue persists to SQLite | HITL | Smoke + unit | Good | TC-PA-001 to TC-PA-008 |
| BS-PA2 | HITL items have approval/rejection lifecycle | HITL | Smoke + unit | Good | TC-PA-009 to TC-PA-015 |
| BS-PA3 | Validation gate collects evidence | Validate | `smoke_test_validate_gate.py` | Good | TC-PA-016 to TC-PA-022 |
| BS-PA4 | Evidence collector generates structured report | Validate | `smoke_test_validate_gate.py` | Good | TC-PA-023 to TC-PA-028 |
| BS-PA5 | Standalone demo script runs self-contained | Demos | `scripts/collect_evidence.py` | Partial | TC-DEMO-001 to TC-DEMO-006 |

### 4.4 E7 — Reflector Verdict Memory

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-R1 | Reflector stores verdicts in SQLite | Reflector | 4 smoke + 2 unit | Good | TC-REF-001 to TC-REF-008 |
| BS-R2 | Repeat violations are suppressed by fingerprint | Reflector | `smoke_test_reflector_suppression.py` | Good | TC-REF-009 to TC-REF-015 |
| BS-R3 | Introspect queries show stored verdicts | Reflector | `smoke_test_reflector_introspect.py` | Good | TC-REF-016 to TC-REF-020 |
| BS-R4 | Concurrent store access is safe | Reflector | `smoke_test_reflector_store_concurrency.py` | Good | TC-REF-021 to TC-REF-025 |
| BS-R5 | Behavioral exit demo works end-to-end | Reflector | `smoke_test_e7_behavioral.py` | Good | TC-REF-026 to TC-REF-030 |

### 4.5 E9/E11 — Truth Model & Emitters

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-T1 | Truth model stores resolved verdicts | Truth | `test_truth_model.py` | Good | TC-TRUTH-001 to TC-TRUTH-008 |
| BS-T2 | Emitters emit structured signals | Emitters | `smoke_test_emitters_unit.py`, `test_emitters.py` | Good | TC-TRUTH-009 to TC-TRUTH-015 |
| BS-T3 | Source adapters ingest from traffic | Sources | `test_source_adapter.py`, `test_sources_db_schema.py`, `test_sources_traffic.py` | Good | TC-TRUTH-016 to TC-TRUTH-025 |
| BS-T4 | Oracle evaluates truth signals | Oracle | `test_oracle.py` | Functional | TC-TRUTH-026 to TC-TRUTH-030 |
| BS-T5 | Embedding index stores/retrieves | Truth | `test_embedding_index.py` | Functional | TC-TRUTH-031 to TC-TRUTH-035 |
| BS-T6 | Epoch 11 coverage loop integrity | Coverage | `test_epoch11_coverage.py` | Functional | TC-COV-001 to TC-COV-006 |

### 4.6 E10 — Copilot Explorer

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-CP1 | Explorer crawls API endpoints | Copilot | `smoke_test_copilot_e10.py` | Functional | TC-COP-001 to TC-COP-006 |
| BS-CP2 | Explorer generates hypotheses | Copilot | `smoke_test_copilot_e10.py` | Functional | TC-COP-007 to TC-COP-010 |
| BS-CP3 | NL intent → role-locator Playwright TS | Copilot | `smoke_test_copilot_e10.py` | Functional | TC-COP-011 to TC-COP-015 |
| BS-CP4 | Mentor role provides pre-session digest | Copilot | `smoke_test_mentor.py` | Functional | TC-COP-016 to TC-COP-020 |
| BS-CP5 | Autonomy mode runs without user input | Copilot | `smoke_test_autonomy.py` | Functional | TC-COP-021 to TC-COP-025 |
| BS-CP6 | SecondPairOfEyes triage UX | Copilot | `smoke_test_copilot_e10.py` | Partial | TC-COP-026 to TC-COP-030 |

### 4.7 E12 — Governance KPI Panel

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-G1 | Governance panel displays KPIs | Governance | `smoke_test_governance.py` | Partial | TC-GOV-001 to TC-GOV-008 |
| BS-G2 | KPI thresholds trigger alerts | Governance | None | Partial | TC-GOV-009 to TC-GOV-015 |
| BS-G3 | Governance data sources aggregate correctly | Governance | None | Partial | TC-GOV-016 to TC-GOV-020 |

### 4.8 Horizon 2 — Federation, OpenClaw, MCP, Continuity

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-H1 | Two CHERENKOV nodes sync verdicts | Federation | `smoke_test_federation_sync.py` + 2 unit | Functional | TC-FED-001 to TC-FED-010 |
| BS-H2 | Cross-check resolves conflicts | Federation | None | Partial | TC-FED-011 to TC-FED-015 |
| BS-H3 | OpenClaw chat relay sends/receives messages | OpenClaw | `smoke_test_openclaw.py` + `test_openclaw_t3.py` | Functional | TC-OC-001 to TC-OC-008 |
| BS-H4 | OpenClaw feedback loop heals tests | OpenClaw | `smoke_test_openclaw.py` | Functional | TC-OC-009 to TC-OC-012 |
| BS-H5 | MCP server starts & serves JSON-RPC | MCP | `smoke_test_mcp.py` | Minimal | TC-MCP-001 to TC-MCP-008 |
| BS-H6 | MCP tool calls execute correctly | MCP | `smoke_test_mcp.py` | Minimal | TC-MCP-009 to TC-MCP-014 |
| BS-H7 | PR diff action runs on commit | Continuity | `test_pr_diff_action.py` | Functional | TC-CONT-001 to TC-CONT-006 |
| BS-H8 | Daemon runs scheduled tasks | Continuity | `test_daemon_cmd.py` | Functional | TC-CONT-007 to TC-CONT-012 |

### 4.9 Track B (Re-integrated — Not Validated)

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-B1 | Performance baselines are captured | Perf | `smoke_test_perf.py` | Minimal | TC-PERF-001 to TC-PERF-008 |
| BS-B2 | Anomaly detection flags regressions | Perf | `smoke_test_perf_anomaly.py` | Minimal | TC-PERF-009 to TC-PERF-015 |
| BS-B3 | Perf intelligence suggests optimizations | Perf | `smoke_test_perf_intelligence.py` | Minimal | TC-PERF-016 to TC-PERF-020 |
| BS-B4 | Visual snapshots captured & compared | Visual | `smoke_test_visual.py` | Minimal | TC-VIS-001 to TC-VIS-008 |
| BS-B5 | Vision stage processes E9 vision tasks | Vision | `smoke_test_vision_e9.py`, `test_epoch9_vision.py` | Minimal | TC-VIS-009 to TC-VIS-014 |

### 4.10 Divergence Engine

| ID | Business Scenario | Feature | Existing Tests | Coverage | New Test Cases |
|----|------------------|---------|---------------|----------|---------------|
| BS-D1 | Divergence engine classifies D1-D5 | Divergence | `test_divergence_engine.py` | Functional | TC-DIV-001 to TC-DIV-010 |
| BS-D2 | Witness loop produces evidence | Divergence | None | Partial | TC-DIV-011 to TC-DIV-015 |
| BS-D3 | Skeptic loop challenges claims | Divergence | None | Partial | TC-DIV-016 to TC-DIV-020 |

---

## 5. QA Testing Cycles

### 5.1 Cycle Definition

| Cycle | Name | Scope | Frequency | Target | Entry Criteria | Exit Criteria |
|-------|------|-------|-----------|--------|---------------|-------------|
| **C1** | Smoke | All 32 `smoke_test_*.py` | Every commit | 100% pass | Repo cloned, venv active | All return code 0 |
| **C2** | Integration | E2E pipeline + HITL + Validate + Eject | Every PR | 100% pass | Smoke passes | All integration tests pass |
| **C3** | Regression | Full suite: all smokes + all unit tests | Before merge | 100% pass | C1 + C2 pass | Full matrix green |
| **C4** | Acceptance | QA Demo Kit (7-min demo) | Each validation reviewer | 3/5 "Yes" | C3 pass, target API running | 3 attributable "Yes" verdicts |
| **C5** | Exploratory | Dashboard UI, edge cases, unsupported specs | After C4 passes | Bug discovery | Acceptance passed | Bug log documented |
| **C6** | Platform | Windows/WSL, Linux, macOS | Per release | Platform parity | C1-C3 pass on one platform | All 3 platforms return same results |

### 5.2 Execution Workflow

```
Commit
  ↓
C1: Smoke (automated, ≤5 min)
  ├── FAIL → Fix → Re-commit
  ↓ PASS
C2: Integration (automated, ≤15 min)
  ├── FAIL → Fix → Re-commit
  ↓ PASS
C3: Regression (automated, ≤30 min)
  ├── FAIL → Fix → Re-commit
  ↓ PASS
C4: Acceptance (manual, 7 min per reviewer)
  ├── NO (x < 3) → Fix feedback → Re-attempt
  ↓ YES (x ≥ 3)
C5: Exploratory (manual, 2-4 hours)
  ├── Bugs found → File issues → Fix
  ↓ Pass
C6: Platform (automated + semi-automated)
  ↓ Pass
SHIP
```

---

## 6. Acceptance Criteria Per Module

### 6.1 INGEST (`stages/ingest.py`)

| Criterion | Test | Status |
|-----------|------|--------|
| Parses valid OpenAPI 3.0 spec | TC-INGEST-001 | **NOT TESTED** |
| Parses valid OpenAPI 3.1 spec | TC-INGEST-002 | **NOT TESTED** |
| Rejects malformed YAML/JSON | TC-INGEST-003 | **NOT TESTED** |
| Handles 200+ endpoint specs | TC-INGEST-004 | **NOT TESTED** |
| Handles 0-endpoint spec gracefully | TC-INGEST-005 | **NOT TESTED** |
| Detects security schemes (API key, OAuth, Basic) | TC-INGEST-006 | **NOT TESTED** |
| Extracts example values from spec | TC-INGEST-007 | **NOT TESTED** |
| Produces depth-1 slice per endpoint | TC-INGEST-008 | **NOT TESTED** |
| Generates openapi-fetch client stub | TC-INGEST-009 | **NOT TESTED** |
| Produces mutation menu | TC-INGEST-010 | **NOT TESTED** |

### 6.2 PLAN (`stages/plan.py`)

| Criterion | Test | Status |
|-----------|------|--------|
| Maps each endpoint to happy_path scenario | TC-PLAN-001 | **NOT TESTED** |
| Maps endpoints to error mutation scenarios | TC-PLAN-002 | **NOT TESTED** |
| Maps endpoints to edge-case mutation scenarios | TC-PLAN-003 | **NOT TESTED** |
| Plans respect endpoint constraints (required fields) | TC-PLAN-004 | **NOT TESTED** |
| Plan output is deterministic (no LLM) | TC-PLAN-005 | **NOT TESTED** |
| Circuit breaker produces D2 loop back to PLAN | TC-PLAN-006 | E2E only |
| Max 2 generation failures per case | TC-PLAN-007 | E2E only |
| Plans for auth endpoints include auth setup | TC-PLAN-008 | **NOT TESTED** |

### 6.3 GENERATE (`stages/generate.py`)

| Criterion | Test | Status |
|-----------|------|--------|
| Produces valid TypeScript with openapi-fetch | TC-GEN-001 | Smoke only |
| Uses `openapi-fetch` client (no fetch/axios) | TC-GEN-002 | Smoke only |
| System prompt matches recency-anchored template | TC-GEN-003 | **NOT TESTED** |
| Response JSON includes `code` and `confidence` | TC-GEN-004 | Smoke only |
| Confidence < 0.7 → regenerate | TC-GEN-005 | E2E only |
| Confidence > 0.9 → auto-approve | TC-GEN-006 | E2E only |
| 0.7-0.9 → HITL review | TC-GEN-007 | E2E only |
| Generates tests for all planned scenarios | TC-GEN-008 | Smoke only |

### 6.4 REVIEW (6 gates)

| Criterion | Test | Status |
|-----------|------|--------|
| Syntax gate: valid TypeScript | TC-REVIEW-001 | **NOT TESTED** (E2E only) |
| Structure gate: correct describe/test nesting | TC-REVIEW-002 | **NOT TESTED** |
| AST gate: uses correct API client methods | TC-REVIEW-003 | **NOT TESTED** |
| Assertions gate: has meaningful assertions | TC-REVIEW-004 | **NOT TESTED** |
| `tsc --noEmit` gate: compiles cleanly | TC-REVIEW-005 | **NOT TESTED** |
| Prism dry-run gate: mock server passes | TC-REVIEW-006 | **NOT TESTED** |
| All 6 gates pass → verdict: auto_approve | TC-REVIEW-007 | E2E only |
| Any gate fail → verdict depends on which gate | TC-REVIEW-008 | E2E only |
| Dry-run fail → D2 loop back to PLAN | TC-REVIEW-009 | E2E only |
| Circuit breaker at 2 fails/case | TC-REVIEW-010 | E2E only |
| Verdict message contains gate breakdown | TC-REVIEW-011 | **NOT TESTED** |
| HITL verdict includes test code + failure details | TC-REVIEW-012 | **NOT TESTED** |

### 6.5 EXECUTION (Validate, Eject, Prism, Playwright)

| Criterion | Test | Status |
|-----------|------|--------|
| Validate runs tests against real server | TC-VAL-001 to TC-VAL-018 | Good |
| Eject strips all cherenkov imports/code | TC-EJECT-001 | Good |
| Eject preserves Playwright + openapi-fetch | TC-EJECT-002 | Good |
| Ejected tests run with `npx playwright test` | TC-EJECT-003 | Good |
| Ejected tests produce same results | TC-EJECT-004 | Good |
| Prism mock responds per spec | TC-PRISM-001 | **GAP** |
| Prism mock handles all endpoints | TC-PRISM-002 | **GAP** |
| Playwright runner executes tests | TC-PW-001 | **GAP** |
| WSL bridge resolves UNC paths | TC-PW-007 | **FIXED, NO TEST** |
| Trace reader parses Playwright output | TC-TRACE-001 | **GAP** |

### 6.6 HEALING

| Criterion | Test | Status |
|-----------|------|--------|
| Detects contract drift (response shape mismatch) | TC-HEAL-001 to TC-HEAL-010 | Partial |
| Detects auth expiry (401 responses) | TC-HEAL-011 to TC-HEAL-015 | Partial |
| Produces diagnosis string | TC-HEAL-016 | Good |
| Produces proposed code (suggest-only) | TC-HEAL-017 | Good |
| Never auto-edits test files | TC-HEAL-018 | Good |
| Never auto-commits healing changes | TC-HEAL-019 | Good |
| Healing report is readable JSON/Markdown | TC-HEAL-020 | Partial |

### 6.7 Dashboard UI (`cherenkov/web/ui/`)

| Criterion | Test | Status |
|-----------|------|--------|
| All screens render without crash | TC-UI-001 | **ZERO COVERAGE** |
| Pipeline progress visual updates on events | TC-UI-002 | **ZERO COVERAGE** |
| Divergence list renders D1-D5 correctly | TC-UI-003 | **ZERO COVERAGE** |
| Healing screen shows failures + proposed code | TC-UI-004 | **ZERO COVERAGE** |
| Settings save/restore from localStorage | TC-UI-005 | **ZERO COVERAGE** |
| Eject screen shows standalone test output | TC-UI-006 | **ZERO COVERAGE** |
| Responsive breakpoints (mobile/tablet/desktop) | TC-UI-007 | **ZERO COVERAGE** |
| Accessibility (keyboard nav, screen reader) | TC-UI-008 | **ZERO COVERAGE** |

---

## 7. UX Issues (from Dashboard Code Inspection)

Based on source code review of `cherenkov/web/ui/src/components/`. Screenshots were attached by user but could not be viewed — issues below are from static code analysis.

### 7.1 Critical (Functionality Impact)

| ID | Component | Issue | Line(s) | Risk |
|----|-----------|-------|---------|------|
| UX-C1 | `HealingScreen.tsx:87-96` | `editTestScenario` + `validateSuite` API calls are `best-effort` with `.catch(console.warn)` — silent failures. User has no feedback loop | 87-96 | Healing actions appear to work but silently fail |
| UX-C2 | `SettingsScreen.tsx` | Settings persist to `localStorage` only — lost on cache clear, no migration strategy | 30-40 | User-configured settings vanish without notice |
| UX-C3 | All screens | All data from `MOCK_DATA` — dashboard is **entirely mocked** with no real API integration | Every file | Dashboard shows fake data; user cannot distinguish real vs mock |
| UX-C4 | `CommandPalette.tsx` | No indication of search index size or loading state on large projects | Unknown | Hang risk on large command sets |

### 7.2 High (Usability Impact)

| ID | Component | Issue | Line(s) | Risk |
|----|-----------|-------|---------|------|
| UX-H1 | `HealingScreen.tsx:92` | Hardcoded `localhost:8080/v2` URL — no configurable endpoint, breaks in Docker/production | 92 | CORS/connectivity failures with no user recourse |
| UX-H2 | `SettingsScreen.tsx:30-32` | `localStorage` keys use `[copilot]` prefix — inconsistent namespace across components | 30-32 | Key collision with other copilot tools |
| UX-H3 | `Sidebar.tsx` | Navigation has no active-state persistence on page reload | Unknown | User loses context on refresh |
| UX-H4 | `OverviewScreen.tsx` | Release Readiness KPI ring has no tooltip explaining calculation | Unknown | Users cannot interpret the score |
| UX-H5 | `TopBar.tsx` | No search/filter functionality in long divergence lists | Unknown | Scalability issue with 200+ endpoints |

### 7.3 Medium (Polish/Layout)

| ID | Component | Issue | Line(s) | Risk |
|----|-----------|-------|---------|------|
| UX-M1 | Multiple | Font uses `font-display` with no web-safe fallback stack | Multiple | Flash of unsupported text on non-Google-Fonts environments |
| UX-M2 | All cards | Borders use `border-white/5` — near-invisible on white/light backgrounds | Multiple | Theme support is dark-mode only; no light theme |
| UX-M3 | `KpiRing` | No a11y `role` or `aria-label` — screen reader invisible | Unknown | Accessibility violation |
| UX-M4 | `PipelineScreen.tsx` | No error state for pipeline stage failures beyond status badge | Unknown | User cannot diagnose pipeline failure cause |
| UX-M5 | `DivergencesScreen.tsx` | No bulk-select/resolve workflow for multiple divergences | Unknown | Manual one-by-one bottleneck |

### 7.4 Low (Minor/Cosmetic)

| ID | Component | Issue | Line(s) | Risk |
|----|-----------|-------|---------|------|
| UX-L1 | All | Console logs abundant — no log level gating in production | Unknown | Performance + debug info leak |
| UX-L2 | Multiple | Magic number spacing (p-6, p-8, gap-6) not sourced from design tokens | Unknown | Theme inconsistency |
| UX-L3 | All screens | Fixed pixel sizing in some components vs relative in others | Unknown | Responsive breakage on non-standard viewports |
| UX-L4 | `HealingScreen.tsx:98` | `setTimeout` of 1500ms for dismiss animation — feels sluggish | 98 | Perceived performance issue |

---

## 8. Recommendations

### 8.1 Immediate (Before Gate)

| # | Recommendation | Why | Effort |
|---|---------------|-----|--------|
| R1 | **Write unit tests for INGEST, PLAN, REVIEW, PRISM** | Three core stages have ZERO unit tests — any change is blind | 2-3 days |
| R2 | **Add Playwright invoke test for WSL bridge** | UNC path fix is untested — will regress on next refactor | 0.5 day |
| R3 | **Replace dashboard mock data with real API calls** | Fake data in demos undermines credibility with QA reviewers | 1-2 days |
| R4 | **Add CI pipeline to GitHub Actions** | No automated CI — every regression is manual discovery | 1 day |
| R5 | **Create test for 3+ acceptance criteria per module gap** | High-risk modules (ingest, plan, review) need baseline coverage | 3-5 days |

### 8.2 Short-Term (During Gate)

| # | Recommendation | Why | Effort |
|---|---------------|-----|--------|
| R6 | **Add WSL detection + skip to smoke tests** | Avoid false failures on Windows without WSL | 0.5 day |
| R7 | **Add exit code check wrapper to run_all_smokes.sh** | Eliminate human error in sequential smoke runs | 0.25 day |
| R8 | **Create test data fixtures for all OpenAPI variants** | Enables reproducible, environment-independent tests | 1 day |
| R9 | **Add lint and typecheck commands to test plan** | Currently absent from all verification steps | 0.5 day |
| R10 | **Document smoke test preconditions per test** | Many smokes fail silently when preconditions unmet | 0.5 day |

### 8.3 Medium-Term (Post-Gate)

| # | Recommendation | Why | Effort |
|---|---------------|-----|--------|
| R11 | **Implement Playwright/React Testing Library tests for dashboard** | UI has zero test coverage; any refactor is blind | 3-5 days |
| R12 | **Add E2E test for full pipeline + validation + eject** | Current smokes test modules in isolation; full E2E gap | 2 days |
| R13 | **Consolidate duplicate smoke/unit tests** | HITL, Federation, OpenClaw have overlapping coverage | 1 day |
| R14 | **Add platform matrix testing** | Windows/WSL vs Linux vs macOS differences uncharacterized | 2-3 days |
| R15 | **Implement snapshot/approval testing for generated TS code** | Ensure LLM output stays within expected patterns | 2 days |

### 8.4 Long-Term

| # | Recommendation | Why | Effort |
|---|---------------|-----|--------|
| R16 | **Add performance budget to smoke tests** | Guard against LLM latency regressions | 0.5 day |
| R17 | **Add mutation testing for core stages** | Validate test suite itself catches real bugs | 3-5 days |
| R18 | **Implement test impact analysis (only run affected tests)** | 57 test files will grow; optimize CI time | 2-3 days |
| R19 | **Add security tests for MCP, Federation, OpenClaw** | Network-facing modules have zero security coverage | 2-3 days |
| R20 | **Create formal test specification for each module** | Move from implicit to explicit acceptance criteria | 5+ days |

---

## 9. Test Data Management

### 9.1 Current Test Data Sources

| Data | Source | Format | Location |
|------|--------|--------|----------|
| OpenAPI spec | `target/target_spec.json` | OpenAPI 3.0 JSON | `stub/` |
| Generated tests | LLM + `stub/generated_tests/` | TypeScript `.spec.ts` | `stub/` |
| HITL items | SQLite (in-memory or file) | SQLite DB | Created per test |
| Reflector verdicts | SQLite file | SQLite DB | `reflector.db` |
| Dashboard mock data | TypeScript `mockData.ts` | In-memory JS objects | `cherenkov/web/ui/src/` |
| Target API | `target/target_api.py` | FastAPI Python | `target/` |
| Prism mock spec | `target/target_spec.json` | OpenAPI 3.0 JSON | `stub/` |

### 9.2 Recommended Fixture Additions

| Fixture | Purpose | Format | Use Case |
|---------|---------|--------|----------|
| `fixtures/specs/petstore_v3.0.json` | Standard OpenAPI 3.0 | JSON | INGEST tests |
| `fixtures/specs/petstore_v3.1.yaml` | Standard OpenAPI 3.1 | YAML | INGEST tests |
| `fixtures/specs/malformed.yaml` | Broken YAML | YAML | Error handling |
| `fixtures/specs/200-endpoint-spec.json` | Large spec | JSON | Scale test |
| `fixtures/specs/0-endpoint-spec.json` | Empty spec | JSON | Edge case |
| `fixtures/specs/auth-apikey.yaml` | API key auth | YAML | Auth detection |
| `fixtures/specs/auth-oauth.yaml` | OAuth auth | YAML | Auth detection |
| `fixtures/generated_tests/` | Pre-generated TS | `.spec.ts` | REVIEW, EJECT tests |
| `fixtures/validate-results/` | Pre-recorded results | JSON | VALIDATE tests |

---

## 10. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| LLM output changes (new model version) break expected code patterns | High | Medium | Snapshot tests on generated code; version-pin model |
| Prism breaking change changes mock behavior | Low | High | Pin Prism version in CI |
| Playwright API changes | Medium | Medium | CI tests run against pinned Playwright |
| WSL UNC path regression | Medium | High | Add targeted test for WSL bridge |
| Dashboard mock data diverges from real API | High | High | Replace mock data with real API calls (R3) |
| Track B and Track C code in `track-b-c-deferred/` diverges from re-integrated live code | High | High | One-time decision: quarantine or adopt (per SCOPE_LEDGER.md) |
| Smoke tests depend on external Ollama instance | High | Medium | All core smokes use stub tests, not live LLM |
| New contributor unaware of AGENTS.md anti-drift rules | Medium | High | Add pre-commit hook checking AGENTS.md reference |

---

## Appendix A — Smoke Test Runbook

> Full instructions in `docs/process/QA_VALIDATION_RUNBOOK.md`

Quick-reference:

```bash
# Prerequisites
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# All 6 core smokes (Track A)
python3 smoke_test.py && echo "PASS" || echo "FAIL"
python3 smoke_test_hitl_race.py && echo "PASS" || echo "FAIL"
python3 smoke_test_hitl_concurrency.py && echo "PASS" || echo "FAIL"
python3 smoke_test_hitl_cli.py && echo "PASS" || echo "FAIL"
python3 smoke_test_eject.py && echo "PASS" || echo "FAIL"
python3 smoke_test_validate.py && echo "PASS" || echo "FAIL"

# Extended smokes (selectively)
python3 smoke_test_healing.py && echo "PASS" || echo "FAIL"
python3 smoke_test_golden_path.py && echo "PASS" || echo "FAIL"
python3 smoke_test_generate_live.py && echo "PASS" || echo "FAIL"
```

## Appendix B — Test Naming Conventions

```
TC-{MODULE}-{NNN}
```

| Module Prefix | Module |
|--------------|--------|
| INGEST | stages/ingest.py |
| PLAN | stages/plan.py |
| GEN | stages/generate.py |
| REVIEW | stages/review.py |
| VAL | execution/validate.py |
| EJECT | execution/eject.py |
| PRISM | execution/prism_mock.py |
| PW | execution/playwright_invoke.py |
| TRACE | execution/trace_reader.py |
| HEAL | healing/ |
| HITL | hitl/ |
| REF | reflector/ |
| DIV | divergence/ |
| TRUTH | truth/ |
| COV | coverage/ |
| SUB | substrate/ |
| CACHE | ai/cache.py |
| CERT | substrate/certification |
| GOV | governance/ |
| COP | copilot/ |
| FED | federation/ |
| OC | openclaw/ |
| MCP | mcp/ |
| CONT | continuity/ |
| PERF | perf/ |
| VIS | visual/ |
| UI | web/ui/ |
| PA | Phase A (validation gate) |
| DEMO | QA demo kit |
| CORE | core/orchestrator.py |
