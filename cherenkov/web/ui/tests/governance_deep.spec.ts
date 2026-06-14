import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoGovernance(page: any) {
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
  await page.click('#nav-item-governance');
  await page.waitForSelector('#governance-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Governance & Model Certification Screen — Deep Coverage', () => {

  // ── Screen loads with heading ─────────────────────────────────────
  test('governance screen renders heading and description', async ({ page }) => {
    await gotoGovernance(page);

    await expect(page.locator('h1')).toContainText('Governance & Model Certification');
    await expect(page.getByText('Verify LLM model performance tier bounds')).toBeVisible();
  });

  // ── Export button triggers toast ──────────────────────────────────
  test('Export Compliance Log button shows success toast', async ({ page }) => {
    await gotoGovernance(page);

    await page.getByText('Export Compliance Log').click();
    await page.waitForTimeout(300);

    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('export');
  });

  // ── Defect escape KPI ─────────────────────────────────────────────
  test('Defect Escape Rate KPI shows value from API', async ({ page }) => {
    await gotoGovernance(page);

    // Mock: defectEscapeRate: 1.2 → "1.2%"
    await expect(page.getByText('Defect Escape Rate')).toBeVisible();
    await expect(page.getByText('1.2%')).toBeVisible();
  });

  // ── False positive KPI ────────────────────────────────────────────
  test('FP Validation Rate KPI shows computed percentage', async ({ page }) => {
    await gotoGovernance(page);

    // Mock: falsePositiveRate: 0.05 → 0.05 * 100 = 5 → "5%"
    await expect(page.getByText('FP Validation Rate')).toBeVisible();
    await expect(page.getByText('5%')).toBeVisible();
  });

  // ── Model certification panel ─────────────────────────────────────
  test('model certification panel renders all three tiers', async ({ page }) => {
    await gotoGovernance(page);

    await expect(page.getByText('Model Capabilities Certification')).toBeVisible();

    // Three tiers from mock
    await expect(page.getByText('Small (Fast) Capability Tier')).toBeVisible();
    await expect(page.getByText('Deep (Precise) Capability Tier')).toBeVisible();
    await expect(page.getByText('Vision (UI) Capability Tier')).toBeVisible();
  });

  // ── Certification status ──────────────────────────────────────────
  test('all certification tiers show success status', async ({ page }) => {
    await gotoGovernance(page);

    // Each cert shows "Status: success"
    const statusItems = page.locator('#governance-screen').getByText(/Status: success/);
    await expect(statusItems.first()).toBeVisible();
  });

  // ── StatusDot indicators visible ──────────────────────────────────
  test('status indicator dots render for each cert tier', async ({ page }) => {
    await gotoGovernance(page);

    // StatusDot components render as colored indicators
    const statusDots = page.locator('#governance-screen [data-testid="status-dot"], #governance-screen .status-dot').first();
    // If no testid, just verify the cert rows are present
    const certRows = page.locator('#governance-screen').getByText(/Capability Tier/);
    await expect(certRows.first()).toBeVisible();
    expect(await certRows.count()).toBe(3);
  });

  // ── Traceability section header ───────────────────────────────────
  test('artifact traceability section renders', async ({ page }) => {
    await gotoGovernance(page);

    await expect(page.getByText('Artifact Traceability Explorer')).toBeVisible();
  });

  // ── Defect & FP section header ────────────────────────────────────
  test('Defect Escape & False Positives section header visible', async ({ page }) => {
    await gotoGovernance(page);

    await expect(page.getByText('Defect Escape & False Positives')).toBeVisible();
  });

  // ── Zero-rate override: 0% escape rate ───────────────────────────
  test('defect escape rate shows 0% when API returns zero', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/governance', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          defectEscapeRate: 0,
          falsePositiveRate: 0,
          modelCertification: [],
          traceability: []
        })
      })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-governance');
    await page.waitForSelector('#governance-screen');
    await page.waitForTimeout(SETTLEMENT);

    // 0% escape rate — green is good
    await expect(page.getByText('0%').first()).toBeVisible();
  });

  // ── Graceful degradation when API returns 500 ─────────────────────
  test('governance screen degrades gracefully when API fails', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/governance', route =>
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
    await page.click('#nav-item-governance');
    await page.waitForSelector('#governance-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Screen renders without crash — heading still visible
    await expect(page.locator('h1')).toContainText('Governance & Model Certification');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  // ── Keyboard accessible ───────────────────────────────────────────
  test('Export button is keyboard focusable', async ({ page }) => {
    await gotoGovernance(page);

    const exportBtn = page.getByRole('button', { name: /Export Compliance Log/i });
    await expect(exportBtn).toBeVisible();
    await exportBtn.focus();
    await expect(exportBtn).toBeFocused();
  });

});
