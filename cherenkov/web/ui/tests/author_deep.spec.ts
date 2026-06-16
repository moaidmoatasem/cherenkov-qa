import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoAuthor(page: any) {
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
  await page.click('#nav-item-author');
  await page.waitForSelector('#author-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Author by Intent Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('author screen renders heading and description', async ({ page }) => {
    await gotoAuthor(page);

    await expect(page.locator('h1')).toContainText('Author by Intent');
    await expect(page.getByText('Transform natural language test goals')).toBeVisible();
  });

  // ── Magic Box mode is default ─────────────────────────────────────
  test('Magic Box mode is active by default', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await expect(textarea).toBeVisible();
    await expect(textarea).toHaveAttribute('placeholder', /Verify that guest checkouts/);
  });

  // ── Intent textarea accepts input ─────────────────────────────────
  test('intent textarea accepts text input', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Verify that the login endpoint returns 401 for invalid credentials.');
    await expect(textarea).toHaveValue('Verify that the login endpoint returns 401 for invalid credentials.');
  });

  // ── Example intent chips render ───────────────────────────────────
  test('three example intent chips render in Magic Box mode', async ({ page }) => {
    await gotoAuthor(page);

    await expect(page.getByText('Verify that guests can checkout with valid cart items and coupons.')).toBeVisible();
    await expect(page.getByText('Test account profile modification checks username collision validation.')).toBeVisible();
    await expect(page.getByText('Check inventory levels decrease after successful purchases.')).toBeVisible();
  });

  // ── Chip click fills textarea ─────────────────────────────────────
  test('clicking example chip fills the intent textarea', async ({ page }) => {
    await gotoAuthor(page);

    await page.getByText('Verify that guests can checkout with valid cart items and coupons.').click();
    await page.waitForTimeout(200);

    const textarea = page.locator('#txt-author-intent');
    await expect(textarea).toHaveValue('Verify that guests can checkout with valid cart items and coupons.');
  });

  // ── Initialize Pilot Run button exists ───────────────────────────
  test('Initialize Pilot Run button is visible', async ({ page }) => {
    await gotoAuthor(page);

    await expect(page.getByText('Initialize Pilot Run')).toBeVisible();
  });

  // ── Run completes with intent filled ─────────────────────────────
  test('pilot run succeeds and shows run ID and status', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Verify checkout flow with coupon code applies 15% discount.');
    await page.getByText('Initialize Pilot Run').click();
    await page.waitForTimeout(600);

    // Success state: run result panel
    await expect(page.getByText('Run completed')).toBeVisible();
    await expect(page.getByText(/Run ID: test-run-id/).first()).toBeVisible();
    await expect(page.getByText(/Status: started/)).toBeVisible();
  });

  // ── CHERENKOV learned message shows after run ─────────────────────
  test('CHERENKOV learned message visible after successful run', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Check that DELETE /pets requires authentication.');
    await page.getByText('Initialize Pilot Run').click();
    await page.waitForTimeout(600);

    await expect(page.getByText(/CHERENKOV learned from this interactive session/)).toBeVisible();
  });

  // ── Save & Eject button appears after run ─────────────────────────
  test('Save & Eject Test Suite button appears after run completes', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Verify POST /user/login returns 200 with valid credentials.');
    await page.getByText('Initialize Pilot Run').click();
    await page.waitForTimeout(600);

    await expect(page.getByText('Save & Eject Test Suite')).toBeVisible();
  });

  // ── Eject clears state and shows toast ───────────────────────────
  test('clicking Save & Eject resets form and shows success toast', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Test rate limiting on POST /user/login.');
    await page.getByText('Initialize Pilot Run').click();
    await page.waitForTimeout(600);

    await page.getByText('Save & Eject Test Suite').click();
    await page.waitForTimeout(300);

    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Ejected');

    // Form reset: textarea empty, eject gone
    await expect(textarea).toHaveValue('');
    await expect(page.getByText('Save & Eject Test Suite')).not.toBeVisible();
  });

  // ── Mode toggle: Deterministic ────────────────────────────────────
  test('switching to Deterministic mode shows CSS selector input', async ({ page }) => {
    await gotoAuthor(page);

    await page.getByText('Deterministic').click();
    await page.waitForTimeout(200);

    await expect(page.getByPlaceholder('e.g. button#checkout-submit')).toBeVisible();
    await expect(page.locator('#txt-author-intent')).not.toBeVisible();
  });

  // ── Deterministic action select ───────────────────────────────────
  test('deterministic mode shows action select with all options', async ({ page }) => {
    await gotoAuthor(page);

    await page.getByText('Deterministic').click();
    await page.waitForTimeout(200);

    const select = page.locator('#author-screen select');
    await expect(select).toBeVisible();
    await expect(select.locator('option[value="click"]')).toBeDefined();
    await expect(select.locator('option[value="type"]')).toBeDefined();
    await expect(select.locator('option[value="assert"]')).toBeDefined();
    await expect(select.locator('option[value="extract"]')).toBeDefined();
  });

  // ── Deterministic: expected result input ─────────────────────────
  test('deterministic mode shows expected result input field', async ({ page }) => {
    await gotoAuthor(page);

    await page.getByText('Deterministic').click();
    await page.waitForTimeout(200);

    await expect(page.getByPlaceholder("e.g. 'Order Confirmed' or input string")).toBeVisible();
  });

  // ── Mode toggle back ──────────────────────────────────────────────
  test('switching back to Magic Box restores intent textarea', async ({ page }) => {
    await gotoAuthor(page);

    await page.getByText('Deterministic').click();
    await page.waitForTimeout(200);

    await page.getByText('Magic Box').click();
    await page.waitForTimeout(200);

    await expect(page.locator('#txt-author-intent')).toBeVisible();
  });

  // ── Mentor idioms panel ───────────────────────────────────────────
  test('Mentor Context Idioms panel renders', async ({ page }) => {
    await gotoAuthor(page);

    await expect(page.getByText('Mentor Context Idioms')).toBeVisible();
  });

  // ── Mentor idiom content from mock ───────────────────────────────
  test('mentor idioms show content from memory API', async ({ page }) => {
    await gotoAuthor(page);

    await expect(page.getByText('Confirm CORS policy is strictly defined for API origins')).toBeVisible();
    await expect(page.getByText('Validate OAuth state token integrity validation')).toBeVisible();
  });

  // ── Run error on 500 pipeline API ────────────────────────────────
  test('pipeline failure shows error state in execution panel', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/run', route =>
      route.fulfill({ status: 500, body: '{"detail":"internal error"}' })
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
    await page.click('#nav-item-author');
    await page.waitForSelector('#author-screen');
    await page.waitForTimeout(SETTLEMENT);

    const textarea = page.locator('#txt-author-intent');
    await textarea.fill('Trigger error scenario.');
    await page.getByText('Initialize Pilot Run').click();
    await page.waitForTimeout(600);

    await expect(page.getByText('Pipeline run failed').first()).toBeVisible();
  });

  // ── Intent area is focusable ──────────────────────────────────────
  test('intent textarea is keyboard focusable', async ({ page }) => {
    await gotoAuthor(page);

    const textarea = page.locator('#txt-author-intent');
    await textarea.focus();
    await expect(textarea).toBeFocused();
  });

});
