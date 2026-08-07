import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

test.describe('UX & Accessibility Preferences', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-settings').click();
    await page.waitForTimeout(SETTLE);
  });

  test('Accessibility & Display panel renders with motion and density controls', async ({ page }) => {
    const panel = page.getByTestId('a11y-settings');
    await expect(panel).toBeVisible();
    await expect(panel.getByText('Accessibility & Display')).toBeVisible();

    await expect(page.getByTestId('motion-system')).toBeVisible();
    await expect(page.getByTestId('motion-reduce')).toBeVisible();
    await expect(page.getByTestId('motion-full')).toBeVisible();
    await expect(page.getByTestId('density-comfortable')).toBeVisible();
    await expect(page.getByTestId('density-compact')).toBeVisible();
  });

  test('density preference persists to localStorage and the html attribute', async ({ page }) => {
    const htmlAttr = () => page.evaluate(() => document.documentElement.getAttribute('data-density'));

    await expect(page.getByTestId('density-comfortable')).toBeChecked();

    await page.getByTestId('density-compact').check();
    await page.waitForTimeout(100);
    expect(await htmlAttr()).toBe('compact');

    const stored = await page.evaluate(() => localStorage.getItem('[cherenkov] ui_density'));
    expect(stored).toBe('compact');

    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLE);
    await expect(page.getByTestId('density-compact')).toBeChecked();
    expect(await htmlAttr()).toBe('compact');
  });

  test('motion override persists and drives the html data-motion attribute', async ({ page }) => {
    const motionAttr = () => page.evaluate(() => document.documentElement.getAttribute('data-motion'));

    await expect(page.getByTestId('motion-system')).toBeChecked();

    await page.getByTestId('motion-reduce').check();
    await page.waitForTimeout(100);
    expect(await motionAttr()).toBe('reduce');

    const stored = await page.evaluate(() => localStorage.getItem('prefers-reduced-motion'));
    expect(stored).toBe('reduce');

    await page.getByTestId('motion-full').check();
    await page.waitForTimeout(100);
    expect(await motionAttr()).toBe('full');
  });

  test('command palette is a modal dialog with a real focus trap', async ({ page }) => {
    await page.getByTestId('nav-workspace-dashboard').focus();
    await page.keyboard.press('Control+KeyK');
    await expect(page.getByTestId('command-palette')).toBeVisible();

    const dialog = page.getByTestId('command-palette');
    await expect(dialog).toHaveAttribute('role', 'dialog');
    await expect(dialog).toHaveAttribute('aria-modal', 'true');
    await expect(dialog).toHaveAttribute('aria-label', 'Command palette');

    await expect(page.locator('#command-palette-input')).toBeFocused();

    // Tab cycles inside the dialog: input -> close button -> wraps back.
    await page.keyboard.press('Tab');
    await expect(page.locator('#command-palette-input')).not.toBeFocused();

    // Shift+Tab from the first element wraps to the last focusable inside.
    await page.locator('#command-palette-input').focus();
    await page.keyboard.press('Shift+Tab');
    const focusInside = await page.evaluate(() =>
      document.querySelector('[data-testid="command-palette"]')?.contains(document.activeElement)
    );
    expect(focusInside).toBe(true);

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('command-palette')).not.toBeVisible();
  });

  test('keyboard map overlay traps focus while open', async ({ page }) => {
    await page.getByTestId('nav-workspace-dashboard').focus();
    await page.keyboard.press('?');
    await expect(page.getByTestId('keyboard-map-overlay')).toBeVisible();

    const focused = await page.evaluate(() =>
      document.querySelector('[data-testid="keyboard-map-overlay"]')?.contains(document.activeElement)
    );
    expect(focused).toBe(true);

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('keyboard-map-overlay')).not.toBeVisible();
  });
});
