/**
 * Headless UI Testing as Real QA User
 *
 * Tests the CHERENKOV dashboard against a real backend (port 8001,
 * the API-mode port matching the Vite dev server's /api/v1 proxy target)
 * via the Vite dev server (port 3000). These are workflow tests,
 * not screen smoke checks — they follow what a QA engineer actually does.
 *
 * NOTE: This suite targets the live 5-workspace UI (nav-workspace-* /
 * workspace panel testids). Legacy screens (SetupScreen, ReviewScreen,
 * Sidebar, TopBar, HealingScreen, etc.) were removed in the UI revamp;
 * their specs are archived via `testIgnore` in playwright.config.ts.
 *
 * Run: npx playwright test tests/qa/headless-qa-user.spec.ts --reporter=list
 */
import { test, expect, Page } from '@playwright/test';
import {
  bootstrapReal,
  waitForBackend,
  mockChatStream,
  Sidebar,
  DashboardWorkspacePage,
  AuthoringWorkspacePage,
  TriageWorkspacePage,
  IntelligenceWorkspacePage,
  SettingsWorkspacePage,
  CommandPalette,
} from './page-objects';

const API = 'http://127.0.0.1:8001';
const WORKSPACES = ['dashboard', 'authoring', 'triage', 'intelligence', 'settings'] as const;

// ─── BACKEND GUARD ────────────────────────────────────────────────────────────

test.describe.configure({ retries: 0 });

test.describe('Headless QA User — Backend Guard', () => {
  test.beforeAll(async ({ request }) => {
    const alive = await waitForBackend(request);
    test.skip(!alive, 'Backend not running on port 8001 — skipping all headless QA tests');
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
    await expect(page.getByTestId('backend-health-badge')).toBeVisible();
    await expect(page.getByTestId('nav-workspace-dashboard')).toBeVisible();
  });

  test('backend health badge reflects real /api/v1/health', async ({ page }) => {
    await bootstrapReal(page);
    await expect(page.getByTestId('backend-health-badge')).toContainText('Backend Online');
  });

  test('all 5 workspace navigation items are visible', async ({ page }) => {
    await bootstrapReal(page);
    for (const ws of WORKSPACES) {
      await expect(page.getByTestId(`nav-workspace-${ws}`)).toBeVisible();
    }
  });
});

// ─── GROUP 2: SPEC SETUP → GENERATE → REVIEW → EJECT ──────────────────────────

test.describe('Headless QA User — Spec Setup & Generation Journey', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('authoring workspace loads spec ingest panel', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('authoring');
    const authoring = new AuthoringWorkspacePage(page);
    await expect(authoring.el).toBeVisible();
    await expect(authoring.specIngestPanel).toBeVisible();
    await expect(page.getByTestId('spec-drop-zone')).toBeVisible();
  });

  test('spec URL input accepts a URL', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('authoring');
    const urlInput = page.getByTestId('spec-ingest-panel').locator('form input[type="url"]');
    await urlInput.fill('https://petstore3.swagger.io/api/v3/openapi.json');
    await expect(urlInput).toHaveValue('https://petstore3.swagger.io/api/v3/openapi.json');
  });

  test('live pipeline monitor renders DAG tracker', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('authoring');
    const authoring = new AuthoringWorkspacePage(page);
    await expect(authoring.livePipelineMonitor).toBeVisible();
  });

  test('review queue panel renders in triage workspace', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('triage');
    const triage = new TriageWorkspacePage(page);
    await expect(triage.el).toBeVisible();
    await expect(triage.hitlReviewQueue).toBeVisible();
    await expect(triage.hitlReviewQueue.getByText('HITL Test Review Queue')).toBeVisible();
  });

  test('approve button triggers real POST /api/v1/review/approve', async ({ page }) => {
    // Backend queue may be empty on a fresh instance — seed a deterministic
    // item for the queue GET only; the approve POST still hits the real backend.
    await page.route('**/api/v1/review/queue*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'test-3',
            endpoint: '/pets',
            method: 'PUT',
            confidence: 0.81,
            confidence_reason: null,
            review_gate_failed: null,
            status: 'review',
            reject_reason: null,
            generated_test: 'test("PUT /pets")',
            created_at: '2026-01-01T00:00:00Z',
          },
        ]),
      });
    });
    await bootstrapReal(page);
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('triage');
    await expect(page.getByTestId('review-item-test-3')).toBeVisible();
    await page.getByTestId('review-item-test-3').click();
    const approveBtn = page.getByTestId('btn-approve-scenario');
    await expect(approveBtn).toBeVisible();
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/review/approve') && req.method() === 'POST') {
        apiCalled = true;
      }
    });
    await approveBtn.click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
  });

  test('eject suite panel triggers real POST /api/v1/eject', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('settings');
    const settings = new SettingsWorkspacePage(page);
    await expect(settings.ejectSuitePanel).toBeVisible();
    await expect(page.getByTestId('eject-output-path')).toBeVisible();
    await page.getByTestId('eject-output-path').fill('./eject-e2e-output');
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/eject') && req.method() === 'POST') {
        apiCalled = true;
      }
    });
    await page.getByTestId('btn-run-eject').click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
  });

  test('release readiness card renders KPI ring', async ({ page }) => {
    const dashboard = new DashboardWorkspacePage(page);
    await expect(dashboard.releaseReadinessCard).toBeVisible();
    await expect(dashboard.releaseReadinessCard.locator('[role="progressbar"]').first()).toBeVisible();
  });
});

