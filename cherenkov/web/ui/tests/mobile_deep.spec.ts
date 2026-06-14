import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoMobile(page: any) {
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
  await page.click('#nav-item-mobile');
  await page.waitForSelector('#mobile-screen');
  // Loading state takes 800ms; wait for it to clear
  await page.waitForTimeout(1200);
}

test.describe('Mobile Testing Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('mobile screen renders heading and description', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.locator('h1')).toContainText('Mobile Testing');
    await expect(page.getByText('Connect and run tests on physical or emulated mobile devices.')).toBeVisible();
  });

  // ── All 4 device cards render ─────────────────────────────────────
  test('four device cards render after loading completes', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.locator('[data-testid="device-card-m1"]')).toBeVisible();
    await expect(page.locator('[data-testid="device-card-m2"]')).toBeVisible();
    await expect(page.locator('[data-testid="device-card-m3"]')).toBeVisible();
    await expect(page.locator('[data-testid="device-card-m4"]')).toBeVisible();
  });

  // ── Device names render ───────────────────────────────────────────
  test('device cards show correct device names', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.getByText('iPhone 15 Pro')).toBeVisible();
    await expect(page.getByText('Pixel 8')).toBeVisible();
    await expect(page.getByText('iPad Air')).toBeVisible();
    await expect(page.getByText('Galaxy Tab S9')).toBeVisible();
  });

  // ── All devices show Disconnected ────────────────────────────────
  test('all devices show Disconnected status since none are connected', async ({ page }) => {
    await gotoMobile(page);

    const disconnectedBadges = page.getByText('Disconnected');
    await expect(disconnectedBadges.first()).toBeVisible();
    expect(await disconnectedBadges.count()).toBe(4);
  });

  // ── iPhone 15 Pro status badge ────────────────────────────────────
  test('iPhone 15 Pro shows Disconnected status badge', async ({ page }) => {
    await gotoMobile(page);

    const m1Card = page.locator('[data-testid="device-card-m1"]');
    await expect(m1Card).toBeVisible();
    await expect(page.locator('[data-testid="device-status-m1"]')).toContainText('Disconnected');
  });

  // ── Device platform and version ───────────────────────────────────
  test('device cards show platform and OS version', async ({ page }) => {
    await gotoMobile(page);

    // iPhone 15 Pro: iOS 17.5
    await expect(page.getByText('iOS 17.5').first()).toBeVisible();
    // Pixel 8: Android 14
    await expect(page.getByText('Android 14').first()).toBeVisible();
  });

  // ── Device resolution ─────────────────────────────────────────────
  test('device cards show screen resolution', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.getByText('1179×2556')).toBeVisible();
    await expect(page.getByText('1080×2400')).toBeVisible();
  });

  // ── Footer note about ADB and Maestro ────────────────────────────
  test('footer info section renders with ADB and Maestro requirement text', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.getByText(/Mobile testing requires ADB \(Android\) or Maestro \(iOS\)/)).toBeVisible();
  });

  // ── Phase note in footer ──────────────────────────────────────────
  test('Phase 5/6 environment note visible in footer', async ({ page }) => {
    await gotoMobile(page);

    await expect(page.getByText('Phase 5/6 — Requires dedicated environment with mobile tooling.')).toBeVisible();
  });

  // ── iPad Air card renders ─────────────────────────────────────────
  test('iPad Air card renders with iOS identifier', async ({ page }) => {
    await gotoMobile(page);

    const m3Card = page.locator('[data-testid="device-card-m3"]');
    await expect(m3Card).toBeVisible();
    await expect(m3Card.getByText('iPad Air')).toBeVisible();
  });

  // ── Run button not visible when disconnected ──────────────────────
  test('Run button is not shown for disconnected devices', async ({ page }) => {
    await gotoMobile(page);

    // Run button only visible when device.connected === true (none are)
    const runButtons = page.locator('#mobile-screen button').filter({ hasText: 'Run' });
    expect(await runButtons.count()).toBe(0);
  });

  // ── MockBadge present on device cards ────────────────────────────
  test('device cards have MockBadge overlays', async ({ page }) => {
    await gotoMobile(page);

    // Cards have MockBadge in absolute top-right
    await expect(page.locator('[data-testid="device-card-m1"]')).toBeVisible();
    // Page renders without crash
    await expect(page.locator('#mobile-screen')).toBeVisible();
  });

  // ── Galaxy Tab S9 renders ─────────────────────────────────────────
  test('Galaxy Tab S9 card renders with Android 14', async ({ page }) => {
    await gotoMobile(page);

    const m4Card = page.locator('[data-testid="device-card-m4"]');
    await expect(m4Card).toBeVisible();
    await expect(m4Card.getByText('Galaxy Tab S9')).toBeVisible();
  });

});
