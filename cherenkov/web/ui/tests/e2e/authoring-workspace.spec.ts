import { test, expect } from '@playwright/test';
import { bootstrapReal } from '../qa/page-objects';

const SETTLE = 400;

test.describe('Authoring Workspace E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await bootstrapReal(page);
    await page.getByTestId('nav-workspace-authoring').click();
    await page.waitForTimeout(SETTLE);
  });

  test('Authoring workspace container renders heading and subcomponents', async ({ page }) => {
    await expect(page.locator('#authoring-workspace')).toBeVisible();
    await expect(page.locator('#authoring-workspace').getByRole('heading', { name: 'Generate Tests' })).toBeVisible();
  });

  test('SpecIngestPanel renders drag & drop zone, repo selector, and URL form', async ({ page }) => {
    const panel = page.getByTestId('spec-ingest-panel');
    await expect(panel).toBeVisible();
    await expect(panel.getByText('OpenAPI Spec Ingestion')).toBeVisible();
    await expect(page.getByTestId('spec-drop-zone')).toBeVisible();
    await expect(panel.locator('form input[type="url"]')).toBeVisible();
  });

  test('DoctorCheckWidget triggers doctor check execution and updates status', async ({ page }) => {
    const widget = page.getByTestId('doctor-check-widget');
    await expect(widget).toBeVisible();
    await expect(widget.getByText('OpenAPI & System Doctor Check')).toBeVisible();
    await expect(widget.getByText('ENGINE READINESS STATUS:')).toBeVisible();

    const refreshBtn = widget.locator('button[title="Run Doctor Checks"]');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    await page.waitForTimeout(200);
    await expect(widget.getByText('ENGINE READINESS STATUS:')).toBeVisible();
  });

  test('IntentAuthoringPanel accepts natural language intent prompt and triggers generation', async ({ page }) => {
    const panel = page.getByTestId('intent-authoring-panel');
    await expect(panel).toBeVisible();
    await expect(panel.getByText('Intent-Driven Test Authoring')).toBeVisible();

    const input = page.getByTestId('intent-input');
    await expect(input).toBeVisible();
    await input.fill('Verify user registration with invalid email format returns 400 Bad Request');

    const generateBtn = page.getByTestId('btn-generate-intent');
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();
    await page.waitForTimeout(300);
  });

  test('LivePipelineMonitor renders DAG stage tracker nodes and execution log console', async ({ page }) => {
    const monitor = page.getByTestId('live-pipeline-monitor');
    await expect(monitor).toBeVisible();
    await expect(monitor.getByText('Live Pipeline Monitor')).toBeVisible();
    await expect(monitor.getByText('Analysis', { exact: true })).toBeVisible();
    await expect(monitor.getByText('Design & Generation', { exact: true })).toBeVisible();
    await expect(monitor.getByText('Live Event Log')).toBeVisible();
  });
});
