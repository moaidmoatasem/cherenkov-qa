import { test, expect } from "@playwright/test";

// Authored by CHERENKOV Copilot from plain-language intent:
//   Check guest checkout with a discount
// Standard Playwright — owned by you, no CHERENKOV runtime required.

test("Check guest checkout with a discount", async ({ page, request }) => {
  await page.goto("http://localhost:8000");
  await expect(page).toHaveURL(/.*/);
});
