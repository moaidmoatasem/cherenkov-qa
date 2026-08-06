/**
 * End-to-end journey tests against the live backend.
 *
 * The previous version of this file drove the pre-revamp screens (#nav-item-*,
 * #*-screen) and had been excluded from every run, so it asserted nothing.
 * This one covers the property the revamp is built on: the dashboard's
 * workflow comes from the backend, and the stepper reports what actually
 * happened rather than where the user is standing.
 *
 * Needs a real backend on :8001; skips cleanly when there is not one, the same
 * way headless-qa-user.spec.ts does.
 */
import { test, expect, Page } from '@playwright/test';

const API = 'http://127.0.0.1:8001';

let backendUp = false;

test.beforeAll(async ({ request }) => {
  try {
    const res = await request.get(`${API}/api/v1/health`, { timeout: 4000 });
    backendUp = res.ok();
  } catch {
    backendUp = false;
  }
});

test.beforeEach(async ({ page }) => {
  test.skip(!backendUp, 'needs a live backend on :8001');
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    localStorage.setItem('[copilot] tour_seen', 'true');
    localStorage.setItem('[cherenkov] onboarding_seen', 'true');
  });
});

async function stageStatuses(page: Page): Promise<Record<string, string>> {
  const entries = await page.$$eval('[data-testid^="journey-step-"]', (els) =>
    els.map((e) => [
      (e as HTMLElement).dataset.testid!.replace('journey-step-', ''),
      (e as HTMLElement).dataset.status!,
    ])
  );
  return Object.fromEntries(entries);
}

test.describe('Journey-driven information architecture', () => {
  test('the stepper is built from the backend journey', async ({ page, request }) => {
    const journeys = await (await request.get(`${API}/api/v1/journeys`)).json();
    const stages = journeys.journeys.find(
      (j: any) => j.id === journeys.default
    ).stages;

    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.getByTestId('journey-stepper').waitFor();

    // Same surfaces, same order as the journey the engine runs.
    for (const stage of stages) {
      await expect(page.getByTestId(`journey-step-${stage.surface}`)).toBeVisible();
    }
    const rendered = Object.keys(await stageStatuses(page));
    expect(rendered).toEqual(stages.map((s: any) => s.surface));
  });

  test('nothing is claimed complete when there is no run', async ({ page }) => {
    await page.goto('/triage', { waitUntil: 'domcontentloaded' });
    await page.getByTestId('journey-stepper').waitFor();

    // The old stepper lit every stage before the current one as done purely
    // because of where you were standing. Being on Triage is not evidence
    // that Generate ran.
    const statuses = await stageStatuses(page);
    for (const [surface, status] of Object.entries(statuses)) {
      expect(status, `${surface} must not claim progress without a run`).toBe(
        'not_started'
      );
    }
  });

  test('the stepper reflects a real run', async ({ page, request }) => {
    const launch = await request.post(
      `${API}/api/v1/journeys/api-conformance/runs`,
      { data: { spec_path: 'petstore.json' } }
    );
    test.skip(!launch.ok(), 'backend has no petstore.json in its working dir');
    const { run_id } = await launch.json();

    await page.goto(`/dashboard?run=${run_id}`, { waitUntil: 'domcontentloaded' });
    await page.getByTestId('journey-stepper').waitFor();

    // Generate covers ingest/plan/scenarios, so it moves as soon as the run
    // starts.
    await expect
      .poll(async () => (await stageStatuses(page))['authoring'], {
        timeout: 20000,
      })
      .not.toBe('not_started');

    // Triage and Knowledge are manual steps. A pipeline run must never mark
    // them done -- that would claim a human reviewed something they did not.
    const statuses = await stageStatuses(page);
    expect(statuses['triage']).toBe('not_started');
    expect(statuses['intelligence']).toBe('not_started');
  });

  test('a run stays addressable after it is started', async ({ request }) => {
    const launch = await request.post(
      `${API}/api/v1/journeys/api-conformance/runs`,
      { data: { spec_path: 'petstore.json' } }
    );
    test.skip(!launch.ok(), 'backend has no petstore.json in its working dir');
    const { run_id } = await launch.json();

    // The whole point of the run-identity work: an id returned by the API can
    // be looked up over the API.
    await expect
      .poll(
        async () => (await request.get(`${API}/api/v1/journeys/runs/${run_id}`)).status(),
        { timeout: 10000 }
      )
      .toBe(200);

    const state = await (
      await request.get(`${API}/api/v1/journeys/runs/${run_id}`)
    ).json();
    expect(state.journey_id).toBe('api-conformance');
    expect(state.steps.length).toBeGreaterThan(0);

    // And its event log is replayable, for a client that missed the socket.
    const events = await (
      await request.get(`${API}/api/v1/runs/${run_id}/events`)
    ).json();
    expect(Array.isArray(events.events)).toBe(true);
  });
});

test.describe('Navigation', () => {
  test('nav is derived from the journey, plus Settings and Mobile', async ({
    page,
    request,
  }) => {
    const journeys = await (await request.get(`${API}/api/v1/journeys`)).json();
    const loop = journeys.journeys
      .find((j: any) => j.id === journeys.default)
      .stages.map((s: any) => s.surface);

    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.getByTestId('nav-workspace-settings').waitFor({ timeout: 15000 });

    const nav = await page.$$eval('[data-testid^="nav-workspace-"]', (els) =>
      els.map((e) => (e as HTMLElement).dataset.testid!.replace('nav-workspace-', ''))
    );

    expect(nav).toEqual([...loop, 'settings', 'mobile']);
  });

  test('legacy deep links redirect instead of dropping you on Dashboard', async ({
    page,
  }) => {
    await page.goto('/divergences', { waitUntil: 'domcontentloaded' });
    // Polling the URL rather than waitForURL: that waits for the 'load' event,
    // which a full document load may never reach if an external font or asset
    // is unreachable. The redirect itself is what we are asserting.
    await expect
      .poll(() => new URL(page.url()).pathname, { timeout: 15000 })
      .toBe('/triage');
  });

  test('an unknown route falls back to the dashboard', async ({ page }) => {
    await page.goto('/no-such-page', { waitUntil: 'domcontentloaded' });
    await expect
      .poll(() => new URL(page.url()).pathname, { timeout: 15000 })
      .toBe('/dashboard');
  });

  test('switching workspaces changes the route', async ({ page }) => {
    await page.goto('/dashboard', { waitUntil: 'domcontentloaded' });
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForURL('**/triage', { timeout: 10000 });
    await expect(page.locator('#triage-workspace')).toBeVisible();
  });
});

test.describe('Multi-step journeys', () => {
  test('detected chains are reported with their evidence', async ({ request }) => {
    const res = await request.get(
      `${API}/api/v1/journeys/api-conformance/chains?spec_path=petstore.json`
    );
    test.skip(!res.ok(), 'backend has no petstore.json in its working dir');
    const { chains } = await res.json();

    expect(chains.map((c: any) => c.resource).sort()).toEqual([
      'order',
      'pet',
      'user',
    ]);

    const pet = chains.find((c: any) => c.resource === 'pet');
    // The id must come from the create response, not from a guess.
    const create = pet.steps.find((s: any) => s.creates_resource);
    expect(create.method).toBe('POST');
    expect(create.captures[0].name).toBe('petId');
    expect(pet.steps[1].uses).toEqual({ petId: '${petId}' });

    // Anything that writes to the target must say so.
    expect(pet.mutating).toBe(true);
  });
});
