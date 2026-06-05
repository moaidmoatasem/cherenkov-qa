# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard_e2e.spec.ts >> CHERENKOV QA Observability Dashboard E2E Tests >> Navigate to Divergences Screen, filter anomalies, and use detail drawer
- Location: tests/dashboard_e2e.spec.ts:66:3

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('text=D-').first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('text=D-').first()

```

```yaml
- complementary:
  - img
  - text: CHERENKOV THE FORENSIC QA PROTOCOL
  - button "New Spec Run"
  - navigation:
    - text: OVERVIEW
    - button "Overview Release readiness & recent learning"
    - text: ENGINE
    - button "Truth Map The endpoint claim graph"
    - button "Divergences Confirmed API inconsistencies"
    - button "Explore Autonomous explorer digests"
    - text: AUTHOR
    - button "Author by Intent NL-intent interactive Copilot"
    - button "Review Queue HITL verdict memory gates"
    - text: SIGNALS
    - button "Signals Visual, Perf & Coverage details"
    - text: OPERATE
    - button "Healing Options API Drift & Self-Repair"
    - button "Eject Suite Export plain Playwright"
    - button "Governance KPI cert & model compliance"
    - text: LEARN
    - button "Memory & Pairing Reflector senior idioms"
  - text: Active Workspace
  - combobox:
    - option "Swagger Petstore v2" [selected]
    - option "Checkout Gateway API"
    - option "Identity Provider OAuth"
  - button "Settings"
  - button "UI Kit Gallery"
  - text: LLM Token Pool 43% Used IDLE PORT 3000
- banner:
  - text: "Swagger Petstore v2 / Divergence Engine Star AUTONOMY:"
  - button "Assisted"
  - button "Augmented"
  - button "Agentic"
  - text: "SESSION COST: $0.14 | Cloud equivalent: $0.476 NODE STATE: Idle"
- main:
  - heading "Divergence Triage Hub" [level=1]
  - paragraph: Review and resolve inconsistencies between system components, specifications, and databases.
  - textbox "Search endpoints or details..."
  - combobox:
    - option "ALL CLASSES" [selected]
    - 'option "D1: SPEC ↔ CODE"'
    - 'option "D2: CODE ↔ PROD"'
    - 'option "D3: UI ↔ SPEC"'
    - 'option "D4: DB ↔ CODE"'
    - 'option "D5: SPEC ↔ PROD"'
  - combobox:
    - option "ALL SEVERITIES"
    - option "CRITICAL" [selected]
    - option "HIGH"
    - option "MEDIUM"
    - option "LOW"
  - combobox:
    - option "ALL STATUSES" [selected]
    - option "REPRODUCED"
    - option "PENDING"
    - option "REJECTED"
  - text: "Keyboard: Navigate list with j/k, open with Enter Showing 0 of 0 active findings"
  - heading "No Divergences Match Filters" [level=3]
  - paragraph: Adjust your search query or dropdown filter selections to find other items.
  - button "Reset Filters"
  - button "Try the Petstore demo"
