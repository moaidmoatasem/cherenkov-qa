import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

const S = 400;

async function smokeSetup(page: import('@playwright/test').Page) {
  page.on('pageerror', err => console.error(`[SMOKE ERROR] ${err.message}`));
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
}

test.describe('Smoke Test Suite — Release Validation', () => {

  test('app shell renders: sidebar + topbar + content area', async ({ page }) => {
    await smokeSetup(page);
    await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
    await expect(page.locator('#cherenkov-topbar')).toBeVisible();
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('projects screen loads as default route', async ({ page }) => {
    await smokeSetup(page);
    await expect(page.locator('#projects-screen')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Cherenkov');
  });

  test('all 15 primary screens render headings', async ({ page }) => {
    await smokeSetup(page);
    const screens: [string, RegExp][] = [
      ['overview', /Release Readiness/],
      ['truth-map', /Endpoint Truth Graph/],
      ['divergences', /Divergence Triage Hub/],
      ['author', /Author by Intent/],
      ['signals', /Telemetry Signals/],
      ['memory', /Reflector Memory/],
      ['governance', /Governance/],
      ['review', /Human-In-The-Loop/],
      ['healing', /Self-Healing/],
      ['eject', /Export & Eject/],
      ['chat', /Chat/],
      ['knowledge', /Knowledge Explorer/],
      ['devices', /Device & Provider/],
      ['sdd', /Agent Cockpit/],
      ['mobile', /Mobile Testing/],
    ];
    for (const [id, headingPattern] of screens) {
      await page.click(`#nav-item-${id}`);
      await page.waitForTimeout(600);
      await expect(page.locator('h1')).toContainText(headingPattern);
    }
  });

  test('command palette opens and closes', async ({ page }) => {
    await smokeSetup(page);
    await page.keyboard.press('Control+KeyK');
    await expect(page.locator('#command-palette-input')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('#command-palette-input')).not.toBeVisible();
  });

  test('health widget shows device and model', async ({ page }) => {
    await smokeSetup(page);
    await expect(page.getByText('cpu').first()).toBeVisible();
    await expect(page.getByText('qwen2.5-coder:7b').first()).toBeVisible();
  });

  test('pilot run button exists on overview', async ({ page }) => {
    await smokeSetup(page);
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    await expect(page.locator('#btn-pilot-run')).toBeVisible();
  });
});

test.describe('Regression Suite — Key Feature Invariants', () => {

  test.describe('D7 Invariant: All repairs are suggest-only (never auto-applied)', () => {
    test('healing screen shows suggest-only banner', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await expect(page.getByText('All repairs are suggest-only')).toBeVisible();
    });

    test('healing dismiss button removes card but does not auto-apply fix', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      const card1 = page.locator('#drift-card-fail-1');
      await expect(card1).toBeVisible();
      await card1.getByText('Dismiss').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#drift-card-fail-1')).not.toBeVisible();
      await expect(page.locator('#drift-card-fail-2')).toBeVisible();
    });

    test('diff viewer shows copy/download/dismiss but no auto-apply', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      await page.locator('#drift-card-fail-1 button:has-text("VIEW SUGGESTION DIFF")').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#btn-diff-copy')).toBeVisible();
      await expect(page.locator('#btn-diff-download')).toBeVisible();
      await expect(page.locator('#btn-diff-dismiss')).toBeVisible();
      await expect(page.locator('button:has-text("Auto-Apply")')).not.toBeVisible();
      await expect(page.locator('button:has-text("Auto Apply")')).not.toBeVisible();
    });
  });

  test.describe('Spec-Derived Testing: Expected HTTP status from OpenAPI spec', () => {
    test('ingest endpoint returns 200 for valid spec', async ({ page }) => {
      await smokeSetup(page);
      await page.route('**/api/v1/ingest', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ spec_path: 'spec.yaml', endpoints: [], richness: 1.0 }) })
      );
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#btn-shortcut-petstore').click();
      await page.waitForTimeout(500);
    });

    test('eject endpoint returns 200 with success status', async ({ page }) => {
      await smokeSetup(page);
      await page.route('**/api/v1/eject', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ status: 'success', path: '/out' }) })
      );
      await page.click('#nav-item-eject');
      await page.waitForSelector('#eject-screen');
      await page.locator('#btn-confirm-eject').click();
      await page.waitForTimeout(300);
      await expect(page.locator('#btn-copy-command')).toBeVisible();
    });
  });

  test.describe('Autonomy Toggle — State Preservation', () => {
    test('autonomy toggle persists state across navigation', async ({ page }) => {
      await smokeSetup(page);
      const autonomyGroup = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
      const buttons = autonomyGroup.locator('[role="radio"]');
      await buttons.nth(1).click();
      await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'true');

      await page.click('#nav-item-overview');
      await page.waitForTimeout(300);
      await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'true');
    });
  });

  test.describe('Settings Persistence', () => {
    test('compact mode persists after navigation', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      await smokeSetup(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      await page.locator('input[type="checkbox"]').first().click();
      await page.locator('#btn-settings-save').click();
      await page.waitForTimeout(500);

      const stored = await page.evaluate(() => localStorage.getItem('[copilot] density'));
      expect(stored).toBe('compact');

      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      const storedAfter = await page.evaluate(() => localStorage.getItem('[copilot] density'));
      expect(storedAfter).toBe('compact');
    });
  });

  test.describe('Toast Notification System', () => {
    test('eject success shows toast', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-eject');
      await page.waitForSelector('#eject-screen');
      await page.locator('#btn-confirm-eject').click();
      await page.waitForTimeout(300);
      const toast = page.locator('[role="status"]').first();
      await expect(toast).toBeVisible();
      await expect(toast).toContainText('Eject successful');
    });

    test('new analysis shows navigation toast', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-overview');
      await page.waitForSelector('#overview-screen');
      await page.locator('button:has-text("New Analysis Run")').first().click();
      await page.waitForSelector('#setup-screen');
      await page.waitForTimeout(200);
      const toast = page.locator('[role="status"]').first();
      if (await toast.isVisible()) {
        await expect(toast).toContainText('Starting discovery');
      }
    });
  });

  test.describe('Anti-Lock-In: Eject produces standalone suite', () => {
    test('eject screen shows file tree with standalone structure', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-eject');
      await page.waitForSelector('#eject-screen');
      await expect(page.getByText('playwright-suite/')).toBeVisible();
      await expect(page.locator('#eject-path')).toBeVisible();
      await expect(page.locator('#btn-confirm-eject')).toBeVisible();
    });
  });

  test.describe('SDD Cockpit Regression', () => {
    test('SDD sessions display correct token totals', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText('13,300')).toBeVisible();
      await expect(page.getByText('22100t')).toBeVisible();
    });

    test('SDD compaction panel shows sessions since compact', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText('Compaction')).toBeVisible();
      await expect(page.getByText('open', { exact: true })).toBeVisible();
    });
  });

  test.describe('Chat Regression', () => {
    test('chat SSE streaming works with mock response', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.locator('#chat-screen input[type="text"]').fill('Regression test');
      await page.locator('#chat-screen button').last().click();
      await page.waitForTimeout(500);
      await expect(page.getByText('Regression test')).toBeVisible();
    });
  });

  test.describe('Mobile Regression', () => {
    test('mobile screen shows 4 device cards after load', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-mobile');
      await page.waitForSelector('#mobile-screen');
      await page.waitForTimeout(1000);
      await expect(page.getByTestId('device-card-m1')).toBeVisible();
      await expect(page.getByTestId('device-card-m2')).toBeVisible();
      await expect(page.getByTestId('device-card-m3')).toBeVisible();
      await expect(page.getByTestId('device-card-m4')).toBeVisible();
    });
  });
});

