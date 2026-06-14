import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoMemory(page: any) {
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
  await page.click('#nav-item-memory');
  await page.waitForSelector('#memory-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Reflector Memory & Pairing Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('memory screen renders heading and description', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
    await expect(page.getByText('Verify stored testing idioms and view context-specific guidelines')).toBeVisible();
  });

  // ── Accumulated idioms panel header ───────────────────────────────
  test('accumulated senior testing idioms panel renders', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('Accumulated Senior Testing Idioms')).toBeVisible();
  });

  // ── Idiom content from mock ───────────────────────────────────────
  test('idiom panel shows CORS policy idiom from mock', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('Confirm CORS policy is strictly defined for API origins')).toBeVisible();
  });

  // ── Second idiom content ──────────────────────────────────────────
  test('idiom panel shows OAuth state token idiom from mock', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('Validate OAuth state token integrity validation')).toBeVisible();
  });

  // ── Idiom usage count visible ─────────────────────────────────────
  test('idiom usage counts visible in idiom panel', async ({ page }) => {
    await gotoMemory(page);

    // idm-1: count 14, idm-2: count 9
    await expect(page.getByText('Confidence Matches: 14')).toBeVisible();
    await expect(page.getByText('Confidence Matches: 9')).toBeVisible();
  });

  // ── Idiom decay / confidence visible ─────────────────────────────
  test('idiom confidence labels visible', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('Confidence: Active')).toBeVisible();
    await expect(page.getByText('Confidence: Slightly Decayed')).toBeVisible();
  });

  // ── Pairing panel renders ─────────────────────────────────────────
  test('Mentor Junior-Senior Pairing panel renders', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('Mentor Junior-Senior Pairing')).toBeVisible();
  });

  // ── Pairing context label ─────────────────────────────────────────
  test('pairing context badge shows OAUTH REDIRECT context', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText('CONTEXT: OAUTH REDIRECT')).toBeVisible();
  });

  // ── Pairing explanation text ──────────────────────────────────────
  test('pairing explanation text visible in panel', async ({ page }) => {
    await gotoMemory(page);

    await expect(page.getByText(/A senior developer checks that redirect URIs are strictly validated/)).toBeVisible();
  });

  // ── Graceful on empty memory ──────────────────────────────────────
  test('memory screen shows empty panels when API returns empty arrays', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/memory', route =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ idioms: [], pairing: [] })
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
    await page.click('#nav-item-memory');
    await page.waitForSelector('#memory-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Screen still renders without crash
    await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
    await expect(page.locator('#memory-screen')).toBeVisible();
  });

  // ── Two idiom entries render ──────────────────────────────────────
  test('two idiom entries visible from mock data', async ({ page }) => {
    await gotoMemory(page);

    const idiomPanel = page.locator('#memory-screen').getByText('Accumulated Senior Testing Idioms').locator('..');
    // Both idiom text blocks visible
    await expect(page.getByText('Confirm CORS policy is strictly defined for API origins')).toBeVisible();
    await expect(page.getByText('Validate OAuth state token integrity validation')).toBeVisible();
  });

  // ── Screen does not crash on API 500 ─────────────────────────────
  test('memory screen degrades gracefully when API returns 500', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/memory', route =>
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
    await page.click('#nav-item-memory');
    await page.waitForSelector('#memory-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Heading still visible, no crash
    await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
  });

});
