import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

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

test.describe('Custom User Journey — Configured Security & Cloud Offload', () => {
  test('User provisions Gemini cloud model with internal egress and sets custom secrets', async ({ page }) => {
    await gotoSettings(page);

    // 1. User selects Gemini 2.5 Flash as the synthetic model provider
    await page.getByText('Gemini 2.5 Flash').click();
    await page.waitForTimeout(200);

    // 2. User sets Substrate Router Tier to "DEEP" for maximum reasoning
    const deepBtn = page.locator('#settings-screen button').filter({ hasText: /^deep$/i });
    await deepBtn.click();
    
    // 3. User restricts API Egress Policy to "INTERNAL" to maintain corporate security
    const internalBtn = page.locator('#settings-screen button').filter({ hasText: /^internal$/i });
    await internalBtn.click();

    // 4. User inputs their corporate API Gateway Secrets key into the Identity Vault
    await page.locator('#input-settings-key').fill('env-sec-test-9901-corporate');
    await expect(page.locator('#input-settings-key')).toHaveValue('env-sec-test-9901-corporate');

    // 5. User applies the new parameters
    await page.locator('#btn-settings-save').click();
    await page.waitForTimeout(800);

    // 6. System validates the settings were applied successfully
    await expect(page.getByText('Configurations saved successfully!')).toBeVisible();
    
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Settings saved successfully');
  });
});
