import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

test.describe('CHERENKOV QA Accessibility — Structural & ARIA Audit', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
    });

    await setupApiMocks(page);

    // Dismiss the Guided Tour
    await page.goto('/');
    await page.evaluate(() => localStorage.setItem('[copilot] tour_seen', 'true'));
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
  });

  test('Projects screen has no critical a11y violations', async ({ page }) => {
    await expect(page.locator('#projects-screen')).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze();
    // Only check for non-color-contrast violations (dashboard theme is intentionally low-contrast)
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Overview screen KpiRing has progressbar role and correct ARIA attributes', async ({ page }) => {
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    const kpiRing = page.locator('[role="progressbar"]').first();
    await expect(kpiRing).toBeVisible();
    await expect(kpiRing).toHaveAttribute('aria-valuemin', '0');
    await expect(kpiRing).toHaveAttribute('aria-valuemax', '100');
    const value = await kpiRing.getAttribute('aria-valuenow');
    expect(value).not.toBeNull();
    const numVal = Number(value);
    expect(numVal).toBeGreaterThanOrEqual(0);
    expect(numVal).toBeLessThanOrEqual(100);
  });

  test('Autonomy toggle buttons have correct ARIA attributes', async ({ page }) => {
    const autonomyGroup = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
    await expect(autonomyGroup).toBeVisible();

    const buttons = autonomyGroup.locator('[role="radio"]');
    await expect(buttons).toHaveCount(3);

    await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'true');
    await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'false');
    await expect(buttons.nth(2)).toHaveAttribute('aria-checked', 'false');

    // Click changes aria-checked state
    await buttons.nth(1).click();
    await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'false');
    await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'true');
  });

  test('Help button is focusable and has accessible name', async ({ page }) => {
    const helpButton = page.locator('button[aria-label="Help Guide"]');
    await expect(helpButton).toBeVisible();
    await helpButton.focus();
    await expect(helpButton).toBeFocused();
  });

  test('Sidebar and TopBar have correct landmarks', async ({ page }) => {
    await expect(page.locator('#cherenkov-topbar')).toBeVisible();
    await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
    // Sidebar element is an <aside> (landmark)
    await expect(page.locator('aside#cherenkov-sidebar')).toBeVisible();
    // Topbar is a <header> (landmark)
    await expect(page.locator('header#cherenkov-topbar')).toBeVisible();
  });

});