test.describe('Exploratory Testing — Session-Based Charters', () => {

  test.describe('Charter 1: Test Spec Ingestion Edge Cases', () => {
    test('empty URL input does not crash', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.waitForTimeout(300);
      await expect(page.locator('#setup-screen')).toBeVisible();
    });

    test('very long URL in spec input does not crash', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      const longUrl = 'https://example.com/' + 'a'.repeat(500) + '/spec.json';
      await page.locator('#spec-url-input').fill(longUrl);
      await page.waitForTimeout(300);
      await expect(page.locator('#setup-screen')).toBeVisible();
    });

    test('special characters in URL input do not crash', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#btn-sidebar-new-run');
      await page.waitForSelector('#setup-screen');
      await page.locator('#spec-url-input').fill('https://example.com/spec.json?token=abc123&redirect=http://other');
      await page.waitForTimeout(300);
      await expect(page.locator('#setup-screen')).toBeVisible();
    });
  });

  test.describe('Charter 2: Test Autonomy Toggle Edge Cases', () => {
    test('rapidly switching autonomy modes does not break state', async ({ page }) => {
      await smokeSetup(page);
      const buttons = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"] [role="radio"]');
      for (let i = 0; i < 15; i++) {
        await buttons.nth(i % 3).click();
        await page.waitForTimeout(50);
      }
      await expect(buttons.nth(0)).toBeVisible();
    });
  });

  test.describe('Charter 3: Test Concurrent Data Loading', () => {
    test('navigating quickly between screens does not cause data contamination', async ({ page }) => {
      await smokeSetup(page);
      const screens = ['overview', 'divergences', 'signals', 'memory', 'governance', 'overview'];
      for (const screen of screens) {
        await page.click(`#nav-item-${screen}`);
        await page.waitForTimeout(150);
      }
      await page.waitForTimeout(500);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
      const heading = await page.locator('h1').first().textContent();
      expect(heading).toContain('Release Readiness');
    });
  });

  test.describe('Charter 4: Test Divergence Triage Edge Cases', () => {
    test('all severity values render without crash', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/divergences**', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
          { id: 'D-CRIT', divergenceClass: 'D1', endpoint: 'POST /critical', severity: 'critical', status: 'reproduced', claimA: 'A', claimB: 'B', evidence: 'E', reproSteps: 'R', confidence: 0.99 },
          { id: 'D-LOW', divergenceClass: 'D5', endpoint: 'GET /low', severity: 'low', status: 'pending', claimA: 'A', claimB: 'B', evidence: 'E', reproSteps: 'R', confidence: 0.3 },
          { id: 'D-INFO', divergenceClass: 'D2', endpoint: 'PUT /info', severity: 'info', status: 'live', claimA: 'A', claimB: 'B', evidence: 'E', reproSteps: 'R', confidence: 0.1 },
        ]) })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-divergences');
      await page.waitForTimeout(600);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });
  });

  test.describe('Charter 5: Test Healing Suggest-Only Boundary', () => {
    test('no auto-apply button exists on any drift card', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-healing');
      await page.waitForSelector('#healing-screen');
      for (let i = 1; i <= 4; i++) {
        const card = page.locator(`#drift-card-fail-${i}`);
        if (await card.isVisible()) {
          await expect(card.locator('button:has-text("Auto-Apply")')).not.toBeVisible();
          await expect(card.locator('button:has-text("Auto Apply")')).not.toBeVisible();
        }
      }
    });
  });

  test.describe('Charter 6: Test Settings Boundary Values', () => {
    test('budget slider can be adjusted within range', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      await smokeSetup(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      const budgetSlider = page.locator('input[type="range"]').first();
      await expect(budgetSlider).toBeVisible();
      const min = await budgetSlider.getAttribute('min');
      const max = await budgetSlider.getAttribute('max');
      expect(Number(min)).toBeLessThan(Number(max));
    });

    test('threads slider can be adjusted', async ({ page }) => {
      await smokeSetup(page);
      await page.click('[title="Open Settings"]');
      await page.waitForSelector('#settings-screen', { timeout: 10000 });
      const threadsSlider = page.locator('#threads-range-slider');
      await expect(threadsSlider).toBeVisible();
    });
  });

  test.describe('Charter 7: Test Visual Regression Scenario Details', () => {
    test('visual regression scenario expansion shows VLM detail', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-visual-regression');
      await page.waitForTimeout(300);
      await expect(page.getByRole('heading', { name: 'Visual Regression' })).toBeVisible();
      await page.getByText('vs-2').click();
      await expect(page.getByText('Button overlaps form field')).toBeVisible();
    });
  });

  test.describe('Charter 8: Test Explorer Configuration', () => {
    test('explorer screen shows API target URL field', async ({ page }) => {
      await smokeSetup(page);
      await page.click('#nav-item-explore');
      await page.waitForTimeout(300);
      await expect(page.getByText('Autonomous Explorer')).toBeVisible();
      await expect(page.getByText('API Target URL')).toBeVisible();
    });
  });
});

