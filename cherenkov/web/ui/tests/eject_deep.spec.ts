import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoEject(page: any) {
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
  await page.click('#nav-item-eject');
  await page.waitForSelector('#eject-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Export & Eject Suite Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('eject screen renders heading and description', async ({ page }) => {
    await gotoEject(page);

    await expect(page.locator('h1')).toContainText('Export & Eject Suite');
    await expect(page.getByText('Unlock your testing resources.')).toBeVisible();
  });

  // ── Eject Playwright Configuration heading ────────────────────────
  test('Eject Playwright Configuration section heading renders', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('Eject Playwright Configuration')).toBeVisible();
  });

  // ── 0% vendor lock-in card ────────────────────────────────────────
  test('0% VENDOR LOCK-IN GUARANTEE card renders', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('0% VENDOR LOCK-IN GUARANTEE')).toBeVisible();
  });

  // ── File statistics render ────────────────────────────────────────
  test('file statistics show 47 Files, 6 Classes, ~3.2 K', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('47 Files')).toBeVisible();
    await expect(page.getByText('6 Classes')).toBeVisible();
    await expect(page.getByText('~3.2 K')).toBeVisible();
  });

  // ── Stats section labels ──────────────────────────────────────────
  test('stats section shows Test Suites, API Clients, Total Lines labels', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('Test Suites')).toBeVisible();
    await expect(page.getByText('API Clients')).toBeVisible();
    await expect(page.getByText('Total Lines')).toBeVisible();
  });

  // ── Output path input renders ─────────────────────────────────────
  test('output path input renders with default value', async ({ page }) => {
    await gotoEject(page);

    const pathInput = page.locator('#eject-path');
    await expect(pathInput).toBeVisible();
    await expect(pathInput).toHaveValue('./playwright-suite');
  });

  // ── Path prefix label ─────────────────────────────────────────────
  test('path input shows /home/workspace/ prefix', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('/home/workspace/')).toBeVisible();
  });

  // ── Path input is editable ────────────────────────────────────────
  test('output path input is editable', async ({ page }) => {
    await gotoEject(page);

    const pathInput = page.locator('#eject-path');
    await pathInput.fill('./custom-suite');
    await expect(pathInput).toHaveValue('./custom-suite');
  });

  // ── Eject to Path button renders ──────────────────────────────────
  test('Eject to Path button renders and is clickable', async ({ page }) => {
    await gotoEject(page);

    const ejectBtn = page.locator('#btn-confirm-eject');
    await expect(ejectBtn).toBeVisible();
    await expect(ejectBtn).toContainText('Eject to Path');
  });

  // ── Download .ZIP button renders ──────────────────────────────────
  test('Download .ZIP button renders', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByRole('button', { name: 'Download .ZIP' })).toBeVisible();
  });

  // ── File tree panel renders ───────────────────────────────────────
  test('Project Folder Inspection Workspace panel renders', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('Project Folder Inspection Workspace')).toBeVisible();
  });

  // ── Playwright-suite folder in tree ──────────────────────────────
  test('playwright-suite folder is visible in the file tree', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('playwright-suite/')).toBeVisible();
  });

  // ── Output path label ─────────────────────────────────────────────
  test('Output file destination path label renders', async ({ page }) => {
    await gotoEject(page);

    await expect(page.getByText('Output file destination path')).toBeVisible();
  });

  // ── Successful eject flow ─────────────────────────────────────────
  test('clicking Eject to Path triggers success state with protocol written message', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    await expect(page.getByText('EXPORT FILE PROTOCOL WRITTEN SUCCESSFULLY')).toBeVisible();
  });

  // ── Success state shows output path ──────────────────────────────
  test('success state shows the configured output path', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    // Default path is ./playwright-suite
    await expect(page.getByText('./playwright-suite').first()).toBeVisible();
  });

  // ── Copy command button shows after eject ────────────────────────
  test('copy command button renders after successful eject', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    await expect(page.locator('#btn-copy-command')).toBeVisible();
  });

  // ── Run command text renders ──────────────────────────────────────
  test('run command text renders after successful eject', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    await expect(page.getByText('cd playwright-suite && npm install && npx playwright test')).toBeVisible();
  });

  // ── Return to configuration link ─────────────────────────────────
  test('Return to eject configuration link resets to initial state', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    await page.getByText('← Return to eject configuration').click();
    await page.waitForTimeout(300);

    // Back to pre-eject state
    await expect(page.locator('#btn-confirm-eject')).toBeVisible();
    await expect(page.getByText('EXPORT FILE PROTOCOL WRITTEN SUCCESSFULLY')).not.toBeVisible();
  });

  // ── Custom path used in success message ──────────────────────────
  test('custom path shows in success state after eject', async ({ page }) => {
    await gotoEject(page);

    await page.locator('#eject-path').fill('./my-tests');
    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(800);

    await expect(page.getByText('./my-tests').first()).toBeVisible();
  });

  // ── Error state on API failure ────────────────────────────────────
  test('eject error card shows when API returns error status', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/eject', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'error' }) })
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
    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(500);

    await expect(page.getByText('Eject Operation Failed')).toBeVisible();
  });

});
