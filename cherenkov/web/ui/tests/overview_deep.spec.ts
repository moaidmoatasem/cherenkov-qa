import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoOverview(page: any) {
  await setupApiMocks(page);
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('[copilot] tour_seen', 'true');
    localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
  });
  await page.reload();
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(SETTLEMENT);
  await page.click('#nav-item-overview');
  await page.waitForSelector('#overview-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Overview (Release Readiness) Screen — Deep Coverage', () => {

  // ── Screen loads with correct heading ────────────────────────────
  test('overview screen renders heading and description', async ({ page }) => {
    await gotoOverview(page);

    await expect(page.locator('h1')).toContainText('Release Readiness');
    await expect(page.getByText('Real-time ship/no-ship gate')).toBeVisible();
  });

  // ── KPI cards: open divergences ──────────────────────────────────
  test('Open Divergences KPI card shows count from API', async ({ page }) => {
    await gotoOverview(page);

    // Mock returns 7 divergences (D-01 through D-07)
    await expect(page.getByText('Open Divergences', { exact: true })).toBeVisible();
    const kpiCard = page.locator('[data-testid="kpi-divergences"]');
    await expect(kpiCard).toBeVisible();
    await expect(kpiCard.getByText('7')).toBeVisible();
    // 1 critical divergence (D-06)
    await expect(kpiCard.getByText('1 critical')).toBeVisible();
  });

  // ── KPI cards: pending review ─────────────────────────────────────
  test('Pending Review KPI card shows count from review queue', async ({ page }) => {
    await gotoOverview(page);

    // Mock review queue returns 2 items
    await expect(page.getByText('Pending Review', { exact: true })).toBeVisible();
    const kpiCard = page.locator('[data-testid="kpi-pending"]');
    await expect(kpiCard).toBeVisible();
    await expect(kpiCard.getByText('2')).toBeVisible();
    await expect(kpiCard.getByText('awaiting HITL')).toBeVisible();
  });

  // ── KPI cards: session cost ───────────────────────────────────────
  test('Session Cost KPI shows cost from metrics API', async ({ page }) => {
    await gotoOverview(page);

    // Mock: totalCost: 0.42
    const kpiCard = page.locator('[data-testid="kpi-cost"]');
    await expect(kpiCard).toBeVisible();
    await expect(kpiCard.getByText('$0.42')).toBeVisible();
    await expect(kpiCard.getByText('128,000 tokens')).toBeVisible();
  });

  // ── KPI cards: cloud equivalent ───────────────────────────────────
  test('Cloud Equivalent KPI shows scaled cost', async ({ page }) => {
    await gotoOverview(page);

    // 0.42 * 3.4 = 1.428
    const kpiCard = page.locator('[data-testid="kpi-cloud"]');
    await expect(kpiCard).toBeVisible();
    await expect(kpiCard.getByText('$1.428')).toBeVisible();
    await expect(kpiCard.getByText('vs GPT-4o list price')).toBeVisible();
  });

  // ── Readiness KPI ring renders ────────────────────────────────────
  test('Readiness KPI ring renders with progressbar role', async ({ page }) => {
    await gotoOverview(page);

    const ring = page.locator('[role="progressbar"]').first();
    await expect(ring).toBeVisible();
    await expect(ring).toHaveAttribute('aria-valuemin', '0');
    await expect(ring).toHaveAttribute('aria-valuemax', '100');

    const value = await ring.getAttribute('aria-valuenow');
    expect(value).not.toBeNull();
    const score = Number(value);
    expect(score).toBeGreaterThanOrEqual(0);
    expect(score).toBeLessThanOrEqual(100);
  });

  // ── Readiness score computation ───────────────────────────────────
  test('readiness score reflects divergences and pending reviews', async ({ page }) => {
    await gotoOverview(page);

    // 7 divergences (1 critical, 2 high) + 2 pending reviews
    // score = 100 - (1*15) - (2*5) - (2*2) = 71
    const ring = page.locator('[role="progressbar"]').first();
    const value = Number(await ring.getAttribute('aria-valuenow'));
    expect(value).toBe(71);

    // 71 is in [50, 80) → "Review Required"
    await expect(page.getByText('Review Required')).toBeVisible();
    await expect(page.getByText('71/100')).toBeVisible();
  });

  // ── Top divergences panel ─────────────────────────────────────────
  test('top divergences panel shows risk-sorted critical divergence first', async ({ page }) => {
    await gotoOverview(page);

    const panel = page.locator('[data-testid="overview-kpi-divergences"]');
    await expect(panel).toBeVisible();
    await expect(panel.getByText('Top Open Divergences')).toBeVisible();

    // D-06 is the only critical → appears first (critical → severity 0)
    const rows = panel.locator('[data-testid^="divergence-row-"]');
    await expect(rows.first()).toContainText('critical');
  });

  // ── Divergence rows navigate to triage screen ─────────────────────
  test('clicking a divergence row navigates to divergences screen', async ({ page }) => {
    await gotoOverview(page);

    const firstDivRow = page.locator('[data-testid^="divergence-row-"]').first();
    await firstDivRow.click();
    await page.waitForTimeout(400);

    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
  });

  // ── Triage All button ─────────────────────────────────────────────
  test('"Triage All Divergences" button navigates to divergences', async ({ page }) => {
    await gotoOverview(page);

    await page.locator('[data-testid="btn-view-all-divergences"]').click();
    await page.waitForTimeout(400);
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
  });

  // ── Review queue panel ────────────────────────────────────────────
  test('pending review panel shows queue items from API', async ({ page }) => {
    await gotoOverview(page);

    const panel = page.locator('[data-testid="overview-kpi-review"]');
    await expect(panel).toBeVisible();
    await expect(panel.getByText('Pending Review Gate')).toBeVisible();

    // Mock has PUT /pets and DELETE /store/order/{orderId}
    await expect(panel.getByText('PUT').first()).toBeVisible();
    await expect(panel.getByText('DELETE').first()).toBeVisible();
  });

  // ── Review row navigates to review screen ─────────────────────────
  test('clicking a review row navigates to review screen', async ({ page }) => {
    await gotoOverview(page);

    const firstReviewRow = page.locator('[data-testid^="review-row-"]').first();
    await firstReviewRow.click();
    await page.waitForTimeout(400);
    await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
  });

  // ── Open Review Gate button ───────────────────────────────────────
  test('"Open Review Gate" button navigates to review screen', async ({ page }) => {
    await gotoOverview(page);

    await page.locator('[data-testid="btn-go-to-review"]').click();
    await page.waitForTimeout(400);
    await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
  });

  // ── Refresh button triggers data reload ───────────────────────────
  test('refresh button calls API and shows info toast', async ({ page }) => {
    await gotoOverview(page);

    await page.locator('#btn-overview-refresh').click();
    await page.waitForTimeout(300);

    // Toast notification for refresh
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Refreshing');
  });

  // ── Pilot Run button visible ──────────────────────────────────────
  test('Pilot Run button renders and is clickable', async ({ page }) => {
    await gotoOverview(page);

    const pilotBtn = page.locator('#btn-pilot-run');
    await expect(pilotBtn).toBeVisible();
    await pilotBtn.click();
    // Navigation triggered (to setup/pipeline) — no crash
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  // ── Clean state: no divergences → 100 score ───────────────────────
  test('readiness shows 100 and Ship Ready when no divergences', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/divergences', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await page.route('**/api/v1/review/queue*', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    await page.waitForTimeout(SETTLEMENT);

    const ring = page.locator('[role="progressbar"]').first();
    expect(Number(await ring.getAttribute('aria-valuenow'))).toBe(100);
    await expect(page.getByText('Ship Ready')).toBeVisible();
    await expect(page.getByText('100/100')).toBeVisible();

    // Empty divergences → clean message
    await expect(page.getByText('No open divergences')).toBeVisible();
    await expect(page.getByText('No pending reviews')).toBeVisible();
  });

  // ── Error state when APIs fail ────────────────────────────────────
  test('error state shown when divergences API returns 500', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/divergences', route =>
      route.fulfill({ status: 500, body: '{"detail":"error"}' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-overview');
    await page.waitForTimeout(SETTLEMENT);

    // Error empty state with retry button
    await expect(page.getByText('Failed to Load Release Readiness')).toBeVisible();
    await expect(page.getByText('Retry')).toBeVisible();
  });

  // ── Data footer visible ───────────────────────────────────────────
  test('data source footer with MockBadge renders', async ({ page }) => {
    await gotoOverview(page);

    await expect(page.getByText(/KPI Ring readiness score/)).toBeVisible();
  });

});
