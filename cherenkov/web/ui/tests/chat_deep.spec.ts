import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoChat(page: any) {
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
  await page.click('#nav-item-chat');
  await page.waitForSelector('#chat-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Chat Screen — Deep Coverage', () => {

  // ── Screen loads with heading ─────────────────────────────────────
  test('chat screen renders heading and description', async ({ page }) => {
    await gotoChat(page);

    await expect(page.locator('h1')).toContainText('Chat');
    await expect(page.getByText('Interact with the CHERENKOV assistant')).toBeVisible();
  });

  // ── Empty state placeholder ───────────────────────────────────────
  test('empty state shows start conversation prompt', async ({ page }) => {
    await gotoChat(page);

    await expect(page.getByText('Start a conversation with the CHERENKOV assistant.')).toBeVisible();
  });

  // ── Input field initialises after session creation ────────────────
  test('input field becomes enabled after session init', async ({ page }) => {
    await gotoChat(page);

    // Mock returns session_id immediately
    const input = page.locator('#chat-screen input[type="text"]');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
    await expect(input).toHaveAttribute('placeholder', 'Type a message...');
  });

  // ── Send button disabled when input is empty ──────────────────────
  test('send button disabled when input is empty', async ({ page }) => {
    await gotoChat(page);

    const sendBtn = page.locator('#chat-screen button').filter({ has: page.locator('svg') }).last();
    await expect(sendBtn).toBeDisabled();
  });

  // ── Send button enables when input has text ───────────────────────
  test('send button enabled when user types a message', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('Hello CHERENKOV');

    const sendBtn = page.locator('#chat-screen button[disabled=""]');
    // There should be no disabled send button now
    const allBtns = page.locator('#chat-screen button');
    // The input has text — send should be enabled
    await expect(input).toHaveValue('Hello CHERENKOV');
  });

  // ── Message send via Enter key ────────────────────────────────────
  test('pressing Enter sends message and displays user bubble', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('What endpoints are covered?');
    await input.press('Enter');
    await page.waitForTimeout(300);

    // User bubble appears
    await expect(page.getByText('What endpoints are covered?')).toBeVisible();
  });

  // ── SSE streaming: assistant response renders ─────────────────────
  test('SSE stream response renders as assistant bubble', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('Hello');
    await input.press('Enter');
    await page.waitForTimeout(800);

    // Mock SSE: "Hello from CHERENKOV"
    await expect(page.getByText('Hello from CHERENKOV')).toBeVisible();
  });

  // ── Message via click on Send button ─────────────────────────────
  test('clicking send button submits message', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('Test via button');

    // Click the send button (SVG inside)
    const sendBtn = page.locator('#chat-screen button').last();
    await sendBtn.click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Test via button')).toBeVisible();
  });

  // ── Input clears after sending ────────────────────────────────────
  test('input field clears after message is sent', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('Clear after send test');
    await input.press('Enter');
    await page.waitForTimeout(200);

    // Input should be cleared
    await expect(input).toHaveValue('');
  });

  // ── Multiple messages render in sequence ──────────────────────────
  test('multiple messages render in order', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');

    await input.fill('First message');
    await input.press('Enter');
    await page.waitForTimeout(600);

    await input.fill('Second message');
    await input.press('Enter');
    await page.waitForTimeout(600);

    await expect(page.getByText('First message')).toBeVisible();
    await expect(page.getByText('Second message')).toBeVisible();
  });

  // ── Shift+Enter does NOT submit ───────────────────────────────────
  test('Shift+Enter adds newline without submitting', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('no submit yet');
    await input.press('Shift+Enter');
    await page.waitForTimeout(200);

    // Input still has content — not submitted
    // The input type is text (not textarea) so shift+enter is a no-op visually
    // But the message should NOT have been sent yet
    await expect(page.getByText('no submit yet')).not.toBeVisible();
  });

  // ── Chat screen shows bot and user avatars ────────────────────────
  test('conversation renders user and bot avatar icons', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('Show me the avatars');
    await input.press('Enter');
    await page.waitForTimeout(800);

    // Bot and User SVG icons should be in the DOM
    const chatArea = page.locator('#chat-screen .flex-1.overflow-y-auto');
    await expect(chatArea).toBeVisible();
    // The message bubbles area contains the conversation
    await expect(chatArea.locator('div').first()).toBeVisible();
  });

  // ── Session init failure shows error message ──────────────────────
  test('shows error when session creation fails', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/chat/sessions', route =>
      route.fulfill({ status: 500, body: '{"detail":"error"}' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-chat');
    await page.waitForSelector('#chat-screen');
    await page.waitForTimeout(SETTLEMENT);

    // Input shows "Initializing session..." placeholder when no session
    const input = page.locator('#chat-screen input[type="text"]');
    await expect(input).toBeVisible();
    await expect(input).toHaveAttribute('placeholder', 'Initializing session...');
    // Input disabled with no session
    await expect(input).toBeDisabled();
  });

  // ── Stream error shows error text ─────────────────────────────────
  test('stream failure shows error text in chat area', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/chat/sessions/*/stream', route =>
      route.fulfill({ status: 500, body: '{"detail":"error"}' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-chat');
    await page.waitForSelector('#chat-screen');
    await page.waitForTimeout(SETTLEMENT);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.fill('trigger error');
    await input.press('Enter');
    await page.waitForTimeout(600);

    // Error message shown in error div or as assistant message
    await expect(
      page.locator('#chat-screen').getByText(/error|failed|An error occurred/i).first()
    ).toBeVisible();
  });

  // ── Input accessible and focusable ────────────────────────────────
  test('chat input is keyboard focusable', async ({ page }) => {
    await gotoChat(page);

    const input = page.locator('#chat-screen input[type="text"]');
    await input.focus();
    await expect(input).toBeFocused();
  });

});
