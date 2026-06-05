import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('CHERENKOV QA Accessibility Audit', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
    });
    await page.goto('/');
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(1000);
  });

  test('Projects screen should have no automated a11y violations', async ({ page }) => {
    await expect(page.locator('#projects-screen')).toBeVisible();
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('Overview screen with KpiRing should have no automated a11y violations', async ({ page }) => {
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    const results = await new AxeBuilder({ page }).analyze();
    expect(results.violations).toEqual([]);
  });

  test('Sidebar and TopBar autonomy toggle should have no automated a11y violations', async ({ page }) => {
    const topbar = page.locator('#cherenkov-topbar');
    await expect(topbar).toBeVisible();
    const sidebar = page.locator('#cherenkov-sidebar');
    await expect(sidebar).toBeVisible();
    const results = await new AxeBuilder({ page })
      .include('#cherenkov-topbar')
      .include('#cherenkov-sidebar')
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('Autonomy toggle buttons have correct ARIA attributes', async ({ page }) => {
    const autonomyGroup = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
    await expect(autonomyGroup).toBeVisible();

    const buttons = autonomyGroup.locator('[role="radio"]');
    await expect(buttons).toHaveCount(3);

    await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'true');
    await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'false');
    await expect(buttons.nth(2)).toHaveAttribute('aria-checked', 'false');

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

  test('KpiRing has progressbar role and correct ARIA attributes', async ({ page }) => {
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
});
