# Handoff & Review Report — M5 Backend API Wiring & Invariant Compliance

**Reviewer**: Reviewer 2 (`reviewer_m5_2`)  
**Working Directory**: `Z:\home\moaid\cherenkov-qa\.agents\reviewer_m5_2`  
**Verdict**: **REQUEST_CHANGES**  
**Overall Risk Level**: **HIGH** (Critical backend routing defect masking live API endpoints)

---

## Review Summary

- **Frontend API Wiring**: **PASS**. All 22 workspace components in `cherenkov/web/ui/src/components/workspaces/` route through `cherenkov/web/ui/src/lib/api.ts` (where `export const API_BASE = '/api/v1'`) and `AuthContext.tsx`. TypeScript validation (`.\node_modules\.bin\tsc --noEmit`) compiles cleanly with 0 errors.
- **SPA Catch-All Route & Backend Router Order**: **FAIL (CRITICAL)**. In `cherenkov/web/api.py` line 84, `static_router` (which contains `@router.get("/{full_path:path}")`) is mounted BEFORE 16 backend API routers. Starlette evaluates routes in order of inclusion, causing the `/{full_path:path}` catch-all to intercept requests intended for routes registered after line 84 (such as `/api/v1/health`, `/api/v1/overview`, `/api/v1/projects`, `/api/v1/review/queue`, `/api/v1/divergences`, `/api/v1/mobile/*`). The catch-all executes line 31 of `static_routes.py` (`if full_path.startswith("api/"): raise HTTPException(status_code=404, detail="API endpoint not found")`), returning 404 for all subsequent API endpoints and causing 14 integration test failures in `pytest tests/integration/test_api_endpoints.py`.
- **Invariant Compliance**:
  - **Invariant D7 (No Auto-Editing Test Code)**: **PASS**. `SandboxHealer` (`cherenkov/healing/sandbox_healer.py`) operates strictly in isolated sandbox directories, writing unified diffs to `.cherenkov/healed_diffs/*.diff`. It never overwrites or auto-edits original test files.
  - **Anti-Lock-In Invariant**: **PASS**. `EjectorEngine` (`cherenkov/execution/eject.py`) generates clean, standalone Playwright test projects with `client.ts` free of CHERENKOV dependencies or monkeypatching hooks.
  - **Spec-Derived Invariant**: **PASS**. `_infer_expected_status` (`cherenkov/coverage/emitter.py`) and scenario generators derive expected HTTP status codes directly from the OpenAPI spec responses section (`operation.get("responses", {})`).

---

## 1. Observation

1. **Frontend Workspace Endpoint Mappings**:
   - `cherenkov/web/ui/src/lib/api.ts`: Line 13 defines `export const API_BASE = '/api/v1'`. All workspace components (`AuthoringWorkspace`, `DashboardWorkspace`, `IntelligenceWorkspace`, `SettingsWorkspace`, `TriageWorkspace`) import helper functions from `lib/api.ts` (e.g. `fetchDoctor`, `runPipeline`, `ingestSpec`, `fetchProjects`, `fetchOverviewData`, `fetchRuns`, `queryKnowledge`, `fetchSddStatus`, `createChatSession`, `fetchHealth`, `ejectSuite`, `fetchSettings`, `fetchDivergences`, `fetchReviewQueue`).
   - Terminal Command: `.\node_modules\.bin\tsc --noEmit` in `cherenkov/web/ui`
   - Result: Exit code 0, 0 TypeScript errors.

2. **SPA Catch-All Route Implementation & Router Order Defect**:
   - `cherenkov/web/routes/static_routes.py`:
     ```python
     29: @router.get("/{full_path:path}")
     30: async def serve_spa_fallback(full_path: str):
     31:     if full_path.startswith("api/"):
     32:         raise HTTPException(status_code=404, detail="API endpoint not found")
     ```
   - `cherenkov/web/api.py`:
     ```python
     82: from cherenkov.web.routes.static_routes import router as static_router
     83: 
     84: app.include_router(static_router)
     85: 
     86: from cherenkov.web.routes.data_routes import router as data_router
     87: app.include_router(data_router)
     88: 
     90: from cherenkov.web.routes.health_routes import router as health_router
     91: app.include_router(health_router)
     ...
     102: from cherenkov.web.routes.workspace_routes import router as workspace_router
     104: app.include_router(workspace_router)
     ```
   - Terminal Command: `python -m pytest tests/integration/test_api_endpoints.py`
   - Result: 14 test failures out of 38 tests with `AssertionError: 404 != 200`.
   - Specific Failing Tests:
     - `TestHealth::test_health_200`
     - `TestHealth::test_health_degrades_gracefully_on_ollama_error`
     - `TestListTests::test_empty_when_no_generated_tests`
     - `TestListTests::test_returns_spec_files_in_generated_tests_dir`
     - `TestReviewQueue::test_queue_returns_list`
     - `TestReviewQueue::test_queue_serialises_items`
     - `TestReviewQueue::test_queue_serialises_reject_reason`
     - `TestReviewQueue::test_queue_status_all_bypasses_filter`
     - `TestReviewQueue::test_queue_surfaces_stored_reject_reason`
     - `TestDivergences::test_list_returns_list`
     - `TestDashboardEndpoints::test_failures_200`
     - `TestDashboardEndpoints::test_overview_200`
     - `TestDashboardEndpoints::test_truth_map_200`
     - `TestMobilePilot::test_status_returns_idle_by_default`

3. **Empirical Direct Test of FastAPI Router Evaluation**:
   - Terminal Command: `python -c "from fastapi.testclient import TestClient; from cherenkov.web.api import app; client = TestClient(app); print('health:', client.get('/api/v1/health').status_code); print('overview:', client.get('/api/v1/overview').status_code); print('projects:', client.get('/api/v1/projects').status_code)"`
   - Result:
     ```
     health: 404
     overview: 404
     projects: 404
     ```

