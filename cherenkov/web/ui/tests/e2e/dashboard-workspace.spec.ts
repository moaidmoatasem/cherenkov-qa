import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

const SETTLE = 400;

test.describe('Dashboard Workspace E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLE);
  });

  test('AppHeader renders brand, project dropdown, token budget, and backend health status badge', async ({ page }) => {
    await expect(page.locator('header')).toBeVisible();
    await expect(page.getByText('CHERENKOV').first()).toBeVisible();
    await expect(page.getByTestId('project-selector-dropdown')).toBeVisible();
    await expect(page.getByTestId('backend-health-badge')).toBeVisible();
    await expect(page.getByText('Tokens:')).toBeVisible();
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
    await expect(page.locator('#dashboard-workspace').getByRole('heading', { name: 'Dashboard Workspace' })).toBeVisible();
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

  test('VerdictHistoryTable renders run history headers and rows', async ({ page }) => {
    const tableCard = page.getByTestId('verdict-history-table');
    await expect(tableCard).toBeVisible();
    await expect(tableCard.getByText('Verdict History & Run Records')).toBeVisible();
    await expect(tableCard.locator('table')).toBeVisible();
    await expect(tableCard.getByText('Run ID', { exact: true })).toBeVisible();
    await expect(tableCard.getByText('Verdict', { exact: true })).toBeVisible();
  });

  test('IntegrityHeatmap renders endpoint integrity risk cards with scores', async ({ page }) => {
    const heatmap = page.getByTestId('integrity-heatmap');
    await expect(heatmap).toBeVisible();
    await expect(heatmap.getByText('Integrity & Risk Heatmap')).toBeVisible();
    await expect(heatmap.getByText(/GET|POST|PUT|DELETE/).first()).toBeVisible();
    await expect(heatmap.getByText(/%/).first()).toBeVisible();
  });
});
