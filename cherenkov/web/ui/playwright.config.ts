import { defineConfig, devices } from '@playwright/test';

const ALL_VIEWPORTS = !!process.env.ALL_VIEWPORTS;

export default defineConfig({
  testDir: './tests',
  testMatch: /.*\.spec\.ts/,
  // Archived legacy specs: these target screens removed in the UI revamp
  // (SetupScreen, ReviewScreen, HealingScreen, Sidebar, TopBar, ...). Files are
  // kept in the tree for reference but are excluded from all runs. The live
  // suites are tests/e2e/*-workspace.spec.ts, tests/qa/headless-qa-user.spec.ts
  // and tests/qa/e2e-journeys.spec.ts (rewritten against the journey-driven IA
  // and no longer archived).
  testIgnore: [
    // 'tests/dashboard_e2e.spec.ts' was deleted in e6b1fc3 and replaced by
    // tests/e2e/new_dashboard.spec.ts; the ignore entry outlived the file.
    'tests/sdd_cockpit.spec.ts',
    'tests/qa/api-contract-integration.spec.ts',
    'tests/qa/functional-suite.spec.ts',
    'tests/qa/nonfunctional-suite.spec.ts',
    'tests/qa/settings_custom_journey.spec.ts',
    'tests/qa/smoke-regression-exploratory.spec.ts',
  ],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  timeout: 90000,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    ...(ALL_VIEWPORTS
      ? [
          {
            name: 'firefox',
            use: { ...devices['Desktop Firefox'] },
          },
          {
            name: 'mobile-chrome',
            use: { ...devices['Pixel 5'] },
          },
        ]
      : []),
  ],
  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
