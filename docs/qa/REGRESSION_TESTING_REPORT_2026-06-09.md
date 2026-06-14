# Cherenkov QA — Comprehensive Regression Testing Report

**Date:** 2026-06-09
**Branch:** `claude/regression-testing-gaps-lupixa`
**Test Run Results:** 16 failed / 245 passed / 9 skipped (261 total, 6.1% failure rate)
**Scope:** Full codebase — E2E, unit, smoke, integration, CI/CD, business logic, customer journeys

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Actual Test Run — Real Failures](#2-actual-test-run--real-failures)
3. [E2E Coverage Assessment](#3-e2e-coverage-assessment)
4. [Customer-Centric Assessment](#4-customer-centric-assessment)
5. [QA Persona Assessment](#5-qa-persona-assessment)
6. [Workflow Coverage Assessment](#6-workflow-coverage-assessment)
7. [Functionality Coverage Assessment](#7-functionality-coverage-assessment)
8. [Technical Gaps](#8-technical-gaps)
9. [Business Gaps](#9-business-gaps)
10. [Needed Enhancements](#10-needed-enhancements)
11. [Recommendations](#11-recommendations)
12. [Gap Heat Map](#12-gap-heat-map)

---

## 1. Executive Summary

Cherenkov QA is a production-grade API conformance test generator (OpenAPI → Playwright) with 217 Python source files, 47 React components, 60+ test files, and 5 CI workflows. Despite impressive breadth, the test suite has **critical structural weaknesses** that prevent reliable regression detection:

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| CI Quality Gates | D | All smoke tests use `\|\| true`; zero blocking gates for tests or coverage |
| E2E Coverage Depth | C+ | 18/20 screens covered, but assertions are visibility-only, not behavioural |
| Python Unit Test Coverage | C | 245 passing tests, but 20+ core modules have zero unit tests |
| API Endpoint Coverage | F | Only ~15–20% of endpoints have any test coverage |
| Error Path Coverage | F | Zero tests for 4xx/5xx, timeouts, or network failures |
| Dependency Completeness | F | `requirements.txt` lists 5 packages; project needs 20+ |
| Security Testing | D | Snyk gates CRITICAL/HIGH but Semgrep is soft; auth endpoints have a failing dependency |

---

## 2. Actual Test Run — Real Failures

Running `python -m pytest tests/ --ignore=tests/eject_fixtures` with full dependency install produces **16 failures**.

### 2.1 Failure Inventory

| # | Test File | Test Name | Root Cause | Severity |
|---|-----------|-----------|------------|----------|
| 1–5 | `tests/test_hitl_auth.py` | All 5 auth tests | Missing `python-multipart` in `requirements.txt`; FastAPI can't process form data | **CRITICAL** |
| 6–8 | `tests/integration/test_redis_fallback.py` | All 3 Redis fallback tests | Missing `redis` module in `requirements.txt` | **CRITICAL** |
| 9 | `tests/test_mutation_validate.py` | `test_validation_mutation` | Test calls `run_pipeline(simulate_fail_stage="REVIEW")` but `CHERENKOV_ENV` is not set to `development` in test setup | **HIGH** |
| 10–13 | `tests/unit/test_chat.py` | 4 LLM fallback tests | Mock LLM not wired; Ollama unavailable returns real error instead of `[MOCK]` prefix | **HIGH** |
| 14 | `tests/unit/test_mcp_chat_tools.py` | `test_with_all_params` | Path normalization bug: test passes `"api.yaml"`, code absolutizes to `/home/user/cherenkov-qa/api.yaml`; assertion expects relative | **MEDIUM** |
| 15 | `tests/test_legacy_deep_healing.py` | `test_legacy_deep_healing` | Playwright E2E sub-process fails because `stub/playwright.config.ts` references `@playwright/test` which is not installed in test env | **MEDIUM** |
| 16 | `tests/test_legacy_visual.py` | `test_legacy_visual` | Visual baseline initialized then immediately detects layout mismatch (self-fulfilling failure); env has no stable UI to screenshot | **MEDIUM** |

### 2.2 DeprecationWarnings

`cherenkov/web/api.py:133` uses `@app.on_event("startup")` which is deprecated in FastAPI. Should be migrated to `lifespan` context manager to avoid future breakage.

### 2.3 Version Mismatch

`requirements.txt` pins `pydantic==2.7.1` but the environment has `pydantic==2.13.4`. This will cause environment drift between dev, CI, and production containers.

---

## 3. E2E Coverage Assessment

### 3.1 Dashboard E2E (Playwright — `cherenkov/web/ui/tests/`)

**27 test cases** across 2 spec files (`dashboard_e2e.spec.ts`, `a11y.spec.ts`).

#### Screen Coverage Matrix

| Screen | LOC | E2E Tests | A11y Tested | Depth |
|--------|-----|-----------|-------------|-------|
| ProjectsScreen | 292 | ✅ Full | ✅ Axe scan | Shallow |
| OverviewScreen | 234 | ✅ Full | ❌ | Shallow |
| TruthMapScreen | 197 | ✅ Full | ❌ | Shallow |
| DivergencesScreen | 344 | ✅ Partial | ❌ | Visibility only |
| AuthorScreen | 251 | ✅ Partial | ❌ | Shallow |
| SignalsScreen | 193 | ✅ Tab switch | ❌ | Visibility only |
| MemoryScreen | 83 | ✅ Visibility | ❌ | Trivial |
| GovernanceScreen | 129 | ✅ Visibility | ❌ | Trivial |
| SetupScreen | 541 | ✅ Full | ❌ | Shallow |
| PipelineScreen | 486 | ✅ Full | ❌ | Shallow |
| **ReviewScreen** | **766** | ✅ Partial | ❌ | **Near-zero** |
| HealingScreen | 319 | ✅ Full | ❌ | Shallow |
| EjectScreen | 287 | ✅ Full | ❌ | Shallow |
| SettingsScreen | 341 | ✅ Full | ❌ | Shallow |
| KnowledgeExplorerScreen | 171 | ✅ Full | ❌ | Shallow |
| DeviceManagerScreen | 243 | ✅ Partial | ❌ | Visibility only |
| ChatScreen | 233 | ✅ Full | ❌ | Shallow |
| UiKitScreen | 251 | ✅ Full | ❌ | Trivial |
| **MobileScreen** | **142** | ❌ **UNTESTED** | ❌ | — |
| **MobilePilotScreen** | **204** | ❌ **UNTESTED** | ❌ | — |

#### Assertion Quality

- **Primary patterns used:** `toBeVisible()`, `toContainText()`, `toHaveAttribute()`
- **Real data validation found in only 3 places** (textarea value, localStorage, API payload)
- **Zero assertions** on filtered results, API response content, state after actions

#### Structural Problems

- **Brittle selectors:** Heavy use of `#id-*` and hardcoded text like `getByText('POST /pets')` — one UI refactor breaks dozens of tests
- **Hardcoded mock data:** `proj-petstore`, `fail-1`, `fail-2` baked into `api_mocks.ts`
- **Single viewport (1280×720):** No mobile (375×667), tablet (768×1024), or wide desktop (1920×1080)
- **Single browser (Chromium):** No Firefox or Safari
- **Magic timeouts:** Scattered `waitForTimeout(500)` calls instead of proper waiter conditions
- **Duplicate test names:** Two tests labelled "Knowledge: enter query…" (lines 455, 467) — one actually tests DeviceManagerScreen

#### Interaction Gaps (Never Tested)

- Drag-and-drop in SetupScreen
- j/k keyboard navigation in DivergencesScreen
- Approval/rejection workflow in ReviewScreen
- Code editing in ReviewScreen editor
- Filter combinations (only filter presence checked, not results)
- Copy-to-clipboard buttons
- Hover states triggering content
- Form validation error messages
- Right-click / context menus

### 3.2 Playwright API Suite (`playwright-suite/`, `stub/`)

| Test File | Content | Status |
|-----------|---------|--------|
| `happy_path.spec.ts` | POST /users → 201, `id`, `email` presence | Shallow |
| `password_too_short.spec.ts` | POST /users invalid → 422 status only | Trivial |
| `visual_regression_baseline_ui.spec.ts` | Screenshot baseline at 1280×720 | Single viewport |
| `golden_edit.spec.ts` | Empty file (`// test`) | **Useless** |
| `GET_v1_customers.spec.ts` | Status 200 + `data` property | Trivial |
| `POST_v1_customers.spec.ts` | Customer created, has `id` | Shallow |
| `GET_v1_customers_search.spec.ts` | Search, has `data` | Trivial |

**Zero tests for:** response body schema, error messages, pagination, update/delete, concurrent operations, boundary conditions.

---

## 4. Customer-Centric Assessment

### 4.1 Zero Error State Testing

Every user flow that encounters an error is completely untested:

| User Action | Error Scenario | Tested? |
|-------------|---------------|---------|
| Upload spec file | File > 10MB | ❌ |
| Enter spec URL | 404 URL | ❌ |
| Enter spec URL | Private IP blocked | ❌ |
| Trigger pipeline run | LLM timeout | ❌ |
| Approve test | Concurrent approval by another user | ❌ |
| Eject tests | Disk full | ❌ |
| Chat query | Ollama not running | ❌ |
| Validate | Target server unreachable | ❌ |

### 4.2 Empty State Coverage

When there is no data (fresh install, no projects yet), the UI shows empty states. **None of these are tested.**

### 4.3 Onboarding / First-Run Experience

`OnboardingWizard.tsx` exists as a component. It has **zero test coverage** — neither E2E nor unit.

### 4.4 Responsive / Multi-Device

The product claims mobile and multi-device support (mobile pilot, device manager, Appium/Maestro). Yet:
- All E2E tests run at one fixed 1280×720 viewport
- MobileScreen and MobilePilotScreen have zero E2E tests
- No touch/swipe interaction tested

### 4.5 Accessibility (A11y)

- Only 2 of 20 screens have any accessibility testing (`ProjectsScreen` via Axe, `OverviewScreen` KpiRing via ARIA)
- Color contrast explicitly excluded from Axe scan
- No keyboard-only navigation tested beyond Ctrl+K
- No screen-reader announcement testing (`aria-live`, `aria-label` content)
- No focus trap testing in modals/drawers

### 4.6 Performance UX

No tests verify:
- Loading skeleton shown while data fetches
- Toast notification timing
- WebSocket reconnection on disconnect
- Long operation progress feedback

---

## 5. QA Persona Assessment

### 5.1 Test Quality Metrics

| Metric | Value | Target |
|--------|-------|--------|
| Total test files | 74 | — |
| Passing tests | 245 | — |
| Failing tests | 16 (6.1%) | 0 |
| Skipped tests | 9 | — |
| Empty/trivial tests | `golden_edit.spec.ts` (1 file) | 0 |
| Tests asserting data content | ~10% | >60% |
| Tests asserting only visibility | ~60% | <20% |
| Error path tests | 0% | >30% |
| Coverage threshold enforced | None | >70% |

### 5.2 Test Organisation

**Strengths:**
- Logical directory split: `tests/smoke/`, `tests/unit/`, `tests/integration/`
- Kill-criteria pattern used in most smoke tests (explicit exit codes + assertions)
- No empty test bodies or bare `pass` statements
- Good use of mocking for external dependencies (LLM, subprocess, HTTP)

**Weaknesses:**
- No `conftest.py` → shared fixtures not available across test modules
- No `pytest.ini` / `[tool.pytest]` configuration in `pyproject.toml`
- Test for simulation mode requires `CHERENKOV_ENV=development` but no fixture sets it
- 4 chat fallback tests rely on Ollama LLM being absent but mock not stubbed → environment-dependent
- Duplicate test names in `dashboard_e2e.spec.ts`

### 5.3 Known Documented Bugs Without Regression Tests

Per `agent_memory/known-bugs.md`:

| Bug | Description | Regression Test? |
|-----|-------------|-----------------|
| Bug #1 (Canonical) | Spec declares 422, target API returns 400 on POST /users validation | `password_too_short.spec.ts` covers status but doesn't assert mismatch pattern |
| Bug #2 | Auth expiry: 201 → 401 drift | `smoke_test_healing.py` covers, no dedicated regression |
| Bug #3 | Contract drift (missing response fields) | No dedicated regression test |

### 5.4 Validation Gate Status

Per `agent_memory/validation-gate.md`: The human validation gate (5-reviewer QA runbook) has **0/5 reviews completed**. The gate is explicitly "NOT PASSED." Product development continues under a waiver but no validated QA stamp exists.

---

## 6. Workflow Coverage Assessment

### 6.1 Core Test Generation Workflow

```
INGEST → PLAN → GENERATE → REVIEW → APPROVE/REJECT → EJECT
```

| Stage | Unit Tests | Integration | E2E | Coverage |
|-------|-----------|-------------|-----|----------|
| INGEST | ❌ | ❌ | ✅ (smoke) | E2E only |
| PLAN | ❌ | ❌ | ✅ (smoke) | E2E only |
| GENERATE | ❌ | ❌ | ✅ (smoke, GPU-opt-in) | E2E only |
| REVIEW (6 gates) | ❌ | ❌ | ✅ (partial smoke) | E2E partial |
| HITL Approve | ✅ (root test) | ✅ (smoke) | ✅ | Good |
| HITL Reject | ✅ (root test) | ✅ (smoke) | ✅ | Good |
| HITL Classify | ❌ | ❌ | ❌ | None |
| EJECT | ❌ | ❌ | ✅ (smoke) | E2E only |

### 6.2 Validation Workflow

| Sub-workflow | Tested? | Notes |
|-------------|---------|-------|
| Run generated tests vs target | ✅ (smoke) | Shallow |
| Trace reader analysis | ❌ | No unit tests |
| Value tightening suggestions | ❌ | No tests |
| TLS / auth header support | ❌ | No tests |

### 6.3 Healing Workflow

| Sub-workflow | Tested? | Notes |
|-------------|---------|-------|
| AuthExpiryHealer | ✅ (smoke) | Shallow |
| ContractDriftHealer | ✅ (smoke) | Shallow |
| SandboxHealer | ❌ | No tests |
| VisualHealer | ❌ | No tests |
| D2 Planner replan loop | ❌ | **Critical gap** |

### 6.4 CI/CD Workflow

All smoke tests run with `|| true` — **a failing smoke test does not block a merge**. Quality gates that are enforced:

| Gate | Blocking? | Notes |
|------|-----------|-------|
| Docker build | ✅ Yes | Hard failure |
| Snyk CRITICAL/HIGH | ✅ Yes | Hard failure |
| Docs drift check | ✅ Yes | Hard failure |
| Smoke tests (36) | ❌ No | `\|\| true` on all |
| Unit tests | ❌ No | Coverage XML generated but never checked |
| mypy type checking | ❌ No | `\|\| true` |
| ruff linting | ❌ No | Pre-commit only, not in CI |
| Semgrep security | ❌ No | `continue-on-error: true` |
| CodeQL analysis | ❌ No | Configured but not in any workflow |
| Accessibility | ❌ No | Not in CI at all |
| Performance regression | ❌ No | k6 runs but no thresholds |

### 6.5 Mobile Workflow

| Step | Tested? |
|------|---------|
| APK/HAR ingestion | ✅ (`test_mobile_pipeline.py`) |
| Mobile plan generation | ✅ |
| Maestro test generation | ✅ |
| Appium test generation | ✅ |
| Mobile eject | ✅ |
| MobileScreen UI | ❌ |
| MobilePilotScreen UI | ❌ |
| Device connectivity check | ❌ |
| Real device run (CI) | ❌ (only on self-hosted ADB runner) |

---

## 7. Functionality Coverage Assessment

### 7.1 API Endpoint Coverage

**Total endpoints defined:** 30+ (core + knowledge + chat)
**Endpoints with any test coverage:** ~6 (20%)

| Endpoint | Method | Tested? | Depth |
|----------|--------|---------|-------|
| `/api/v1/health` | GET | ✅ (smoke) | Shallow |
| `/api/v1/doctor` | GET | ❌ | None |
| `/api/v1/ingest` | POST | ❌ | None |
| `/api/v1/run` | POST | ✅ (E2E, smoke) | Shallow |
| `/api/v1/tests` | GET | ❌ | None |
| `/api/v1/review/queue` | GET | ✅ (smoke) | Shallow |
| `/api/v1/review/approve` | POST | ✅ (root test) | Good |
| `/api/v1/review/reject` | POST | ✅ (root test) | Good |
| `/api/v1/review/edit` | POST | ❌ | None |
| `/api/v1/review/classify` | POST | ❌ | None |
| `/api/v1/validate` | POST | ✅ (smoke) | Shallow |
| `/api/v1/eject` | POST | ✅ (smoke) | Shallow |
| `/api/v1/divergences` | GET | ❌ | None |
| `/api/v1/divergences/act` | POST | ❌ | None |
| `/api/v1/overview` | GET | ❌ | None |
| `/api/v1/truth-map` | GET | ❌ | None |
| `/api/v1/failures` | GET | ❌ | None |
| `/api/v1/metrics` | GET | ❌ | None |
| `/api/v1/mobile/pilot/status` | GET | ❌ | None |
| `/api/v1/mobile/pilot/start` | POST | ❌ | None |
| `/ws/live` | WS | ❌ | None |
| All `/api/v1/chat/*` | Multiple | ❌ | None |
| All `/api/v1/knowledge/*` | Multiple | ❌ | None |

### 7.2 Python Source Modules Without Any Tests

**Core (`cherenkov/core/`):**
- `errors.py` — Zero tests
- `compat.py` — Zero tests
- `feedback_store.py` — No direct unit tests

**Execution (`cherenkov/execution/`):**
- `k6_runner.py` — Zero tests
- `trace_reader.py` — Zero tests
- `visual_diff.py` — No unit tests (smoke only)
- `playwright_invoke.py` — Zero tests
- `perf_analyzer.py` — Zero tests
- `prism_mock.py` — Zero tests
- `demo_mode.py` — Zero tests

**Stages (`cherenkov/stages/`):**
- `certify_cmd.py` — Zero tests
- `copilot_cmd.py` — No isolated unit tests
- `daemon_cmd.py` — Zero tests
- `governance_cmd.py` — Zero tests
- `map_cmd.py` — Zero tests
- `profile_cmd.py` — Zero tests
- `report_cmd.py` — Zero tests
- `review_serve.py` — Zero tests
- `self_test_cmd.py` — Zero tests
- `ui_generate.py` — Zero tests
- `ui_plan.py` — Zero tests

---

## 8. Technical Gaps

### T1 — CRITICAL: Incomplete `requirements.txt`

**File:** `requirements.txt`
**Impact:** Causes 8 test failures. Breaks fresh installs.

Missing from `requirements.txt` but required by the project:
- `fastapi` (used by `cherenkov/web/api.py` and 3 test files)
- `redis` (used by `tests/integration/test_redis_fallback.py`, optional store backend)
- `python-multipart` (required by FastAPI for form data — HITL auth endpoints)
- `click` (used by `tests/unit/test_doctor.py`, CLI framework)
- `httpx2` / `httpx` (FastAPI TestClient dependency)
- `uvicorn` (FastAPI ASGI server)
- `pytest` (test runner)
- `pytest-cov` (coverage)
- `anyio` (async test support)

Also: `pydantic==2.7.1` is pinned but `2.13.4` is in use. The pin will cause `pip install` to install a version that doesn't match the running environment.

### T2 — CRITICAL: All CI Smoke Tests Are Non-Blocking

**File:** `.github/workflows/ci.yml`
**Impact:** A broken commit merges silently. Tests are theater.

Every smoke test step uses `|| true`:
```yaml
- run: python -m pytest tests/smoke/smoke_test.py -v || true
```
This means any failure is swallowed and CI reports green regardless.

### T3 — HIGH: No Coverage Threshold

Coverage XML is generated but never evaluated. There is no `--cov-fail-under` flag and no CI step inspects `coverage.xml`. The project can regress to 0% coverage without CI alerting.

### T4 — HIGH: Test Requires Environment Variable Not Set by Fixture

**File:** `tests/test_mutation_validate.py`
`run_pipeline(simulate_fail_stage="REVIEW")` asserts `CHERENKOV_ENV != "production"` but no fixture sets this env var. The test will always fail unless run with `CHERENKOV_ENV=development` manually.

**Fix:** Add `os.environ["CHERENKOV_ENV"] = "development"` in test setup or `conftest.py`.

### T5 — HIGH: LLM Mock Not Wired in Chat Tests

**File:** `tests/unit/test_chat.py` (lines 259–271)
Tests expect `[MOCK]` prefix from a mock LLM but the mock is never injected. When Ollama is unavailable, the agent returns a real error message, not the mock response. 4 tests fail.

### T6 — HIGH: Path Normalization Bug

**File:** `tests/unit/test_mcp_chat_tools.py:129`
Test passes `spec_path="api.yaml"` but the tool absolutizes it to `/home/user/cherenkov-qa/api.yaml`. The assertion expects the relative form. Either the test must pass an absolute path, or the tool must not absolutize relative paths.

### T7 — MEDIUM: FastAPI `on_event` Deprecation

**File:** `cherenkov/web/api.py:133`
`@app.on_event("startup")` is deprecated. Must be migrated to the `lifespan` context manager pattern before the next FastAPI major release.

### T8 — MEDIUM: Visual Regression Tests Require Stable Running UI

`test_legacy_visual.py` and `test_legacy_deep_healing.py` start a FastAPI target server and take screenshots. Without the full dashboard running, they produce unstable baselines and immediately fail on layout mismatch. These tests should either be isolated behind a `@pytest.mark.requires_ui` tag or converted to mock-based tests.

### T9 — MEDIUM: `eject` Endpoint Returns Success on Exception

**File:** `cherenkov/web/api.py:541`
```python
except Exception as e:
    return {"status": "ejected", "output_path": payload.output_path, "files": []}
```
A failed eject returns HTTP 200 with an empty `files` array, misleading the client that ejection succeeded.

### T10 — MEDIUM: WebSocket `/ws/live` Has No Authentication

Any client can connect to the live event stream without credentials. In multi-tenant or network-exposed deployments this leaks pipeline state.

### T11 — LOW: Dashboard Endpoints Have No Authentication

`/api/v1/overview`, `/api/v1/truth-map`, `/api/v1/failures`, `/api/v1/metrics` require no auth while `/api/v1/review/*` endpoints do. Inconsistent security model.

### T12 — LOW: Feedback Store Not Transactional

**File:** `cherenkov/core/feedback_store.py`
Uses a plain JSON file with no file lock. Concurrent feedback writes will corrupt the file.

### T13 — LOW: No conftest.py for Shared Fixtures

No `conftest.py` exists at the project root or in `tests/`. Environment variable setup, common mocks, and test database cleanup must be duplicated across every test file.

### T14 — LOW: CodeQL Configured But Not Running

`.github/codeql/codeql-config.yml` exists but no GitHub Actions workflow invokes it. CodeQL is the most important static security analysis tool in the stack and is silently disabled.

---

## 9. Business Gaps

### B1 — Classify Action Untested

`POST /api/v1/review/classify` accepts three values (`regression`, `intended`, `ignore`) and maps them to different downstream actions. This classification drives false-positive rate reduction — a core business KPI. It has **zero test coverage**.

### B2 — D2 Feedback Loop (Replan) Untested

The orchestrator's D2 Planner detects repeated failures and replans test scenarios. The hard-coded limits (3 replans, 2 failures per case type before circuit break) and replan logic are complex state machine code with **no tests**. If the planner loop misbehaves, it can generate infinite loops or silently skip entire endpoint categories.

### B3 — Demo Mode Untested

`execution/demo_mode.py` injects mock findings for demonstration purposes. No tests verify that demo mode correctly fakes data, that demo flags are stripped before production runs, or that demo mode doesn't contaminate real verdicts.

### B4 — Knowledge Graph / RAG Quality Untested

`cherenkov/knowledge/` and GraphRAG-based enrichment have smoke test coverage but no quality metrics. There is no test for relevance, recall, or correctness of knowledge-enriched test generation.

### B5 — Governance KPIs Not Validated

`GET /api/v1/metrics` and the GovernanceScreen display defect escape count, false positive rate, and cache hit ratio. These calculations are **never tested**. A bug in accounting could silently under/over-report KPIs shown to stakeholders.

### B6 — Human Validation Gate Not Passed

Per `docs/process/QA_VALIDATION_RUNBOOK.md`, 5 QA reviewers must answer "Yes" to: "Would you keep these generated tests in your suite?" **0/5 reviews have been completed.** The validation gate is explicitly "NOT PASSED." Any claim of QA certification is unsupported.

### B7 — Prism Mock Drift Undetected

`execution/prism_mock.py` launches a Stoplight Prism mock server from the OpenAPI spec. If the spec and the Prism version drift (new spec keywords, stricter validation), mock startup silently fails. There is no consumer-driven contract test (CDC) to detect Prism drift.

### B8 — MENA Compliance Scanner Not in CI

`test_mena_compliance.py` exists but is not wired into the CI pipeline. Compliance scanning is a business requirement (MENA market) but runs only locally.

### B9 — Exposed Credential in Repository

Per `agent_memory/validation-gate.md`: `scripts/close_validation_gate.py` contains an exposed GitHub token. This credential must be revoked and rotated. Storing credentials in source code is a critical security violation.

### B10 — No Multi-Tenant / RBAC Model

The system uses a single shared API key. There is no role-based access control. All authenticated users have identical permissions. For enterprise deployment (multi-team, audit requirements), this is a blocker.

---

## 10. Needed Enhancements

### NE1 — Fix requirements.txt Immediately

Add all missing runtime and test dependencies with pinned versions:
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
redis>=5.0.0
python-multipart>=0.0.9
click>=8.1.0
httpx>=0.27.0
pytest>=8.0.0
pytest-cov>=5.0.0
pytest-anyio>=0.0.0
anyio>=4.0.0
```
Remove the `pydantic==2.7.1` pin; use `pydantic>=2.7.0,<3.0.0` to allow minor upgrades.

### NE2 — Make Smoke Tests Block CI

Remove all `|| true` from `.github/workflows/ci.yml`. Tests that are expected to fail in certain environments (e.g., GPU tests) should be marked with `pytest.mark.skip` or `pytest.mark.requires_ollama` and excluded from the default run, not silently swallowed.

### NE3 — Enforce Coverage Threshold

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "--cov=cherenkov --cov-fail-under=60 --cov-report=xml"
```

### NE4 — Add conftest.py with Shared Fixtures

Create `/home/user/cherenkov-qa/tests/conftest.py`:
```python
import os, pytest

@pytest.fixture(autouse=True)
def dev_env(monkeypatch):
    monkeypatch.setenv("CHERENKOV_ENV", "development")

@pytest.fixture
def mock_llm(monkeypatch):
    # Inject a deterministic mock LLM for all chat/generate tests
    ...
```

### NE5 — Wire CodeQL into CI

Add a new job in `ci.yml` or in `security-scan.yml`:
```yaml
- uses: github/codeql-action/init@v3
  with:
    languages: python, javascript
- uses: github/codeql-action/analyze@v3
```

### NE6 — Migrate FastAPI `on_event` to Lifespan

**File:** `cherenkov/web/api.py:133`
Replace:
```python
@app.on_event("startup")
async def startup_event():
    ...
```
With:
```python
from contextlib import asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup code
    yield
    # shutdown code
app = FastAPI(lifespan=lifespan)
```

### NE7 — Fix Eject Endpoint Error Response

**File:** `cherenkov/web/api.py:541`
Return HTTP 500 on exception:
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

### NE8 — Add E2E Tests for MobileScreen and MobilePilotScreen

Add to `dashboard_e2e.spec.ts`:
- Navigate to MobileScreen, verify device list, trigger pilot
- Navigate to MobilePilotScreen, verify run controls, check status panel

### NE9 — Add Error Path E2E Tests

Add a dedicated `error_paths.spec.ts` that uses `api_mocks.ts` to inject error responses and verifies the UI handles them gracefully:
- 500 on `/api/v1/run` → shows error toast
- 404 on spec URL → shows validation message
- Network timeout → shows offline overlay

### NE10 — Add Multi-Viewport Playwright Config

Update `playwright.config.ts`:
```typescript
projects: [
  { name: 'desktop', use: { viewport: { width: 1280, height: 720 } } },
  { name: 'tablet',  use: { viewport: { width: 768,  height: 1024 } } },
  { name: 'mobile',  use: { viewport: { width: 375,  height: 667 }, isMobile: true } },
]
```

### NE11 — Replace Brittle Selectors with `data-testid`

Add `data-testid` attributes to all interactive elements in React components and update E2E tests to use `page.getByTestId()` instead of `#id` and `getByText()`.

### NE12 — Add API Integration Tests

Create `tests/integration/test_api_endpoints.py` using FastAPI's `TestClient`:
```python
from fastapi.testclient import TestClient
from cherenkov.web.api import app

client = TestClient(app)

def test_health_returns_200():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "status" in resp.json()
```
Implement for all 21 core endpoints.

### NE13 — Add Unit Tests for Core Untested Modules

Priority order:
1. `cherenkov/core/errors.py` — Error codes, retry behavior
2. `cherenkov/execution/trace_reader.py` — HAR parsing, assertion extraction
3. `cherenkov/execution/prism_mock.py` — Startup, CDC contract
4. `cherenkov/execution/k6_runner.py` — Script generation, threshold parsing
5. `cherenkov/execution/visual_diff.py` — Pixel diff algorithm
6. `cherenkov/core/feedback_store.py` — Concurrency safety

### NE14 — Revoke Exposed GitHub Token

Immediately revoke the token referenced in `scripts/close_validation_gate.py` via GitHub Settings → Developer settings → Personal access tokens. Replace with a GitHub Actions secret.

### NE15 — Add Accessibility Tests for All Screens

Extend `a11y.spec.ts` to run `injectAxe()` + `checkA11y()` on every screen, not just ProjectsScreen. Add focused tests for:
- ReviewScreen form label associations
- Drawer focus trap
- Toast announcements (`aria-live`)

---

## 11. Recommendations

### Priority 1 — Immediate (Blocks reliability)

| ID | Action | Effort | Impact |
|----|--------|--------|--------|
| T1 | Complete `requirements.txt` with all missing dependencies | 1h | Fixes 8 test failures |
| T2 | Remove `|| true` from all CI smoke test steps | 2h | Makes CI actually gate builds |
| B9 | Revoke exposed GitHub token in `scripts/close_validation_gate.py` | 30min | Security critical |
| T4 | Add `conftest.py` that sets `CHERENKOV_ENV=development` | 1h | Fixes mutation test failure |
| T5 | Wire mock LLM in chat test setup (monkeypatch substrate router) | 2h | Fixes 4 chat test failures |
| T6 | Fix path normalization in MCP tool (accept absolute paths) or fix test assertion | 30min | Fixes 1 test failure |

### Priority 2 — Short-term (Improves correctness detection)

| ID | Action | Effort | Impact |
|----|--------|--------|--------|
| T3 | Enforce `--cov-fail-under=60` in pytest config | 1h | Prevents silent regression |
| NE5 | Wire CodeQL into `.github/workflows/ci.yml` | 2h | Critical static security analysis |
| NE7 | Fix eject endpoint to return 500 on error | 30min | Corrects misleading success response |
| NE6 | Migrate `on_event` to `lifespan` in `api.py` | 1h | Removes deprecation before FastAPI drops it |
| NE12 | Create FastAPI integration tests for all endpoints | 3d | Covers 80% of untested endpoints |
| T13 | Create `conftest.py` with shared fixtures and env setup | 2h | Enables consistent test isolation |

### Priority 3 — Medium-term (Improves coverage depth)

| ID | Action | Effort | Impact |
|----|--------|--------|--------|
| NE8 | Add E2E for MobileScreen and MobilePilotScreen | 1d | Covers 2 untested screens |
| NE9 | Add error-path E2E tests (`error_paths.spec.ts`) | 2d | Covers zero-tested error flows |
| NE10 | Add multi-viewport Playwright projects | 1d | Enables responsive regression |
| NE11 | Add `data-testid` attributes; update selectors | 2d | Eliminates brittle E2E selectors |
| NE13 | Unit tests for 6 priority untested modules | 3d | Fills critical coverage gaps |
| B6 | Complete QA human validation gate (5 reviewers) | 1–2 weeks | Unblocks official certification |

### Priority 4 — Long-term (Enables scale)

| ID | Action | Effort | Impact |
|----|--------|--------|--------|
| NE15 | A11y tests for all 20 screens | 3d | Full WCAG 2.1 AA compliance |
| B10 | Implement RBAC (reviewer, admin, viewer roles) | 2 weeks | Enterprise readiness |
| T12 | Replace JSON feedback store with SQLite + file lock | 1d | Concurrency safety |
| B4 | Add knowledge graph quality metrics and tests | 1 week | RAG relevance assurance |
| NE3 | Raise coverage threshold to 80% in phases | Ongoing | Long-term quality floor |

---

## 12. Gap Heat Map

```
COMPONENT              UNIT   INT    E2E    CI-GATE   RISK
─────────────────────────────────────────────────────────
Core Orchestrator       ⚠️     ❌     ✅      ❌        HIGH
INGEST Stage            ❌     ❌     ⚠️      ❌        HIGH
PLAN Stage              ❌     ❌     ⚠️      ❌        HIGH
GENERATE Stage          ❌     ❌     ⚠️      ❌        HIGH
REVIEW Stage (6 gates)  ❌     ❌     ⚠️      ❌        HIGH
HITL Approve/Reject     ✅     ✅     ✅      ❌        LOW
HITL Classify           ❌     ❌     ❌      ❌        HIGH
Validate Engine         ⚠️     ❌     ✅      ❌        MEDIUM
Eject                   ❌     ❌     ✅      ❌        MEDIUM
Healing (all)           ❌     ❌     ⚠️      ❌        HIGH
API Endpoints           ❌     ❌     ⚠️      ❌        CRITICAL
Auth/HITL Auth          ⚠️     ❌     ❌      ❌        HIGH
WebSocket Events        ❌     ❌     ❌      ❌        HIGH
Dashboard - 18 screens  N/A    N/A    ⚠️      ❌        MEDIUM
Dashboard - Mobile (2)  N/A    N/A    ❌      ❌        HIGH
A11y - 18 screens       N/A    N/A    ❌      ❌        MEDIUM
Error Paths (all)       ❌     ❌     ❌      ❌        CRITICAL
Dependencies (reqs.txt) N/A    N/A    N/A     ❌        CRITICAL
CI Quality Gates        N/A    N/A    N/A     ❌        CRITICAL

Legend: ✅ Good  ⚠️ Partial  ❌ None/Broken
```

---

*Report generated by automated regression analysis on 2026-06-09.*
*Run command: `python -m pytest tests/ --ignore=tests/eject_fixtures -q`*
*Result: 16 failed, 245 passed, 9 skipped in 31.53 seconds*
