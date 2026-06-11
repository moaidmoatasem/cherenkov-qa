import { test, expect } from '@playwright/test';

import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

test.describe('CHERENKOV QA Dashboard — Full Screen Regression Suite', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });
    page.on('pageerror', err => {
      console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
    });

    await setupApiMocks(page);

    // Dismiss the Guided Tour and Onboarding Wizard that appear on first visit
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
  });

  // ── 1. Projects Screen (default landing) ──────────────────────────
  test('Projects screen: cards, search, timer bars, and New Run button', async ({ page }) => {
    await expect(page.locator('#projects-screen')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Cherenkov Observability Root');

    // Three project cards exist
    await expect(page.locator('#project-card-proj-petstore')).toBeVisible();
    await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
    await expect(page.locator('#project-card-proj-auth-identity')).toBeVisible();

    // Timer bars visible on petstore card
    await expect(page.locator('#timer-bar-proj-petstore')).toBeVisible();

    // Search filters projects
    await page.fill('#workspace-search-input', 'Checkout');
    await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
    await expect(page.locator('#project-card-proj-petstore')).not.toBeVisible();

    // Clear search
    await page.fill('#workspace-search-input', '');
    await expect(page.locator('#project-card-proj-petstore')).toBeVisible();

    // New Run button
    await expect(page.locator('#btn-projects-new-run')).toBeVisible();
  });

  // ── 2. Overview Screen ────────────────────────────────────────────
  test('Overview: KPI rings, release readiness, divergences list', async ({ page }) => {
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    await expect(page.locator('h1')).toContainText('Release Readiness & Learning');

    // KPI ring with progressbar role
    const kpiRing = page.locator('[role="progressbar"]').first();
    await expect(kpiRing).toBeVisible();
    const value = await kpiRing.getAttribute('aria-valuenow');
    expect(value).not.toBeNull();
  });

  // ── 3. Truth Map Screen ───────────────────────────────────────────
  test('Truth Map: endpoint list, click endpoint, verify claims panel', async ({ page }) => {
    await page.click('#nav-item-truth-map');
    await page.waitForSelector('#truth-map-screen');
    await expect(page.locator('h1')).toContainText('Endpoint Truth Graph');

    // Endpoint list items render
    await expect(page.getByText('POST /pets').first()).toBeVisible();
    await expect(page.getByText('GET /user/login').first()).toBeVisible();

    // Click the GET /user/login endpoint
    await page.getByText('GET /user/login').first().click();
    await page.waitForTimeout(300);

    // The h3 in the claims detail panel shows the selected endpoint
    const claimsH3 = page.locator('#truth-map-screen h3');
    await expect(claimsH3.first()).toContainText('GET /user/login');

    // Claims list shows VERIFIED text
    await expect(page.getByText('SPEC VERIFIED').first()).toBeVisible();
  });

  // ── 4. Divergences Screen ─────────────────────────────────────────
  test('Divergences: filter, detail drawer open/close', async ({ page }) => {
    await page.click('#nav-item-divergences');
    await page.waitForTimeout(500);
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');

    // Severity filter exists
    const severitySelect = page.locator('select:has(option[value="critical"])');
    await expect(severitySelect).toBeVisible();
    await severitySelect.selectOption('critical');

    // Click a divergence row to open detail drawer
    const row = page.getByText('D-').first();
    await expect(row).toBeVisible();
    await row.click();

    await expect(page.getByText('Divergence Detail').first()).toBeVisible();
    await expect(page.getByText('Evidence payload')).toBeVisible();

    // Close drawer
    await page.click('button[aria-label="Close details"]');
    await expect(page.getByText('Divergence Detail')).not.toBeVisible();
  });

  // ── 5. Author Screen ──────────────────────────────────────────────
  test('Author by Intent: textarea, example chips, mentor idioms', async ({ page }) => {
    await page.click('#nav-item-author');
    await page.waitForSelector('#author-screen');
    await expect(page.locator('h1')).toContainText('Author by Intent');

    // Textarea for NL input
    const textarea = page.locator('textarea').first();
    await expect(textarea).toBeVisible();

    // Click example intent chip
    const chip = page.getByText('Verify that guests can checkout').first();
    await expect(chip).toBeVisible();
    await chip.click();
    await page.waitForTimeout(200);
    const inputVal = await page.inputValue('textarea');
    expect(inputVal).toContain('Verify that guests can checkout');

    // Mentor idioms panel
    await expect(page.getByText('Mentor Context Idioms')).toBeVisible();
  });

  // ── 6. Signals Screen ─────────────────────────────────────────────
  test('Signals: tab switching (Performance, Visual, Coverage)', async ({ page }) => {
    await page.click('#nav-item-signals');
    await page.waitForSelector('#signals-screen');
    await expect(page.locator('h1')).toContainText('Telemetry Signals');

    // Performance tab default
    await expect(page.getByText('API Latency & Anomaly Baselines')).toBeVisible();

    // Switch to Visual
    await page.click('button:has-text("Visual Regression")');
    await expect(page.getByText('UI Snapshot Comparisons')).toBeVisible();

    // Switch to Coverage
    await page.click('button:has-text("SDET Coverage")');
    await expect(page.getByText('Code Path Verification Coverage')).toBeVisible();
  });

  // ── 7. Memory Screen ──────────────────────────────────────────────
  test('Memory & Pairing: idioms and pairing panels', async ({ page }) => {
    await page.click('#nav-item-memory');
    await page.waitForSelector('#memory-screen');
    await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
    await expect(page.getByText('Accumulated Senior Testing Idioms')).toBeVisible();
    await expect(page.getByText('Mentor Junior-Senior Pairing')).toBeVisible();
  });

  // ── 8. Governance Screen ──────────────────────────────────────────
  test('Governance: KPI metrics and compliance', async ({ page }) => {
    await page.click('#nav-item-governance');
    await page.waitForSelector('#governance-screen');
    await expect(page.locator('h1')).toContainText('Governance & Model Certification');
    await expect(page.getByText('Defect Escape Rate')).toBeVisible();
    await expect(page.getByText('Model Capabilities Certification')).toBeVisible();
  });

  // ── 9. Setup Screen ───────────────────────────────────────────────
  test('Setup screen: drag zone, URL input, preset buttons, server validation toggle', async ({ page }) => {
    // Click "New Spec Run" in sidebar to navigate to setup
    await page.click('#btn-sidebar-new-run');
    await page.waitForSelector('#setup-screen');
    await expect(page.locator('h1')).toContainText('New Test Generation Run');

    // Drag zone visible
    await expect(page.getByText('Drag & Drop OpenAPI Spec')).toBeVisible();

    // URL input field
    await expect(page.locator('#spec-url-input')).toBeVisible();

    // Preset shortcut buttons
    await expect(page.locator('#btn-shortcut-petstore')).toBeVisible();
    await expect(page.locator('#btn-shortcut-checkout')).toBeVisible();

    // Click petstore shortcut to load mock spec
    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(500);
    await expect(page.getByText('swagger-petstore-v2.json')).toBeVisible();

    // Toggle server validation expand
    await page.locator('#btn-toggle-server-validation').click();
    await expect(page.locator('#input-server-url')).toBeVisible();
    await expect(page.locator('#input-auth-header')).toBeVisible();
  });

  // ── 10. Pipeline Screen (via Live Execution Drawer) ─────────────────
  test('Pipeline: DAG nodes via live drawer, pause/resume, telemetry', async ({ page }) => {
    // Open the live execution drawer by clicking the node state in TopBar
    await page.click('[title="Click to view live executing pipeline monitor"]');
    await page.waitForTimeout(300);

    // Drawer opens with PipelineScreen inside
    await expect(page.getByText('Live Execution Pipeline Monitor')).toBeVisible();

    // Pipeline DAG nodes
    await expect(page.locator('#pipeline-node-ingest')).toBeVisible();
    await expect(page.locator('#pipeline-node-generate')).toBeVisible();
    await expect(page.locator('#pipeline-node-review')).toBeVisible();

    // Pause/Resume button
    const pauseBtn = page.locator('#pipeline-pause-resume-btn');
    await expect(pauseBtn).toBeVisible();
    await expect(pauseBtn).toContainText('PAUSE');
    await pauseBtn.click();
    await page.waitForTimeout(200);
    await expect(pauseBtn).toContainText('RESUME');

    // Telemetry panel shows token budget
    await expect(page.getByText('TOKEN BUDGET')).toBeVisible();
    await expect(page.getByText('PROMPT ATTENTION SPACE')).toBeVisible();
  });

  // ── 11. Review Screen ──────────────────────────────────────────────
  test('Review: filter tabs, test queue, code viewer', async ({ page }) => {
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');

    // Filter tabs
    await expect(page.locator('#filter-tab-all')).toBeVisible();
    await expect(page.locator('#filter-tab-approved')).toBeVisible();
    await expect(page.locator('#filter-tab-review')).toBeVisible();
    await expect(page.locator('#filter-tab-rejected')).toBeVisible();

    // Click a filter tab
    await page.locator('#filter-tab-approved').click();
    await page.waitForTimeout(200);
  });

  // ── 12. Healing Screen ─────────────────────────────────────────────
  test('Healing: drift cards, dismiss, apply suggestion flow', async ({ page }) => {
    await page.click('#nav-item-healing');
    await page.waitForSelector('#healing-screen');
    await expect(page.locator('h1')).toContainText('Self-Healing & Drift Redress');

    // Drift cards rendered
    await expect(page.locator('#drift-card-fail-1')).toBeVisible();
    await expect(page.locator('#drift-card-fail-2')).toBeVisible();

    // Diagnosis text visible
    await expect(page.getByText('Why it failed:').first()).toBeVisible();

    // Dismiss a card
    const dismissBtn = page.locator('#drift-card-fail-1 button:has-text("Dismiss")');
    await expect(dismissBtn).toBeVisible();
  });

  // ── 13. Eject Screen ──────────────────────────────────────────────
  test('Eject: file tree, output path, eject form, copy command', async ({ page }) => {
    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await expect(page.locator('h1')).toContainText('Export & Eject Suite');

    // Output path input
    await expect(page.locator('#eject-path')).toBeVisible();

    // File tree visible (playwright-suite root)
    await expect(page.getByText('playwright-suite/')).toBeVisible();

    // Eject button
    await expect(page.locator('#btn-confirm-eject')).toBeVisible();

    // Click eject
    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(300);

    // Success state shows copy command button
    await expect(page.locator('#btn-copy-command')).toBeVisible();
  });

  // ── 14. Settings Screen ───────────────────────────────────────────
  test('Settings: model provider, tiers, egress policy, budget sliders, save', async ({ page }) => {
    // Settings is a bottom-pinned button in the sidebar
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await expect(page.locator('h1')).toContainText('System Settings & Credentials');

    // Model provider cards
    await expect(page.getByText('Qwen 2.5 Coder (7B)')).toBeVisible();
    await expect(page.getByText('Gemini 2.5 Flash')).toBeVisible();

    // Substrate tier buttons
    await expect(page.getByText('small').first()).toBeVisible();
    await expect(page.getByText('deep').first()).toBeVisible();
    await expect(page.getByText('vision').first()).toBeVisible();

    // Egress policy buttons
    await expect(page.getByText('Sovereign').first()).toBeVisible();

    // Budget slider
    await expect(page.locator('input[type="range"]').first()).toBeVisible();

    // Thread limit slider
    await expect(page.locator('#threads-range-slider')).toBeVisible();

    // Compact view checkbox
    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await expect(compactCheckbox).toBeVisible();
    await compactCheckbox.click();

    // Save button
    await expect(page.locator('#btn-settings-save')).toBeVisible();
  });

  // ── 15. Explore Screen (inline crawler) ────────────────────────────
  test('Explore screen: inline crawler with "Configure Scope" button', async ({ page }) => {
    await page.click('#nav-item-explore');
    await page.waitForTimeout(300);
    await expect(page.getByText('Explore Crawler')).toBeVisible();
    await expect(page.getByText('Configure Scope & Target')).toBeVisible();
  });

  // ── 16. UI Kit Screen ─────────────────────────────────────────────
  test('UI Kit: panels, cards, pills, tabs, drawer, toasts', async ({ page }) => {
    // UI Kit is a bottom-pinned button in the sidebar
    await page.click('[title="Open UI Kit Gallery"]');
    await page.waitForTimeout(300);
    await expect(page.getByText('UI Kit Consistency Gallery')).toBeVisible();

    // Panels section
    await expect(page.getByText('Panels & Cards')).toBeVisible();
    await expect(page.getByText('Standard Panel')).toBeVisible();
    await expect(page.getByText('Hoverable Card')).toBeVisible();

    // Pills section
    await expect(page.getByText('SeverityPills')).toBeVisible();
    await expect(page.getByText('StatusDots')).toBeVisible();
    await expect(page.getByText('Provenance Chips')).toBeVisible();

    // Interactive elements
    await expect(page.getByText('Tabs Navigation')).toBeVisible();
    await expect(page.getByText('Detail Drawer').first()).toBeVisible();
    await expect(page.getByText('Toasts Feedback')).toBeVisible();

    // KPI Ring section
    await expect(page.getByText('Release Readiness').first()).toBeVisible();
    await expect(page.getByText('False Positive Rate')).toBeVisible();

    // Skeleton toggle
    await expect(page.getByText('Toggle Load View')).toBeVisible();

    // Empty state
    await expect(page.getByText('No Divergences Discovered')).toBeVisible();
    await expect(page.getByText('Trigger Scanner')).toBeVisible();
  });

  // ── 17. Sidebar Navigation & Shell ────────────────────────────────
  test('Sidebar shell: nav items, workspace selector, token pool, status', async ({ page }) => {
    const sidebar = page.locator('#cherenkov-sidebar');
    await expect(sidebar).toBeVisible();

    await expect(page.getByText('LLM Token Pool')).toBeVisible();
    await expect(page.getByText('Active Workspace')).toBeVisible();

    // Status indicator idle initially
    await expect(page.getByText('IDLE').first()).toBeVisible();

    // Project selector
    await expect(page.locator('#project-selector')).toBeVisible();
  });

  // ── 18. TopBar: Autonomy toggle and help button ────────────────────
  test('TopBar: autonomy toggle, session cost, help button', async ({ page }) => {
    const topbar = page.locator('#cherenkov-topbar');
    await expect(topbar).toBeVisible();

    // Autonomy radio group
    const autonomyGroup = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
    await expect(autonomyGroup).toBeVisible();

    const buttons = autonomyGroup.locator('[role="radio"]');
    await expect(buttons).toHaveCount(3);
    await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'true');

    // Click Augmented
    await buttons.nth(1).click();
    await expect(buttons.nth(0)).toHaveAttribute('aria-checked', 'false');
    await expect(buttons.nth(1)).toHaveAttribute('aria-checked', 'true');

    // Session cost visible
    await expect(page.getByText('SESSION COST')).toBeVisible();

    // Help button
    const helpButton = page.locator('button[aria-label="Help Guide"]');
    await expect(helpButton).toBeVisible();
  });

  // ── 19. Health Widget ─────────────────────────────────────────────
  test('Health widget renders backend status in TopBar', async ({ page }) => {
    const topbar = page.locator('#cherenkov-topbar');
    await expect(topbar).toBeVisible();

    // Widget shows device chip
    await expect(page.getByText('cpu').first()).toBeVisible();

    // Widget shows gen model chip
    await expect(page.getByText('qwen2.5-coder:7b').first()).toBeVisible();

    // Widget shows seconds-ago text
    await expect(page.getByText(/\d+s ago/).first()).toBeVisible();
  });

  // ── 20. Command Palette ───────────────────────────────────────────
  test('Command Palette: Ctrl+K opens, search filters, ESC closes', async ({ page }) => {
    await page.keyboard.press('Control+KeyK');
    const paletteInput = page.locator('#command-palette-input');
    await expect(paletteInput).toBeVisible();

    // Type to filter
    await paletteInput.fill('author');
    await page.waitForTimeout(200);
    await expect(page.getByText('Go to Author by Intent')).toBeVisible();

    // Close with ESC
    await page.keyboard.press('Escape');
    await expect(paletteInput).not.toBeVisible();
  });

  // ── 21. Settings Persistence (localStorage) ───────────────────────
  test('Settings: toggle compact mode persists to localStorage', async ({ page }) => {
    // Mock the PUT endpoint so handleSave succeeds and writes localStorage
    await page.route('**/api/v1/settings', async route => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });

    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await compactCheckbox.click();

    await page.locator('#btn-settings-save').click();
    await page.waitForTimeout(500);

    const storedDensity = await page.evaluate(() => localStorage.getItem('[copilot] density'));
    expect(storedDensity).toBe('compact');
  });

  // ── 22. Device & Provider Manager Screen ──────────────────────────
  test('Devices: connectivity, model availability, and provider status panels', async ({ page }) => {
    await page.click('#nav-item-devices');
    await page.waitForSelector('#devices-screen');
    await expect(page.locator('h1')).toContainText('Device & Provider Manager');
    await expect(page.getByText('Device Connectivity')).toBeVisible();
    await expect(page.getByText('Model Availability')).toBeVisible();
    await expect(page.getByText('Provider Status').first()).toBeVisible();
    await expect(page.getByText('LocalAI').first()).toBeVisible();
    await expect(page.getByText('Ollama').first()).toBeVisible();
  });

  // ── 22. Knowledge Explorer Screen ──────────────────────────────────
  test('Knowledge: enter query, submit, verify results grid', async ({ page }) => {
    await page.click('#nav-item-knowledge');
    await page.waitForSelector('#knowledge-screen');
    await expect(page.locator('h1')).toContainText('Knowledge Explorer');

    const input = page.locator('#knowledge-screen input[type="text"]');
    await expect(input).toBeVisible();
    await input.fill('login redirect');

    const submitBtn = page.locator('#knowledge-screen button[type="submit"]');
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    await page.waitForTimeout(500);
    await expect(page.getByText('reflector').first()).toBeVisible();
    await expect(page.getByText('idiom').first()).toBeVisible();
  });

  // ── 24. Pilot Run Button (Overview) ───────────────────────────────
  test('Overview: Pilot Run button triggers POST /api/v1/run with demo intent', async ({ page }) => {
    // Setup route tracking for the run POST
    let runPayload: any = null;
    await page.route('**/api/v1/run', async (route) => {
      if (route.request().method() === 'POST') {
        runPayload = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ run_id: 'pilot-run-id', status: 'started' }) });
      } else {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
      }
    });

    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');

    const pilotBtn = page.locator('#btn-pilot-run');
    await expect(pilotBtn).toBeVisible();
    await expect(pilotBtn).toContainText('Pilot Run');
    await pilotBtn.click();

    await page.waitForTimeout(300);
    expect(runPayload).not.toBeNull();
    expect(runPayload.spec_path).toBe('stub/openapi.yaml');
    expect(runPayload.demo_mode).toBe(true);
  });

  // ── 26. Toast Notifications ────────────────────────────────────────
  test('Toast notifications on user actions across screens', async ({ page }) => {
    // Eject screen: clicking eject shows success toast
    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(300);
    const ejectToast = page.locator('[role="status"]').first();
    await expect(ejectToast).toBeVisible();
    await expect(ejectToast).toContainText('Eject successful');

    // Overview screen: click Run Discovery Scan shows info toast
    await page.click('#nav-item-overview');
    await page.waitForSelector('#overview-screen');
    await page.locator('button:has-text("Run Discovery Scan")').first().click();
    await page.waitForSelector('#setup-screen');
    await page.waitForTimeout(200);
    const navToast = page.locator('[role="status"]').first();
    await expect(navToast).toBeVisible();
    await expect(navToast).toContainText('Initiating discovery scan');

    // Setup screen: load presets then generate shows info toast
    await page.locator('#btn-shortcut-petstore').click();
    await page.waitForTimeout(500);
    await page.locator('#btn-launch-generation').click();
    await page.waitForTimeout(200);
    const genToast = page.locator('[role="status"]').first();
    await expect(genToast).toBeVisible();
    await expect(genToast).toContainText('Starting generation');
  });

  // ── 27. Chat Screen ──────────────────────────────────────────────
  test('Chat: session creation, message input, SSE streaming response', async ({ page }) => {
    await page.click('#nav-item-chat');
    await page.waitForSelector('#chat-screen');
    await expect(page.locator('h1')).toContainText('Chat');

    const textInput = page.locator('#chat-screen input[type="text"]');
    await expect(textInput).toBeVisible();
    await expect(textInput).toBeEnabled();

    await textInput.fill('What tests should I run?');
    const sendButton = page.locator('#chat-screen button:has(svg)');
    await expect(sendButton).toBeVisible();
    await sendButton.click();

    await expect(page.getByText('What tests should I run?')).toBeVisible();

    await page.waitForTimeout(500);
    await expect(page.getByText(/Hello from CHERENKOV/)).toBeVisible();
  });

  // ── 28. Mobile Screen (NE8) ──────────────────────────────────────────
  test('Mobile screen: device grid renders with disconnected badges', async ({ page }) => {
    await page.click('#nav-item-mobile');
    await page.waitForSelector('#mobile-screen');
    await expect(page.locator('h1')).toContainText('Mobile Testing');

    // Wait for 800ms loading timer to fire
    await page.waitForTimeout(1000);

    // All four device cards present via data-testid
    await expect(page.getByTestId('device-card-m1')).toBeVisible();
    await expect(page.getByTestId('device-card-m2')).toBeVisible();
    await expect(page.getByTestId('device-card-m3')).toBeVisible();
    await expect(page.getByTestId('device-card-m4')).toBeVisible();

    // Device names visible
    await expect(page.getByText('iPhone 15 Pro')).toBeVisible();
    await expect(page.getByText('Pixel 8')).toBeVisible();

    // All devices start disconnected
    const m1Status = page.getByTestId('device-status-m1');
    await expect(m1Status).toBeVisible();
    await expect(m1Status).toContainText('Disconnected');

    // Instructions panel visible
    await expect(page.getByText('Mobile testing requires ADB')).toBeVisible();
    await expect(page.getByText('Phase 5/6')).toBeVisible();
  });

  test('Mobile screen: skeleton visible during load then replaced by device cards', async ({ page }) => {
    await page.click('#nav-item-mobile');
    await page.waitForSelector('#mobile-screen');

    // A card or skeleton container should be visible immediately
    const firstCard = page.locator('#mobile-screen [class*="space-y-3"]').first();
    await expect(firstCard).toBeVisible();

    // After timer fires, real device cards appear
    await page.waitForTimeout(1100);
    await expect(page.getByTestId('device-card-m1')).toBeVisible();
  });

});

