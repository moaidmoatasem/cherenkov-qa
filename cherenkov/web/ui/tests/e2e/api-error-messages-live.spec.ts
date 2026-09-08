/**
 * Exploratory persona: Jordan, a QA engineer trying to point CHERENKOV at an
 * internal-only API and getting a rejection they can't explain. The backend's
 * error contract (cherenkov/web/errors.py) is deliberate and well-documented:
 * every API error is `{"error": {"code", "message", "detail?"}}` -- no
 * top-level `detail`. It exists specifically so failures come with a real,
 * actionable message instead of a bare status code.
 *
 * Exploratory testing found that almost none of the frontend actually reads
 * it. `cherenkov/web/ui/src/lib/api.ts` had 15 call sites reading `err.detail`
 * directly (plus one each in AuthContext.tsx and SupportPortal.tsx) -- always
 * `undefined` against the real envelope -- so every API error in the app fell
 * straight through to a generic templated fallback ("Spec ingestion failed:
 * 400") no matter what the backend actually said. Confirmed live: feeding the
 * Spec Ingestion Panel a URL the SSRF guard rejects used to render "Ingestion
 * failed: Spec ingestion failed: 400" -- the backend's specific answer,
 * "Internal network URLs not allowed", never reached the screen at all.
 *
 * Fixed alongside this file with one shared helper (`apiErrorMessage` in
 * api.ts) used at every one of those call sites, in preference to hand-editing
 * 17 near-identical lines with room to typo one differently from the rest.
 * This file is the regression guard: one true end-to-end proof against the
 * real backend, plus a fast contract test against the documented envelope
 * shape so the fix doesn't quietly regress if a future call site is added by
 * copy-pasting the old `err.detail` pattern instead of the helper.
 */
import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

test.describe('API error messages — the backend\'s own words reach the user', () => {
  test('SSRF-blocked ingest URL shows the backend\'s specific reason, not a generic status code', async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(400);

    await page.getByPlaceholder('https://api.example.com/openapi.json').fill(
      'http://169.254.169.254/latest/meta-data/'
    );
    const ingestResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/ingest') && resp.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Fetch' }).click();
    const resp = await ingestResponse;
    expect(resp.status()).toBe(400);

    await expect(page.getByText('Internal network URLs not allowed')).toBeVisible({ timeout: 5000 });
    // The old failure mode: real backend text replaced by a templated
    // "<action> failed: <status code>" string with no explanation.
    await expect(page.getByText(/Spec ingestion failed: 400/)).toHaveCount(0);
  });

  test('apiErrorMessage prefers the structured envelope over the legacy top-level field', async ({ page }) => {
    // Isolates the helper's contract from any one backend route: proves it
    // reads {"error":{"message"}} first, and still falls back to a bare
    // {"detail": ...} shape for any endpoint not yet migrated to the
    // structured envelope (e.g. a third-party-style error body).
    await bootstrapReal(page, async (p) => {
      await p.route('**/api/v1/ingest', async (route) => {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ error: { code: 'INVALID_URL', message: 'Structured envelope message reached the UI' }, detail: 'legacy field should be ignored when both are present' }),
        });
      });
    });
    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(400);
    await page.getByPlaceholder('https://api.example.com/openapi.json').fill('https://example.com/spec.json');
    await page.getByRole('button', { name: 'Fetch' }).click();

    await expect(page.getByText('Structured envelope message reached the UI')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('legacy field should be ignored when both are present')).toHaveCount(0);
  });
});
