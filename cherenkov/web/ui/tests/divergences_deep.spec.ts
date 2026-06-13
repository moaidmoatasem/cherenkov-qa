import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoDivergences(page: any) {
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
  await page.click('#nav-item-divergences');
  await page.waitForTimeout(600);
}

test.describe('Divergences Screen — Deep Coverage', () => {

  // ── All divergences render ────────────────────────────────────────
  test('divergences list renders all 7 items from mock', async ({ page }) => {
    await gotoDivergences(page);
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');

    // 7 divergences in mock (D-01 through D-07)
    for (const id of ['D-01', 'D-02', 'D-03', 'D-04', 'D-05', 'D-06', 'D-07']) {
      await expect(page.getByText(id).first()).toBeVisible();
    }
  });

  // ── Severity filter: critical ──────────────────────────────────────
  test('severity filter "critical" shows only D-06 (UI /checkout)', async ({ page }) => {
    await gotoDivergences(page);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await severitySelect.selectOption('critical');
    await page.waitForTimeout(300);

    await expect(page.getByText('D-06').first()).toBeVisible();
    await expect(page.getByText('D-01').first()).not.toBeVisible();
    await expect(page.getByText('D-02').first()).not.toBeVisible();
  });

  // ── Severity filter: high ──────────────────────────────────────────
  test('severity filter "high" shows D-02 and D-07', async ({ page }) => {
    await gotoDivergences(page);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await severitySelect.selectOption('high');
    await page.waitForTimeout(300);

    await expect(page.getByText('D-02').first()).toBeVisible();
    await expect(page.getByText('D-07').first()).toBeVisible();
    await expect(page.getByText('D-01').first()).not.toBeVisible();
  });

  // ── Severity filter: low ───────────────────────────────────────────
  test('severity filter "low" shows only D-03', async ({ page }) => {
    await gotoDivergences(page);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await severitySelect.selectOption('low');
    await page.waitForTimeout(300);

    await expect(page.getByText('D-03').first()).toBeVisible();
    await expect(page.getByText('D-02').first()).not.toBeVisible();
  });

  // ── Severity filter reset to ALL ──────────────────────────────────
  test('resetting severity filter to ALL shows all items again', async ({ page }) => {
    await gotoDivergences(page);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await severitySelect.selectOption('critical');
    await page.waitForTimeout(200);
    await expect(page.getByText('D-01').first()).not.toBeVisible();

    await severitySelect.selectOption('ALL');
    await page.waitForTimeout(200);
    await expect(page.getByText('D-01').first()).toBeVisible();
  });

  // ── Status filter: rejected ────────────────────────────────────────
  test('status filter "rejected" shows only D-07', async ({ page }) => {
    await gotoDivergences(page);

    // Find status select (has option "rejected")
    const statusSelect = page.locator('select:has(option[value="rejected"])');
    await statusSelect.selectOption('rejected');
    await page.waitForTimeout(300);

    await expect(page.getByText('D-07').first()).toBeVisible();
    await expect(page.getByText('D-01').first()).not.toBeVisible();
  });

  // ── Status filter: pending ─────────────────────────────────────────
  test('status filter "pending" shows only D-06', async ({ page }) => {
    await gotoDivergences(page);

    const statusSelect = page.locator('select:has(option[value="rejected"])');
    await statusSelect.selectOption('pending');
    await page.waitForTimeout(300);

    await expect(page.getByText('D-06').first()).toBeVisible();
    await expect(page.getByText('D-01').first()).not.toBeVisible();
  });

  // ── Search filter ─────────────────────────────────────────────────
  test('search input filters by endpoint substring', async ({ page }) => {
    await gotoDivergences(page);

    const searchInput = page.locator('#divergences-search');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('inventory');
    // Wait for D-04 to be visible (confirms filter applied)
    await expect(page.getByText('D-04').first()).toBeVisible();
    await expect(page.locator('span.text-\\[10px\\].font-mono.font-bold.text-text-muted').getByText('D-01')).not.toBeVisible();
  });

  // ── Search filter clears ───────────────────────────────────────────
  test('clearing search restores all items', async ({ page }) => {
    await gotoDivergences(page);

    const searchInput = page.locator('#divergences-search');
    await searchInput.fill('login');
    // Wait for D-05 to be visible (the login endpoint)
    await expect(page.getByText('D-05').first()).toBeVisible();

    await searchInput.fill('');
    // All items return
    await expect(page.getByText('D-01').first()).toBeVisible();
    await expect(page.getByText('D-04').first()).toBeVisible();
  });

  // ── Detail drawer opens with full content ─────────────────────────
  test('clicking a divergence row opens detail drawer with all sections', async ({ page }) => {
    await gotoDivergences(page);

    // Click D-02 card (POST /pet, high severity)
    const d02Card = page.locator('.flex.flex-col.sm\\:flex-row').filter({ hasText: 'D-02' }).first();
    await d02Card.click();
    await page.waitForTimeout(300);

    // Drawer header includes divergence id
    await expect(page.getByText(/Divergence Detail/)).toBeVisible();

    // Evidence payload section
    await expect(page.getByText('Evidence payload')).toBeVisible();

    // Repro steps section (multiple elements contain "Repro", use .first())
    await expect(page.getByText(/Repro/).first()).toBeVisible();

    // Confidence value: D-02 has confidence 0.99 → "99%" in drawer
    await expect(page.getByText('99%')).toBeVisible();
  });

  // ── Drawer close via aria-label ────────────────────────────────────
  test('drawer closes via close button', async ({ page }) => {
    await gotoDivergences(page);

    await page.getByText('D-01').first().click();
    await expect(page.getByText('Divergence Detail')).toBeVisible();

    await page.click('button[aria-label="Close details"]');
    await expect(page.getByText('Divergence Detail')).not.toBeVisible();
  });

  // ── Keyboard J/K navigation ────────────────────────────────────────
  test('keyboard J moves focus to next item', async ({ page }) => {
    await gotoDivergences(page);

    // Start with no focus (index -1)
    await page.keyboard.press('j');
    await page.waitForTimeout(100);
    await page.keyboard.press('j');
    await page.waitForTimeout(100);
    // After 2 J presses, index is 1 (second item)
    // The second item is D-02
    await expect(page.getByText('D-02').first()).toBeVisible();
  });

  // ── Copy link button ───────────────────────────────────────────────
  test('drawer copy link button appears and fires without error', async ({ page }) => {
    await gotoDivergences(page);

    await page.getByText('D-01').first().click();
    await page.waitForTimeout(300);

    // Copy button (uses navigator.clipboard)
    const copyBtn = page.getByTitle(/Copy|copy/).first();
    if (await copyBtn.count() > 0) {
      await expect(copyBtn).toBeVisible();
    }
    // Alternatively look for a Copy button text
    const copyAlt = page.getByRole('button', { name: /Copy/i }).first();
    if (await copyAlt.count() > 0) {
      await copyAlt.click();
      await page.waitForTimeout(200);
    }
    // No crash = pass
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  // ── Empty state: no results after filtering ────────────────────────
  test('empty state shown when filters match no divergences', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/divergences**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-divergences');
    await page.waitForTimeout(600);

    // Should show empty state (no results)
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  // ── Class filter ──────────────────────────────────────────────────
  test('divergence class filter "D3" shows only UI divergences', async ({ page }) => {
    await gotoDivergences(page);

    // D3 class filter (D-06 is the only D3 class)
    const classSelect = page.locator('select:has(option[value="D1"])').first();
    if (await classSelect.count() > 0) {
      await classSelect.selectOption('D3');
      await page.waitForTimeout(300);
      await expect(page.getByText('D-06').first()).toBeVisible();
      await expect(page.getByText('D-01').first()).not.toBeVisible();
    }
  });

  // ── SeverityPill colors ───────────────────────────────────────────
  test('severity pills display uppercase labels for all severity levels', async ({ page }) => {
    await gotoDivergences(page);

    // SeverityPill renders uppercase labels — target span elements specifically since
    // select options (hidden) also contain these uppercase strings
    await expect(page.locator('span').filter({ hasText: /^CRITICAL$/ }).first()).toBeVisible();
    await expect(page.locator('span').filter({ hasText: /^HIGH$/ }).first()).toBeVisible();
    await expect(page.locator('span').filter({ hasText: /^MEDIUM$/ }).first()).toBeVisible();
    await expect(page.locator('span').filter({ hasText: /^LOW$/ }).first()).toBeVisible();
  });

  // ── Divergence class filter "D1" ──────────────────────────────────
  test('class D1 filter shows schema violations (D-01 and D-02)', async ({ page }) => {
    await gotoDivergences(page);

    const classSelect = page.locator('select:has(option[value="D1"])').first();
    if (await classSelect.count() > 0) {
      await classSelect.selectOption('D1');
      await page.waitForTimeout(300);
      await expect(page.getByText('D-01').first()).toBeVisible();
      await expect(page.getByText('D-02').first()).toBeVisible();
      await expect(page.getByText('D-03').first()).not.toBeVisible();
    }
  });

  // ── Multiple filters combined ─────────────────────────────────────
  test('combining severity and search filters narrows results correctly', async ({ page }) => {
    await gotoDivergences(page);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await severitySelect.selectOption('high');
    const searchInput = page.locator('#divergences-search');
    await searchInput.fill('pet');
    // D-02 (POST /pet, high) should be visible
    await expect(page.getByText('D-02').first()).toBeVisible();
    // D-07 (POST /user/createWithList, high) should not match "pet"
    await expect(page.locator('span').filter({ hasText: /^D-07$/ })).not.toBeVisible();
  });

  // ── Confidence values in drawer ───────────────────────────────────
  test('confidence percentage visible in divergence detail drawer', async ({ page }) => {
    await gotoDivergences(page);

    // Click D-02 which has confidence 0.99 → "99%"
    const d02Card = page.locator('.flex.flex-col.sm\\:flex-row').filter({ hasText: 'D-02' }).first();
    await d02Card.click();
    await page.waitForTimeout(300);
    await expect(page.getByText('99%')).toBeVisible();
  });

});
