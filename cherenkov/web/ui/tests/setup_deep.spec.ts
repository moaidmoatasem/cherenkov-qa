import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoSetup(page: any) {
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
  await page.click('#nav-item-setup');
  await page.waitForSelector('#setup-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Setup & Spec Ingest Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('setup screen renders heading and description', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.locator('h1')).toContainText('New Test Generation Run');
    await expect(page.getByText('Supply an OpenAPI index to generate synthetically verified Playwright tests.')).toBeVisible();
  });

  // ── System check passes with mock data ───────────────────────────
  test('system readiness banner shows ALL CHECKS PASSED when doctor returns ready', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByText('ALL SYSTEM CHECKS PASSED. ENGINE READY.')).toBeVisible();
  });

  // ── Upload drag zone renders ──────────────────────────────────────
  test('drag-and-drop upload zone renders with prompt text', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByText('Drag & Drop OpenAPI Spec (.json / .yaml)')).toBeVisible();
    await expect(page.getByText('Accepts schema definitions up to 10MB')).toBeVisible();
  });

  // ── Ingest API Definition heading ────────────────────────────────
  test('Ingest API Definition section renders', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByText('Ingest API Definition')).toBeVisible();
  });

  // ── Spec URL input renders ────────────────────────────────────────
  test('URL input field renders with placeholder when no file loaded', async ({ page }) => {
    await gotoSetup(page);

    const urlInput = page.locator('#spec-url-input');
    await expect(urlInput).toBeVisible();
    await expect(urlInput).toHaveAttribute('placeholder', /swagger.json/);
  });

  // ── Fetch button renders ──────────────────────────────────────────
  test('Fetch button renders next to URL input', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByRole('button', { name: 'Fetch' })).toBeVisible();
  });

  // ── Preset shortcuts render ───────────────────────────────────────
  test('preset mock shortcut buttons render (petstore and checkout)', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.locator('#btn-shortcut-petstore')).toBeVisible();
    await expect(page.locator('#btn-shortcut-checkout')).toBeVisible();
  });

  // ── Petstore shortcut loads spec ──────────────────────────────────
  test('clicking petstore shortcut loads endpoints into spec analyzer', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    // Mock returns 3 endpoints from MOCK_ENDPOINTS.slice(0, 3)
    await expect(page.getByText('Spec Richness Analyzer')).toBeVisible();
    // Avg Richness Score label visible in the analyzer panel
    await expect(page.getByText('Avg Richness Score')).toBeVisible();
  });

  // ── After spec load: endpoints indexed count ─────────────────────
  test('endpoints indexed shows count after spec load', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    // "Endpoints Indexed" label
    await expect(page.getByText('Endpoints Indexed')).toBeVisible();
  });

  // ── After spec load: launch generation button ─────────────────────
  test('generate button becomes available after spec load', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    await expect(page.locator('#btn-launch-generation')).toBeVisible();
    // Button enabled (system ready + endpoints loaded)
    await expect(page.locator('#btn-launch-generation')).not.toBeDisabled();
  });

  // ── Generation button shows endpoint count ────────────────────────
  test('generate button shows endpoint count in label', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    await expect(page.locator('#btn-launch-generation')).toContainText('Generate 3 API Test Suites');
  });

  // ── Server validation panel toggle ───────────────────────────────
  test('Real-server Validation Configuration panel toggles on click', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByText('Real-server Validation Configuration')).toBeVisible();

    // Expand panel
    await page.locator('#btn-toggle-server-validation').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#input-server-url')).toBeVisible();
    await expect(page.locator('#input-auth-header')).toBeVisible();
  });

  // ── Server URL default value ──────────────────────────────────────
  test('server URL input shows default localhost value when expanded', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-toggle-server-validation').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#input-server-url')).toHaveValue('http://localhost:8080/v2');
  });

  // ── Auth header input renders ─────────────────────────────────────
  test('auth header input is visible and editable when expanded', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-toggle-server-validation').click();
    await page.waitForTimeout(300);

    const authInput = page.locator('#input-auth-header');
    await expect(authInput).toBeVisible();
    await authInput.fill('Bearer test-token-abc');
    await expect(authInput).toHaveValue('Bearer test-token-abc');
  });

  // ── Spec Richness Analyzer empty state ───────────────────────────
  test('Spec Richness Analyzer shows empty prompt before spec is loaded', async ({ page }) => {
    await gotoSetup(page);

    await expect(page.getByText('Please load or drop a spec configuration')).toBeVisible();
  });

  // ── Band legend renders after spec load ──────────────────────────
  test('quality coverage segment legend renders after spec load', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    await expect(page.getByText('Quality coverage segments')).toBeVisible();
  });

  // ── Inference threshold warning renders ──────────────────────────
  test('Inference Threshold Warning shows after spec load', async ({ page }) => {
    await gotoSetup(page);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    await expect(page.getByText('Inference Threshold Warning')).toBeVisible();
  });

  // ── Doctor failure shows warning banner ──────────────────────────
  test('system warning shows when doctor API returns not ready', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/doctor', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ checks: [], ready: false })
      })
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
    await page.click('#nav-item-setup');
    await page.waitForSelector('#setup-screen');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText(/Cannot verify system readiness|backend unreachable/)).toBeVisible();
  });

  // ── Ingest error shows error card ────────────────────────────────
  test('spec ingest error shows error card with retry hint', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/ingest', route =>
      route.fulfill({ status: 422, body: '{"detail":"invalid spec"}' })
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
    await page.click('#nav-item-setup');
    await page.waitForSelector('#setup-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(800);

    await expect(page.locator('[data-testid="ingest-error-card"]')).toBeVisible();
    await expect(page.getByText('Spec Ingestion Failed')).toBeVisible();
  });

});
