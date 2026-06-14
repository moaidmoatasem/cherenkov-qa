import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoKnowledge(page: any) {
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
  await page.click('#nav-item-knowledge');
  await page.waitForSelector('#knowledge-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Knowledge Explorer Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('knowledge screen renders heading and description', async ({ page }) => {
    await gotoKnowledge(page);

    await expect(page.locator('h1')).toContainText('Knowledge Explorer');
    await expect(page.getByText('Query the Second Brain knowledge mesh for insights')).toBeVisible();
  });

  // ── Search input renders ──────────────────────────────────────────
  test('search input renders with placeholder text', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('placeholder', 'Search the knowledge mesh...');
  });

  // ── Query button renders ──────────────────────────────────────────
  test('Query button renders and is initially disabled when input is empty', async ({ page }) => {
    await gotoKnowledge(page);

    const queryBtn = page.getByRole('button', { name: /Query/i });
    await expect(queryBtn).toBeVisible();
    await expect(queryBtn).toBeDisabled();
  });

  // ── Query button enables with input ──────────────────────────────
  test('Query button enables when search input has text', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('POST /user/login redirect handling');

    const queryBtn = page.getByRole('button', { name: /Query/i });
    await expect(queryBtn).not.toBeDisabled();
  });

  // ── Search returns results ────────────────────────────────────────
  test('submitting a query shows results from API mock', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('user login redirect');

    await page.getByRole('button', { name: /Query/i }).click();
    await page.waitForTimeout(500);

    // Mock returns 2 results
    await expect(page.getByText('reflector').first()).toBeVisible();
    await expect(page.getByText('idiom').first()).toBeVisible();
  });

  // ── Result cards show confidence ──────────────────────────────────
  test('result cards show confidence percentages', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('cross-tenant verification');

    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // k-1: confidence 0.92 → 92%, k-2: confidence 0.85 → 85%
    await expect(page.getByText('92%')).toBeVisible();
    await expect(page.getByText('85%')).toBeVisible();
  });

  // ── Result card content ───────────────────────────────────────────
  test('result cards show knowledge text from mock', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('known-noise findings');

    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    await expect(page.getByText(/Stopped re-surfacing known-noise findings/)).toBeVisible();
    await expect(page.getByText(/Accrued senior testing idiom/)).toBeVisible();
  });

  // ── Result card metadata: endpoint ───────────────────────────────
  test('result card with endpoint metadata shows endpoint field', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('login endpoint');

    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // k-1 has metadata.endpoint: 'POST /user/login'
    await expect(page.getByText('Endpoint: POST /user/login')).toBeVisible();
  });

  // ── Enter key submits search ──────────────────────────────────────
  test('pressing Enter submits the search query', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('API contract patterns');
    await input.press('Enter');
    await page.waitForTimeout(500);

    await expect(page.getByText(/Stopped re-surfacing|Accrued senior/).first()).toBeVisible();
  });

  // ── Empty query shows no results state ───────────────────────────
  test('empty results state shows when query has no matches', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/knowledge/query*', route =>
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
    await page.click('#nav-item-knowledge');
    await page.waitForSelector('#knowledge-screen');
    await page.waitForTimeout(SETTLEMENT);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('something unknown xyz');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    await expect(page.getByText('No Results')).toBeVisible();
    await expect(page.getByText('Your query returned no results.')).toBeVisible();
  });

  // ── API error shows Query Failed state ───────────────────────────
  test('query failure shows Query Failed empty state with Retry', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/knowledge/query*', route =>
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
    await page.click('#nav-item-knowledge');
    await page.waitForSelector('#knowledge-screen');
    await page.waitForTimeout(SETTLEMENT);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.fill('trigger error');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    await expect(page.getByText('Query Failed')).toBeVisible();
    await expect(page.getByText('Retry')).toBeVisible();
  });

  // ── Input is focusable ────────────────────────────────────────────
  test('search input is keyboard focusable', async ({ page }) => {
    await gotoKnowledge(page);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.focus();
    await expect(input).toBeFocused();
  });

});