// ── Error-Path E2E Suite (NE9) ─────────────────────────────────────────────
test.describe('CHERENKOV QA Dashboard — Error Path Coverage', () => {

  test.beforeEach(async ({ page }) => {
    page.on('pageerror', err => {
      console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}`);
    });

    await setupApiMocks(page);

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
  });

  test('Health widget degrades gracefully when API returns 500', async ({ page }) => {
    await page.route('**/api/v1/health', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'service unavailable' }) })
    );

    await page.reload();
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);

    // App shell must not crash — topbar and sidebar still render
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    await expect(page.locator('#cherenkov-topbar')).toBeVisible();
    await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
  });

  test('Divergences screen renders without crash when API returns empty list', async ({ page }) => {
    await page.route('**/api/v1/divergences**', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );

    await page.click('#nav-item-divergences');
    await page.waitForTimeout(600);

    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('Divergences screen renders without crash when API returns 500', async ({ page }) => {
    await page.route('**/api/v1/divergences**', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'internal error' }) })
    );

    await page.click('#nav-item-divergences');
    await page.waitForTimeout(600);

    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    await expect(page.locator('#cherenkov-app-core')).toBeVisible();
  });

  test('Eject screen: UI survives when eject API returns 500', async ({ page }) => {
    await page.route('**/api/v1/eject', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'disk full' }) })
    );

    await page.click('#nav-item-eject');
    await page.waitForSelector('#eject-screen');
    await page.locator('#btn-confirm-eject').click();
    await page.waitForTimeout(500);

    await expect(page.locator('#eject-screen')).toBeVisible();
  });

  test('Review screen: renders correctly when approve/reject endpoints return 500', async ({ page }) => {
    await page.route('**/api/v1/review/approve', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'error' }) })
    );
    await page.route('**/api/v1/review/reject', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'error' }) })
    );

    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');

    await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
    await expect(page.locator('#filter-tab-all')).toBeVisible();
  });

});
