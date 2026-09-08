/**
 * Exploratory persona: Priya, a compliance/procurement lead evaluating whether
 * to trust CHERENKOV with her org's data before signing off on a purchase. She
 * opens the Enterprise Command Center first -- SLA, SOC2, GDPR, support -- because
 * that is the page that is supposed to earn the trust the rest of the product
 * asks for. She does not read source. She clicks the buttons and reads what
 * comes back.
 *
 * This surface had zero e2e coverage before this file (confirmed against
 * a11y.spec.ts's own WORKSPACES list, which omits it, and against every other
 * active spec in tests/e2e/ and tests/qa/). It also runs against the real
 * backend (bootstrapReal), not the api_mocks.ts fixtures -- the bug this file
 * exists to catch (a dev/preview-server proxy gap swallowing `/api/enterprise/*`
 * behind the SPA's own index.html) is invisible to a mocked run, because
 * page.route() intercepts the request before it ever reaches the proxy.
 *
 * Two things below were found broken during exploratory testing and fixed
 * alongside this file (see vite.config.ts and SupportPortal.tsx):
 *   1. `/api/enterprise/*` wasn't in the dev/preview proxy allowlist, so every
 *      panel here failed with "Unexpected token '<' ... is not valid JSON".
 *   2. The Support Portal's honest 501 ("ticketing isn't wired to a backend")
 *      rendered in success-green because the color check only looked for the
 *      literal word "Failed" in the message.
 *
 * One thing is flagged but deliberately left as-is, since fixing it means
 * deciding product behavior, not fixing a bug: the SOC2 "Security / Availability
 * / Privacy" badges on the Compliance tab are hardcoded JSX (100%, 100%, 85%),
 * never wired to the real `GET /api/enterprise/soc2/summary` endpoint that
 * already exists server-side. That's the exact "green verdict nobody measured"
 * pattern this project has already caught and fixed once at the CLI layer
 * (`check-suite`, see HANDOVER.md) -- on its own compliance page, unmeasured
 * numbers with no source ever change.
 */
import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

test.describe('Enterprise Workspace — live backend', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-enterprise').click();
    await page.waitForTimeout(400);
  });

  test('SLA Dashboard renders real backend data, not a JSON-parse error', async ({ page }) => {
    // The failure mode this guards against is not "element missing" -- it's a
    // raw JS exception string rendered as if it were content. Assert its
    // literal absence anywhere on the page, not just that the widget is empty.
    await expect(page.getByText(/Unexpected token|is not valid JSON/i)).toHaveCount(0);
    await expect(
      page.getByText(/No runs recorded yet|SLA metrics/i).or(page.getByText(/%|ms/))
    ).toBeVisible({ timeout: 10000 });
  });

  test('Compliance tab: SOC2 status badges are present but are static copy, not measured data', async ({ page }) => {
    await page.getByRole('button', { name: 'Compliance (SOC2 / GDPR)' }).click();
    await expect(page.getByText('SOC 2 Type II Reporting')).toBeVisible();

    // These three values are hardcoded in CompliancePanel.tsx. This assertion
    // is a characterization test, not an endorsement: if this ever starts
    // failing because someone wired the panel to the real soc2/summary
    // endpoint, that is progress -- update the assertion, don't just re-pin it.
    await expect(page.getByText('100% Operational')).toHaveCount(2);
    await expect(page.getByText('85% Operational')).toBeVisible();
  });

  test('Compliance tab: GDPR manual purge is a real, confirmed, destructive action', async ({ page }) => {
    await page.getByRole('button', { name: 'Compliance (SOC2 / GDPR)' }).click();

    let confirmMessage = '';
    page.once('dialog', (dialog) => {
      confirmMessage = dialog.message();
      dialog.accept();
    });

    const purgeResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/enterprise/gdpr/purge') && resp.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Trigger Manual Purge' }).click();
    const resp = await purgeResponse;

    expect(confirmMessage).toContain('cannot be undone');
    expect(resp.status()).toBe(200);
    await expect(page.getByText(/Successfully purged \d+ records/)).toBeVisible();
  });

  test('Support Portal: the honest "no ticketing backend" failure renders as a failure, not a success', async ({ page }) => {
    await page.getByRole('button', { name: 'Support Portal' }).click();

    await page.getByPlaceholder('Describe your issue...').fill(
      'Staging conformance run has read "no_data" for three days -- is the run store writing at all?'
    );
    const ticketResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/enterprise/support/ticket') && resp.request().method() === 'POST'
    );
    await page.getByRole('button', { name: 'Submit Ticket' }).click();
    const resp = await ticketResponse;

    // The backend deliberately answers 501 here (see enterprise_routes.py) rather
    // than faking a ticket ID -- confirm the UI doesn't undo that honesty by
    // painting the message green.
    expect(resp.status()).toBe(501);
    const result = page.getByTestId('ticket-result');
    await expect(result).toBeVisible();
    await expect(result).toHaveText(/unavailable|not wired/i);
    await expect(result).toHaveClass(/text-red-500/);
    await expect(result).not.toHaveClass(/text-green-500/);
  });
});
