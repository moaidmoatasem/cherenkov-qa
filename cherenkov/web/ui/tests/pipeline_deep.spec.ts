import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoPipeline(page: any) {
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
  await page.click('#nav-item-pipeline');
  await page.waitForSelector('#pipeline-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('AI Code Generation Pipeline Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('pipeline screen renders heading and description', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.locator('h1')).toContainText('AI Code Generation Pipeline');
    await expect(page.getByText('Observe the active state models synthesize API validation tests from OpenAPI paths.')).toBeVisible();
  });

  // ── Pipeline stage nodes render ───────────────────────────────────
  test('all six pipeline stage nodes render', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.locator('#pipeline-node-ingest')).toBeVisible();
    await expect(page.locator('#pipeline-node-plan')).toBeVisible();
    await expect(page.locator('#pipeline-node-generate')).toBeVisible();
    await expect(page.locator('#pipeline-node-review')).toBeVisible();
    await expect(page.locator('#pipeline-node-visual')).toBeVisible();
    await expect(page.locator('#pipeline-node-perf')).toBeVisible();
  });

  // ── Stage labels render ───────────────────────────────────────────
  test('pipeline stage labels INGEST, PLAN, GENERATE are visible', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('INGEST')).toBeVisible();
    await expect(page.getByText('PLAN')).toBeVisible();
    await expect(page.getByText('GENERATE')).toBeVisible();
  });

  // ── Initial stage statuses ────────────────────────────────────────
  test('ingest and plan stages show done status initially', async ({ page }) => {
    await gotoPipeline(page);

    const ingestStatus = page.locator('[data-testid="pipeline-status-ingest"]');
    const planStatus = page.locator('[data-testid="pipeline-status-plan"]');

    await expect(ingestStatus).toHaveAttribute('data-status', 'done');
    await expect(planStatus).toHaveAttribute('data-status', 'done');
  });

  // ── Generate stage is running ─────────────────────────────────────
  test('generate stage shows running status initially', async ({ page }) => {
    await gotoPipeline(page);

    const generateStatus = page.locator('[data-testid="pipeline-status-generate"]');
    await expect(generateStatus).toHaveAttribute('data-status', 'running');
  });

  // ── Downstream stages are queued ──────────────────────────────────
  test('review, visual, perf stages show queued status initially', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.locator('[data-testid="pipeline-status-review"]')).toHaveAttribute('data-status', 'queued');
    await expect(page.locator('[data-testid="pipeline-status-visual"]')).toHaveAttribute('data-status', 'queued');
    await expect(page.locator('[data-testid="pipeline-status-perf"]')).toHaveAttribute('data-status', 'queued');
  });

  // ── Pause button renders ──────────────────────────────────────────
  test('PAUSE PIPELINE button renders and is clickable', async ({ page }) => {
    await gotoPipeline(page);

    const pauseBtn = page.locator('#pipeline-pause-resume-btn');
    await expect(pauseBtn).toBeVisible();
    await expect(pauseBtn).toContainText('PAUSE PIPELINE');
  });

  // ── Pause/resume toggles ──────────────────────────────────────────
  test('clicking pause button toggles to RESUME PIPELINE', async ({ page }) => {
    await gotoPipeline(page);

    const pauseBtn = page.locator('#pipeline-pause-resume-btn');
    await pauseBtn.click();
    await page.waitForTimeout(200);

    await expect(pauseBtn).toContainText('RESUME PIPELINE');
  });

  // ── Elapsed timer renders ─────────────────────────────────────────
  test('ELAPSED timer renders with initial time', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('ELAPSED:')).toBeVisible();
    // Timer starts at 2:18 (138s) and increments
    await expect(page.locator('#pipeline-screen')).toContainText(/\d{1,2}:\d{2}/);
  });

  // ── Token budget section renders ──────────────────────────────────
  test('TOKEN BUDGET telemetry section renders with token count', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('TOKEN BUDGET')).toBeVisible();
    // Initial tokensSpent: 11243
    await expect(page.locator('#pipeline-screen')).toContainText('11,243');
  });

  // ── Token progress bar renders ────────────────────────────────────
  test('token budget progress bar renders', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.locator('[data-testid="pipeline-progress"]')).toBeVisible();
  });

  // ── Prompt attention space renders ────────────────────────────────
  test('PROMPT ATTENTION SPACE section renders', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('PROMPT ATTENTION SPACE')).toBeVisible();
  });

  // ── Context token count renders ───────────────────────────────────
  test('context vector space usage renders with token count', async ({ page }) => {
    await gotoPipeline(page);

    // Initial contextTokens: 14200 / 32,768
    await expect(page.locator('#pipeline-screen')).toContainText('14,200');
    await expect(page.locator('#pipeline-screen')).toContainText('32,768');
  });

  // ── Active telemetry header ───────────────────────────────────────
  test('Active Telemetry panel heading renders', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('Active Telemetry')).toBeVisible();
  });

  // ── Current expenditure section ───────────────────────────────────
  test('CURRENT EXPENDITURE section renders with local cost', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('CURRENT EXPENDITURE')).toBeVisible();
    await expect(page.getByText('$0.00 local')).toBeVisible();
  });

  // ── AST pipeline structure heading ───────────────────────────────
  test('AST TRANSLATION pipeline structure heading renders', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('AST TRANSLATION pipeline structure')).toBeVisible();
  });

  // ── STREAMING ACTIVE indicator ────────────────────────────────────
  test('STREAMING ACTIVE indicator is visible in code panel', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('STREAMING ACTIVE')).toBeVisible();
  });

  // ── Completed tests render ────────────────────────────────────────
  test('initially completed tests are shown in the code panel', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('GET /user/login · checks auth cookie parameter values')).toBeVisible();
    await expect(page.getByText('POST /user · creates standard user entity')).toBeVisible();
  });

  // ── Stage drawer opens on click ───────────────────────────────────
  test('clicking a pipeline stage node opens the stage diagnostics drawer', async ({ page }) => {
    await gotoPipeline(page);

    await page.locator('#pipeline-node-ingest').click();
    await page.waitForTimeout(300);

    await expect(page.getByText(/Stage Diagnostics: ingest/i)).toBeVisible();
    await expect(page.getByText('SECURED_200')).toBeVisible();
  });

  // ── Stage drawer dismiss ──────────────────────────────────────────
  test('DISMISS DIAGNOSTIC button closes the stage drawer', async ({ page }) => {
    await gotoPipeline(page);

    await page.locator('#pipeline-node-ingest').click();
    await page.waitForTimeout(300);

    await page.getByRole('button', { name: 'DISMISS DIAGNOSTIC' }).click();
    await page.waitForTimeout(200);

    await expect(page.getByText(/Stage Diagnostics:/)).not.toBeVisible();
  });

  // ── Stage drawer for generate stage ──────────────────────────────
  test('clicking GENERATE stage node shows generate diagnostics', async ({ page }) => {
    await gotoPipeline(page);

    await page.locator('#pipeline-node-generate').click();
    await page.waitForTimeout(300);

    await expect(page.getByText(/Stage Diagnostics: generate/i)).toBeVisible();
  });

  // ── Current scenario footer ───────────────────────────────────────
  test('CURRENT SCENARIO section shows scenario tags', async ({ page }) => {
    await gotoPipeline(page);

    await expect(page.getByText('CURRENT SCENARIO:')).toBeVisible();
    await expect(page.getByText('authorization_expiry_check, json_syntax_validation')).toBeVisible();
  });

});
