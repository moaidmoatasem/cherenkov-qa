import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./generated_tests",
  testIgnore: process.env.RUN_VISUAL_TESTS ? [] : ["**/visual_regression_baseline_ui.spec.ts"],
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || "./test-results",
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.API_URL ?? "http://localhost:8000",
    trace: "on-first-retry",
  },
});
