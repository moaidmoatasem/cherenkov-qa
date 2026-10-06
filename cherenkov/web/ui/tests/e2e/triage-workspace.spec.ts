import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

// The HITL review queue is populated only when a generated test lands in the
// mid-confidence band (ReviewStage._bridge_hitl, quality 0.7-0.9) — most
// generated tests are auto-approved or regenerated without ever reaching a
// human, by design. A fresh real backend therefore has a genuinely empty
// queue, so asserting the approve/reject controls without first putting a
// pending item in the same SQLite store the backend reads from cannot pass
// against real data — it only ever worked here by coincidence of leftover
// state. Seed and clean up through the actual HitlQueue class rather than a
// test-only REST endpoint, so this exercises the real approve/reject path.
const SEED_ID = 'e2e_triage_seed_item';

function seedHitlItem() {
  execFileSync('python3', [
    '-c',
    `
from cherenkov.hitl import HitlItem, HitlQueue
HitlQueue().enqueue(HitlItem(
    id="${SEED_ID}", endpoint="/pet/{petId}", method="GET",
    confidence=0.75, confidence_reason="e2e seed", review_gate_failed="tsc",
    run_id="e2e-triage-spec",
))
`,
  ]);
}

function deleteHitlItem() {
  execFileSync('python3', [
    '-c',
    `
import os, sqlite3
data_dir = os.environ.get("CHERENKOV_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cherenkov"))
con = sqlite3.connect(os.path.join(data_dir, "hitl.db"))
con.execute("DELETE FROM hitl_queue WHERE id = ?", ("${SEED_ID}",))
con.execute("DELETE FROM audit_log WHERE item_id = ?", ("${SEED_ID}",))
con.commit()
`,
  ]);
}

test.describe('Triage Workspace E2E Suite', () => {
  test.beforeAll(() => {
    seedHitlItem();
  });

  test.afterAll(() => {
    deleteHitlItem();
  });

  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-triage').click();
    await page.waitForTimeout(SETTLE);
  });

  test('Triage workspace container renders heading and subcomponents', async ({ page }) => {
    await expect(page.locator('#triage-workspace')).toBeVisible();
    await expect(page.locator('#triage-workspace').getByRole('heading', { name: 'Triage', level: 1 })).toBeVisible();
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