4. **Invariant D7 Check**:
   - `cherenkov/healing/sandbox_healer.py`: Line 176 writes diffs to `.cherenkov/healed_diffs/{scenario_id}.diff`. Original test spec files in `stub/generated_tests/` are read-only inputs for diff generation; zero auto-editing or writeback to original test files occurs.

5. **Anti-Lock-In Check**:
   - `cherenkov/execution/eject.py`: `EjectorEngine.eject_suite` generates standalone `client.ts` with standard `openapi-fetch` client and standard `playwright.config.ts`, removing all CHERENKOV metadata and hooks.

---

## 2. Logic Chain

1. **Observation 1 & 3** prove that while frontend React components correctly construct `/api/v1/*` endpoint requests, incoming HTTP requests to `/api/v1/health`, `/api/v1/overview`, `/api/v1/projects`, `/api/v1/review/queue`, and `/api/v1/divergences` receive HTTP 404 responses from the backend server.
2. **Observation 2** identifies the root cause: Starlette/FastAPI matches incoming URL paths sequentially against registered application routes.
3. Because `static_router` is included at line 84 of `cherenkov/web/api.py`, its catch-all handler `@router.get("/{full_path:path}")` takes precedence over all API routers included on lines 88–154.
4. When any request starting with `/api/` (e.g. `/api/v1/health`) reaches `serve_spa_fallback`, line 31 explicitly executes `if full_path.startswith("api/"): raise HTTPException(status_code=404, detail="API endpoint not found")`.
5. Therefore, mounting `static_router` before API endpoint routers masks all subsequent API routes, preventing live UI components and tests from accessing backend endpoints.

---

## 3. Caveats

- **Physical Mobile Device Testing**: Physical Android/iOS device execution was not tested as per the track status (Phase 5-6 tools installed; live runs require physical device/emulator). Mobile API endpoints were verified via route code inspection and test suite execution.
- **No Code Editing Constraint**: As a Reviewer agent, no implementation code in `cherenkov/web/api.py` was altered during this review. The fix must be applied by an implementer.

---

## 4. Conclusion

- **Verdict**: **REQUEST_CHANGES**
- **Action Item for Implementer**: In `cherenkov/web/api.py`, move `app.include_router(static_router)` to the VERY END of router inclusions (after line 154, following `integrity_router`), so that all specific API endpoint routes are registered first. `static_router` must serve as the final catch-all fallback for SPA client-side routing.

---

## 5. Verification Method

To independently verify the fix:

1. **Run Integration API Test Suite**:
   ```powershell
   python -m pytest tests/integration/test_api_endpoints.py
   ```
   *Expected Result after fix*: 38 passed, 0 failed.

2. **Probe API Endpoints via TestClient**:
   ```powershell
   python -c "from fastapi.testclient import TestClient; from cherenkov.web.api import app; client = TestClient(app); print('health:', client.get('/api/v1/health').status_code); print('overview:', client.get('/api/v1/overview').status_code); print('projects:', client.get('/api/v1/projects').status_code)"
   ```
   *Expected Result after fix*: Status codes should return `200` (or `401` if auth required), NOT `404`.

3. **Verify Frontend TypeScript Compilation**:
   ```powershell
   cd cherenkov/web/ui; .\node_modules\.bin\tsc --noEmit
   ```
   *Expected Result*: Exit code 0, 0 errors.

---

## Findings Summary

### [Critical] Finding 1: `static_router` Included Prematurely in `cherenkov/web/api.py` Masking API Routes

- **What**: `static_router` containing `/{full_path:path}` catch-all fallback is included at line 84 of `cherenkov/web/api.py`, preceding 16 backend API routers.
- **Where**: `cherenkov/web/api.py`: line 84
- **Why**: Starlette route resolution order matches `/{full_path:path}` first for all GET requests, intercepting `/api/v1/*` routes added after line 84 and throwing `HTTPException(404)`.
- **Suggestion**: Move `app.include_router(static_router)` to the bottom of `cherenkov/web/api.py` after `integrity_router`.

---

## Verified Claims Matrix

| Claim | Verification Method | Status | Details |
|---|---|---|---|
| Frontend components connect to `/api/v1/*` | Code inspection of 22 workspace components & `lib/api.ts` | **PASS** | `API_BASE = '/api/v1'` used consistently across all requests |
| Frontend TypeScript compilation | `.\node_modules\.bin\tsc --noEmit` | **PASS** | 0 errors |
| Invariant D7 Compliance | Inspection of `cherenkov/healing/sandbox_healer.py` | **PASS** | Isolated sandboxes used; outputs diffs only; original files untouched |
| Anti-Lock-In Invariant Compliance | Inspection of `cherenkov/execution/eject.py` | **PASS** | Ejects standard `@playwright/test` suites with no CHERENKOV imports |
| Spec-Derived Logic Invariant | Inspection of `cherenkov/coverage/emitter.py` | **PASS** | Expected HTTP status derived from OpenAPI spec responses |
| Backend Endpoint Connectivity | `pytest tests/integration/test_api_endpoints.py` & TestClient probe | **FAIL** | 14 tests fail with 404 due to `static_router` ordering bug |

---

## Challenge & Attack Surface Summary

- **Scenario**: Requesting live backend endpoints (`/api/v1/health`, `/api/v1/overview`, `/api/v1/projects`) when SPA fallback router is mounted before API routers.
- **Actual Behavior**: Returns 404 HTTP Exception from `static_routes.py`.
- **Mitigation**: Re-order `app.include_router(static_router)` to be the last route handler in `cherenkov/web/api.py`.
