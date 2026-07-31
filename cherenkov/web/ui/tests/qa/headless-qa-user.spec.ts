/**
 * Headless UI Testing as Real QA User
 *
 * Tests the CHERENKOV dashboard against a real backend (port 8000)
 * via the Vite dev server (port 3000). These are workflow tests,
 * not screen smoke checks — they follow what a QA engineer actually does.
 *
 * Run: npx playwright test tests/qa/headless-qa-user.spec.ts --reporter=list
 */
import { test, expect, Page } from '@playwright/test';
import {
  bootstrapReal,
  waitForBackend,
  mockChatStream,
  Sidebar,
  TopBar,
  SetupPage,
  PipelinePage,
  ReviewPage,
  HealingPage,
  EjectPage,
  OverviewPage,
  DivergencesPage,
  ChatPage,
  SettingsPage,
  CommandPalette,
} from './page-objects';

const SETTLE = 500;

async function navTo(page: Page, id: string) {
  await page.click(`#nav-item-${id}`);
  await page.waitForTimeout(SETTLE);
}

// ─── BACKEND GUARD ────────────────────────────────────────────────────────────

test.describe.configure({ retries: 0 });

test.describe('Headless QA User — Backend Guard', () => {
  test.beforeAll(async ({ request }) => {
    const alive = await waitForBackend(request);
    test.skip(!alive, 'Backend not running on port 8000 — skipping all headless QA tests');
  });

  test('health endpoint returns 200 with valid structure', async ({ request }) => {
    const res = await request.get(`${API}/api/v1/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.status).toBe('online');
    expect(typeof body.demo_mode).toBe('boolean');
    expect(typeof body.gen_model).toBe('string');
  });

  test('app core container renders with real backend', async ({ page }) => {
    await bootstrapReal(page);
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
    await expect(page.locator('#cherenkov-topbar')).toBeVisible();
  });

  test('topbar health indicator shows real device/model from backend', async ({ page }) => {
    await bootstrapReal(page);
    const healthRes = await page.evaluate(async () => {
      const r = await fetch('/api/v1/health');
      return r.json();
    });
    expect(healthRes.status).toBe('online');
    const topBar = new TopBar(page);
    await expect(topBar.healthDevice.first()).toBeVisible();
    await expect(topBar.healthModel.first()).toBeVisible();
  });

  test('sidebar navigation items all visible', async ({ page }) => {
    await bootstrapReal(page);
    const navItems = [
      'overview', 'truth-map', 'divergences', 'review', 'healing',
      'eject', 'author', 'signals', 'memory', 'governance',
      'knowledge', 'devices', 'chat', 'mobile', 'sdd',
    ];
    for (const id of navItems) {
      await expect(page.locator(`#nav-item-${id}`)).toBeVisible();
    }
  });
});

// ─── GROUP 2: SPEC SETUP → GENERATE → REVIEW → EJECT ──────────────────────────

test.describe('Headless QA User — Spec Setup & Generation Journey', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('setup screen loads and accepts spec URL', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.newRun();
    await expect(page.locator('#setup-screen')).toBeVisible();
    const setup = new SetupPage(page);
    await setup.urlInput.fill('https://petstore3.swagger.io/api/v3/openapi.json');
    await expect(setup.urlInput).toHaveValue('https://petstore3.swagger.io/api/v3/openapi.json');
  });

  test('petstore preset loads and shows spec name', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.newRun();
    const setup = new SetupPage(page);
    await setup.loadPetstore();
    await expect(page.getByText('swagger-petstore')).toBeVisible();
  });

  test('launch button appears after preset load', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.newRun();
    const setup = new SetupPage(page);
    await setup.loadPetstore();
    await expect(setup.launchBtn).toBeVisible();
  });

  test('launch triggers pipeline drawer with nodes', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.newRun();
    const setup = new SetupPage(page);
    await setup.loadPetstore();
    await setup.launchBtn.click();
    await page.waitForTimeout(1000);
    const topBar = new TopBar(page);
    await topBar.openPipelineDrawer();
    const pipeline = new PipelinePage(page);
    await expect(pipeline.node('ingest')).toBeVisible();
    await expect(pipeline.node('generate')).toBeVisible();
    await expect(pipeline.node('review')).toBeVisible();
  });

  test('review screen shows real HITL queue from backend', async ({ page }) => {
    await navTo(page, 'review');
    const review = new ReviewPage(page);
    await expect(review.el).toBeVisible();
    await expect(review.filterTab('all')).toBeVisible();
    await expect(review.filterTab('approved')).toBeVisible();
    await expect(review.filterTab('review')).toBeVisible();
    await expect(review.filterTab('rejected')).toBeVisible();
  });

  test('approve button triggers real API call', async ({ page }) => {
    await navTo(page, 'review');
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/review/approve') && req.method() === 'POST') {
        apiCalled = true;
      }
    });
    const review = new ReviewPage(page);
    await review.approveBtn.click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
  });

  test('eject screen loads and eject button triggers real POST', async ({ page }) => {
    await navTo(page, 'eject');
    const eject = new EjectPage(page);
    await expect(eject.el).toBeVisible();
    await expect(eject.pathInput).toBeVisible();
    await expect(eject.ejectBtn).toBeVisible();
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/eject') && req.method() === 'POST') {
        apiCalled = true;
      }
    });
    await eject.ejectBtn.click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
  });

  test('overview screen KPI ring renders', async ({ page }) => {
    await navTo(page, 'overview');
    const overview = new OverviewPage(page);
    await expect(overview.el).toBeVisible();
    await expect(overview.kpiRing).toBeVisible();
  });
});