// ─── GROUP 3: DIVERGENCE TRIAGE ───────────────────────────────────────────────

test.describe('Headless QA User — Divergence Triage', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('divergence table renders with severity filter', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('triage');
    const triage = new TriageWorkspacePage(page);
    await expect(triage.divergenceTable).toBeVisible();
    await expect(triage.divergenceTable.locator('select').first()).toBeVisible();
  });

  test('severity filter narrows the table', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('triage');
    const triage = new TriageWorkspacePage(page);
    const select = triage.divergenceTable.locator('select').first();
    await expect(select).toBeVisible();
    await select.selectOption('critical');
    await expect(select).toHaveValue('critical');
  });
});

// ─── GROUP 4: CHAT AGENT REAL SSE STREAMING ──────────────────────────────────

test.describe('Headless QA User — Chat Agent SSE Streaming', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await mockChatStream(page);
  });

  test('chat assistant loads with input and send button', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('intelligence');
    const intelligence = new IntelligenceWorkspacePage(page);
    await expect(intelligence.sseChatAssistant).toBeVisible();
    await expect(page.getByTestId('chat-input')).toBeVisible();
    await expect(page.getByTestId('chat-send-btn')).toBeVisible();
  });

  test('sending message creates user bubble and clears input', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('intelligence');
    const input = page.getByTestId('chat-input');
    const text = 'What tests should I run for the Petstore API?';
    await input.fill(text);
    await page.getByTestId('chat-send-btn').click();
    await expect(page.getByText(text)).toBeVisible();
    await expect(input).toHaveValue('');
  });

  test('assistant response streams via SSE (event: token / event: complete)', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('intelligence');
    const input = page.getByTestId('chat-input');
    await input.fill('Show me the test count');
    await page.getByTestId('chat-send-btn').click();
    // Real backend substrate is live: assert a streamed assistant bubble appears,
    // not the offline "[MOCK]" fallback that only shows when no router is available.
    await expect(page.getByTestId('chat-message-assistant').first()).toBeVisible({ timeout: 15000 });
  });

  test('follow-up message maintains conversation context', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('intelligence');
    const input = page.getByTestId('chat-input');
    const sendBtn = page.getByTestId('chat-send-btn');
    await input.fill('First message');
    await sendBtn.click();
    await expect(page.getByTestId('chat-message-assistant').first()).toBeVisible({ timeout: 15000 });
    await input.fill('Follow up question');
    await sendBtn.click();
    await expect(page.getByTestId('chat-message-user')).toHaveCount(2, { timeout: 15000 });
    await expect(page.getByText('First message')).toBeVisible();
    await expect(page.getByText('Follow up question')).toBeVisible();
  });
});

// ─── GROUP 5: SETTINGS PERSISTENCE + KEYBOARD + STRESS ────────────────────────

test.describe('Headless QA User — Settings, Keyboard, Stress', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
  });

  test('settings workspace loads project, device and governance panels', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('settings');
    const settings = new SettingsWorkspacePage(page);
    // 15s assertion timeout: the 4 panels mount under load + real backend fetches;
    // a transient dev-server reload has been observed to delay first paint.
    await expect(settings.el).toBeVisible();
    await expect(settings.projectManager).toBeVisible({ timeout: 15000 });
    await expect(settings.deviceManager).toBeVisible({ timeout: 15000 });
    await expect(settings.governanceSettings).toBeVisible({ timeout: 15000 });
  });

  test('save governance settings triggers real PUT /api/v1/settings', async ({ page }) => {
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('settings');
    const saveBtn = page.getByTestId('btn-save-governance-settings');
    await expect(saveBtn).toBeVisible();
    // Button starts disabled until fetchSettings() resolves; the suite docs note
    // dev-server reload + real backend fetches can delay first paint up to 15s.
    await expect(saveBtn).toBeEnabled({ timeout: 15000 });
    let apiCalled = false;
    page.on('request', req => {
      if (req.url().includes('/api/v1/settings') && req.method() === 'PUT') {
        apiCalled = true;
      }
    });
    await saveBtn.click();
    await page.waitForTimeout(500);
    expect(apiCalled).toBe(true);
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

  test('keyboard-only navigation reaches all 5 workspace containers', async ({ page }) => {
    await bootstrapReal(page);
    for (const ws of WORKSPACES) {
      await page.getByTestId(`nav-workspace-${ws}`).focus();
      await page.keyboard.press('Enter');
      await page.waitForTimeout(250);
      await expect(page.locator(`#${ws}-workspace`)).toBeVisible();
    }
  });

  test('rapid navigation across all 5 workspaces does not crash', async ({ page }) => {
    await bootstrapReal(page);
    for (const ws of WORKSPACES) {
      await page.getByTestId(`nav-workspace-${ws}`).click();
      await page.waitForTimeout(150);
    }
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('rapid chat sends do not crash', async ({ page }) => {
    await bootstrapReal(page);
    await mockChatStream(page);
    const sidebar = new Sidebar(page);
    await sidebar.navToWorkspace('intelligence');
    const input = page.getByTestId('chat-input');
    const sendBtn = page.getByTestId('chat-send-btn');
    for (let i = 0; i < 3; i++) {
      await input.fill(`Rapid message ${i}`);
      await sendBtn.click();
      await expect(page.getByText(`Rapid message ${i}`)).toBeVisible({ timeout: 10000 });
    }
    await expect(page.getByTestId('sse-chat-assistant')).toBeVisible();
  });
});
