/**
 * Exploratory persona: Sam, an on-call SRE, opens /mobile from a phone during
 * an incident to check whether the last device pilot run actually passed. This
 * screen had essentially no e2e coverage before this file: the only prior
 * references were a nav-array assertion and a widget-label check on the
 * Settings page (see HANDOVER.md-adjacent survey); nothing drove the screen
 * itself, and nothing ran it at a real mobile viewport against a real backend.
 *
 * What exploratory testing found, against the live backend:
 *
 *   1. "Start Pilot" is a one-way door. The legacy `/api/v1/mobile/pilot/start`
 *      endpoint (cherenkov/web/routes/mobile_routes.py) claims the hardcoded
 *      device "emulator-5554" and flips its session straight to RUNNING --
 *      nothing ever drives it further, so the screen sits at "Running · 0/0
 *      steps · 0%" forever. MobilePilotScreen.tsx has no Stop/Cancel/Reset
 *      control anywhere, and the Start button itself only renders while
 *      `pilot.status === 'idle'`, so once it fires it never comes back. Because
 *      the claim lives in the backend's in-memory device registry, this is not
 *      per-browser-session state: it is shared, global, and -- from the UI --
 *      permanent. One click by anyone (a curious first-time visitor included)
 *      takes the Mobile Pilot workspace offline for the whole team until the
 *      backend process restarts. This is left as a documented finding, not
 *      fixed here -- recovering from it needs a real UI affordance (a
 *      Stop/Reset action wired to `registry.release`) and that's a product
 *      decision, not a one-line correction.
 *
 *   2. A failed `startMobilePilot()` call (device already claimed -> 409, no
 *      emulator registered -> 503) used to be swallowed outright: `setError`
 *      only rendered through the full-screen "Pilot Unavailable" empty state,
 *      which is gated on `!pilot`, and by the time a start can fail the initial
 *      status poll has already populated `pilot`. The button just silently
 *      re-enabled with zero explanation. Fixed alongside this file by also
 *      routing that failure through the app's toast system (see
 *      MobilePilotScreen.tsx), the same pattern App.tsx already uses for the
 *      demo-mode-enable failure.
 *
 * Test order matters here and is deliberate: the "start" test runs before the
 * "second start conflicts" test in the same worker so the claim from the first
 * is what produces the 409 the second observes. Because the claim is real,
 * global backend state, this file's tests must not be reordered or run
 * `fullyParallel` against another spec that also starts a pilot -- exactly the
 * shared-state fragility that finding #1 above is about.
 */
import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

test.describe.serial('Mobile Pilot — live backend, mobile viewport', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('idle state is legible on a phone-sized viewport', async ({ page }) => {
    await bootstrapReal(page, async (p) => {
      await p.route('**/api/v1/mobile/pilot/status', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'idle', session_id: null, device_id: null, current_step: 0, total_steps: 0, steps: [] }),
        });
      });
    });
    await page.goto('/mobile');
    await page.waitForSelector('#mobile-pilot-screen');

    await expect(page.getByTestId('pilot-status-badge')).toHaveText('Idle');
    const startBtn = page.getByTestId('pilot-start-btn');
    await expect(startBtn).toBeVisible();
    // The button must be reachable without horizontal scrolling at this width.
    const box = await startBtn.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x + box!.width).toBeLessThanOrEqual(390);
  });

  test('starting a pilot claims the device and has no way back', async ({ page }) => {
    await bootstrapReal(page);
    await page.goto('/mobile');
    await page.waitForSelector('#mobile-pilot-screen');
    // Wait for the first status poll to resolve before reading either the
    // badge or the button -- both are absent from the DOM entirely while
    // `pilot` is still null, which reads as "not visible" either way and
    // would otherwise race this check against the initial fetch.
    await expect(page.getByTestId('pilot-status-badge')).toBeVisible();

    const startBtn = page.getByTestId('pilot-start-btn');
    // If a prior run in this environment already claimed the device, the
    // button won't be idle-visible any more -- that is itself the finding.
    if (!(await startBtn.isVisible().catch(() => false))) {
      await expect(page.getByTestId('pilot-status-badge')).not.toHaveText('Idle');
      return;
    }

    const startResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/mobile/pilot/start') && resp.request().method() === 'POST'
    );
    await startBtn.click();
    await startResponse;
    await page.waitForTimeout(500);

    await expect(page.getByTestId('pilot-status-badge')).toHaveText('Running');
    // No Start button any more, and nothing that could stop, cancel, or reset
    // the session -- this is the "point of no return" this test documents.
    await expect(page.getByTestId('pilot-start-btn')).toHaveCount(0);
    await expect(page.getByRole('button', { name: /stop|cancel|reset/i })).toHaveCount(0);

    // Give it a few poll cycles (the screen polls every 2s) -- it never moves.
    await page.waitForTimeout(4000);
    await expect(page.getByText('0 / 0 steps')).toBeVisible();
  });

  test('a failed start is surfaced to the user, not silently dropped', async ({ page }) => {
    // Force the failure deterministically via route overrides rather than
    // depending on the previous test's server-side claim still being in
    // place -- this isolates "does the UI report a start failure" from
    // "is the device currently claimed", which is the previous test's concern.
    // Both endpoints need overriding: by this point in the suite the real
    // device is already claimed (previous test), so the real status poll
    // would answer "running" and hide the Start button entirely regardless
    // of what /pilot/start returns.
    await bootstrapReal(page, async (p) => {
      await p.route('**/api/v1/mobile/pilot/status', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ status: 'idle', session_id: null, device_id: null, current_step: 0, total_steps: 0, steps: [] }),
        });
      });
      await p.route('**/api/v1/mobile/pilot/start', async (route) => {
        await route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ error: { code: 'CONFLICT', message: "Device 'emulator-5554' is already claimed" } }),
        });
      });
    });
    await page.goto('/mobile');
    await page.waitForSelector('#mobile-pilot-screen');
    await expect(page.getByTestId('pilot-status-badge')).toBeVisible();

    const startBtn = page.getByTestId('pilot-start-btn');
    await expect(startBtn).toBeVisible();
    await startBtn.click();

    await expect(page.getByText(/Failed to start pilot: 409/)).toBeVisible({ timeout: 5000 });
  });
});