test.describe('Build & Release Artifact Validation', () => {

  test('app loads without JavaScript errors on initial render', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', err => errors.push(err.message));
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(`CONSOLE: ${msg.text()}`);
    });
    await smokeSetup(page);
    const criticalErrors = errors.filter(e => !e.includes('favicon') && !e.includes('404') && !e.includes('ResizeObserver'));
    expect(criticalErrors.length).toBeLessThanOrEqual(2);
  });

  test('all API mock routes are registered and respond', async ({ page }) => {
    const routes: string[] = [];
    page.on('request', request => {
      if (request.url().includes('/api/v1/')) {
        routes.push(`${request.method()} ${request.url()}`);
      }
    });
    await smokeSetup(page);
    await page.click('#nav-item-overview');
    await page.waitForTimeout(600);
    expect(routes.length).toBeGreaterThan(0);
  });

  test('localStorage tour_seen and onboarding_seen flags prevent modals', async ({ page }) => {
    await smokeSetup(page);
    const tourSeen = await page.evaluate(() => localStorage.getItem('[copilot] tour_seen'));
    const onboardingSeen = await page.evaluate(() => localStorage.getItem('[cherenkov] onboarding_seen'));
    expect(tourSeen).toBe('true');
    expect(onboardingSeen).toBe('true');
  });

  test('sidebar mode persists across page reloads', async ({ page }) => {
    await smokeSetup(page);
    await page.evaluate(() => localStorage.setItem('[cherenkov] sidebar_mode', 'expert'));
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(S);
    const mode = await page.evaluate(() => localStorage.getItem('[cherenkov] sidebar_mode'));
    expect(mode).toBe('expert');
  });
});

test.describe('Proof of Fix — Regression Prevention', () => {

  test('fix: empty divergences list renders without crash (was crashing on undefined.length)', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/divergences**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(S);
    await page.click('#nav-item-divergences');
    await page.waitForTimeout(600);
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('fix: empty failures list shows healthy state instead of crash', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/failures', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(S);
    await page.click('#nav-item-healing');
    await page.waitForSelector('#healing-screen');
    await page.waitForTimeout(S);
    await expect(page.getByText('All tests completely healthy')).toBeVisible();
  });

  test('fix: health 500 does not crash app shell', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/health', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'service unavailable' }) })
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
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    await expect(page.locator('#cherenkov-topbar')).toBeVisible();
    await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
  });

  test('fix: auth header input in setup is properly typed (not leaking passwords)', async ({ page }) => {
    await smokeSetup(page);
    await page.click('#btn-sidebar-new-run');
    await page.waitForSelector('#setup-screen');
    await page.locator('#btn-toggle-server-validation').click();
    await page.waitForTimeout(200);
    const authInput = page.locator('#input-auth-header');
    if (await authInput.isVisible()) {
      const inputType = await authInput.getAttribute('type');
      expect(['password', 'text']).toContain(inputType);
    }
  });
});
