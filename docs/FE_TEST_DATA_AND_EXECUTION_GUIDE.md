# Cherenkov QA Dashboard - Test Data & Execution Guide

> **Document Version:** 1.0.0  
> **Last Updated:** 2026-06-06  
> **Owner:** QA Engineering Team  
> **Purpose:** Supplementary guide with test data, execution details, and implementation notes

---

## Table of Contents

1. [Detailed Test Data](#1-detailed-test-data)
2. [Test Environment Configuration](#2-test-environment-configuration)
3. [Test Implementation Notes](#3-test-implementation-notes)
4. [CI/CD Integration](#4-cicd-integration)
5. [Test Reporting & Metrics](#5-test-reporting--metrics)
6. [Troubleshooting Guide](#6-troubleshooting-guide)

---

## 1. Detailed Test Data

### 1.1 Project Data Structure

The dashboard works with the following project structure from `mockData.ts`:

```typescript
// Project Interface
export interface Project {
  id: string;                           // Unique identifier (e.g., 'proj-petstore')
  name: string;                        // Display name (e.g., 'Swagger Petstore v2')
  lastRun: string;                     // Timestamp (e.g., '2 hours ago')
  pipelineStatus: {                     // Status of each pipeline stage
    ingest: 'done' | 'running' | 'queued' | 'failed';
    plan: 'done' | 'running' | 'queued' | 'failed';
    generate: 'done' | 'running' | 'queued' | 'failed';
    review: 'done' | 'running' | 'queued' | 'failed';
    visual?: 'done' | 'running' | 'queued' | 'failed';
    perf?: 'done' | 'running' | 'queued' | 'failed';
  };
  stats: {                              // Project statistics
    testsCount: number;                // Total number of tests
    passRate: number;                  // Percentage (0-100)
    healingCount: number;              // Number of healing suggestions
  };
  sparkline: number[];                 // Array of pass rates over last runs
  lastRunDuration?: {                  // Optional duration info
    durationMs: number;                // Actual duration in milliseconds
    limitMs: number;                  // Time limit in milliseconds
  };
}
```

### 1.2 Initial Projects Data

```typescript
// From mockData.ts
export const INITIAL_PROJECTS: Project[] = [
  {
    id: 'proj-petstore',
    name: 'Swagger Petstore v2',
    lastRun: '2 hours ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'done'
    },
    stats: {
      testsCount: 47,
      passRate: 91,
      healingCount: 3
    },
    sparkline: [75, 80, 82, 88, 91, 91],
    lastRunDuration: { durationMs: 14800, limitMs: 20000 }
  },
  {
    id: 'proj-checkout-api',
    name: 'Checkout Gateway API',
    lastRun: '1 day ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'done'
    },
    stats: {
      testsCount: 32,
      passRate: 84,
      healingCount: 1
    },
    sparkline: [90, 88, 85, 84, 84],
    lastRunDuration: { durationMs: 8400, limitMs: 15000 }
  },
  {
    id: 'proj-auth-identity',
    name: 'Identity Provider OAuth',
    lastRun: '3 days ago',
    pipelineStatus: {
      ingest: 'done',
      plan: 'done',
      generate: 'done',
      review: 'failed'
    },
    stats: {
      testsCount: 18,
      passRate: 61,
      healingCount: 4
    },
    sparkline: [80, 78, 70, 65, 61],
    lastRunDuration: { durationMs: 28200, limitMs: 30000 }
  }
];
```

### 1.3 Endpoint Richness Data

```typescript
// EndpointRichness Interface
export interface EndpointRichness {
  id: string;                           // Unique endpoint identifier
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;                        // API endpoint path
  richness: number;                    // 0.0 to 1.0
  band: 'full' | 'inferred' | 'degraded';
  missingElements: string[];           // Array of missing specification elements
}

// Sample endpoints from mockData.ts
export const MOCK_ENDPOINTS: EndpointRichness[] = [
  { id: 'ep-1', method: 'POST', path: '/pets', richness: 0.95, band: 'full', missingElements: [] },
  { id: 'ep-2', method: 'GET', path: '/pets/{petId}', richness: 0.88, band: 'full', missingElements: [] },
  { id: 'ep-3', method: 'PUT', path: '/pets', richness: 0.72, band: 'full', 
    missingElements: ['missing 400 response model details'] },
  { id: 'ep-4', method: 'DELETE', path: '/pets/{petId}', richness: 0.55, band: 'inferred', 
    missingElements: ['missing 404 error schema'] },
  { id: 'ep-5', method: 'POST', path: '/pets/{petId}/uploadImage', richness: 0.42, band: 'degraded', 
    missingElements: ['empty multipart/form-data detail', 'missing 2xx response template'] },
  // ... 15 more endpoints
];
```

### 1.4 Pipeline Stages Data

```typescript
// PipelineStage Interface
export interface PipelineStage {
  id: StageId;                           // 'ingest' | 'plan' | 'generate' | 'review' | 'visual' | 'perf'
  name: string;                        // Display name
  status: 'done' | 'running' | 'queued' | 'failed';
  summary: string;                     // Stage summary
}

type StageId = 'ingest' | 'plan' | 'generate' | 'review' | 'visual' | 'perf';
```

### 1.5 Test Items Data

```typescript
// TestGate Interface
export interface TestGate {
  syntax: boolean;
  structure: boolean;
  ast: boolean;
  novelty: boolean;
  dryRun: boolean;
  quality: boolean;
}

// TestItem Interface
export interface TestItem {
  id: string;
  name: string;
  path: string;
  method: string;
  confidence: number;                 // 0 to 1
  verdict: 'approved' | 'review' | 'regenerating' | 'rejected';
  gates: TestGate;
  gateReasons: { [key in keyof TestGate]?: string };
  code: string;
  actualResult?: {
    status: 'passed' | 'failed';
    stdout: string;
    duration: string;
  };
}

// Sample test item
{
  id: 'test-001',
  name: 'POST /pets - Creates a Pet',
  path: '/pets',
  method: 'POST',
  confidence: 0.95,
  verdict: 'approved',
  gates: {
    syntax: true,
    structure: true,
    ast: true,
    novelty: true,
    dryRun: true,
    quality: true
  },
  gateReasons: {},
  code: `import { test, expect } from '@playwright/test';...`
}
```

### 1.6 Failing Test Data

```typescript
// FailingTest Interface
export interface FailingTest {
  id: string;
  name: string;
  failureType: 'CONTRACT_DRIFT' | 'AUTH_EXPIRY' | 'STATE_SEQUENCING' | 'NETWORK_FLAKY' | 'ASSERTION_DRIFT';
  diagnosis: string;
  oldCode: string;
  proposedCode: string;
  hasAssertionWarning?: boolean;
}

// Failure types:
// - CONTRACT_DRIFT: API contract has changed
// - AUTH_EXPIRY: Authentication token expired
// - STATE_SEQUENCING: Test state sequence issue
// - NETWORK_FLAKY: Network instability
// - ASSERTION_DRIFT: Assertion no longer valid
```

### 1.7 Divergence Data

```typescript
// Divergence Interface
export interface Divergence {
  id: string;
  divergenceClass: 'D1' | 'D2' | 'D3' | 'D4' | 'D5';
  endpoint: string;
  severity: SeverityType;             // 'critical' | 'high' | 'medium' | 'low' | 'info'
  status: StatusType;                // 'reproduced' | 'pending' | 'rejected' | 'live'
  claimA: string;
  claimB: string;
  evidence: string;
  reproSteps: string;
  confidence?: number;
}

type SeverityType = 'critical' | 'high' | 'medium' | 'low' | 'info';
type StatusType = 'reproduced' | 'pending' | 'rejected' | 'live';

// Divergence Classes:
// - D1: Specification inconsistency
// - D2: Implementation drift
// - D3: Response format mismatch
// - D4: Error handling discrepancy
// - D5: Performance characteristic anomaly
```

---

## 2. Test Environment Configuration

### 2.1 Backend Configuration

The backend API is configured in `cherenkov/web/ui/src/lib/api.ts`:

```typescript
export const API_BASE = '/api/v1';

// In development, Vite proxies /api/v1/* to http://127.0.0.1:8000/api/v1/*
// In production, static files and API are hosted under same origin
```

### 2.2 Playwright Configuration

From `cherenkov/web/ui/playwright.config.ts`:

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    trace: 'on-first-retry',
    baseURL: 'http://localhost:5173',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
});
```

### 2.3 Environment Variables

```bash
# .env.example
VITE_API_BASE=/api/v1
VITE_BACKEND_URL=http://localhost:8000
VITE_DEMO_MODE=false
VITE_GEN_MODEL=qwen2.5-coder:7b
```

---

## 3. Test Implementation Notes

### 3.1 Test File Structure

```
cherenkov/web/ui/tests/
├── a11y.spec.ts           # Accessibility tests
├── dashboard_e2e.spec.ts # Main E2E test suite
└── fixtures/             # (Optional) Test fixtures
```

### 3.2 Existing Test Coverage

The `dashboard_e2e.spec.ts` file already covers:
- Projects screen (PRJ-001 to PRJ-012)
- Overview screen (OVR-001 to OVR-003)
- Truth Map screen (TM-001 to TM-003)
- Divergences screen (DIV-001 to DIV-004)
- Author screen (AUT-001 to AUT-003)
- Signals screen (SIG-001 to SIG-003)
- Memory screen (MEM-001)
- Governance screen (GOV-001 to GOV-002)
- Setup screen (SET-001 to SET-009)
- Pipeline screen (PIP-001 to PIP-010)
- Review screen (REV-001 to REV-011)
- Healing screen (HEL-001 to HEL-003)
- Eject screen (EJT-001 to EJT-008)
- Settings screen (SETT-001 to SETT-015)
- Explore screen (EXP-001)
- UI Kit screen (UIK-001 to UIK-009)
- Sidebar (SB-001 to SB-007)
- TopBar (TB-001 to TB-008)
- Command Palette (CP-001 to CP-002)
- Settings persistence (SETT-001)

### 3.3 Test Hooks and Utilities

```typescript
// From dashboard_e2e.spec.ts
const SETTLEMENT = 500; // ms to wait for UI to settle

test.beforeEach(async ({ page }) => {
  page.on('console', msg => {
    console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
  });
  page.on('pageerror', err => {
    console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
  });

  // Dismiss Guided Tour for consistent testing
  await page.goto('/');
  await page.evaluate(() => localStorage.setItem('[copilot] tour_seen', 'true'));
  await page.reload();
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(SETTLEMENT);
});
```

### 3.4 Selector Conventions

| Element | Selector Type | Example |
|---------|---------------|---------|
| Screen containers | `#{screen-name}-screen` | `#projects-screen`, `#review-screen` |
| Project cards | `#project-card-{id}` | `#project-card-proj-petstore` |
| Timer bars | `#timer-bar-{id}` | `#timer-bar-proj-petstore` |
| Navigation items | `#nav-item-{name}` | `#nav-item-overview`, `#nav-item-review` |
| Buttons | `#btn-{action}` | `#btn-projects-new-run`, `#btn-confirm-eject` |
| Input fields | `#input-{name}` | `#spec-url-input`, `#eject-path` |
| Filter tabs | `#filter-tab-{status}` | `#filter-tab-all`, `#filter-tab-approved` |
| Pipeline nodes | `#pipeline-node-{stage}` | `#pipeline-node-ingest`, `#pipeline-node-review` |
| Divergence rows | Text-based | `page.getByText('D-').first()` |

---

## 4. CI/CD Integration

### 4.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Cherenkov FE Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *' # Run nightly at 2 AM

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        browser: [chromium, firefox, webkit]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: '20'
    
    - name: Install dependencies
      run: |
        cd cherenkov/web/ui
        npm ci
    
    - name: Install Playwright browsers
      run: npx playwright install --with-deps
    
    - name: Start backend
      run: |
        cd cherenkov
        python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
    
    - name: Start frontend
      run: |
        cd cherenkov/web/ui
        npm run dev &
    
    - name: Run smoke tests
      run: npx playwright test --browser ${{ matrix.browser }} --grep "@smoke"
    
    - name: Run critical tests
      run: npx playwright test --browser ${{ matrix.browser }} --grep "@critical"
    
    - name: Upload test results
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: playwright-results-${{ matrix.browser }}
        path: cherenkov/web/ui/test-results/
```

### 4.2 Test Tagging System

Use Playwright's `@tag` annotation to categorize tests:

```typescript
// Smoke tests - quick sanity checks
test('Projects screen loads', { tag: '@smoke' }, async ({ page }) => { ... });

// Critical tests - must pass for deployment
test('Pipeline execution works', { tag: '@critical' }, async ({ page }) => { ... });

// Functional tests - component/screen functionality
test('Review queue filtering', { tag: '@functional' }, async ({ page }) => { ... });

// API integration tests
test('Backend health check', { tag: '@api' }, async ({ page }) => { ... });

// Accessibility tests
test('Keyboard navigation', { tag: '@a11y' }, async ({ page }) => { ... });

// Performance tests
test('Page load performance', { tag: '@performance' }, async ({ page }) => { ... });
```

Run specific tags:
```bash
npx playwright test --grep "@smoke"
npx playwright test --grep "@smoke|@critical"
npx playwright test --grep "@api"
```

### 4.3 Parallel Test Execution

Playwright supports parallel test execution:

```bash
# Run all tests in parallel
npx playwright test

# Run with specific number of workers
npx playwright test --workers 4

# Run sequentially
npx playwright test --workers 1
```

---

## 5. Test Reporting & Metrics

### 5.1 Report Types

| Report Type | File | Purpose |
|-------------|------|---------|
| HTML Report | `test-results/index.html` | Interactive test report |
| JSON Report | `test-results/results.json` | Machine-readable results |
| JUnit Report | `test-results/results.xml` | CI/CD integration |
| Trace Viewer | `test-results/trace/` | Debug failed tests |

### 5.2 Generate Reports

```bash
# Generate HTML report (default)
npx playwright test

# Generate multiple report formats
npx playwright test --reporter=html,json,junit

# Open HTML report
npx playwright show-report

# Open trace viewer for specific test
npx playwright show-report test-results/trace.zip
```

### 5.3 Test Metrics Dashboard

Create a metrics dashboard with:

```json
{
  "totalTests": 700,
  "passed": 650,
  "failed": 50,
  "skipped": 0,
  "flaky": 5,
  "passRate": "92.86%",
  "executionTime": "28m 45s",
  "coverage": {
    "screens": "100%",
    "components": "95%",
    "workflows": "90%",
    "api": "85%"
  },
  "byPriority": {
    "critical": { "total": 80, "passed": 78, "failed": 2 },
    "high": { "total": 200, "passed": 190, "failed": 10 },
    "medium": { "total": 350, "passed": 330, "failed": 20 },
    "low": { "total": 30, "passed": 30, "failed": 0 }
  },
  "byCategory": {
    "smoke": { "total": 15, "passed": 15, "failed": 0 },
    "functional": { "total": 350, "passed": 325, "failed": 25 },
    "api": { "total": 40, "passed": 38, "failed": 2 },
    "a11y": { "total": 20, "passed": 18, "failed": 2 },
    "performance": { "total": 15, "passed": 14, "failed": 1 }
  },
  "flakyTests": [
    { "id": "PIP-004", "description": "DAG edges sometimes invisible", "count": 3 },
    { "id": "A11Y-CC-001", "description": "Color contrast varies by theme", "count": 2 }
  ]
}
```

### 5.4 Test Trend Analysis

Track metrics over time:
- **Pass Rate Trend:** Weekly pass rate percentages
- **Failure Rate:** Number of failures per run
- **Flaky Tests:** Tests that pass/fail inconsistently
- **Execution Time:** Average and max test execution times
- **Coverage Growth:** New test cases added per sprint

---

## 6. Troubleshooting Guide

### 6.1 Common Issues

#### Issue: Tests flaky due to timing

**Symptoms:** Tests pass locally but fail in CI, or pass/fail randomly

**Solutions:**
1. Increase wait times: `await page.waitForTimeout(1000)`
2. Use proper selectors: Wait for specific elements to be visible
3. Add retry logic:
```typescript
test('Flaky test', async ({ page }) => {
  await test.step('Step 1', async () => {
    await page.click('#button');
  });
  
  await test.step('Step 2 with retry', async () => {
    await expect(page.locator('#result')).toBeVisible({ timeout: 10000 });
  });
});
```
4. Use Playwright's auto-retry:
```typescript
npx playwright test --retries 2
```

#### Issue: Backend not available

**Symptoms:** API tests fail, offline overlay shown

**Solutions:**
1. Ensure backend is running: `python -m uvicorn main:app --port 8000`
2. Check backend health: `curl http://localhost:8000/api/v1/health`
3. Use mock data for frontend-only tests
4. Implement backend health check in tests:
```typescript
test.beforeAll(async () => {
  const response = await fetch('http://localhost:8000/api/v1/health');
  if (!response.ok) {
    test.skip('Backend not available', () => {});
  }
});
```

#### Issue: Tests fail in CI but pass locally

**Symptoms:** Tests work on developer machine but fail in CI environment

**Solutions:**
1. Check browser differences (headless vs headed)
2. Verify viewport sizes match
3. Ensure same Node.js version
4. Check environment variables
5. Add debugging to CI:
```yaml
- name: Debug CI environment
  run: |
    node --version
    npm --version
    npx playwright --version
    echo "Display: $DISPLAY"
```

#### Issue: Memory leaks in long-running tests

**Symptoms:** Tests slow down over time, browser crashes

**Solutions:**
1. Use `test.afterEach` to clean up:
```typescript
test.afterEach(async ({ page }) => {
  await page.close();
});
```
2. Limit parallel workers:
```bash
npx playwright test --workers 2
```
3. Use separate browsers for different test suites
4. Monitor memory usage with:
```bash
npx playwright test --debug
```

### 6.2 Debugging Tests

#### Enable Debug Mode

```bash
npx playwright test --debug
```

This opens Playwright Inspector with:
- Test execution visualization
- Live DOM inspection
- Console logs
- Network requests

#### Run with Headed Browser

```bash
npx playwright test --headed
```

#### Pause Test Execution

```typescript
test('Debug test', async ({ page }) => {
  // Pause here - Playwright will open inspector
  await page.pause();
  
  // Continue execution
  await page.click('#button');
});
```

#### Take Screenshots on Failure

```typescript
// In playwright.config.ts
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

#### Generate Trace on Failure

```bash
npx playwright test --trace on
```

View trace with:
```bash
npx playwright show-trace trace.zip
```

### 6.3 Performance Issues

#### Slow Test Execution

**Solutions:**
1. Reduce `waitForTimeout` calls - use element-based waits instead
2. Disable animations in tests:
```typescript
test.beforeEach(async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
});
```
3. Parallelize tests across multiple workers
4. Use test isolation to avoid shared state

#### Slow Page Loads

**Solutions:**
1. Mock API responses for development:
```typescript
// In tests, mock fetch calls
await page.route('**/api/v1/**', route => route.fulfill({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(mockData)
}));
```
2. Use cached responses:
```typescript
const response = await page.request.get('http://localhost:8000/api/v1/projects');
const data = await response.json();
// Cache and reuse
```

### 6.4 Test Data Issues

#### Inconsistent Mock Data

**Solutions:**
1. Centralize mock data in test fixtures:
```typescript
// tests/fixtures/mockData.ts
export const mockProjects = [ ... ];
export const mockEndpoints = [ ... ];
```
2. Reset state before each test:
```typescript
test.beforeEach(async ({ page }) => {
  // Reset mock data
  await page.evaluate(() => {
    localStorage.clear();
  });
});
```
3. Use unique test data for each test to avoid conflicts

#### Missing Test Data

**Solutions:**
1. Create test data generators:
```typescript
function generateTestProject(overrides = {}) {
  return {
    id: `test-proj-${Date.now()}`,
    name: 'Test Project',
    lastRun: 'just now',
    pipelineStatus: { ingest: 'done', plan: 'done', generate: 'done', review: 'done' },
    stats: { testsCount: 10, passRate: 100, healingCount: 0 },
    sparkline: [100],
    ...overrides
  };
}
```
2. Use real API when possible (for integration tests)

---

## Quick Reference

### Test Counts by Category

| Category | Test Count | File | Priority |
|----------|------------|------|----------|
| Screens | 150 | dashboard_e2e.spec.ts | High |
| Components | 100 | dashboard_e2e.spec.ts | Medium |
| Workflows | 50 | New file needed | Critical |
| API | 40 | New file needed | High |
| Accessibility | 20 | a11y.spec.ts | High |
| Performance | 15 | New file needed | Medium |
| Error Handling | 30 | New file needed | High |
| Edge Cases | 20 | New file needed | Medium |
| **Total** | **425** | | |

### Recommended Test Files Structure

```
cherenkov/web/ui/tests/
├── smoke.spec.ts               # 15 smoke tests
├── screens/
│   ├── projects.spec.ts        # Projects screen tests
│   ├── review.spec.ts          # Review screen tests
│   ├── pipeline.spec.ts        # Pipeline screen tests
│   └── ...
├── components/
│   ├── topbar.spec.ts          # TopBar component tests
│   ├── sidebar.spec.ts         # Sidebar component tests
│   └── ...
├── workflows/
│   ├── test_generation.spec.ts # Test generation workflow
│   ├── review_approval.spec.ts # Review & approval workflow
│   └── ...
├── api/
│   ├── health.spec.ts           # Health API tests
│   ├── pipeline.spec.ts         # Pipeline API tests
│   └── ...
├── accessibility/
│   └── a11y.spec.ts             # Accessibility tests
├── performance/
│   └── perf.spec.ts             # Performance tests
└── fixtures/
    ├── mockData.ts              # Test data fixtures
    ├── utils.ts                 # Test utilities
    └── selectors.ts             # Selector constants
```

---

*Generated for Cherenkov QA Dashboard Full Regression Test Suite*
*Supplementary guide with detailed test data, execution instructions, and troubleshooting*
