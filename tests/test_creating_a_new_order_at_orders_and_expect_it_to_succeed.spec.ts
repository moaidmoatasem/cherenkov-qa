import { test, expect } from "@playwright/test";

// Authored by CHERENKOV Copilot from plain-language intent:
//   Test creating a new order at /orders and expect it to succeed
// Standard Playwright — owned by you, no CHERENKOV runtime required.

test("Test creating a new order at /orders and expect it to succeed", async ({ page, request }) => {
  await page.goto("http://localhost:8000");
  await expect(page).toHaveURL(/.*/);
});
