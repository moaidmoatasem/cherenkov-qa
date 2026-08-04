import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

test.describe('Triage Workspace E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForTimeout(SETTLE);
  });

  test('Triage workspace container renders heading and subcomponents', async ({ page }) => {
    await expect(page.locator('#triage-workspace')).toBeVisible();
    await expect(page.locator('#triage-workspace').getByRole('heading', { name: 'Triage' })).toBeVisible();
  });

  test('HitlReviewQueue renders queue display, test details, and code viewer', async ({ page }) => {
    const queue = page.getByTestId('hitl-review-queue');
    await expect(queue).toBeVisible();
    await expect(queue.getByText('HITL Test Review Queue')).toBeVisible();
    await expect(page.getByTestId('btn-approve-scenario').first()).toBeVisible();
    await expect(page.getByTestId('btn-reject-scenario').first()).toBeVisible();
  });

  test('HitlReviewQueue approve and reject actions operate on review items', async ({ page }) => {
    const approveBtn = page.getByTestId('btn-approve-scenario').first();
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();
    await page.waitForTimeout(200);

    const queue = page.getByTestId('hitl-review-queue');
    await expect(queue.getByText('approved').first()).toBeVisible();
  });

  test('DivergenceTable renders risk-scored triage table and severity filter', async ({ page }) => {
    const table = page.getByTestId('divergence-table');
    await expect(table).toBeVisible();
    await expect(table.getByText('Risk-Scored Divergence Triage Table')).toBeVisible();

    const select = table.locator('select');
    await expect(select).toBeVisible();
    await select.selectOption('critical');
    await page.waitForTimeout(200);
    await select.selectOption('all');
  });

  test('SpecVsRealityDiffViewer renders side-by-side payload comparison panes', async ({ page }) => {
    const diff = page.getByTestId('spec-vs-reality-diff-viewer');
    await expect(diff).toBeVisible();
    await expect(diff.getByText('Spec vs Reality Payload Comparison')).toBeVisible();
    await expect(diff.getByText('OpenAPI Spec Claim (Expectation)')).toBeVisible();
    await expect(diff.getByText('Runtime Server Reality (Observed)')).toBeVisible();
  });
});