```

# Test source

```ts
  1   | import { test, expect } from '@playwright/test';
  2   | 
  3   | test.describe('CHERENKOV QA Observability Dashboard E2E Tests', () => {
  4   | 
  5   |   test.beforeEach(async ({ page }) => {
  6   |     // Capture browser console logs
  7   |     page.on('console', msg => {
  8   |       console.log(`[BROWSER CONSOLE] ${msg.type()}: ${msg.text()}`);
  9   |     });
  10  | 
  11  |     // Capture uncaught exceptions in page
  12  |     page.on('pageerror', err => {
  13  |       console.error(`[BROWSER UNCAUGHT ERROR] ${err.message}\nStack: ${err.stack}`);
  14  |     });
  15  | 
  16  |     // Navigate to the local dashboard Vite dev server port 3000
  17  |     await page.goto('/');
  18  |     await page.waitForSelector('#cherenkov-app-core');
  19  |     
  20  |     // Wait for React hydration to fully attach event handlers to buttons
  21  |     await page.waitForTimeout(1000);
  22  |   });
  23  | 
  24  |   test('Page shell and Sidebar controls function properly', async ({ page }) => {
  25  |     const sidebar = page.locator('#cherenkov-sidebar');
  26  |     await expect(sidebar).toBeVisible();
  27  | 
  28  |     await expect(page.locator('text=LLM Token Pool')).toBeVisible();
  29  |     await expect(page.locator('text=Active Workspace')).toBeVisible();
  30  | 
  31  |     // Verify status indicator is present and idle initially
  32  |     await expect(page.locator('text=IDLE').first()).toBeVisible();
  33  |   });
  34  | 
  35  |   test('Navigate to Overview Screen and verify release metrics', async ({ page }) => {
  36  |     await page.click('#nav-item-overview');
  37  |     
  38  |     // Check main title is correct
  39  |     const header = page.locator('h1');
  40  |     await expect(header).toContainText('Release Readiness & Learning');
  41  |     
  42  |     // Verify key metrics KPI components
  43  |     await expect(page.locator('text=Release Readiness Score')).toBeVisible();
  44  |     await expect(page.locator('text=Reflector Verdict Memory')).toBeVisible();
  45  |     
  46  |     // Use exact match to avoid strict mode violation on "Readiness" substring
  47  |     await expect(page.getByText('Readiness', { exact: true })).toBeVisible();
  48  |   });
  49  | 
  50  |   test('Navigate to Truth Map Screen and inspect endpoint claims', async ({ page }) => {
  51  |     await page.click('#nav-item-truth-map');
  52  | 
  53  |     // Check header
  54  |     await expect(page.locator('h1')).toContainText('Endpoint Truth Graph');
  55  | 
  56  |     // Click on /user/login endpoint to view its claims list (present in mockData.ts)
  57  |     const endpointRow = page.getByText('/user/login').first();
  58  |     await expect(endpointRow).toBeVisible();
  59  |     await endpointRow.click();
  60  | 
  61  |     // Ensure claims matching the selected endpoint render
  62  |     await expect(page.locator('h3').first()).toContainText('/user/login');
  63  |     await expect(page.locator('text=VERIFIED').first()).toBeVisible();
  64  |   });
  65  | 
  66  |   test('Navigate to Divergences Screen, filter anomalies, and use detail drawer', async ({ page }) => {
  67  |     await page.click('#nav-item-divergences');
  68  | 
  69  |     // Check header
  70  |     await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
  71  | 
  72  |     // Filter by severity critical (specifically targeting the select elements containing critical option)
  73  |     const severitySelect = page.locator('select:has(option[value="critical"])');
  74  |     await expect(severitySelect).toBeVisible();
  75  |     await severitySelect.selectOption('critical');
  76  | 
  77  |     // Click a divergence row to open the detail drawer
  78  |     const row = page.locator('text=D-').first();
> 79  |     await expect(row).toBeVisible();
      |                       ^ Error: expect(locator).toBeVisible() failed
  80  |     await row.click();
  81  | 
  82  |     // Verify detail drawer elements are shown
  83  |     await expect(page.locator('text=Divergence Detail').first()).toBeVisible();
  84  |     await expect(page.locator('text=Evidence payload')).toBeVisible();
  85  |     await expect(page.locator('text=Independent Repro Steps')).toBeVisible();
  86  | 
  87  |     // Close the drawer (using correct close button aria-label)
  88  |     await page.click('button[aria-label="Close details"]');
  89  |     await expect(page.locator('text=Divergence Detail')).not.toBeVisible();
  90  |   });
  91  | 
  92  |   test('Navigate to Author by Intent Screen and check manual NL-QA flow', async ({ page }) => {
  93  |     await page.click('#nav-item-author');
  94  | 
  95  |     // Verify UI components
  96  |     await expect(page.locator('h1')).toContainText('Author by Intent');
  97  |     await expect(page.locator('[placeholder="e.g. Verify that guest checkouts apply 15% discount code and succeed with 200 OK..."]')).toBeVisible();
  98  | 
  99  |     // Click an example intent chip to populate input
  100 |     const chip = page.locator('text="Verify that guests can checkout with valid cart items and coupons."').first();
  101 |     await expect(chip).toBeVisible();
  102 |     await chip.click();
  103 | 
  104 |     // Verify prompt value got updated
  105 |     const inputVal = await page.inputValue('textarea');
  106 |     expect(inputVal).toContain('Verify that guests can checkout');
  107 | 
  108 |     // Verify Mentor Idioms advice displays contextually
  109 |     await expect(page.locator('text=Mentor Context Idioms')).toBeVisible();
  110 |   });
  111 | 
  112 |   test('Navigate to Signals Screen and review latency and visual regression baseline tabs', async ({ page }) => {
  113 |     await page.click('#nav-item-signals');
  114 | 
  115 |     await expect(page.locator('h1')).toContainText('Telemetry Signals');
  116 | 
  117 |     // Performance tab is active by default
  118 |     await expect(page.locator('text=API Latency & Anomaly Baselines')).toBeVisible();
  119 | 
  120 |     // Switch to Visual tab
  121 |     await page.click('button:has-text("Visual Regression")');
  122 |     await expect(page.locator('text=UI Snapshot Comparisons')).toBeVisible();
  123 | 
  124 |     // Switch to Coverage tab
  125 |     await page.click('button:has-text("SDET Coverage")');
  126 |     await expect(page.locator('text=Code Path Verification Coverage')).toBeVisible();
  127 |   });
  128 | 
  129 |   test('Navigate to Memory & Pairing Screen and inspect senior idioms', async ({ page }) => {
  130 |     await page.click('#nav-item-memory');
  131 | 
  132 |     await expect(page.locator('h1')).toContainText('Reflector Memory & Pairing');
  133 |     await expect(page.locator('text=Accumulated Senior Testing Idioms')).toBeVisible();
  134 |     await expect(page.locator('text=Mentor Junior-Senior Pairing')).toBeVisible();
  135 |   });
  136 | 
  137 |   test('Navigate to Governance Screen and verify model compliance', async ({ page }) => {
  138 |     await page.click('#nav-item-governance');
  139 | 
  140 |     await expect(page.locator('h1')).toContainText('Governance & Model Certification');
  141 |     await expect(page.locator('text=Defect Escape Rate')).toBeVisible();
  142 |     await expect(page.locator('text=Model Capabilities Certification')).toBeVisible();
  143 |   });
  144 | 
  145 |   test('Navigate to Settings, modify configuration, and verify persistence', async ({ page }) => {
  146 |     await page.click('button:has-text("Settings")');
  147 | 
  148 |     await expect(page.locator('h1')).toContainText('System Settings & Credentials');
  149 | 
  150 |     // Toggle density (using checkbox element instead of nonexistent button)
  151 |     const compactCheckbox = page.locator('input[type="checkbox"]').first();
  152 |     await expect(compactCheckbox).toBeVisible();
  153 |     await compactCheckbox.click();
  154 | 
  155 |     // Verify LocalStorage updates or stays custom
  156 |     const storedAutonomy = await page.evaluate(() => localStorage.getItem('[copilot] autonomy'));
  157 |     expect(storedAutonomy).toBeDefined();
  158 |   });
  159 | 
  160 |   test('Trigger global Command Palette (Ctrl+K / Cmd+K)', async ({ page }) => {
  161 |     // Dispatch keyboard shortcut
  162 |     await page.keyboard.press('Control+KeyK');
  163 | 
  164 |     // Palette input field should display
  165 |     const paletteInput = page.locator('[placeholder="Type page name or action command (e.g. \'author\', \'setup\', \'divergences\')..."]');
  166 |     await expect(paletteInput).toBeVisible();
  167 | 
  168 |     // Close palette using ESC key
  169 |     await page.keyboard.press('Escape');
  170 |     await expect(paletteInput).not.toBeVisible();
  171 |   });
  172 | });
  173 | 
```