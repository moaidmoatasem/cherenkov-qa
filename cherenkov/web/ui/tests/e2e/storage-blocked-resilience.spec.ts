/**
 * Exploratory persona: a user on a locked-down corporate browser (or Safari
 * private browsing, where `localStorage.setItem` throws `QuotaExceededError`
 * rather than just failing silently -- `getItem` still works, only writes
 * fail) opens a link a teammate shared straight into Triage. No existing spec
 * simulates blocked storage; every current test runs with full localStorage
 * access.
 *
 * What exploratory testing found before this file's companion fixes
 * (App.tsx, NavigationBar.tsx): the app went to a fully blank, white,
 * unrecoverable screen on a deep link -- no ErrorBoundary fallback, no reload
 * button, nothing in the DOM at all -- because the Guided Tour's `showTour`
 * `useState` initializer in App.tsx wrote to localStorage unconditionally on
 * any deep-link path, unguarded, during InnerApp's own render. That throw
 * happens above where `<ErrorBoundary>` is mounted (it wraps a child of
 * InnerApp's returned JSX, not InnerApp itself), so no boundary in the tree
 * could catch it -- React unmounts everything with nothing to fall back to.
 * Landing on `/` first was less catastrophic but still broken: that path skips
 * the tour's deep-link write, but NavigationBar's two unguarded persistence
 * effects (pinned surfaces, collapsed sections) threw on mount instead,
 * which *did* land inside the ErrorBoundary's subtree -- so at least "Something
 * went wrong" rendered, with no way to reach the app short of the Reload
 * button (which doesn't fix anything, since the same write fails again).
 *
 * Every localStorage write on both paths is now wrapped in try/catch,
 * matching the pattern already used elsewhere in the same files (App.tsx's
 * own `RECENTS_KEY` effect, `useDensity.ts`). This file is the regression
 * guard for that fix, and a permanent, repeatable way to simulate the failure
 * mode rather than needing a real Safari private window to prove it.
 */
import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

// A *returning* user: tour and onboarding were already completed on a normal
// visit (real writes, storage not yet blocked), then something in their
// environment starts blocking storage before this session -- a switch to
// private browsing, an IT policy rollout, ITP kicking in. Seeding this way
// (rather than leaving onboarding_seen unset) isolates the deep-link crash
// this file guards against from the separate, unrelated question of whether
// the onboarding wizard itself behaves with storage blocked.
const SEED_RETURNING_USER = () => {
  localStorage.setItem('[copilot] tour_seen', 'true');
  localStorage.setItem('[cherenkov] onboarding_seen', 'true');
};

// Only `setItem` throws from here on -- `getItem` keeps working and returns
// whatever was already there. This mirrors Safari ITP / private-mode behavior
// more precisely than blocking storage outright.
const BLOCK_STORAGE_WRITES = () => {
  Storage.prototype.setItem = function () {
    throw new DOMException('storage blocked', 'QuotaExceededError');
  };
};

test.describe('Resilience — localStorage writes blocked', () => {
  test('deep link into Triage renders the workspace, not a blank screen', async ({ page }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    await setupApiMocks(page);
    await page.addInitScript(SEED_RETURNING_USER);
    await page.addInitScript(BLOCK_STORAGE_WRITES);
    await page.goto('/triage');
    await page.waitForTimeout(800);

    expect(pageErrors, `uncaught exceptions with storage blocked: ${pageErrors.join('; ')}`).toEqual([]);
    // A blank screen has an empty <body> text and no landmark content --
    // assert real, specific UI is present, not just "no crash".
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    await expect(page.getByText('Triage', { exact: true }).first()).toBeVisible();
  });

  test('root path with storage blocked never shows the ErrorBoundary fallback', async ({ page }) => {
    const pageErrors: string[] = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    await setupApiMocks(page);
    await page.addInitScript(BLOCK_STORAGE_WRITES);
    await page.goto('/');
    await page.waitForTimeout(800);

    expect(pageErrors).toEqual([]);
    await expect(page.getByText('Something went wrong')).toHaveCount(0);
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();

    // First-run onboarding still opens normally (its own read path never
    // touches the blocked writes until the user acts) and Skip still works.
    const skip = page.getByTestId('onboarding-skip');
    if (await skip.isVisible().catch(() => false)) {
      await skip.click();
    }
    await page.waitForTimeout(300);
    await expect(page.getByText('Something went wrong')).toHaveCount(0);
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });
});