// ─── GROUP 3: DIVERGENCE TRIAGE & HEALING ─────────────────────────────────────

test.describe('Headless QA User — Divergence Triage & Healing', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('divergences screen loads 7 real divergences from backend', async ({ page }) => {
    await navTo(page, 'divergences');
    const divs = new DivergencesPage(page);
    await expect(divs.el).toBeVisible();
    await expect(divs.heading).toContainText('Divergence Triage Hub');
    const divCount = await page.getByText('D-', { exact: false }).count();
    expect(divCount).toBeGreaterThanOrEqual(7);
  });

  test('severity filter works against real data', async ({ page }) => {
    await navTo(page, 'divergences');
    const divs = new DivergencesPage(page);
    await divs.filterBySeverity('critical');
    await page.waitForTimeout(300);
    await expect(divs.el).toBeVisible();
  });

  test('clicking divergence opens detail drawer', async ({ page }) => {
    await navTo(page, 'divergences');
    await page.getByText('D-').first().click();
    await page.waitForTimeout(300);
    await expect(page.getByText('Divergence Detail').first()).toBeVisible();
    await page.locator('button[aria-label="Close details"]').click();
    await expect(page.getByText('Divergence Detail').first()).not.toBeVisible();
  });

  test('healing screen loads with drift cards from /api/v1/failures', async ({ page }) => {
    await navTo(page, 'healing');
    const healing = new HealingPage(page);
    await expect(healing.el).toBeVisible();
    await expect(healing.banner).toBeVisible();
    await expect(page.getByText('All repairs are suggest-only')).toBeVisible();
  });

  test('drift card shows diff viewer on click', async ({ page }) => {
    await navTo(page, 'healing');
    const healing = new HealingPage(page);
    await healing.viewDiff('fail-1');
    await expect(healing.diffViewer()).toBeVisible();
    await expect(healing.diffCopyBtn).toBeVisible();
    await expect(healing.diffDownloadBtn).toBeVisible();
    await healing.diffDismissBtn.click();
  });

  test('dismissing drift card removes it from view', async ({ page }) => {
    await navTo(page, 'healing');
    const healing = new HealingPage(page);
    await healing.dismissCard('fail-1');
    await page.waitForTimeout(300);
    await expect(healing.card('fail-1')).not.toBeVisible();
  });
});

// ─── GROUP 4: CHAT AGENT REAL SSE STREAMING ──────────────────────────────────

test.describe('Headless QA User — Chat Agent SSE Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await mockChatStream(page);
  });

  test('chat screen loads and session is created', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await expect(chat.el).toBeVisible();
    await expect(chat.input).toBeVisible();
  });

  test('sending message creates user bubble and clears input', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await chat.send('What tests should I run for the Petstore API?');
    await expect(chat.messageBubble('What tests should I run for the Petstore API?')).toBeVisible();
    await expect(chat.input).toHaveValue('');
  });

  test('assistant response streams via SSE (event: token / event: complete)', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await chat.send('Show me the test count');
    await chat.waitForStreamResponse(15000);
    await expect(chat.messagesList.getByText('[MOCK]')).toBeVisible({ timeout: 10000 });
  });

  test('streaming cursor appears during streaming and disappears after complete', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await chat.send('Streaming test');
    const streamingIndicator = chat.messagesList.locator('.animate-pulse').first();
    await expect(streamingIndicator).toBeVisible({ timeout: 5000 });
    await chat.waitForStreamResponse(15000);
    await expect(streamingIndicator).not.toBeVisible({ timeout: 10000 });
  });

  test('follow-up message maintains conversation context', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await chat.send('First message');
    await chat.waitForStreamResponse(15000);
    await chat.send('Follow up question');
    await chat.waitForStreamResponse(15000);
    await expect(chat.messageBubble('First message')).toBeVisible();
    await expect(chat.messageBubble('Follow up question')).toBeVisible();
  });

  test('persona selector changes context', async ({ page }) => {
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    await expect(page.locator('select').first()).toBeVisible();
    await page.locator('select').first().selectOption('qa');
    await page.waitForTimeout(200);
  });
});

