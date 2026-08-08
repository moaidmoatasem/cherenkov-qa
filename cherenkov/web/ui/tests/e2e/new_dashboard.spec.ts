import { test, expect } from '@playwright/test';

// The new Vanilla CSS dashboard tests
// These tests run against the real backend, so they only check for structural presence of the new UI components

test.describe('CHERENKOV QA Dashboard — Vanilla CSS E2E Suite', () => {

  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
  });

  test('AppHeader renders correctly with new styling', async ({ page }) => {
    const header = page.locator('#cherenkov-app-header');
    await expect(header).toBeVisible();
    await expect(page.locator('text=CHERENKOV')).toBeVisible();
    
    // Verify the TopBar interactive elements
    await expect(page.locator('#btn-global-search')).toBeVisible();
    await expect(page.locator('#btn-user-profile')).toBeVisible();
  });

  test('DashboardWorkspace mounts and shows key metrics', async ({ page }) => {
    // Verify the new layout ID
    const workspace = page.locator('#dashboard-workspace');
    await expect(workspace).toBeVisible();

    // The PageHeader title
    await expect(page.locator('h1:has-text("Dashboard")')).toBeVisible();

    // ReleaseReadinessCard
    const readinessCard = page.locator('[data-testid="release-readiness-card"]');
    await expect(readinessCard).toBeVisible();
    await expect(page.locator('text=Release Readiness Gate')).toBeVisible();

    // VerdictHistoryTable
    const verdictTable = page.locator('[data-testid="verdict-history-table"]');
    await expect(verdictTable).toBeVisible();
  });

  test('Navigation via N-2 quick links', async ({ page }) => {
    const quickLinks = page.locator('[data-testid="dashboard-quick-links"]');
    await expect(quickLinks).toBeVisible();

    const reviewLink = page.locator('[data-testid="quick-link-review-divergences"]');
    await expect(reviewLink).toBeVisible();
    await expect(reviewLink).toContainText('Open recent divergence');
  });

  test('Toggles to Coverage & Signals tab', async ({ page }) => {
    // Click the "Coverage & Signals" tab
    await page.locator('button:has-text("Coverage & Signals")').click();
    
    // The heatmap and coverage panels should become visible
    await expect(page.locator('[data-testid="integrity-heatmap"]')).toBeVisible();
    await expect(page.locator('[data-testid="coverage-perf-screen"]')).toBeVisible();
  });
});
