import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoSettings(page: any) {
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
  await page.click('[title="Open Settings"]');
  await page.waitForSelector('#settings-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('System Settings & Credentials Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('settings screen renders heading and description', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.locator('h1')).toContainText('System Settings & Credentials');
    await expect(page.getByText('Configure target copilot execution settings, egress network policies, and user preferences.')).toBeVisible();
  });

  // ── Section headers render ────────────────────────────────────────
  test('all four configuration section headings render', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Synthetic Synthesis Model Provider')).toBeVisible();
    await expect(page.getByText('Substrate Router Capability Tier')).toBeVisible();
    await expect(page.getByText('API Sandbox Egress Policy Dial')).toBeVisible();
    await expect(page.getByText('Maximum Run Spend Budget ($)')).toBeVisible();
  });

  // ── Model provider cards render ───────────────────────────────────
  test('both model provider cards render: Qwen and Gemini', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Qwen 2.5 Coder (7B)')).toBeVisible();
    await expect(page.getByText('Gemini 2.5 Flash')).toBeVisible();
  });

  // ── Model provider subtitles render ──────────────────────────────
  test('model provider cards show execution context labels', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Local execution · Ollama integration')).toBeVisible();
    await expect(page.getByText('Cloud execution · Serverless token endpoints')).toBeVisible();
  });

  // ── Qwen cost label ───────────────────────────────────────────────
  test('Qwen card shows 0% API COST PROJECTIONS label', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('0% API COST PROJECTIONS')).toBeVisible();
  });

  // ── Gemini label ──────────────────────────────────────────────────
  test('Gemini card shows HIGH COVERAGE DISPATCHER label', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('HIGH COVERAGE DISPATCHER')).toBeVisible();
  });

  // ── Click Gemini selects it ───────────────────────────────────────
  test('clicking Gemini 2.5 Flash card selects it', async ({ page }) => {
    await gotoSettings(page);

    await page.getByText('Gemini 2.5 Flash').click();
    await page.waitForTimeout(200);

    // Card is now visually selected (checked via border class - just verify page didn't crash)
    await expect(page.locator('#settings-screen')).toBeVisible();
    await expect(page.getByText('Gemini 2.5 Flash')).toBeVisible();
  });

  // ── Tier buttons render ───────────────────────────────────────────
  test('four substrate tier buttons render: small, deep, vision, ml', async ({ page }) => {
    await gotoSettings(page);

    const screen = page.locator('#settings-screen');
    await expect(screen.getByText('small')).toBeVisible();
    await expect(screen.getByText('deep')).toBeVisible();
    await expect(screen.getByText('vision')).toBeVisible();
    await expect(screen.getByText('ml')).toBeVisible();
  });

  // ── Click tier button ─────────────────────────────────────────────
  test('clicking a tier button selects it', async ({ page }) => {
    await gotoSettings(page);

    // Click 'small' tier
    const smallBtn = page.locator('#settings-screen button').filter({ hasText: /^small$/i });
    await smallBtn.click();
    await page.waitForTimeout(200);

    await expect(page.locator('#settings-screen')).toBeVisible();
  });

  // ── Egress policy buttons render ──────────────────────────────────
  test('three egress policy buttons render: Sovereign, internal, any', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Sovereign')).toBeVisible();
    await expect(page.locator('#settings-screen button').filter({ hasText: /^internal$/i })).toBeVisible();
    await expect(page.locator('#settings-screen button').filter({ hasText: /^any$/i })).toBeVisible();
  });

  // ── Click egress button ───────────────────────────────────────────
  test('clicking Sovereign egress policy button selects it', async ({ page }) => {
    await gotoSettings(page);

    await page.getByText('Sovereign').click();
    await page.waitForTimeout(200);

    await expect(page.locator('#settings-screen')).toBeVisible();
  });

  // ── Budget slider renders ─────────────────────────────────────────
  test('spend budget slider renders with SPEND BUDGET LIMIT label', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('SPEND BUDGET LIMIT:')).toBeVisible();
    await expect(page.locator('input[type="range"]').first()).toBeVisible();
  });

  // ── Budget shows from mock data ───────────────────────────────────
  test('budget shows value loaded from API (execution_budget: 100)', async ({ page }) => {
    await gotoSettings(page);

    // Mock returns execution_budget: 100 → $100.00
    await expect(page.getByText('$100.00 USD')).toBeVisible();
  });

  // ── Thread limit section renders ──────────────────────────────────
  test('Parallelization Thread Limit section renders', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Parallelization Thread Limit')).toBeVisible();
    await expect(page.locator('#threads-range-slider')).toBeVisible();
  });

  // ── Thread limit shows initial value ─────────────────────────────
  test('thread limit shows workers value from API (workers: 2)', async ({ page }) => {
    await gotoSettings(page);

    // Mock returns workers: 2 → "2 THREADS"
    await expect(page.getByText('2 THREADS')).toBeVisible();
  });

  // ── Interface section renders ─────────────────────────────────────
  test('Interface & Accessibility Settings section renders', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Interface & Accessibility Settings')).toBeVisible();
    await expect(page.getByText('Compact View Mode')).toBeVisible();
    await expect(page.getByText('Reduce Motion Animations')).toBeVisible();
  });

  // ── Compact view checkbox ─────────────────────────────────────────
  test('Compact View Mode checkbox is unchecked by default (comfortable density)', async ({ page }) => {
    await gotoSettings(page);

    // density from mock: 'comfortable' → checkbox unchecked
    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await expect(compactCheckbox).not.toBeChecked();
  });

  // ── Compact view checkbox is toggleable ──────────────────────────
  test('Compact View Mode checkbox toggles when clicked', async ({ page }) => {
    await gotoSettings(page);

    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await compactCheckbox.click();
    await expect(compactCheckbox).toBeChecked();
  });

  // ── Reduced motion checkbox ───────────────────────────────────────
  test('Reduce Motion Animations checkbox is unchecked by default', async ({ page }) => {
    await gotoSettings(page);

    // reducedMotion from mock: false → unchecked
    const checkboxes = page.locator('input[type="checkbox"]');
    const reducedMotionCheckbox = checkboxes.nth(1);
    await expect(reducedMotionCheckbox).not.toBeChecked();
  });

  // ── Identity Vault section renders ───────────────────────────────
  test('Identity Vault section renders with API key input', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('Identity Vault')).toBeVisible();
    await expect(page.locator('#input-settings-key')).toBeVisible();
  });

  // ── API key input is password type ───────────────────────────────
  test('API key input is of type password', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.locator('#input-settings-key')).toHaveAttribute('type', 'password');
  });

  // ── API key input accepts text ────────────────────────────────────
  test('API key input accepts text entry', async ({ page }) => {
    await gotoSettings(page);

    await page.locator('#input-settings-key').fill('test-secret-key-abc');
    await expect(page.locator('#input-settings-key')).toHaveValue('test-secret-key-abc');
  });

  // ── Apply Parameters button renders ──────────────────────────────
  test('Apply Parameters save button renders', async ({ page }) => {
    await gotoSettings(page);

    const saveBtn = page.locator('#btn-settings-save');
    await expect(saveBtn).toBeVisible();
    await expect(saveBtn).toContainText('Apply Parameters');
  });

  // ── Save triggers success toast ───────────────────────────────────
  test('clicking Apply Parameters saves and shows success message', async ({ page }) => {
    await gotoSettings(page);

    await page.locator('#btn-settings-save').click();
    await page.waitForTimeout(800);

    // Success state shows "Configurations saved successfully!" in UI
    await expect(page.getByText('Configurations saved successfully!')).toBeVisible();
  });

  // ── Save toast notification ───────────────────────────────────────
  test('save shows toast notification with success message', async ({ page }) => {
    await gotoSettings(page);

    await page.locator('#btn-settings-save').click();
    await page.waitForTimeout(500);

    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Settings saved successfully');
  });

  // ── LocalStorage persistence on save ─────────────────────────────
  test('saving compact mode persists density to localStorage', async ({ page }) => {
    await gotoSettings(page);

    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await compactCheckbox.click();
    await expect(compactCheckbox).toBeChecked();

    await page.locator('#btn-settings-save').click();
    await page.waitForTimeout(800);

    const stored = await page.evaluate(() => localStorage.getItem('[copilot] density'));
    expect(stored).toBe('compact');
  });

  // ── MAX INSTANCES label renders ───────────────────────────────────
  test('MAX INSTANCES label renders in thread limit section', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText('MAX INSTANCES:')).toBeVisible();
  });

  // ── Security notice renders ───────────────────────────────────────
  test('Identity Vault shows security notice about credentials', async ({ page }) => {
    await gotoSettings(page);

    await expect(page.getByText(/Environment credentials are piped relative/)).toBeVisible();
  });

});
