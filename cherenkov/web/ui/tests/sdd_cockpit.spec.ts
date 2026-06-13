import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoSdd(page: any) {
  await setupApiMocks(page);
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('[copilot] tour_seen', 'true');
    localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
  });
  await page.reload();
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(SETTLEMENT);
  await page.click('#nav-item-sdd');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('SDD Agent Cockpit — Full Coverage', () => {

  // ── Screen loads and heading renders ──────────────────────────────
  test('SDD Cockpit renders heading and KPI row', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByRole('heading', { name: 'Agent Cockpit' })).toBeVisible();
    await expect(page.getByText('SDD sync state, token budget')).toBeVisible();

    // KPI row: 4 cards
    await expect(page.getByText('Token Budget', { exact: true })).toBeVisible();
    await expect(page.getByText('Sessions', { exact: true })).toBeVisible();
    await expect(page.getByText('Experience Records')).toBeVisible();
    await expect(page.getByText('Session State', { exact: true })).toBeVisible();
  });

  // ── Token budget KPI ring renders with correct value ──────────────
  test('token budget KPI ring shows correct percentage', async ({ page }) => {
    await gotoSdd(page);

    // Mock: 13300 / 50000 = 26% → success glow
    const kpiRing = page.locator('[role="progressbar"]').first();
    await expect(kpiRing).toBeVisible();

    const valuenow = await kpiRing.getAttribute('aria-valuenow');
    // 13300/50000 = 26.6%, rounds to 27
    expect(Number(valuenow)).toBe(27);
    expect(Number(valuenow)).toBeGreaterThanOrEqual(0);
    expect(Number(valuenow)).toBeLessThanOrEqual(100);
  });

  // ── Sessions count card renders correct number ─────────────────────
  test('sessions completed card shows count from API', async ({ page }) => {
    await gotoSdd(page);
    // Mock returns sessions_completed: 12
    await expect(page.getByText('12', { exact: true })).toBeVisible();
  });

  // ── Experience count card ─────────────────────────────────────────
  test('experience records card shows count from API', async ({ page }) => {
    await gotoSdd(page);
    // Mock returns experience_count: 47
    await expect(page.getByText('47')).toBeVisible();
  });

  // ── Session state card shows LIVE for open session ────────────────
  test('session state card shows LIVE when session is open', async ({ page }) => {
    await gotoSdd(page);
    await expect(page.getByText('LIVE', { exact: true })).toBeVisible();
    await expect(page.getByText('Session State', { exact: true })).toBeVisible();
    // Active task name in session state card description
    await expect(page.getByText('ui-e2e-thorough').first()).toBeVisible();
  });

  // ── Recent Sessions panel ─────────────────────────────────────────
  test('recent sessions panel lists sessions with task names and token counts', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Recent Sessions')).toBeVisible();

    // Three sessions from mock
    await expect(page.getByText('ui-e2e-thorough').first()).toBeVisible();
    await expect(page.getByText('api-regression')).toBeVisible();
    await expect(page.getByText('bug-3-detection')).toBeVisible();

    // Token totals visible
    await expect(page.getByText('13300t')).toBeVisible();
    await expect(page.getByText('22100t')).toBeVisible();
  });

  // ── Token breakdown panel ─────────────────────────────────────────
  test('current session token breakdown shows all action categories', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Current Session Tokens')).toBeVisible();

    // Action categories (exact:true avoids matching GuidedFlow step text that contains similar words)
    await expect(page.getByText('prompt', { exact: true })).toBeVisible();
    await expect(page.getByText('generate', { exact: true })).toBeVisible();
    await expect(page.getByText('read', { exact: true })).toBeVisible();
    await expect(page.getByText('search', { exact: true })).toBeVisible();

    // Total row
    await expect(page.getByText('Total', { exact: true })).toBeVisible();
    await expect(page.getByText('13,300')).toBeVisible();
  });

  // ── Experience panel ──────────────────────────────────────────────
  test('experience panel lists recent decisions with outcomes and patterns', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Recent Experience')).toBeVisible();

    // Three experience records from mock
    await expect(page.getByText('Added BUG-3 detection test for GET /users')).toBeVisible();
    await expect(page.getByText('Fixed null-body 204 response in stub client')).toBeVisible();
    await expect(page.getByText('Attempted bearer auth with Anthropic SDK')).toBeVisible();

    // Outcome badges
    const successBadges = page.getByText('success');
    await expect(successBadges.first()).toBeVisible();
    await expect(page.getByText('failure').first()).toBeVisible();

    // Pattern chips (use .first() since same pattern names also appear in patterns panel)
    await expect(page.getByText('regression-detection').first()).toBeVisible();
    await expect(page.getByText('api-contract').first()).toBeVisible();
    await expect(page.getByText('http-semantics').first()).toBeVisible();
  });

  // ── Patterns panel ────────────────────────────────────────────────
  test('patterns panel displays pattern cloud with frequency counts', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Patterns')).toBeVisible();

    // Four patterns from mock (use .first() since same names appear in experience panel chips too)
    await expect(page.getByText(/regression-detection/).first()).toBeVisible();
    await expect(page.getByText(/api-contract/).first()).toBeVisible();
    await expect(page.getByText(/http-semantics/).first()).toBeVisible();
    await expect(page.getByText(/auth/).first()).toBeVisible();

    // Frequency counts visible as ×N
    await expect(page.getByText('×8')).toBeVisible();
    await expect(page.getByText('×12')).toBeVisible();
  });

  // ── Compaction panel ─────────────────────────────────────────────
  test('compaction panel shows sessions since compact and session status', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Compaction')).toBeVisible();
    await expect(page.getByText('Sessions since last compact')).toBeVisible();
    // Mock returns sessions_since_compact: 3 — scope to the compaction row to avoid 14 matches
    await expect(page.getByText('Sessions since last compact').locator('..').locator('span.font-mono')).toHaveText('3');

    await expect(page.getByText('Session status')).toBeVisible();
    // open session → green "open" (exact to avoid matching GuidedFlow "Upload or fetch OpenAPI spec")
    await expect(page.getByText('open', { exact: true })).toBeVisible();
  });

  // ── By Task Type panel ────────────────────────────────────────────
  test('by task type panel shows task categories and token totals', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('By Task Type')).toBeVisible();

    // Two task types from mock (exact match to avoid matching 'ui-e2e-thorough')
    await expect(page.getByText('ui-e2e', { exact: true })).toBeVisible();
    await expect(page.getByText('api-test', { exact: true })).toBeVisible();
  });

  // ── Active session banner in compaction panel ─────────────────────
  test('active session detail shown in compaction panel when session is open', async ({ page }) => {
    await gotoSdd(page);

    await expect(page.getByText('Active Session')).toBeVisible();
    await expect(page.getByText('ui-e2e-thorough').last()).toBeVisible();
  });

  // ── Warning banner at high token budget ───────────────────────────
  test('warning banner appears when token budget exceeds 80%', async ({ page }) => {
    await setupApiMocks(page);
    // Override SDD status to return >80% usage
    await page.route('**/api/v1/sdd/status', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        session: { id: 'sess-high', status: 'open', task: 'big-job' },
        current_tokens: { session_id: 'sess-high', prompt: 42000, generate: 0, read: 0, search: 0, total: 42000 },
        budget: { per_session: 50000 },
        historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} },
        experience_count: 0,
        sessions_since_compact: 1
      }) });
    });
    // Need token mock too
    await page.route('**/api/v1/sdd/tokens', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
        current_session: { session_id: 'sess-high', prompt: 42000, generate: 0, read: 0, search: 0, total: 42000 },
        budget: { per_session: 50000 },
        historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} },
        top_consumers: []
      }) });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);

    // 42000/50000 = 84% → warning banner
    await expect(page.getByText(/Token budget at 84%/)).toBeVisible();
    await expect(page.getByText('compaction recommended')).toBeVisible();
  });

  // ── Empty state: no sessions ──────────────────────────────────────
  test('sessions panel shows empty state when no sessions returned', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/sdd/sessions*', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('No sessions')).toBeVisible();
    await expect(page.getByText('Run agent_sync before to start')).toBeVisible();
  });

  // ── Empty state: no patterns ──────────────────────────────────────
  test('patterns panel shows empty state when no patterns returned', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/sdd/graph/patterns', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('No patterns mined')).toBeVisible();
  });

  // ── Graceful degradation when all SDD APIs fail ───────────────────
  test('SDD screen degrades gracefully when all APIs return 500', async ({ page }) => {
    await setupApiMocks(page);
    for (const pattern of ['**/api/v1/sdd/**']) {
      await page.route(pattern, route =>
        route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"error"}' })
      );
    }

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-sdd');
    await page.waitForTimeout(SETTLEMENT);

    // Screen renders without crashing — empty states shown
    await expect(page.getByRole('heading', { name: 'Agent Cockpit' })).toBeVisible();
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  // ── Pattern tooltip available ──────────────────────────────────────
  test('pattern chips have title attribute with frequency and success rate', async ({ page }) => {
    await gotoSdd(page);

    // Find the pattern chip by its title attribute
    const patternChip = page.locator('[title*="8x | 88% success"]').first();
    await expect(patternChip).toBeVisible();

    const title = await patternChip.getAttribute('title');
    expect(title).toContain('8x'); // frequency: 8
    expect(title).toContain('88% success'); // success_rate: 0.88
  });

});
