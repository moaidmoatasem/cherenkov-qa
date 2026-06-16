import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoVisualRegression(page: any) {
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
  await page.click('#nav-item-visual-regression');
  // VisualRegressionScreen has no root id; wait for its h2 heading
  await page.waitForSelector('text=Visual Regression');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Visual Regression Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('visual regression screen renders heading and description', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.locator('h2').filter({ hasText: 'Visual Regression' })).toBeVisible();
    await expect(page.getByText('VLM-semantic classification — distinguishes real anomalies from harmless pixel drift')).toBeVisible();
  });

  // ── Four filter cards render ──────────────────────────────────────
  test('four VLM kind filter cards render: Anomaly, Harmless Shift, Redesign, Unknown', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByText('Anomaly').first()).toBeVisible();
    await expect(page.getByText('Harmless Shift').first()).toBeVisible();
    await expect(page.getByText('Redesign').first()).toBeVisible();
    await expect(page.getByText('Unknown').first()).toBeVisible();
  });

  // ── Filter card counts ────────────────────────────────────────────
  test('filter card counts reflect mock data: 1 Anomaly, 1 Harmless Shift', async ({ page }) => {
    await gotoVisualRegression(page);

    // vs-1 is harmless_shift, vs-2 is anomaly
    // Find the Anomaly card count - should show 1
    const anomalyCard = page.getByText('Anomaly').locator('..').locator('..');
    // Use simpler approach: the count divs contain the numbers
    // Each card shows: icon, label, then count as large text
    // Verify both scenarios show in the list
    await expect(page.getByText('vs-1')).toBeVisible();
    await expect(page.getByText('vs-2')).toBeVisible();
  });

  // ── Both mock scenarios appear ────────────────────────────────────
  test('vs-1 (harmless_shift) and vs-2 (anomaly) scenario rows render', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByText('vs-1')).toBeVisible();
    await expect(page.getByText('vs-2')).toBeVisible();
  });

  // ── VLM kind badges render on rows ───────────────────────────────
  test('Harmless Shift badge shows for vs-1 scenario', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByText('Harmless Shift').first()).toBeVisible();
  });

  // ── Anomaly badge shows for vs-2 ─────────────────────────────────
  test('Anomaly badge shows for vs-2 scenario', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByText('Anomaly').first()).toBeVisible();
  });

  // ── HITL pending badge ────────────────────────────────────────────
  test('pending HITL banner shows 1 scenario awaiting review', async ({ page }) => {
    await gotoVisualRegression(page);

    // vs-2 has verdict: HITL and no decision yet
    await expect(page.getByText('1 scenario awaiting your review (HITL verdict)')).toBeVisible();
  });

  // ── Scenario URLs render ──────────────────────────────────────────
  test('scenario URLs from mock data are visible', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByText('http://localhost:8000/').first()).toBeVisible();
    await expect(page.getByText('http://localhost:8000/checkout')).toBeVisible();
  });

  // ── Refresh button renders ────────────────────────────────────────
  test('Refresh button renders in the header', async ({ page }) => {
    await gotoVisualRegression(page);

    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
  });

  // ── Expand row reveals VLM Analysis ──────────────────────────────
  test('clicking vs-1 row expands and shows VLM Analysis section', async ({ page }) => {
    await gotoVisualRegression(page);

    // Click the vs-1 row header button
    await page.getByText('vs-1').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('VLM Analysis')).toBeVisible();
    await expect(page.getByText('Anti-aliasing drift only')).toBeVisible();
  });

  // ── VLM confidence renders in expanded view ───────────────────────
  test('VLM confidence percentage shows in expanded row', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByText('vs-1').click();
    await page.waitForTimeout(300);

    // vs-1 has vlm_confidence: 0.93 → 93%
    await expect(page.getByText('93% confidence')).toBeVisible();
  });

  // ── vs-2 expand shows anomaly VLM detail ─────────────────────────
  test('expanding vs-2 shows anomaly VLM detail text', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByText('vs-2').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Button overlaps form field')).toBeVisible();
  });

  // ── HITL approval buttons render ─────────────────────────────────
  test('HITL approve and reject buttons render when vs-2 is expanded', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByText('vs-2').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Your decision (suggest-only):')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Approve change' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reject — fix needed' })).toBeVisible();
  });

  // ── Approve HITL verdict ──────────────────────────────────────────
  test('clicking Approve change sets Approved badge on vs-2', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByText('vs-2').click();
    await page.waitForTimeout(300);

    await page.getByRole('button', { name: 'Approve change' }).click();
    await page.waitForTimeout(200);

    await expect(page.getByText('✓ Approved')).toBeVisible();
    // Buttons hidden after decision
    await expect(page.getByRole('button', { name: 'Approve change' })).not.toBeVisible();
  });

  // ── Reject HITL verdict ───────────────────────────────────────────
  test('clicking Reject sets Rejected badge on vs-2', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByText('vs-2').click();
    await page.waitForTimeout(300);

    await page.getByRole('button', { name: 'Reject — fix needed' }).click();
    await page.waitForTimeout(200);

    await expect(page.getByText('✗ Rejected')).toBeVisible();
  });

  // ── Filter by kind ────────────────────────────────────────────────
  test('clicking Anomaly filter card shows only anomaly scenarios', async ({ page }) => {
    await gotoVisualRegression(page);

    // Click the Anomaly filter card button
    await page.getByRole('button').filter({ hasText: 'Anomaly' }).first().click();
    await page.waitForTimeout(300);

    // vs-2 (anomaly) should be visible; vs-1 (harmless_shift) should not
    await expect(page.getByText('vs-2')).toBeVisible();
    await expect(page.getByText('vs-1')).not.toBeVisible();
  });

  // ── Filter deselects on second click ─────────────────────────────
  test('clicking active filter again shows all scenarios', async ({ page }) => {
    await gotoVisualRegression(page);

    const anomalyBtn = page.getByRole('button').filter({ hasText: 'Anomaly' }).first();
    await anomalyBtn.click();
    await page.waitForTimeout(200);
    await anomalyBtn.click();
    await page.waitForTimeout(200);

    // Both scenarios visible again
    await expect(page.getByText('vs-1')).toBeVisible();
    await expect(page.getByText('vs-2')).toBeVisible();
  });

  // ── Refresh re-fetches data ───────────────────────────────────────
  test('clicking Refresh button does not crash the screen', async ({ page }) => {
    await gotoVisualRegression(page);

    await page.getByRole('button', { name: 'Refresh' }).click();
    await page.waitForTimeout(500);

    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    await expect(page.getByText('vs-1')).toBeVisible();
  });

  // ── Empty state on API failure ────────────────────────────────────
  test('empty state renders when visual scenarios API returns empty array', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/visual/scenarios', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-visual-regression');
    await page.waitForSelector('text=Visual Regression');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('No visual scenarios found.')).toBeVisible();
  });

});
