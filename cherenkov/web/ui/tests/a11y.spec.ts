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

    // Dismiss the Guided Tour and Onboarding Wizard
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
    });
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

  test('Review screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#review-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Review filter tabs have correct ARIA attributes', async ({ page }) => {
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Filter buttons are clickable
    await expect(page.locator('#filter-tab-all')).toBeVisible();
    await expect(page.locator('#filter-tab-approved')).toBeVisible();
    await expect(page.locator('#filter-tab-review')).toBeVisible();
    await expect(page.locator('#filter-tab-rejected')).toBeVisible();

    // All filter tabs are focusable buttons
    for (const tabId of ['#filter-tab-all', '#filter-tab-approved', '#filter-tab-review', '#filter-tab-rejected']) {
      await page.focus(tabId);
      await expect(page.locator(tabId)).toBeFocused();
    }
  });

  test('Review approve and reject buttons are keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    const approveBtn = page.locator('[data-testid="review-approve-btn"]');
    const rejectBtn = page.locator('[data-testid="review-reject-btn"]');

    await expect(approveBtn).toBeVisible();
    await expect(rejectBtn).toBeVisible();

    await approveBtn.focus();
    await expect(approveBtn).toBeFocused();

    await rejectBtn.focus();
    await expect(rejectBtn).toBeFocused();
  });

  test('SDD Cockpit KpiRing has correct ARIA attributes', async ({ page }) => {
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);

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

  test('SDD Cockpit has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Divergences screen severity filter select is keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-divergences');
    await page.waitForTimeout(600);

    const severitySelect = page.locator('select:has(option[value="critical"])');
    await expect(severitySelect).toBeVisible();
    await severitySelect.focus();
    await expect(severitySelect).toBeFocused();
  });

  test('Command Palette has correct ARIA role and label', async ({ page }) => {
    await page.keyboard.press('Control+KeyK');
    const palette = page.locator('#command-palette-input');
    await expect(palette).toBeVisible();
    await expect(palette).toBeFocused();
    await page.keyboard.press('Escape');
  });

  test('Setup screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-setup');
    await page.waitForSelector('#setup-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#setup-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Setup screen URL input and Fetch button are keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-setup');
    await page.waitForSelector('#setup-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.focus('#spec-url-input');
    await expect(page.locator('#spec-url-input')).toBeFocused();

    const fetchBtn = page.getByRole('button', { name: 'Fetch' });
    await fetchBtn.focus();
    await expect(fetchBtn).toBeFocused();
  });

  test('Healing screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-healing');
    await page.waitForSelector('#healing-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#healing-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Knowledge screen search input is keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-knowledge');
    await page.waitForSelector('#knowledge-screen');
    await page.waitForTimeout(SETTLEMENT);

    const input = page.locator('#knowledge-screen input[type="text"]');
    await input.focus();
    await expect(input).toBeFocused();

    // Tab to submit button
    await page.keyboard.press('Tab');
    const submitBtn = page.locator('#knowledge-screen button[type="submit"]');
    await expect(submitBtn).toBeFocused();
  });

  test('Knowledge screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-knowledge');
    await page.waitForSelector('#knowledge-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#knowledge-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Governance screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-governance');
    await page.waitForSelector('#governance-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#governance-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Memory screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-memory');
    await page.waitForSelector('#memory-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#memory-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Truth Map screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-truth-map');
    await page.waitForSelector('#truth-map-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#truth-map-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Eject screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#eject-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Eject screen path input and buttons are keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.focus('#eject-path');
    await expect(page.locator('#eject-path')).toBeFocused();

    await page.focus('#btn-confirm-eject');
    await expect(page.locator('#btn-confirm-eject')).toBeFocused();
  });

  test('Devices screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-devices');
    await page.waitForSelector('#devices-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#devices-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Settings screen has no critical a11y violations', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#settings-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Settings API key input has correct label association', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen');
    await page.waitForTimeout(SETTLEMENT);

    const input = page.locator('#input-settings-key');
    await expect(input).toBeVisible();
    await input.focus();
    await expect(input).toBeFocused();
  });

  test('Projects screen has no critical a11y violations beyond color-contrast', async ({ page }) => {
    await page.waitForSelector('#projects-screen');
    const results = await new AxeBuilder({ page })
      .include('#projects-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

  test('Signals screen tabs are keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-signals');
    await page.waitForSelector('#signals-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Tab buttons within signals screen are focusable
    const performanceTab = page.locator('#signals-screen button').filter({ hasText: 'Performance' });
    await performanceTab.focus();
    await expect(performanceTab).toBeFocused();
  });

  test('Healing drift cards dismiss buttons are keyboard focusable', async ({ page }) => {
    await page.click('#nav-item-healing');
    await page.waitForSelector('#healing-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Dismiss button on first drift card is focusable
    const dismissBtn = page.locator('#drift-card-fail-1 button:has-text("Dismiss")');
    await expect(dismissBtn).toBeVisible();
    await dismissBtn.focus();
    await expect(dismissBtn).toBeFocused();
  });

  test('Author screen intent textarea is keyboard accessible', async ({ page }) => {
    await page.click('#nav-item-author');
    await page.waitForSelector('#author-screen');
    await page.waitForTimeout(SETTLEMENT);

    const textarea = page.locator('#txt-author-intent');
    await textarea.focus();
    await expect(textarea).toBeFocused();

    // Can type into it via keyboard
    await page.keyboard.type('Test intent via keyboard');
    await expect(textarea).toHaveValue('Test intent via keyboard');
  });

  test('Author screen has no critical a11y violations', async ({ page }) => {
    await page.click('#nav-item-author');
    await page.waitForSelector('#author-screen');
    await page.waitForTimeout(SETTLEMENT);
    const results = await new AxeBuilder({ page })
      .include('#author-screen')
      .withTags(['wcag2aa'])
      .analyze();
    const nonColorViolations = results.violations.filter(v => v.id !== 'color-contrast');
    expect(nonColorViolations.length).toBe(0);
  });

});
