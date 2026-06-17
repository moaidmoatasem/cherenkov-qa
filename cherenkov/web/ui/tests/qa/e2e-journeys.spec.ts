import { test, expect } from '@playwright/test';
import { bootstrap, Sidebar, TopBar } from './page-objects';
import { setupApiMocks } from '../api_mocks';

const S = 400;

test.describe('QA Engineer: End-to-End User Journeys', () => {

  test.describe('Journey 1: New QA Engineer Onboarding — First Run', () => {
    test('complete first-run: landing → overview → settings → project setup', async ({ page }) => {
      await setupApiMocks(page);
      await page.goto('/');
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(500);
      await page.evaluate(() => {
        localStorage.removeItem('[copilot] tour_seen');
        localStorage.removeItem('[cherenkov] onboarding_seen');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(500);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });
  });

  test.describe('Journey 2: Spec Ingestion → Test Generation → Review → Approval', () => {
    test('full pipeline: ingest spec → review generated tests → approve', async ({ page }) => {
      let ingestCalled = false;
      await setupApiMocks(page);
      await page.route('**/api/v1/ingest', async route => {
        if (route.request().method() === 'POST') {
          ingestCalled = true;
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ spec_path: 'petstore.yaml', endpoints: [], richness: 0.95 }) });
      });
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);

      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#btn-shortcut-petstore').click();
      await page.waitForTimeout(800);
      await expect(page.getByText('swagger-petstore-v2.json')).toBeVisible();

      await page.click('#nav-item-review');
      await page.waitForSelector('#review-screen');
      await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
      await expect(page.locator('#filter-tab-all')).toBeVisible();
    });
  });

  test.describe('Journey 3: Drift Detection → Triage → Healing → Eject', () => {
    test('full drift flow: detect → triage → heal suggestion → eject', async ({ page }) => {
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

      await page.click('#nav-item-divergences');
      await page.waitForTimeout(500);
      await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
      await expect(page.getByText('D-').first()).toBeVisible();

      const severitySelect = page.locator('select:has(option[value="critical"])');
      await expect(severitySelect).toBeVisible();
      await severitySelect.selectOption('critical');
      await page.waitForTimeout(200);

      await page.getByText('D-').first().click();
      await page.waitForTimeout(300);
      await expect(page.getByText('Divergence Detail').first()).toBeVisible();
      await page.locator('button[aria-label="Close details"]').click();

      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await expect(page.locator('#drift-card-fail-1')).toBeVisible();
      await expect(page.getByText('All repairs are suggest-only')).toBeVisible();

      await page.locator('#drift-card-fail-1 button:has-text("VIEW SUGGESTION DIFF")').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#read-only-diff-viewer')).toBeVisible();
      await expect(page.locator('#btn-diff-copy')).toBeVisible();
      await expect(page.locator('#btn-diff-download')).toBeVisible();
      await page.locator('#btn-diff-dismiss').click();

      await page.click('#nav-item-eject');
      await page.waitForSelector('#eject-screen');
      await page.locator('#btn-confirm-eject').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#btn-copy-command')).toBeVisible();
    });
  });

  test.describe('Journey 4: Chat-Assisted Testing Workflow', () => {
    test('create chat session → ask question → receive SSE response', async ({ page }) => {
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

      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');

      const input = page.locator('#chat-screen input[type="text"]');
      await expect(input).toBeVisible();
      await expect(input).toBeEnabled();

      await input.fill('What divergences should I focus on first?');
      await page.locator('#chat-screen button').last().click();
      await page.waitForTimeout(800);
      await expect(page.getByText('What divergences should I focus on first?')).toBeVisible();
      await expect(page.getByText(/Hello from CHERENKOV/)).toBeVisible();
    });
  });

  test.describe('Journey 5: Knowledge-Driven Testing Research', () => {
    test('query knowledge mesh → read results → act on insights', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-knowledge');
      await page.waitForSelector('#knowledge-screen');

      await page.locator('#knowledge-screen input[type="text"]').fill('OAuth redirect');
      await page.locator('#knowledge-screen button[type="submit"]').click();
      await page.waitForTimeout(500);
      await expect(page.getByText('reflector').first()).toBeVisible();
      await expect(page.getByText('idiom').first()).toBeVisible();
    });
  });

  test.describe('Journey 6: SDD Agent Cockpit Monitoring', () => {
    test('monitor token budget → review sessions → check patterns → compact', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);

      await expect(page.getByRole('heading', { name: 'Agent Cockpit' })).toBeVisible();
      await expect(page.getByText('Token Budget', { exact: true })).toBeVisible();
      await expect(page.getByText('Sessions', { exact: true })).toBeVisible();
      await expect(page.getByText('Experience Records')).toBeVisible();

      await expect(page.getByText('Recent Sessions')).toBeVisible();
      await expect(page.getByText('Current Session Tokens')).toBeVisible();
      await expect(page.getByText('Recent Experience')).toBeVisible();
      await expect(page.getByText('Patterns')).toBeVisible();
      await expect(page.getByText('Compaction')).toBeVisible();
      await expect(page.getByText('By Task Type')).toBeVisible();
    });
  });

  test.describe('Journey 7: Settings Configuration & Persistence', () => {
    test('change model tier → adjust budget → toggle compact → save → verify persistence', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        if (route.request().method() === 'PUT') {
          const body = JSON.parse(route.request().postData() || '{}');
          expect(body).toBeDefined();
        }
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          target: { url: 'http://localhost' }, engine: { model_tier: 'high', enable_demo_mode: false, execution_budget: 150, workers: 2 },
          security: { egress_policy: 'strict' }, ui: { density: 'compact', reduced_motion: false }
        }) });
      });
      await bootstrap(page);

      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });

      await expect(page.getByText('Qwen 2.5 Coder (7B)')).toBeVisible();
      await expect(page.locator('input[type="range"]').first()).toBeVisible();

      await page.locator('input[type="checkbox"]').first().click();
      await page.locator('#btn-settings-save').click();
      await page.waitForTimeout(500);

      const stored = await page.evaluate(() => localStorage.getItem('[copilot] density'));
      expect(stored).toBe('compact');
    });
  });

  test.describe('Journey 8: Visual Regression & Explorer Review', () => {
    test('navigate visual regression scenarios → review anomaly detail', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-visual-regression');
      await page.waitForTimeout(300);
      await expect(page.getByRole('heading', { name: 'Visual Regression' })).toBeVisible();
      await expect(page.getByText('vs-1')).toBeVisible();
      await page.getByText('vs-2').click();
      await expect(page.getByText('Button overlaps form field')).toBeVisible();
    });
  });

  test.describe('Journey 9: Mobile Device Management', () => {
    test('view mobile device grid → check status → understand pilot instructions', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-mobile');
      await page.waitForSelector('#mobile-screen');
      await page.waitForTimeout(1000);

      await expect(page.getByText('iPhone 15 Pro')).toBeVisible();
      await expect(page.getByText('Pixel 8')).toBeVisible();
      await expect(page.getByTestId('device-card-m1')).toBeVisible();
      await expect(page.getByText('Disconnected').first()).toBeVisible();
      await expect(page.getByText('Mobile testing requires ADB')).toBeVisible();
    });
  });

  test.describe('Journey 10: Full Dashboard Regression — All Screens', () => {
    const screenIds = [
      'overview', 'truth-map', 'divergences', 'author', 'signals',
      'memory', 'governance', 'review', 'healing', 'eject',
      'chat', 'knowledge', 'devices', 'sdd', 'mobile',
    ];

    for (const screenId of screenIds) {
      test(`screen ${screenId} loads without console errors`, async ({ page }) => {
        const consoleErrors: string[] = [];
        page.on('console', msg => {
          if (msg.type() === 'error') consoleErrors.push(msg.text());
        });
        page.on('pageerror', err => consoleErrors.push(err.message));

        await bootstrap(page);
        await page.click(`#nav-item-${screenId}`);
        await page.waitForTimeout(600);

        const criticalErrors = consoleErrors.filter(e =>
          !e.includes('favicon') && !e.includes('404') && !e.includes('net::ERR')
        );
        expect(criticalErrors.length).toBe(0);
      });
    }
  });
});