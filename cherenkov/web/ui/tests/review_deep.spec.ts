import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoReview(page: any) {
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
  await page.click('#nav-item-review');
  await page.waitForSelector('#review-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Review Screen — Deep Flow Coverage', () => {

  // ── Queue renders with mocked items ──────────────────────────────
  test('review queue loads items from API with correct structure', async ({ page }) => {
    await gotoReview(page);

    // Two items from mock (test-3: PUT /pets, test-4: DELETE /store/order)
    const queueList = page.locator('[data-testid="review-queue-list"]');
    await expect(queueList).toBeVisible();

    // Both items have verdict badge
    await expect(page.getByText('PUT').first()).toBeVisible();
    await expect(page.getByText('DELETE').first()).toBeVisible();

    // Filter tab 'all' shows count badge matching item count
    const allTab = page.locator('#filter-tab-all');
    await expect(allTab).toContainText('(2)');

    // Both items are 'review' verdict — review tab shows count 2
    const reviewTab = page.locator('#filter-tab-review');
    await expect(reviewTab).toContainText('(2)');

    // Approved tab shows (0)
    const approvedTab = page.locator('#filter-tab-approved');
    await expect(approvedTab).toContainText('(0)');
  });

  // ── Item selection populates right-pane details ───────────────────
  test('selecting an item populates the code panel', async ({ page }) => {
    await gotoReview(page);

    // First item auto-selected; code panel shows the endpoint
    const rightPane = page.locator('.lg\\:col-span-3');
    await expect(rightPane).toBeVisible();

    // Confidence metric visible
    await expect(page.getByText('Confidence metrics')).toBeVisible();

    // Gate status panel visible
    await expect(page.getByText('Assertion Quality')).toBeVisible();
    await expect(page.getByText('AST validation')).toBeVisible();

    // Code block rendered
    await expect(page.locator('pre code').first()).toBeVisible();
  });

  // ── Approve flow: button click → API call → verdict changes ───────
  test('approve button calls API and moves item to approved filter', async ({ page }) => {
    let approveCallCount = 0;
    await setupApiMocks(page);
    await page.route('**/api/v1/review/approve', async (route: any) => {
      approveCallCount++;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    const approveBtn = page.locator('[data-testid="review-approve-btn"]');
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Wait for the 400ms animation delay + settlement
    await page.waitForTimeout(700);

    // API was called
    expect(approveCallCount).toBe(1);

    // Approved tab now shows count (1)
    await expect(page.locator('#filter-tab-approved')).toContainText('(1)');

    // Toast notification appeared
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Approved');
  });

  // ── Reject flow: modal, reason textarea, confirm ───────────────────
  test('reject flow: opens modal, fills reason, confirms rejection', async ({ page }) => {
    let rejectPayload: any = null;
    await setupApiMocks(page);
    await page.route('**/api/v1/review/reject', async (route: any) => {
      rejectPayload = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Click REJECT TEST button
    const rejectBtn = page.locator('[data-testid="review-reject-btn"]');
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();

    // Modal appears
    await expect(page.getByText('Rejection Reason')).toBeVisible();
    await expect(page.getByText('Describe what\'s wrong')).toBeVisible();

    // Fill reason textarea
    const reasonTA = page.locator('textarea').last();
    await reasonTA.fill('Hardcoded pet ID — must use dynamic fixture instead.');

    // Confirm
    await page.getByText('CONFIRM REJECT').click();
    await page.waitForTimeout(400);

    // API called with reason
    expect(rejectPayload).not.toBeNull();
    expect(rejectPayload.reason || rejectPayload).toBeTruthy();

    // Rejected tab count increments
    await expect(page.locator('#filter-tab-rejected')).toContainText('(1)');

    // Modal closed
    await expect(page.getByText('Rejection Reason')).not.toBeVisible();
  });

  // ── Reject modal cancel ────────────────────────────────────────────
  test('rejection modal cancel dismisses without state change', async ({ page }) => {
    await gotoReview(page);

    await page.locator('[data-testid="review-reject-btn"]').click();
    await expect(page.getByText('Rejection Reason')).toBeVisible();

    await page.getByText('CANCEL').last().click();
    await expect(page.getByText('Rejection Reason')).not.toBeVisible();

    // Rejected count still 0
    await expect(page.locator('#filter-tab-rejected')).toContainText('(0)');
  });

  // ── Edit inline: toggle editor, modify code, save ─────────────────
  test('edit inline: textarea appears, code editable, save calls API and auto-approves', async ({ page }) => {
    let editPayload: any = null;
    await setupApiMocks(page);
    await page.route('**/api/v1/review/edit', async (route: any) => {
      editPayload = JSON.parse(route.request().postData() || '{}');
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Click EDIT INLINE CODE
    await page.getByText('EDIT INLINE CODE').click();

    // "EDIT MODE ACTIVE" badge appears
    await expect(page.getByText('EDIT MODE ACTIVE')).toBeVisible();

    // Inline editor textarea visible
    const editor = page.locator('#review-inline-editor');
    await expect(editor).toBeVisible();

    // Modify the code
    await editor.fill('// Fixed test\nimport { test, expect } from "@playwright/test";\ntest("fixed", async () => { expect(true).toBe(true); });');

    // CANCEL EDIT button visible
    await expect(page.getByText('CANCEL EDIT')).toBeVisible();

    // Save
    await page.getByText('SAVE CHANGE & INGEST DIRECTORY').click();
    await page.waitForTimeout(400);

    // API called
    expect(editPayload).not.toBeNull();

    // Edit mode closed (no more "EDIT MODE ACTIVE")
    await expect(page.getByText('EDIT MODE ACTIVE')).not.toBeVisible();

    // Item auto-approved — approved count increments
    await expect(page.locator('#filter-tab-approved')).toContainText('(1)');
  });

  // ── Edit inline cancel ─────────────────────────────────────────────
  test('cancel edit returns to read-only code view', async ({ page }) => {
    await gotoReview(page);

    await page.getByText('EDIT INLINE CODE').click();
    await expect(page.locator('#review-inline-editor')).toBeVisible();

    await page.getByText('CANCEL EDIT').click();
    await expect(page.locator('#review-inline-editor')).not.toBeVisible();
    await expect(page.locator('pre code').first()).toBeVisible();
  });

  // ── AI Explain button (on 'review' items) ─────────────────────────
  test('AI explain button fetches and displays explanation text', async ({ page }) => {
    await gotoReview(page);

    // "Ask Copilot" section visible on review items
    await expect(page.getByText('Ask Copilot')).toBeVisible();

    // Click "EXPLAIN FLAGGED STATUS"
    await page.getByText('EXPLAIN FLAGGED STATUS').click();

    // Spinner appears briefly then explanation renders
    await page.waitForTimeout(600);
    await expect(page.getByText(/quality gate flagged/)).toBeVisible();
  });

  // ── Filter tabs: switching hides/shows items ───────────────────────
  test('filter tabs change visible item set', async ({ page }) => {
    await gotoReview(page);

    // All filter: 2 items visible
    const listItems = page.locator('[id^="test-row-"]');
    await expect(listItems).toHaveCount(2);

    // Approved filter: 0 items → empty state
    await page.locator('#filter-tab-approved').click();
    await page.waitForTimeout(200);
    await expect(page.getByText('No tests match this audit filter')).toBeVisible();

    // Review filter: 2 items
    await page.locator('#filter-tab-review').click();
    await page.waitForTimeout(200);
    await expect(listItems).toHaveCount(2);

    // Rejected filter: 0 items
    await page.locator('#filter-tab-rejected').click();
    await page.waitForTimeout(200);
    await expect(page.getByText('No tests match this audit filter')).toBeVisible();
  });

  // ── Keyboard navigation: J/K moves selection ──────────────────────
  test('keyboard J/K navigates between test items', async ({ page }) => {
    await gotoReview(page);

    // First item is selected (test-3: PUT /pets)
    await expect(page.locator('#test-row-test-3')).toHaveClass(/bg-white\/10/);

    // Press J to move to next
    await page.keyboard.press('j');
    await page.waitForTimeout(200);
    // Second item (test-4) now selected
    await expect(page.locator('#test-row-test-4')).toHaveClass(/bg-white\/10/);

    // Press K to go back
    await page.keyboard.press('k');
    await page.waitForTimeout(200);
    await expect(page.locator('#test-row-test-3')).toHaveClass(/bg-white\/10/);
  });

  // ── Keyboard shortcut: E toggles edit mode ────────────────────────
  test('keyboard E shortcut toggles edit mode', async ({ page }) => {
    await gotoReview(page);

    // Press E to enter edit
    await page.keyboard.press('e');
    await page.waitForTimeout(200);
    await expect(page.locator('#review-inline-editor')).toBeVisible();

    // Press E again to exit (cancel)
    await page.keyboard.press('e');
    await page.waitForTimeout(200);
    await expect(page.locator('#review-inline-editor')).not.toBeVisible();
  });

  // ── Keyboard shortcut: A approves active test ─────────────────────
  test('keyboard A shortcut approves the selected test', async ({ page }) => {
    let approveCount = 0;
    await setupApiMocks(page);
    await page.route('**/api/v1/review/approve', async (route: any) => {
      approveCount++;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.keyboard.press('a');
    await page.waitForTimeout(800);

    expect(approveCount).toBe(1);
    await expect(page.locator('#filter-tab-approved')).toContainText('(1)');
  });

  // ── Chat panel: toggle open, send message via Enter ───────────────
  test('chat panel opens, accepts input, and displays streamed response', async ({ page }) => {
    await gotoReview(page);

    // Click Chat button (scoped to review screen header to avoid nav "Chat" link)
    const chatBtn = page.locator('#review-screen button').filter({ hasText: 'Chat' }).first();
    await expect(chatBtn).toBeVisible();
    await chatBtn.click();
    await page.waitForTimeout(300);

    // Chat panel visible
    await expect(page.getByText(/Chat about:/)).toBeVisible();

    // Input field present
    const chatInput = page.locator('input[placeholder="Ask about this test..."]');
    await expect(chatInput).toBeVisible();
    await chatInput.fill('Why did the quality gate fail?');

    // Submit via Enter
    await chatInput.press('Enter');
    await page.waitForTimeout(800);

    // User message bubbles up
    await expect(page.getByText('Why did the quality gate fail?')).toBeVisible();

    // SSE streamed assistant response
    await expect(page.getByText(/Hello from CHERENKOV/)).toBeVisible();
  });

  // ── Chat panel: close button ───────────────────────────────────────
  test('chat panel close button dismisses the panel', async ({ page }) => {
    await gotoReview(page);

    const chatBtn = page.locator('#review-screen button').filter({ hasText: 'Chat' }).first();
    await chatBtn.click();
    await page.waitForTimeout(200);
    await expect(page.getByText(/Chat about:/)).toBeVisible();

    // Close via X button in the chat panel header — it's a sibling of the "Chat about:" span
    const closeBtn = page.getByText(/Chat about:/).locator('..').locator('button');
    await closeBtn.click();
    await page.waitForTimeout(200);
    await expect(page.getByText(/Chat about:/)).not.toBeVisible();
  });

  // ── Confidence bar renders correctly ──────────────────────────────
  test('confidence bar width reflects confidence percentage', async ({ page }) => {
    await gotoReview(page);

    // test-3 has confidence 0.81 → "81%"
    await expect(page.locator('#test-row-test-3').getByText('81%')).toBeVisible();

    // test-4 has confidence 0.45 → "45%"
    await expect(page.locator('#test-row-test-4').getByText('45%')).toBeVisible();
  });

  // ── Autonomy: Augmented mode auto-approves high-confidence tests ───
  test('Augmented autonomy auto-approves tests at ≥90% confidence', async ({ page }) => {
    // Wire a high-confidence item in the queue
    await setupApiMocks(page);
    await page.route('**/api/v1/review/queue*', async (route: any) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([
        { id: 'high-conf', method: 'GET', endpoint: '/pets', status: 'review', confidence: 0.95, review_gate_failed: null, confidence_reason: 'All gates pass' },
        { id: 'low-conf', method: 'POST', endpoint: '/pets', status: 'review', confidence: 0.55, review_gate_failed: 'quality', confidence_reason: 'Missing assertions' },
      ]) });
    });

    let autoApproveCount = 0;
    await page.route('**/api/v1/review/approve', async (route: any) => {
      autoApproveCount++;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);

    // Switch autonomy to Augmented (second radio button)
    const autonomyGroup = page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]');
    await autonomyGroup.locator('[role="radio"]').nth(1).click();
    await page.waitForTimeout(200);

    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(1000); // wait for auto-approve effect

    // High-confidence item got auto-approved
    expect(autoApproveCount).toBeGreaterThanOrEqual(1);

    // Auto-approve toast visible
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('auto-approved');
  });

  // ── Error path: queue API 500 shows error state ────────────────────
  test('review screen shows error state when queue API returns 500', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/review/queue*', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'DB error' }) })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForTimeout(600);

    // Error state shown — no crash
    await expect(page.locator('#review-screen')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
  });

  // ── Approve error: API 500 shows toast, verdict unchanged ─────────
  test('approve failure shows error toast and leaves verdict unchanged', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/review/approve', route =>
      route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'internal error' }) })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-review');
    await page.waitForSelector('#review-screen');
    await page.waitForTimeout(SETTLEMENT);

    await page.locator('[data-testid="review-approve-btn"]').click();
    await page.waitForTimeout(500);

    // Error toast
    const toast = page.locator('[role="status"]').first();
    await expect(toast).toBeVisible();
    await expect(toast).toContainText('Failed to approve');

    // Approved count unchanged
    await expect(page.locator('#filter-tab-approved')).toContainText('(0)');
  });

  // ── Keyboard shortcut legend rendered ─────────────────────────────
  test('shortcut legend visible in header on wide viewport', async ({ page }) => {
    await gotoReview(page);

    // The legend is hidden on <xl, shown on xl+. Default viewport is 1280px which is xl.
    await expect(page.getByText('Shortcuts:').first()).toBeVisible();
    await expect(page.getByText(/Navigate/).first()).toBeVisible();
    // "Approve" appears in the legend — scope to the shortcuts bar
    const shortcutsBar = page.locator('.hidden.xl\\:flex').first();
    await expect(shortcutsBar).toBeVisible();
    await expect(shortcutsBar.getByText(/Approve/)).toBeVisible();
  });

});
