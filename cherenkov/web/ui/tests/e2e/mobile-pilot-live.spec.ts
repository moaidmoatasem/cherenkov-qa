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
 *   1. "Start Pilot" was a one-way door. The legacy `/api/v1/mobile/pilot/start`
 *      endpoint (cherenkov/web/routes/mobile_routes.py) claims the hardcoded
 *      device "emulator-5554" and flips its session straight to RUNNING --
 *      nothing ever drives it further, so the screen sat at "Running · 0/0
 *      steps · 0%" forever. MobilePilotScreen.tsx had no Stop/Cancel/Reset
 *      control anywhere, and the Start button itself only renders while
 *      `pilot.status === 'idle'`, so once it fired it never came back. Because
 *      the claim lives in the backend's in-memory device registry, this was
 *      not per-browser-session state: it was shared, global, and -- from the
 *      UI -- permanent. One click by anyone (a curious first-time visitor
 *      included) took the Mobile Pilot workspace offline for the whole team
 *      until the backend process restarted.
 *
 *      Fixed with a counterpart legacy endpoint, `POST /api/v1/mobile/pilot/stop`
 *      (mirrors `close_session`'s `registry.release`, but looks the session up
 *      by the hardcoded device id rather than a session id, since the legacy
 *      UI never learns a session id), and a "Stop Pilot" button in
 *      MobilePilotScreen.tsx that renders whenever status isn't idle. Verified
 *      the claim is really released server-side, not just hidden client-side,
 *      by re-checking from a second, unrelated page/tab below.
 *
 *   2. A failed `startMobilePilot()` call (device already claimed -> 409, no
 *      emulator registered -> 503) used to be swallowed outright: `setError`
 *      only rendered through the full-screen "Pilot Unavailable" empty state,
 *      which is gated on `!pilot`, and by the time a start can fail the initial
 *      status poll has already populated `pilot`. The button just silently
 *      re-enabled with zero explanation. Fixed by also routing that failure
 *      through the app's toast system (see MobilePilotScreen.tsx), the same
 *      pattern App.tsx already uses for the demo-mode-enable failure.
 *
 * Test order matters here and is deliberate: even with a working Stop button,
 * a test that fails partway through (before it reaches its own cleanup) still
 * leaves the real, shared device claimed for whichever test runs next. This
 * file's tests must not be reordered or run `fullyParallel` against another
 * spec that also starts a pilot.
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

  test('starting a pilot claims the device, and Stop actually releases it', async ({ page, context }) => {
    await bootstrapReal(page);
    await page.goto('/mobile');
    await page.waitForSelector('#mobile-pilot-screen');
    // Wait for the first status poll to resolve before reading either the
    // badge or the button -- both are absent from the DOM entirely while
    // `pilot` is still null, which reads as "not visible" either way and
    // would otherwise race this check against the initial fetch.
    await expect(page.getByTestId('pilot-status-badge')).toBeVisible();

    const startBtn = page.getByTestId('pilot-start-btn');
    // If a prior run in this environment already claimed the device and left
    // it claimed (e.g. a previous failed run in this same suite), release it
    // first so this test starts from the state it actually needs to prove
    // anything -- rather than silently skipping, which used to be the only
    // reasonable response when there was no way to release it.
    if (!(await startBtn.isVisible().catch(() => false))) {
      await page.getByTestId('pilot-stop-btn').click();
      await expect(startBtn).toBeVisible({ timeout: 5000 });
    }

    const startResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/mobile/pilot/start') && resp.request().method() === 'POST'
    );
    await startBtn.click();
    await startResponse;
    await page.waitForTimeout(500);

    await expect(page.getByTestId('pilot-status-badge')).toHaveText('Running');
    await expect(page.getByTestId('pilot-start-btn')).toHaveCount(0);
    const stopBtn = page.getByTestId('pilot-stop-btn');
    await expect(stopBtn).toBeVisible();

    // Give it a few poll cycles (the screen polls every 2s) -- nothing drives
    // the legacy session past RUNNING on its own, so it never moves by itself.
    await page.waitForTimeout(4000);
    await expect(page.getByText('0 / 0 steps')).toBeVisible();

    const stopResponse = page.waitForResponse(
      (resp) => resp.url().includes('/api/v1/mobile/pilot/stop') && resp.request().method() === 'POST'
    );
    await stopBtn.click();
    await stopResponse;
    await page.waitForTimeout(500);

    await expect(page.getByTestId('pilot-status-badge')).toHaveText('Idle');
    await expect(page.getByTestId('pilot-start-btn')).toBeVisible();
    await expect(page.getByTestId('pilot-stop-btn')).toHaveCount(0);

    // Prove the release is real backend state, not just this tab's local
    // state: a second, unrelated page in a fresh navigation sees idle too,
    // and can start its own pilot -- the whole point of fixing this.
    const page2 = await context.newPage();
    await page2.goto('/mobile');
    await page2.waitForSelector('#mobile-pilot-screen');
    await expect(page2.getByTestId('pilot-status-badge')).toHaveText('Idle');
    await expect(page2.getByTestId('pilot-start-btn')).toBeVisible();
    await page2.close();
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
