import { test, expect } from '@playwright/test';
import { bootstrap } from '../qa/page-objects';

const SETTLE = 400;

test.describe('Phase 4 Journeys (J1-J3)', () => {
  test('J1a: vision fallback banner appears only when OCR is installed', async ({ page }) => {
    await page.route('**/api/v1/ocr/status', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ installed: true, binary: 'tesseract', version: '5.4.0', error: '' }),
      })
    );
    await bootstrap(page);
    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(SETTLE);

    const banner = page.getByTestId('vision-fallback-banner');
    await expect(banner).toBeVisible();
    await expect(banner).toContainText('tesseract');

    await page.getByTestId('btn-vision-fallback-triage').click();
    await page.waitForTimeout(SETTLE);
    await expect(page).toHaveURL(/\/triage/);
  });

  test('J1a: banner is absent when OCR binary is not installed', async ({ page }) => {
    await page.route('**/api/v1/ocr/status', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ installed: false, binary: '', version: '', error: 'ocr binary missing' }),
      })
    );
    await bootstrap(page);
    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(SETTLE);
    await expect(page.getByTestId('vision-fallback-banner')).toHaveCount(0);
  });

  test('J1b: live pipeline shows preview skeletons then evidence disclosure', async ({ page }) => {
    // Intercept the live-events WebSocket so the test can drive pipeline
    // events deterministically without a running backend pipeline.
    let push: (payload: object) => void = () => {};
    await page.routeWebSocket('**/ws/live', (ws) => {
      push = (payload) => ws.send(JSON.stringify(payload));
    });
    await bootstrap(page);

    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(SETTLE);

    // Start a pipeline through the real intent flow to arm the monitor.
    await page.getByTestId('intent-input').fill('Test POST /pets returns 201 with the created pet id');
    await page.getByTestId('btn-generate-intent').click();
    await page.waitForTimeout(400);
    await expect(page.getByTestId('live-pipeline-monitor')).toBeVisible();

    // stage_start -> preview skeleton placeholders. Stage names match the
    // orchestrator's real payloads (uppercase: INGEST / PLAN / GENERATE / REVIEW).
    push({ type: 'stage_start', payload: { stage: 'PLAN' } });
    await expect(page.getByTestId('live-preview-skeletons')).toBeVisible();

    // test_generated -> real evidence card with collapsible generated code.
    push({
      type: 'test_generated',
      payload: {
        endpoint: 'POST /pets',
        method: 'POST',
        agent: 'qa-agent-1',
        code: 'const res = await request.post("/pets", { data });\nexpect(res.status()).toBe(201);',
      },
    });
    await page.waitForTimeout(200);
    const evidence = page.getByTestId('pipeline-evidence');
    await expect(evidence).toBeVisible();
    await expect(page.getByTestId('evidence-row-0')).toBeVisible();

    await page.getByTestId('evidence-row-0').click();
    await expect(page.getByText('await request.post("/pets"', { exact: false })).toBeVisible();
  });

  test('J2a: divergence table renders confidence badges from real corpus', async ({ page }) => {
    await bootstrap(page);
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForTimeout(SETTLE);

    const table = page.getByTestId('divergence-table');
    await expect(table).toBeVisible();
    await expect(table.getByText('99%')).toBeVisible();
    await expect(table.getByText('95%')).toBeVisible();
    await expect(table.getByText('Confidence', { exact: true })).toBeVisible();
  });

  test('J2b: spec-vs-reality evidence stays collapsed until revealed', async ({ page }) => {
    await bootstrap(page);
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForTimeout(SETTLE);

    const disclosure = page.getByTestId('evidence-disclosure');
    await expect(disclosure).toBeVisible();
    await expect(page.getByTestId('evidence-body')).toHaveCount(0);

    await disclosure.click();
    await expect(page.getByTestId('evidence-body')).toBeVisible();
    await expect(page.getByTestId('evidence-body')).toContainText('curl');
  });

  test('J3: knowledge node "Author this check" deep-links intent into authoring', async ({ page }) => {
    await bootstrap(page);
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForTimeout(SETTLE);

    await page.getByTestId('knowledge-search-input').fill('cors');
    await page.getByTestId('knowledge-graph-explorer').getByText('Query Mesh').click();
    await page.waitForTimeout(500);

    const cta = page.getByTestId('btn-author-this-check').first();
    await expect(cta).toBeVisible();
    await cta.click();
    await page.waitForTimeout(SETTLE);

    await expect(page).toHaveURL(/\/authoring\?intent=/);
    const intentInput = page.getByTestId('intent-input');
    await expect(intentInput).toHaveValue(/Author a check derived from knowledge:/);
  });

  test('J3: memory decay strip reports healthy patterns by default', async ({ page }) => {
    await bootstrap(page);
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForTimeout(SETTLE);

    const strip = page.getByTestId('memory-decay-strip');
    await expect(strip).toBeVisible();
    await expect(strip).toContainText('healthy');
  });

  test('J3: memory decay strip surfaces fading patterns suggest-only', async ({ page }) => {
    await bootstrap(page);
    // Register the override after bootstrap so it wins over the canned mock
    // (Playwright matches the most recently registered route first).
    await page.route('**/api/v1/memory', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          idioms: [
            { id: 'idm-a', text: 'CORS policy check', count: 3, decay: '35%' },
            { id: 'idm-b', text: 'OAuth state check', count: 9, decay: 'ACTIVE' },
          ],
          pairing: [],
        }),
      })
    );
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForTimeout(SETTLE);

    const strip = page.getByTestId('memory-decay-strip');
    await expect(strip).toBeVisible();
    await expect(strip).toContainText('1 of 2 stored patterns are fading');
  });
});
