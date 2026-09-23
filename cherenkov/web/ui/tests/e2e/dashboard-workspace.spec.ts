import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

// VerdictHistoryTable renders an EmptyState, not a <table>, until at least
// one run has been persisted (VerdictHistoryTable.tsx: `runs.length === 0`)
// — true of any freshly started backend. Seed one through the same RunStore
// class the `verify`/`validate`/`certify` CLI commands write through
// (cherenkov/persistence/run_store.py), same pattern as the HITL seed in
// triage-workspace.spec.ts, rather than a test-only REST endpoint.
const SEED_RUN_ID = 'e2e_dashboard_seed_run';

function seedRun() {
  execFileSync('python3', [
    '-c',
    `
from cherenkov.persistence.run_store import RunRecord, get_run_store
get_run_store().save(RunRecord(
    run_id="${SEED_RUN_ID}", command="verify", target_url="https://e2e-seed.example",
    verdict="PASS", divergence_count=0, coverage_pct=100.0, duration_ms=1200,
))
`,
  ]);
}

function deleteRun() {
  execFileSync('python3', [
    '-c',
    `
import os, sqlite3
from pathlib import Path
db_path = os.environ.get("CHERENKOV_RUNS_DB") or str(Path.home() / ".cherenkov" / "runs.db")
con = sqlite3.connect(db_path)
con.execute("DELETE FROM runs WHERE run_id = ?", ("${SEED_RUN_ID}",))
con.commit()
`,
  ]);
}

test.describe('Dashboard Workspace E2E Suite', () => {
  test.beforeAll(() => {
    seedRun();
  });

  test.afterAll(() => {
    deleteRun();
  });

  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.waitForTimeout(SETTLE);
  });

  test('AppHeader renders brand, project dropdown, and backend health status badge', async ({ page }) => {
    // Previously asserted a "Tokens:" text label. AppHeader takes a
    // `tokenUsagePercent` prop but never renders it anywhere in the
    // component — there is no token-budget UI at all, text or ring, despite
    // HANDOVER.md's 2026-08-20 entry describing it as a ring. Whether to
    // wire the prop up or drop it is a product call, not made here; this
    // test now only checks the header chrome that actually exists.
    await expect(page.locator('header')).toBeVisible();
    await expect(page.getByText('CHERENKOV').first()).toBeVisible();
    await expect(page.getByTestId('project-selector-dropdown')).toBeVisible();
    await expect(page.getByTestId('backend-health-badge')).toBeVisible();
  });

  test('NavigationBar renders 5 core workspace navigation links and new analysis button', async ({ page }) => {
    const nav = page.locator('nav').first();
    await expect(nav).toBeVisible();
    await expect(page.getByTestId('nav-new-analysis-btn')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-dashboard')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-authoring')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-triage')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-intelligence')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-settings')).toBeVisible();
  });

  test('Workspace switching to Dashboard displays Dashboard Workspace container', async ({ page }) => {
    await page.getByTestId('nav-workspace-dashboard').click();
    await page.waitForTimeout(SETTLE);
    await expect(page.locator('#dashboard-workspace')).toBeVisible();
    await expect(page.locator('#dashboard-workspace').getByRole('heading', { name: 'Dashboard', level: 1 })).toBeVisible();
  });

  test('ReleaseReadinessCard renders KPI score ring, verdict grade, and queue counts', async ({ page }) => {
    const card = page.getByTestId('release-readiness-card');
    await expect(card).toBeVisible();
    await expect(card.getByText('Release Readiness Gate')).toBeVisible();
    await expect(card.locator('[role="progressbar"]').first()).toBeVisible();
    await expect(card.getByText('Verdict Grade', { exact: true })).toBeVisible();
    await expect(card.getByText('Open Divergences', { exact: true })).toBeVisible();
    await expect(card.getByText('Pending HITL Queue', { exact: true })).toBeVisible();
  });

  test('VerdictHistoryTable renders run history headers and the seeded run', async ({ page }) => {
    const tableCard = page.getByTestId('verdict-history-table');
    await expect(tableCard).toBeVisible();
    await expect(tableCard.getByText('Verdict History & Run Records')).toBeVisible();
    await expect(tableCard.locator('table')).toBeVisible();
    await expect(tableCard.getByText('Run ID', { exact: true })).toBeVisible();
    await expect(tableCard.getByText('Verdict', { exact: true })).toBeVisible();
    await expect(tableCard.getByTestId(`run-row-${SEED_RUN_ID}`)).toBeVisible();
  });

  test('IntegrityHeatmap renders endpoint integrity risk cards with scores', async ({ page }) => {
    // Lives in the Dashboard's "Coverage & Signals" tab
    // (DashboardWorkspace.tsx), not the default "Overview" tab — the prior
    // fixme reason ("no integrity/risk scores in a fresh backend") was
    // wrong: IntegrityHeatmap.tsx derives its cards from /api/v1/divergences,
    // which falls back to a 7-endpoint demo corpus on a fresh backend
    // (cherenkov/web/divergences.py: `list_divergences`), so data is present
    // without seeding anything — the test just never switched tabs to find
    // the element.
    await page.getByRole('tab', { name: 'Coverage & Signals' }).click();
    await page.waitForTimeout(SETTLE);
    const heatmap = page.getByTestId('integrity-heatmap');
    await expect(heatmap).toBeVisible();
    await expect(heatmap.getByText('Integrity & Risk Heatmap')).toBeVisible();
    await expect(heatmap.getByText(/GET|POST|PUT|DELETE/).first()).toBeVisible();
    await expect(heatmap.getByText(/%/).first()).toBeVisible();
  });
});
