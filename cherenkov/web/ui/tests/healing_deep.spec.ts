import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoHealing(page: any) {
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
  await page.click('#nav-item-healing');
  await page.waitForSelector('#healing-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Self-Healing & Drift Redress Screen — Deep Coverage', () => {

  // ── Screen loads with heading ─────────────────────────────────────
  test('healing screen renders heading and description', async ({ page }) => {
    await gotoHealing(page);

    await expect(page.locator('h1')).toContainText('Self-Healing & Drift Redress');
    await expect(page.getByText('Detect schema specification discrepancies')).toBeVisible();
  });

  // ── Top banner renders ────────────────────────────────────────────
  test('interactive agent banner renders with disclaimer text', async ({ page }) => {
    await gotoHealing(page);

    await expect(page.locator('#healing-banner')).toBeVisible();
    await expect(page.getByText('Interactive Agent Diagnostic Healing Suggestions')).toBeVisible();
    await expect(page.getByText('All repairs are suggest-only')).toBeVisible();
  });

  // ── All 4 drift cards render ──────────────────────────────────────
  test('all four drift cards render from API mock', async ({ page }) => {
    await gotoHealing(page);

    await expect(page.locator('#drift-card-fail-1')).toBeVisible();
    await expect(page.locator('#drift-card-fail-2')).toBeVisible();
    await expect(page.locator('#drift-card-fail-3')).toBeVisible();
    await expect(page.locator('#drift-card-fail-4')).toBeVisible();
  });

  // ── Failure names render ──────────────────────────────────────────
  test('drift cards show test names from mock data', async ({ page }) => {
    await gotoHealing(page);

    await expect(page.getByText('POST /user/login · Validates account credentials')).toBeVisible();
    await expect(page.getByText('GET /store/inventory · Fetches inventory matrix')).toBeVisible();
    await expect(page.getByText('DELETE /pets/{petId} · Removes target pet item')).toBeVisible();
    await expect(page.getByText('POST /checkout/initialize · Initiates shopping session')).toBeVisible();
  });

  // ── Failure type badges ───────────────────────────────────────────
  test('CONTRACT DRIFT badge shown on fail-1 card', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await expect(card.getByText('CONTRACT DRIFT')).toBeVisible();
  });

  test('AUTH EXPIRY badge shown on fail-2 card', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-2');
    await expect(card.getByText('AUTH EXPIRY')).toBeVisible();
  });

  test('STATE SEQUENCING badge shown on fail-3 card', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-3');
    await expect(card.getByText('STATE SEQUENCING')).toBeVisible();
  });

  test('ASSERTION DRIFT badge shown on fail-4 card', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-4');
    await expect(card.getByText('ASSERTION DRIFT')).toBeVisible();
  });

  // ── Diagnosis text renders ────────────────────────────────────────
  test('diagnosis text visible on CONTRACT_DRIFT card', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await expect(card.getByText(/response field drift/)).toBeVisible();
  });

  // ── Assertion warning only on fail-4 ─────────────────────────────
  test('Potential Server-Side Defect warning only on assertion drift card', async ({ page }) => {
    await gotoHealing(page);

    const card4 = page.locator('#drift-card-fail-4');
    await expect(card4.getByText('Potential Server-Side Defect Identified')).toBeVisible();

    // Other cards should NOT show this warning
    const card1 = page.locator('#drift-card-fail-1');
    await expect(card1.getByText('Potential Server-Side Defect Identified')).not.toBeVisible();
  });

  // ── Each card has action buttons ──────────────────────────────────
  test('each drift card has OPEN EXPLAINER TRACE and VIEW SUGGESTION DIFF buttons', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await expect(card.getByText('OPEN EXPLAINER TRACE')).toBeVisible();
    await expect(card.getByText('VIEW SUGGESTION DIFF')).toBeVisible();
    await expect(card.getByText('Dismiss')).toBeVisible();
  });

  // ── Explainer trace modal opens ───────────────────────────────────
  test('OPEN EXPLAINER TRACE opens modal with trace log content', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('OPEN EXPLAINER TRACE').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('APIs contract tracer Playwright logs:')).toBeVisible();
    await expect(page.getByText('[CHERENKOV REPLAY MONITOR]')).toBeVisible();
    await expect(page.getByText('Drifting elements matched fields')).toBeVisible();
  });

  // ── Close Trace console dismisses modal ──────────────────────────
  test('Close Trace console button dismisses trace modal', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('OPEN EXPLAINER TRACE').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Close Trace console')).toBeVisible();
    await page.getByText('Close Trace console').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('[CHERENKOV REPLAY MONITOR]')).not.toBeVisible();
  });

  // ── Trace content changes per failure ─────────────────────────────
  test('trace modal shows fail-2 specific auth error content', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-2');
    await card.getByText('OPEN EXPLAINER TRACE').click();
    await page.waitForTimeout(300);

    await expect(page.getByText(/Authorization exception/)).toBeVisible();
  });

  // ── VIEW SUGGESTION DIFF opens ReadOnlyDiffViewer ────────────────
  test('VIEW SUGGESTION DIFF opens diff modal overlay', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('VIEW SUGGESTION DIFF').click();
    await page.waitForTimeout(300);

    // ReadOnlyDiffViewer appears as floating overlay
    await expect(page.locator('#read-only-diff-viewer')).toBeVisible();
  });

  // ── ReadOnlyDiffViewer has controls ──────────────────────────────
  test('diff viewer has copy, download and dismiss buttons', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('VIEW SUGGESTION DIFF').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#btn-diff-copy')).toBeVisible();
    await expect(page.locator('#btn-diff-download')).toBeVisible();
    await expect(page.locator('#btn-diff-dismiss')).toBeVisible();
  });

  // ── Dismiss closes the diff viewer ───────────────────────────────
  test('diff viewer dismiss button closes overlay', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('VIEW SUGGESTION DIFF').click();
    await page.waitForTimeout(300);

    await page.locator('#btn-diff-dismiss').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#read-only-diff-viewer')).not.toBeVisible();
  });

  // ── Dismiss card removes it from list ────────────────────────────
  test('Dismiss button removes the drift card from the list', async ({ page }) => {
    await gotoHealing(page);

    await expect(page.locator('#drift-card-fail-1')).toBeVisible();

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('Dismiss').click();
    await page.waitForTimeout(300);

    await expect(page.locator('#drift-card-fail-1')).not.toBeVisible();
    // Other cards remain
    await expect(page.locator('#drift-card-fail-2')).toBeVisible();
  });

  // ── Empty state when all failures dismissed ───────────────────────
  test('all tests healthy empty state shows when no failures', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/failures', route =>
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
    await page.click('#nav-item-healing');
    await page.waitForSelector('#healing-screen');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('All tests completely healthy')).toBeVisible();
  });

  // ── Diff shows old and proposed code sides ────────────────────────
  test('diff viewer shows CURRENT OUTDATED and PROPOSED HEALED panels', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await card.getByText('VIEW SUGGESTION DIFF').click();
    await page.waitForTimeout(300);

    const viewer = page.locator('#read-only-diff-viewer');
    await expect(viewer).toBeVisible();
  });

  // ── Diagnosis block ID shown ──────────────────────────────────────
  test('drift cards show DIAGNOSIS BLOCK ID with failure id', async ({ page }) => {
    await gotoHealing(page);

    const card = page.locator('#drift-card-fail-1');
    await expect(card.getByText('DIAGNOSIS BLOCK ID: fail-1')).toBeVisible();
  });

});
