import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

test.describe('Navigation & IA Enhancements (N-1..N-8)', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.waitForTimeout(SETTLE);
  });

  test('N-1 Breadcrumbs render below the top bar and deep-link home', async ({ page }) => {
    const crumbs = page.getByTestId('breadcrumbs');
    await expect(crumbs).toBeVisible();
    await expect(crumbs.getByText('Home')).toBeVisible();
    await expect(crumbs.getByText('Dashboard')).toBeVisible();

    // Navigate to another surface and the trail follows.
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForTimeout(SETTLE);
    await expect(page.getByTestId('breadcrumbs').getByText('Triage')).toBeVisible();

    // Home crumb deep-links back to the dashboard.
    await page.getByTestId('breadcrumb-home').click();
    await page.waitForTimeout(SETTLE);
    await expect(page.locator('#dashboard-workspace')).toBeVisible();
  });

  test('N-6 "?" opens the keyboard map overlay and Esc closes it', async ({ page }) => {
    await page.keyboard.press('?');
    await expect(page.getByTestId('keyboard-map-overlay')).toBeVisible();
    await expect(page.getByTestId('keyboard-map-overlay').getByText('Keyboard Shortcuts')).toBeVisible();

    // The map only advertises shortcuts that exist.
    await expect(page.getByTestId('keyboard-map-overlay').getByText('g d')).toBeVisible();
    await expect(page.getByTestId('keyboard-map-overlay').getByText('g m')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('keyboard-map-overlay')).not.toBeVisible();
  });

  test('N-6 g-prefix chord navigates to a surface', async ({ page }) => {
    await page.keyboard.press('g');
    await page.keyboard.press('t');
    await page.waitForTimeout(SETTLE);
    await expect(page.locator('#triage-workspace')).toBeVisible();

    await page.keyboard.press('g');
    await page.keyboard.press('d');
    await page.waitForTimeout(SETTLE);
    await expect(page.locator('#dashboard-workspace')).toBeVisible();
  });

  test('N-5 pinning a workspace shows it in the Pinned section and persists', async ({ page }) => {
    await expect(page.getByTestId('nav-pin-triage')).toBeVisible();
    await page.getByTestId('nav-pin-triage').click();
    await page.waitForTimeout(200);

    const pinnedSection = page.getByTestId('nav-section-pinned');
    await expect(pinnedSection).toBeVisible();
    await expect(pinnedSection.getByTestId('nav-workspace-triage')).toBeVisible();

    // Unpin restores it to the Workspaces section.
    await page.getByTestId('nav-unpin-triage').click();
    await page.waitForTimeout(200);
    await expect(page.getByTestId('nav-section-pinned')).not.toBeVisible();
    await expect(page.getByTestId('nav-workspace-triage')).toBeVisible();

    // Repin and verify it survives a reload (localStorage-backed).
    await page.getByTestId('nav-pin-triage').click();
    await page.waitForTimeout(200);
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLE);
    await expect(page.getByTestId('nav-section-pinned').getByTestId('nav-workspace-triage')).toBeVisible();
  });

  test('N-4 command palette lists recently visited surfaces', async ({ page }) => {
    await page.keyboard.press('Control+k');
    await expect(page.locator('#command-palette-input')).toBeVisible();
    await expect(page.getByText('Recently visited').first()).toBeVisible();
    await expect(page.getByText('Go to Dashboard').first()).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('#command-palette-input')).not.toBeVisible();
  });

  test('N-8 project switcher is honest about its cosmetic scope', async ({ page }) => {
    const dropdown = page.getByTestId('project-selector-dropdown');
    await expect(dropdown).toBeVisible();
    const tip = await dropdown.getAttribute('title');
    expect(tip).toContain('cosmetic');
  });

  test('N-2 dashboard section landing links navigate', async ({ page }) => {
    await expect(page.getByTestId('dashboard-quick-links')).toBeVisible();
    await expect(page.getByTestId('quick-link-review-divergences')).toBeVisible();
    await page.getByTestId('quick-link-review-divergences').click();
    await page.waitForTimeout(SETTLE);
    await expect(page.locator('#triage-workspace')).toBeVisible();
  });
});
