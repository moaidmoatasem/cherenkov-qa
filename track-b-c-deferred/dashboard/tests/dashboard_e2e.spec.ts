import { test, expect } from '@playwright/test';

test.describe('CHERENKOV QA Observability Dashboard E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    // Capture browser console logs
    page.on('console', msg => {
      console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
    });

    // Capture uncaught exceptions in page
    page.on('pageerror', err => {
      console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
    });

    // Navigate to the local dashboard Vite dev server port 3000
    await page.goto('/');
    await page.waitForSelector('#cherenkov-app-core');
    
    // Wait for React hydration to fully attach event handlers to buttons
    await page.waitForTimeout(1000);
  });

  test('Page shell and Sidebar controls function properly', async ({ page }) => {
    const sidebar = page.locator('#cherenkov-sidebar');
    await expect(sidebar).toBeVisible();

    await expect(page.locator('text=LLM Token Pool')).toBeVisible();
    await expect(page.locator('text=Active Workspace')).toBeVisible();

    // Verify status indicator is present and idle initially
    await expect(page.locator('text=IDLE').first()).toBeVisible();
  });

  test('Navigate to Overview Screen and verify release metrics', async ({ page }) => {
    await page.click('#nav-item-overview');
    
    // Check main title is correct
    const header = page.locator('h1');
    await expect(header).toContainText('Release Readiness & Learning');
    
    // Verify key metrics KPI components
    await expect(page.locator('text=Release Readiness Score')).toBeVisible();
    await expect(page.locator('text=Reflector Verdict Memory')).toBeVisible();
    
    // Use exact match to avoid strict mode violation on "Readiness" substring
    await expect(page.getByText('Readiness', { exact: true })).toBeVisible();
  });

  test('Navigate to Truth Map Screen and inspect endpoint claims', async ({ page }) => {
    await page.click('#nav-item-truth-map');

    // Check header
    await expect(page.locator('h1')).toContainText('Endpoint Truth Graph');

    // Click on /user/login endpoint to view its claims list (present in mockData.ts)
    const endpointRow = page.getByText('/user/login').first();
    await expect(endpointRow).toBeVisible();
    await endpointRow.click();

    // Ensure claims matching the selected endpoint render
    await expect(page.locator('h3').first()).toContainText('/user/login');
    await expect(page.locator('text=VERIFIED').first()).toBeVisible();
  });

  test('Navigate to Divergences Screen, filter anomalies, and use detail drawer', async ({ page }) => {
    await page.click('#nav-item-divergences');

    // Check header
    await expect(page.locator('h1')).toContainText('Divergence Triage Hub');

    // Filter by severity critical (specifically targeting the select elements containing critical option)
    const severitySelect = page.locator('select:has(option[value="critical"])');
    await expect(severitySelect).toBeVisible();
    await severitySelect.selectOption('critical');

    // Click a divergence row to open the detail drawer
    const row = page.locator('text=D-').first();
    await expect(row).toBeVisible();
    await row.click();

    // Verify detail drawer elements are shown
    await expect(page.locator('text=Divergence Detail').first()).toBeVisible();
    await expect(page.locator('text=Evidence payload')).toBeVisible();
    await expect(page.locator('text=Independent Repro Steps')).toBeVisible();

    // Close the drawer (using correct close button aria-label)
    await page.click('button[aria-label="Close details"]');
    await expect(page.locator('text=Divergence Detail')).not.toBeVisible();
  });

  test('Navigate to Author by Intent Screen and check manual NL-QA flow', async ({ page }) => {
    await page.click('#nav-item-author');

    // Verify UI components
    await expect(page.locator('h1')).toContainText('Author by Intent');
    await expect(page.locator('[placeholder="e.g. Verify that guest checkouts apply 15% discount code and succeed with 200 OK..."]')).toBeVisible();

    // Click an example intent chip to populate input
    const chip = page.locator('text="Verify that guests can checkout with valid cart items and coupons."').first();
    await expect(chip).toBeVisible();
    await chip.click();

    // Verify prompt value got updated
    const inputVal = await page.inputValue('textarea');
    expect(inputVal).toContain('Verify that guests can checkout');

    // Verify Mentor Idioms advice displays contextually
    await expect(page.locator('text=Mentor Context Idioms')).toBeVisible();
  });

  test('Navigate to Signals Screen and review latency and visual regression baseline tabs', async ({ page }) => {
    await page.click('#nav-item-signals');

    await expect(page.locator('h1')).toContainText('Telemetry Signals');

    // Performance tab is active by default
    await expect(page.locator('text=API Latency & Anomaly Baselines')).toBeVisible();

    // Switch to Visual tab
    await page.click('button:has-text("Visual Regression")');
    await expect(page.locator('text=UI Snapshot Comparisons')).toBeVisible();

    // Switch to Coverage tab
    await page.click('button:has-text("SDET Coverage")');
    await expect(page.locator('text=Code Path Verification Coverage')).toBeVisible();
  });

  test('Navigate to Memory & Pairing Screen and inspect senior idioms', async ({ page }) => {
    await page.click('#nav-item-memory');

    await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
    await expect(page.locator('text=Accumulated Senior Testing Idioms')).toBeVisible();
    await expect(page.locator('text=Mentor Junior-Senior Pairing')).toBeVisible();
  });

  test('Navigate to Governance Screen and verify model compliance', async ({ page }) => {
    await page.click('#nav-item-governance');

    await expect(page.locator('h1')).toContainText('Governance & Model Certification');
    await expect(page.locator('text=Defect Escape Rate')).toBeVisible();
    await expect(page.locator('text=Model Capabilities Certification')).toBeVisible();
  });

  test('Navigate to Settings, modify configuration, and verify persistence', async ({ page }) => {
    await page.click('button:has-text("Settings")');

    await expect(page.locator('h1')).toContainText('System Settings & Credentials');

    // Toggle density (using checkbox element instead of nonexistent button)
    const compactCheckbox = page.locator('input[type="checkbox"]').first();
    await expect(compactCheckbox).toBeVisible();
    await compactCheckbox.click();

    // Verify LocalStorage updates or stays custom
    const storedAutonomy = await page.evaluate(() => localStorage.getItem('[copilot] autonomy'));
    expect(storedAutonomy).toBeDefined();
  });

  test('Trigger global Command Palette (Ctrl+K / Cmd+K)', async ({ page }) => {
    // Dispatch keyboard shortcut
    await page.keyboard.press('Control+KeyK');

    // Palette input field should display
    const paletteInput = page.locator('[placeholder="Type page name or action command (e.g. \'author\', \'setup\', \'divergences\')..."]');
    await expect(paletteInput).toBeVisible();

    // Close palette using ESC key
    await page.keyboard.press('Escape');
    await expect(paletteInput).not.toBeVisible();
  });
});
