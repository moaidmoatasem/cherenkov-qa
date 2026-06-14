import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoSignals(page: any) {
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
  await page.click('#nav-item-signals');
  await page.waitForSelector('#signals-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Telemetry Signals Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('signals screen renders heading and description', async ({ page }) => {
    await gotoSignals(page);

    await expect(page.locator('h1')).toContainText('Telemetry Signals');
    await expect(page.getByText('Verify performance, visual changes, and functional coverage profiles')).toBeVisible();
  });

  // ── Three tabs render ─────────────────────────────────────────────
  test('three tabs render: Performance, Visual Regression, SDET Coverage', async ({ page }) => {
    await gotoSignals(page);

    // Scope to the signals screen to avoid sidebar nav item for "Visual Regression"
    const screen = page.locator('#signals-screen');
    await expect(screen.getByText('Performance')).toBeVisible();
    await expect(screen.getByText('Visual Regression')).toBeVisible();
    await expect(screen.getByText('SDET Coverage')).toBeVisible();
  });

  // ── Performance tab is default ────────────────────────────────────
  test('performance tab is active by default and shows latency data', async ({ page }) => {
    await gotoSignals(page);

    await expect(page.getByText('API Latency & Anomaly Baselines')).toBeVisible();
    // 4 performance entries from mock
    await expect(page.getByText('Time: 10:00')).toBeVisible();
    await expect(page.getByText('Latency: 120ms')).toBeVisible();
  });

  // ── ANOMALY DETECTED banner shows for anomalous entry ────────────
  test('ANOMALY DETECTED shown for latency spike entry', async ({ page }) => {
    await gotoSignals(page);

    // Mock entry at 10:10 with latency: 250, anomaly: true
    await expect(page.getByText('Time: 10:10')).toBeVisible();
    await expect(page.getByText('Latency: 250ms')).toBeVisible();
    await expect(page.getByText('ANOMALY DETECTED')).toBeVisible();
  });

  // ── Normal bounds shows for non-anomalous entries ─────────────────
  test('NORMAL BOUNDS label shows for normal latency entries', async ({ page }) => {
    await gotoSignals(page);

    const normalItems = page.getByText('NORMAL BOUNDS');
    // 3 out of 4 entries are normal
    await expect(normalItems.first()).toBeVisible();
    expect(await normalItems.count()).toBe(3);
  });

  // ── Baseline value visible ────────────────────────────────────────
  test('baseline latency values visible in performance entries', async ({ page }) => {
    await gotoSignals(page);

    await expect(page.getByText('Baseline: 110ms')).toBeVisible();
    await expect(page.getByText('Baseline: 115ms')).toBeVisible();
  });

  // ── Visual Regression tab ─────────────────────────────────────────
  test('Visual Regression tab shows UI snapshot comparisons', async ({ page }) => {
    await gotoSignals(page);

    await page.locator('#signals-screen').getByText('Visual Regression').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('UI Snapshot Comparisons')).toBeVisible();
  });

  // ── Visual snapshot data from mock ────────────────────────────────
  test('visual regression tab shows checkout form and header snapshots', async ({ page }) => {
    await gotoSignals(page);

    await page.locator('#signals-screen').getByText('Visual Regression').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Checkout Form Desktop')).toBeVisible();
    await expect(page.getByText('Header Navigation Bar')).toBeVisible();
  });

  // ── DRIFT DETECTED on warning visual ─────────────────────────────
  test('DRIFT DETECTED badge shown for warning visual snapshot', async ({ page }) => {
    await gotoSignals(page);

    await page.locator('#signals-screen').getByText('Visual Regression').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Diff: 3.4% pixel shift')).toBeVisible();
    await expect(page.getByText('DRIFT DETECTED')).toBeVisible();
  });

  // ── MATCHED badge on success visual ──────────────────────────────
  test('MATCHED badge shown for passing visual snapshot', async ({ page }) => {
    await gotoSignals(page);

    await page.locator('#signals-screen').getByText('Visual Regression').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Diff: 0.0% match')).toBeVisible();
    await expect(page.getByText('MATCHED')).toBeVisible();
  });

  // ── SDET Coverage tab ─────────────────────────────────────────────
  test('SDET Coverage tab shows code path verification', async ({ page }) => {
    await gotoSignals(page);

    await page.getByText('SDET Coverage').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Code Path Verification Coverage')).toBeVisible();
  });

  // ── Coverage data from mock ───────────────────────────────────────
  test('coverage tab shows all three paths from mock', async ({ page }) => {
    await gotoSignals(page);

    await page.getByText('SDET Coverage').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('/pets')).toBeVisible();
    await expect(page.getByText('/store/order')).toBeVisible();
    await expect(page.getByText('/user/login')).toBeVisible();
  });

  // ── Coverage percentages render ───────────────────────────────────
  test('coverage tab shows Cherenkov vs SDET percentages', async ({ page }) => {
    await gotoSignals(page);

    await page.getByText('SDET Coverage').click();
    await page.waitForTimeout(300);

    // /pets: SDET 95, Cherenkov 100
    await expect(page.getByText('Cherenkov: 100% vs SDET: 95%')).toBeVisible();
  });

  // ── Tab switching preserves state ─────────────────────────────────
  test('switching tabs changes content correctly', async ({ page }) => {
    await gotoSignals(page);

    // Start on Performance
    await expect(page.getByText('API Latency & Anomaly Baselines')).toBeVisible();

    // Go to Visual
    await page.locator('#signals-screen').getByText('Visual Regression').click();
    await page.waitForTimeout(300);
    await expect(page.getByText('UI Snapshot Comparisons')).toBeVisible();
    await expect(page.getByText('API Latency & Anomaly Baselines')).not.toBeVisible();

    // Go back to Performance
    await page.getByText('Performance').click();
    await page.waitForTimeout(300);
    await expect(page.getByText('API Latency & Anomaly Baselines')).toBeVisible();
  });

  // ── Graceful on API failure ───────────────────────────────────────
  test('signals screen renders without crash when API returns 500', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/signals', route =>
      route.fulfill({ status: 500, body: '{"detail":"error"}' })
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
    await page.click('#nav-item-signals');
    await page.waitForSelector('#signals-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Screen renders without crashing
    await expect(page.locator('h1')).toContainText('Telemetry Signals');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

});
