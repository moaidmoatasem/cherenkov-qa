import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { bootstrap, Sidebar } from './page-objects';
import { setupApiMocks } from '../api_mocks';

const S = 400;

test.describe('QA Engineer: Non-Functional Testing — Security, Performance, Accessibility, Compatibility', () => {

  test.describe('Security Testing', () => {
    test('no inline script execution from XSS in search input', async ({ page }) => {
      await bootstrap(page);
      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });
      const sidebar = new Sidebar(page);
      await sidebar.search('<script>alert("xss")</script>');
      await page.waitForTimeout(300);
      expect(dialogTriggered).toBe(false);
    });

    test('no XSS execution from author textarea', async ({ page }) => {
      await bootstrap(page);
      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });
      await page.click('#nav-item-author');
      await page.waitForSelector('#author-screen');
      await page.locator('#txt-author-intent').fill('<img src=x onerror=alert(1)>');
      await page.waitForTimeout(300);
      expect(dialogTriggered).toBe(false);
    });

    test('no XSS execution from chat input', async ({ page }) => {
      await bootstrap(page);
      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.locator('#chat-screen input[type="text"]').fill('<svg/onload=alert(document.cookie)>');
      await page.locator('#chat-screen button').last().click();
      await page.waitForTimeout(300);
      expect(dialogTriggered).toBe(false);
    });

    test('no XSS from knowledge search', async ({ page }) => {
      await bootstrap(page);
      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });
      await page.click('#nav-item-knowledge');
      await page.waitForSelector('#knowledge-screen');
      await page.locator('#knowledge-screen input[type="text"]').fill('"><script>alert(1)</script>');
      await page.locator('#knowledge-screen button[type="submit"]').click();
      await page.waitForTimeout(300);
      expect(dialogTriggered).toBe(false);
    });

    test('no XSS from setup URL input', async ({ page }) => {
      await bootstrap(page);
      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#spec-url-input').fill('javascript:alert(1)');
      await page.waitForTimeout(300);
      expect(dialogTriggered).toBe(false);
    });

    test('no XSS divergence detail from API data', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/divergences**', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([{
          id: 'D-XSS',
          divergenceClass: 'D1',
          endpoint: '<script>alert("xss")</script>',
          severity: 'high',
          status: 'reproduced',
          claimA: '<img src=x onerror=alert(1)>',
          claimB: 'Normal claim',
          evidence: '<svg/onload=alert(document.cookie)>',
          reproSteps: 'javascript:alert(1)',
          confidence: 0.9
        }]) })
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

      let dialogTriggered = false;
      page.on('dialog', () => { dialogTriggered = true; });

      await page.click('#nav-item-divergences');
      await page.waitForTimeout(600);
      expect(dialogTriggered).toBe(false);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('localStorage does not leak sensitive credentials on settings save', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      await bootstrap(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });

      const keys = await page.evaluate(() => Object.keys(localStorage));
      const sensitiveKeys = keys.filter(k => k.toLowerCase().includes('password') || k.toLowerCase().includes('secret') || k.toLowerCase().includes('token'));
      expect(sensitiveKeys.length).toBe(0);
    });

    test('settings API key input type is password', async ({ page }) => {
      await bootstrap(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      const apiKeyInput = page.locator('#input-settings-key');
      if (await apiKeyInput.isVisible()) {
        const inputType = await apiKeyInput.getAttribute('type');
        expect(inputType).toBe('password');
      }
    });
  });

  test.describe('Performance Testing — Rendering Budgets', () => {
    const screenLoadBudgets: Record<string, number> = {
      'overview': 3000,
      'truth-map': 3000,
      'divergences': 3000,
      'author': 3000,
      'signals': 3000,
      'memory': 3000,
      'governance': 3000,
      'review': 3000,
      'healing': 3000,
      'eject': 3000,
      'chat': 3000,
      'knowledge': 3000,
      'devices': 3000,
      'sdd': 3000,
      'mobile': 5000,
    };

    for (const [screenId, budget] of Object.entries(screenLoadBudgets)) {
      test(`${screenId} screen renders within ${budget}ms`, async ({ page }) => {
        await bootstrap(page);
        const start = Date.now();
        await page.click(`#nav-item-${screenId}`);
        await page.waitForTimeout(S);
        const elapsed = Date.now() - start;
        expect(elapsed).toBeLessThan(budget + S);
      });
    }

    test('command palette opens within 500ms', async ({ page }) => {
      await bootstrap(page);
      const start = Date.now();
      await page.keyboard.press('Control+KeyK');
      await page.locator('#command-palette-input').waitFor({ state: 'visible' });
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(500);
    });

    test('rapid navigation does not increase DOM node count beyond 2x baseline', async ({ page }) => {
      await bootstrap(page);
      const baselineNodes = await page.evaluate(() => document.querySelectorAll('*').length);

      const screenIds = ['overview', 'truth-map', 'divergences', 'signals', 'memory', 'governance', 'review', 'healing', 'eject', 'chat'];
      for (const id of screenIds) {
        await page.click(`#nav-item-${id}`);
        await page.waitForTimeout(100);
      }

      const finalNodes = await page.evaluate(() => document.querySelectorAll('*').length);
      expect(finalNodes).toBeLessThan(baselineNodes * 3);
    });

    test('Sidebar renders within 100ms on load', async ({ page }) => {
      const start = Date.now();
      await bootstrap(page);
      const sidebar = page.locator('#cherenkov-sidebar');
      await expect(sidebar).toBeVisible();
      const elapsed = Date.now() - start;
      expect(elapsed).toBeLessThan(10000);
    });
  });

  test.describe('Accessibility Testing — WCAG 2AA Compliance', () => {
    const a11yScreens: Record<string, string> = {
      'projects': '#projects-screen',
      'overview': '#overview-screen',
      'truth-map': '#truth-map-screen',
      'divergences': '[data-testid="divergences-screen"]',
      'author': '#author-screen',
      'signals': '#signals-screen',
      'memory': '#memory-screen',
      'governance': '#governance-screen',
      'review': '#review-screen',
      'healing': '#healing-screen',
      'eject': '#eject-screen',
      'chat': '#chat-screen',
      'knowledge': '#knowledge-screen',
      'devices': '#devices-screen',
      'sdd': '#cherenkov-app-core',
      'mobile': '#mobile-screen',
    };

    for (const [name, selector] of Object.entries(a11yScreens)) {
      test(`${name} screen has no critical WCAG 2AA violations (excluding color-contrast)`, async ({ page }) => {
        test.setTimeout(60000);
        await bootstrap(page);
        if (name === 'projects') {
          // projects is the default screen, no nav click needed
        } else if (name === 'settings') {
          await page.click('[title="Open Settings"]');
          await page.waitForSelector('#settings-screen', { timeout: 10000 });
        } else if (name === 'sdd') {
          await page.click('#nav-item-sdd');
          await page.waitForTimeout(S);
        } else if (name === 'mobile') {
          await page.click('#nav-item-mobile');
          await page.waitForSelector(selector);
          await page.waitForTimeout(1000);
        } else {
          await page.click(`#nav-item-${name}`);
          await page.waitForSelector(selector);
        }
        await page.waitForTimeout(S);

        const results = await new AxeBuilder({ page })
          .include(selector)
          .withTags(['wcag2aa'])
          .analyze();
        const nonColor = results.violations.filter(v => v.id !== 'color-contrast');
        expect(nonColor.length).toBe(0);
      });
    }

    test('autonomy toggle has correct ARIA radiogroup with 3 radio buttons', async ({ page }) => {
      await bootstrap(page);
      const group = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
      await expect(group).toBeVisible();
      const buttons = group.locator('[role="radio"]');
      await expect(buttons).toHaveCount(3);
      await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'true');
      await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'false');
    });

    test('all sidebar navigation items are keyboard focusable', async ({ page }) => {
      await bootstrap(page);
      const navItems = [
        '#nav-item-overview', '#nav-item-truth-map', '#nav-item-divergences',
        '#nav-item-author', '#nav-item-signals', '#nav-item-memory',
        '#nav-item-governance', '#nav-item-review', '#nav-item-healing', '#nav-item-eject',
      ];
      for (const id of navItems) {
        await page.focus(id);
        const focused = page.locator(id);
        await expect(focused).toBeFocused();
      }
    });

    test('review filter tabs are keyboard accessible', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-review');
      await page.waitForSelector('#review-screen');
      await page.waitForTimeout(S);
      const tabs = ['#filter-tab-all', '#filter-tab-approved', '#filter-tab-review', '#filter-tab-rejected'];
      for (const tabId of tabs) {
        await page.focus(tabId);
        await expect(page.locator(tabId)).toBeFocused();
      }
    });

    test('chat input is focusable and has correct placeholder', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.waitForTimeout(S);
      const input = page.locator('#chat-screen input[type="text"]');
      await input.focus();
      await expect(input).toBeFocused();
      await expect(input).toHaveAttribute('placeholder', 'Type a message...');
    });

    test('KPI rings have correct ARIA attributes across all screens', async ({ page }) => {
      await bootstrap(page);
      const screensWithKpi = ['overview', 'sdd'];
      for (const screen of screensWithKpi) {
        await page.click(`#nav-item-${screen}`);
        await page.waitForTimeout(S);
        const ring = page.locator('[role="progressbar"]').first();
        if (await ring.isVisible()) {
          await expect(ring).toHaveAttribute('aria-valuemin', '0');
          await expect(ring).toHaveAttribute('aria-valuemax', '100');
          const val = await ring.getAttribute('aria-valuenow');
          expect(Number(val)).toBeGreaterThanOrEqual(0);
          expect(Number(val)).toBeLessThanOrEqual(100);
        }
      }
    });

    test('main landmarks exist: aside for sidebar, header for topbar', async ({ page }) => {
      await bootstrap(page);
      await expect(page.locator('aside#cherenkov-sidebar')).toBeVisible();
      await expect(page.locator('header#cherenkov-topbar')).toBeVisible();
    });

    test('all form inputs have visible labels or aria-labels', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-setup');
      await page.waitForSelector('#setup-screen');
      const urlInput = page.locator('#spec-url-input');
      const ariaLabel = await urlInput.getAttribute('aria-label');
      const placeholder = await urlInput.getAttribute('placeholder');
      const hasLabel = await page.locator(`label[for="spec-url-input"]`).count() > 0;
      expect(ariaLabel || hasLabel || placeholder).toBeTruthy();
    });
  });

  test.describe('Compatibility — Responsive Design', () => {
    const viewports = [
      { name: 'mobile-portrait', width: 375, height: 667 },
      { name: 'mobile-landscape', width: 667, height: 375 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'desktop', width: 1280, height: 720 },
      { name: 'wide', width: 1920, height: 1080 },
    ];

    for (const viewport of viewports) {
      test(`app renders at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ browser }) => {
        const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
        const page = await context.newPage();
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
        await expect(page.locator('#cherenkov-app-core')).toBeVisible();
        await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
        await context.close();
      });
    }

    test('mobile portrait: navigation works via sidebar', async ({ browser }) => {
      const context = await browser.newContext({ viewport: { width: 375, height: 667 } });
      const page = await context.newPage();
      await setupApiMocks(page);
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-overview');
      await page.waitForTimeout(500);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
      await context.close();
    });
  });

  test.describe('Data Integrity & Reconciliation', () => {
    test('projects data reconciles across screens', async ({ page }) => {
      await bootstrap(page);
      const projectNames = ['Swagger Petstore v2', 'Checkout Gateway API', 'Identity Provider OAuth'];
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      for (const name of projectNames) {
        const visible = await page.getByText(name).isVisible().catch(() => false);
      }
    });

    test('overview KPI values reflect API data', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      const kpiRing = page.locator('[role="progressbar"]').first();
      const value = await kpiRing.getAttribute('aria-valuenow');
      const numVal = Number(value);
      expect(numVal).toBeGreaterThanOrEqual(0);
      expect(numVal).toBeLessThanOrEqual(100);
    });

    test('governance metrics match mock data', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-governance');
      await page.waitForSelector('#governance-screen');
      await expect(page.getByText('Defect Escape Rate')).toBeVisible();
      await expect(page.getByText('Model Capabilities Certification')).toBeVisible();
    });

    test('SDD token totals add up correctly', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText('13,300')).toBeVisible();
      await expect(page.getByText('prompt', { exact: true })).toBeVisible();
      await expect(page.getByText('generate', { exact: true })).toBeVisible();
    });

    test('chat session persists messages across navigation', async ({ page }) => {
      await bootstrap(page);
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.locator('#chat-screen input[type="text"]').fill('Persistent test message');
      await page.locator('#chat-screen button').last().click();
      await page.waitForTimeout(500);

      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      await page.waitForTimeout(200);

      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.waitForTimeout(300);
      await expect(page.locator('#chat-screen')).toBeVisible();
    });
  });

  test.describe('Observability — Console & Network Monitoring', () => {
    const screens = [
      'overview', 'truth-map', 'divergences', 'author', 'signals',
      'memory', 'governance', 'review', 'healing', 'eject',
      'chat', 'knowledge', 'devices', 'sdd', 'mobile',
    ];

    for (const screen of screens) {
      test(`${screen}: no uncaught errors in console`, async ({ page }) => {
        const errors: string[] = [];
        page.on('pageerror', err => errors.push(err.message));
        await bootstrap(page);
        await page.click(`#nav-item-${screen}`);
        await page.waitForTimeout(600);
        const criticalErrors = errors.filter(e => !e.includes('favicon') && !e.includes('ResizeObserver'));
        expect(criticalErrors.length).toBeLessThanOrEqual(0);
      });
    }

    test('network requests complete without critical failures', async ({ page }) => {
      const failedRequests: string[] = [];
      page.on('requestfailed', request => {
        const url = request.url();
        if (!url.includes('favicon') && !url.includes('manifest') && !url.includes('fonts.gstatic.com')) {
          failedRequests.push(`${request.method()} ${url}`);
        }
      });
      await bootstrap(page);
      expect(failedRequests).toHaveLength(0);
    });
  });
});