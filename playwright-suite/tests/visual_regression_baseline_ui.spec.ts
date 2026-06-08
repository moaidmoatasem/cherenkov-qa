import { test, expect } from '@playwright/test';

test('visual regression baseline UI', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto(process.env.API_URL || 'http://127.0.0.1:8000/');
  await expect(page).toHaveScreenshot('baseline.png');
});