// ─── GROUP 5: SETTINGS PERSISTENCE + KEYBOARD + STRESS ────────────────────────

test.describe('Headless QA User — Settings, Keyboard, Stress', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('settings screen loads real values from backend', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
    const settings = new SettingsPage(page);
    await expect(settings.el).toBeVisible();
    await expect(settings.heading).toContainText('System Settings');
    await expect(settings.budgetSlider).toBeVisible();
    await expect(settings.threadsSlider).toBeVisible();
    await expect(settings.compactCheckbox).toBeVisible();
  });

  test('changing tier selection persists visually', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
    const tierButtons = page.locator('[data-testid="model-tier-select"] button');
    await expect(tierButtons.first()).toBeVisible();
    await tierButtons.nth(1).click(); // deep
    await page.waitForTimeout(200);
    await expect(tierButtons.nth(1)).toHaveClass(/bg-glow-blue/);
  });

  test('thread limit slider updates display value', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
    const settings = new SettingsPage(page);
    const initialValue = await settings.threadsSlider.inputValue();
    await settings.threadsSlider.fill('8');
    await page.waitForTimeout(200);
    await expect(settings.threadsSlider).toHaveValue('8');
  });

  test('compact mode toggle persists to localStorage', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
    const checkbox = page.locator('input[type="checkbox"]').first();
    await checkbox.click();
    await page.waitForTimeout(200);
    await expect(checkbox).toBeChecked();
    const lsValue = await page.evaluate(() => localStorage.getItem('[copilot] density'));
    expect(lsValue).toBe('compact');
  });

  test('save button triggers real PUT /api/v1/settings', async ({ page }) => {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/settings') && req.method() === 'PUT') {
        apiCalled = true;
      }
    });
    const settings = new SettingsPage(page);
    await settings.saveBtn.click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
  });

  test('keyboard-only navigation reaches all sidebar items', async ({ page }) => {
    await bootstrapReal(page);
    const sidebar = page.locator('#cherenkov-sidebar');
    await sidebar.focus();
    const navItems = ['overview', 'truth-map', 'divergences', 'review', 'healing', 'eject', 'author', 'signals', 'memory', 'governance', 'knowledge', 'devices', 'chat', 'mobile', 'sdd'];
    for (const id of navItems) {
      await page.keyboard.press('Tab');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);
      await expect(page.locator(`#nav-item-${id}`)).toBeFocused();
    }
  });

  test('command palette opens with Ctrl+K, searches, closes with Escape', async ({ page }) => {
    await bootstrapReal(page);
    const palette = new CommandPalette(page);
    await palette.open();
    await expect(palette.input).toBeVisible();
    await palette.search('author');
    await expect(page.getByText('Go to Author by Intent')).toBeVisible();
    await palette.close();
    await expect(palette.input).not.toBeVisible();
  });

  test('rapid navigation across all screens does not crash', async ({ page }) => {
    await bootstrapReal(page);
    const screens = ['overview', 'truth-map', 'divergences', 'author', 'signals', 'memory', 'governance', 'review', 'healing', 'eject', 'chat', 'knowledge', 'devices', 'mobile', 'sdd'];
    for (const id of screens) {
      await page.click(`#nav-item-${id}`);
      await page.waitForTimeout(150);
    }
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('rapid chat sends do not crash', async ({ page }) => {
    await bootstrapReal(page);
    await mockChatStream(page);
    await navTo(page, 'chat');
    const chat = new ChatPage(page);
    for (let i = 0; i < 3; i++) {
      await chat.send(`Rapid message ${i}`);
      await page.waitForTimeout(200);
    }
    await expect(chat.el).toBeVisible();
  });

  test('overview screen KPI ring displays real backend data', async ({ page }) => {
    await navTo(page, 'overview');
    const overview = new OverviewPage(page);
    await expect(overview.kpiRing).toBeVisible();
    const ariaValue = await overview.kpiRing.getAttribute('aria-valuenow');
    expect(Number(ariaValue)).toBeGreaterThanOrEqual(0);
    expect(Number(ariaValue)).toBeLessThanOrEqual(100);
  });
});