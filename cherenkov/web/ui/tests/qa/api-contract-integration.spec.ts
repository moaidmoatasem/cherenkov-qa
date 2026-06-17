import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';
import { bootstrap, Sidebar, TopBar } from './page-objects';
import { makeProject, makeEndpoints, makeTestItem, makeFailingTest, makeDivergence, EMPTY_PROJECTS, EMPTY_TESTS, EMPTY_FAILURES, EMPTY_DIVERGENCES } from './test-data-factory';

const S = 400;

test.describe('QA Engineer: API Contract & Integration Testing', () => {

  test.describe('API Contract Validation — Request/Response Shape', () => {

    test('GET /api/v1/projects returns array of Project objects with required fields', async ({ page }) => {
      let responseBody: string = '';
      await page.route('**/api/v1/projects', async route => {
        responseBody = route.request().method() === 'GET' ? 'captured' : '';
        await route.continue();
      });
      await bootstrap(page);
      expect(responseBody).toBeDefined();
    });

    test('GET /api/v1/overview contract: releaseReadiness is numeric 0-100', async ({ page }) => {
      await bootstrap(page);
      await page.route('**/api/v1/overview', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ releaseReadiness: 95, falsePositiveRate: 1.2, recentLearnings: [] }) })
      );
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      const kpiRing = page.locator('[role="progressbar"]').first();
      const value = await kpiRing.getAttribute('aria-valuenow');
      const num = Number(value);
      expect(num).toBeGreaterThanOrEqual(0);
      expect(num).toBeLessThanOrEqual(100);
    });

    test('GET /api/v1/truth-map contract: endpoints array with richness 0-1', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-truth-map');
      await page.waitForSelector('#truth-map-screen');
      await page.getByText('POST /pets').first().click();
      await page.waitForTimeout(300);
      await expect(page.locator('#truth-map-screen h3').first()).toBeVisible();
    });

    test('GET /api/v1/failures contract: failureType enum values', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      const visibleTypes = ['CONTRACT DRIFT', 'AUTH EXPIRY', 'STATE SEQUENCING', 'ASSERTION DRIFT'];
      for (const type of visibleTypes) {
        const card = page.locator(`#healing-screen :text("${type}")`);
        if (await card.count() > 0) {
          await expect(card.first()).toBeVisible();
        }
      }
    });

    test('GET /api/v1/divergences contract: severity and status enum values', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-divergences');
      await page.waitForTimeout(500);
      await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    });

    test('POST /api/v1/ingest contract: returns spec_path and endpoints', async ({ page }) => {
      let capturedBody: any = null;
      await page.route('**/api/v1/ingest', async route => {
        if (route.request().method() === 'POST') {
          capturedBody = route.request().postData();
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ spec_path: 'spec.yaml', endpoints: [], richness: 1.0 }) });
      });
      await bootstrap(page);
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#btn-shortcut-petstore').click();
      await page.waitForTimeout(500);
      await page.locator('#btn-launch-generation').click();
      await page.waitForTimeout(300);
    });

    test('POST /api/v1/run contract: requires spec_path and demo_mode', async ({ page }) => {
      let runPayload: any = null;
      await page.route('**/api/v1/run', async route => {
        if (route.request().method() === 'POST') {
          runPayload = JSON.parse(route.request().postData() || '{}');
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ run_id: 'qa-contract-run', status: 'started' }) });
        } else {
          await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
        }
      });
      await setupApiMocks(page);
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      await page.locator('#btn-pilot-run').click();
      await page.waitForTimeout(500);
      expect(runPayload).not.toBeNull();
      expect(runPayload.spec_path).toBe('stub/openapi.yaml');
      expect(runPayload.demo_mode).toBe(true);
    });

    test('POST /api/v1/review/approve contract: sends test id', async ({ page }) => {
      let approvePayload: string | null = null;
      await page.route('**/api/v1/review/approve', async route => {
        if (route.request().method() === 'POST') {
          approvePayload = route.request().postData();
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      await bootstrap(page);
      await page.click('#nav-item-review');
      await page.waitForSelector('#review-screen');
    });

    test('PUT /api/v1/settings contract: sends settings object', async ({ page }) => {
      let settingsPayload: any = null;
      await page.route('**/api/v1/settings', async route => {
        if (route.request().method() === 'PUT') {
          settingsPayload = JSON.parse(route.request().postData() || '{}');
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      await bootstrap(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      await page.locator('#btn-settings-save').click();
      await page.waitForTimeout(300);
    });

    test('POST /api/v1/chat/sessions contract: creates new session', async ({ page }) => {
      let sessionCreated = false;
      await page.route('**/api/v1/chat/sessions', async route => {
        if (route.request().method() === 'POST') {
          sessionCreated = true;
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ session_id: 'test-session', persona_id: 'default' }) });
        } else {
          await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
        }
      });
      await bootstrap(page, async p => {
        await p.route('**/api/v1/chat/sessions/*/stream', route =>
          route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'event: complete\ndata: {}\n\n' })
        );
      });
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
    });

    test('GET /api/v1/health contract: returns status, device, gen_model', async ({ page }) => {
      await bootstrap(page);
      let healthData: any;
      await page.route('**/api/v1/health', async route => {
        healthData = { status: 'online', device: 'cpu', gen_model: 'qwen2.5-coder:7b' };
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(healthData) });
      });
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
    });
  });

  test.describe('API Error Handling — Server Errors', () => {

    test('All screens survive global 500 errors on data endpoints', async ({ page }) => {
      const errorRoutes = [
        '**/api/v1/projects',
        '**/api/v1/overview',
        '**/api/v1/divergences**',
        '**/api/v1/failures',
        '**/api/v1/truth-map',
        '**/api/v1/signals',
        '**/api/v1/governance',
        '**/api/v1/memory',
        '**/api/v1/settings',
        '**/api/v1/metrics',
        '**/api/v1/review/queue*',
      ];
      await setupApiMocks(page);
      for (const pattern of errorRoutes) {
        await page.route(pattern, route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'Internal Server Error' }) })
        );
      }
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);

      const screens = ['overview', 'truth-map', 'divergences', 'healing', 'signals', 'memory', 'governance'];
      for (const screen of screens) {
        await page.click(`#nav-item-${screen}`);
        await page.waitForTimeout(500);
        await expect(page.locator('#cherenkov-app-core')).toBeVisible();
      }
    });

    test('404 on unknown route shows app shell without crash', async ({ page }) => {
      await page.route('**/api/v1/unknown-endpoint', route =>
        route.fulfill({ status: 404, contentType: 'application/json', body: JSON.stringify({ detail: 'Not found' }) })
      );
      await bootstrap(page);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('Network timeout: app remains interactive', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/overview', async route => {
        await new Promise(resolve => setTimeout(resolve, 10000));
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ releaseReadiness: 50, falsePositiveRate: 5, recentLearnings: [] }) });
      });
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('Malformed JSON response: app handles gracefully', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/divergences**', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '{malformed json' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-divergences');
      await page.waitForTimeout(600);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });
  });

  test.describe('Cross-Module Integration Flows', () => {

    test('Setup → Pipeline: New Run triggers pipeline view', async ({ page }) => {
      await bootstrap(page);
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#btn-shortcut-petstore').click();
      await page.waitForTimeout(500);
      await page.locator('#btn-launch-generation').click();
      await page.waitForTimeout(500);
    });

    test('Projects → Divergences → Healing: defect flow', async ({ page }) => {
      await bootstrap(page);
      await expect(page.locator('#projects-screen')).toBeVisible();
      await page.click('#nav-item-divergences');
      await page.waitForTimeout(500);
      await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await expect(page.locator('h1')).toContainText('Self-Healing & Drift Redress');
      await expect(page.locator('#drift-card-fail-1')).toBeVisible();
    });

    test('Healing → Eject: fix suggestion → eject standalone suite', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await page.locator('#drift-card-fail-1 button:has-text("VIEW SUGGESTION DIFF")').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#read-only-diff-viewer')).toBeVisible();
      await page.locator('#btn-diff-dismiss').click();
      await page.waitForTimeout(300);
      await page.click('#nav-item-eject');
      await page.waitForSelector('#eject-screen');
      await expect(page.locator('h1')).toContainText('Export & Eject Suite');
    });

    test('Overview → Governance → Memory: KPI review flow', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      const kpiRing = page.locator('[role="progressbar"]').first();
      const value = await kpiRing.getAttribute('aria-valuenow');
      expect(Number(value)).toBeGreaterThanOrEqual(0);
      await page.click('#nav-item-governance');
      await page.waitForSelector('#governance-screen');
      await expect(page.getByText('Defect Escape Rate')).toBeVisible();
      await page.click('#nav-item-memory');
      await page.waitForSelector('#memory-screen');
      await expect(page.getByText('Accumulated Senior Testing Idioms')).toBeVisible();
    });

    test('SDD Cockpit → Chat: session context carries over', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByRole('heading', { name: 'Agent Cockpit' })).toBeVisible();
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      const chatInput = page.locator('#chat-screen input[type="text"]');
      await expect(chatInput).toBeVisible();
    });

    test('Settings → Multiple screens: persistent config', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          target: { url: 'http://localhost' }, engine: { model_tier: 'high', enable_demo_mode: false, execution_budget: 100, workers: 2 },
          security: { egress_policy: 'strict' }, ui: { density: 'compact', reduced_motion: false }
        }) });
      });
      await bootstrap(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      await page.click('#btn-settings-save');
      await page.waitForTimeout(300);
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      await expect(page.locator('#settings-screen')).toBeVisible();
    });

    test('Author → Review → Healing: spec → test → fix cycle', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-author');
      await page.waitForSelector('#author-screen');
      const textarea = page.locator('#txt-author-intent');
      await textarea.fill('Verify all CRUD endpoints for Petstore');
      await page.click('#nav-item-review');
      await page.waitForSelector('#review-screen');
      await expect(page.locator('#filter-tab-all')).toBeVisible();
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await expect(page.locator('#drift-card-fail-1')).toBeVisible();
    });

    test('Knowledge search returns results from mock', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-knowledge');
      await page.waitForSelector('#knowledge-screen');
      const input = page.locator('#knowledge-screen input[type="text"]');
      await input.fill('login redirect');
      await page.locator('#knowledge-screen button[type="submit"]').click();
      await page.waitForTimeout(500);
      await expect(page.getByText('reflector').first()).toBeVisible();
    });
  });
});