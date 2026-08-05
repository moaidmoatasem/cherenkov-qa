import { test, expect } from '@playwright/test';
import { bootstrapReal, mockChatStream } from '../qa/page-objects';

const SETTLE = 400;

test.describe('Intelligence Workspace E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await mockChatStream(page);
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForTimeout(SETTLE);
  });

  test('Intelligence workspace container renders heading and subcomponents', async ({ page }) => {
    await expect(page.locator('#intelligence-workspace')).toBeVisible();
    await expect(page.locator('#intelligence-workspace').getByRole('heading', { name: 'Knowledge', level: 1 })).toBeVisible();
  });

  test('SseChatAssistant creates chat session and sends user message', async ({ page }) => {
    const chat = page.getByTestId('sse-chat-assistant');
    await expect(chat).toBeVisible();
    await expect(chat.getByText('AI Copilot (SSE Streamed Chat)')).toBeVisible();

    const input = page.getByTestId('chat-input');
    await expect(input).toBeVisible();
    await input.fill('What API endpoints are currently unverified?');

    const sendBtn = page.getByTestId('chat-send-btn');
    await expect(sendBtn).toBeVisible();
    await sendBtn.click();

    await page.waitForTimeout(500);
    await expect(chat.getByText('What API endpoints are currently unverified?')).toBeVisible();
  });

  test('KnowledgeGraphExplorer accepts query input and renders results grid', async ({ page }) => {
    const explorer = page.getByTestId('knowledge-graph-explorer');
    await expect(explorer).toBeVisible();
    await expect(explorer.getByText('GraphRAG Second Brain Knowledge Explorer')).toBeVisible();

    const input = page.getByTestId('knowledge-search-input');
    await expect(input).toBeVisible();
    await input.fill('authentication token schema');
    await input.press('Enter');

    await page.waitForTimeout(500);
  });

  test('SddMemoryCockpit renders token budget KPI ring and compaction button', async ({ page }) => {
    const cockpit = page.getByTestId('sdd-memory-cockpit');
    await expect(cockpit).toBeVisible();
    await expect(cockpit.getByText('SDD Agent Cockpit & Memory Budget')).toBeVisible();
    await expect(cockpit.getByText('Token Budget')).toBeVisible();
    await expect(cockpit.getByText('Compact Memory')).toBeVisible();
  });
});
