/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Pins the offline fallback journey to the shipped builtin journey.
 *
 * FALLBACK_STAGES (src/journey/fallback.ts) is what the shell renders while
 * the backend is unreachable. The shell promises it renders the same loop
 * offline as online, so this test compares it against GET /api/v1/journeys --
 * if the engine side changes the loop, this fails and a human updates the
 * fallback instead of the two silently disagreeing.
 *
 * Needs a real backend on :8001; skips cleanly when there is not one.
 */
import { test, expect } from '@playwright/test';
import { FALLBACK_STAGES } from '../../src/journey/fallback';

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

test('the offline fallback journey mirrors the shipped builtin journey', async ({
  request,
}) => {
  test.skip(!backendUp, 'needs a live backend on :8001');

  const journeys = await (await request.get(`${API}/api/v1/journeys`)).json();
  const server = journeys.journeys.find((j: any) => j.id === journeys.default);

  test.skip(!server, 'backend does not serve a default journey');

  const serverStages = (server.stages as any[]).map((s) => ({
    surface: s.surface,
    label: s.label,
    blurb: s.blurb,
  }));

  expect(serverStages.map((s) => s.surface)).toEqual(
    FALLBACK_STAGES.map((s) => s.surface)
  );

  for (let i = 0; i < FALLBACK_STAGES.length; i++) {
    expect(FALLBACK_STAGES[i].label, `surface ${FALLBACK_STAGES[i].surface} label`).toBe(
      serverStages[i].label
    );
    expect(FALLBACK_STAGES[i].blurb, `surface ${FALLBACK_STAGES[i].surface} blurb`).toBe(
      serverStages[i].blurb
    );
  }
});
