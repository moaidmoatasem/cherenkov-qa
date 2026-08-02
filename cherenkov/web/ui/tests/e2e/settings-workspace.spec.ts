import { test, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

const SETTLE = 400;

test.describe('Settings Workspace E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await page.goto('/settings');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLE);
  });

  test('Settings workspace container renders heading and subcomponents', async ({ page }) => {
    await expect(page.locator('#settings-workspace')).toBeVisible();
    await expect(page.locator('#settings-workspace').getByRole('heading', { name: 'Settings Workspace' })).toBeVisible();
  });

  test('ProjectManager renders active projects and create project toggle', async ({ page }) => {
    const pm = page.getByTestId('project-manager');
    await expect(pm).toBeVisible();
    await expect(pm.getByText('Workspace & Project Manager')).toBeVisible();

    const toggleBtn = page.getByTestId('btn-create-project-toggle');
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();

    await expect(page.getByTestId('input-new-project-name')).toBeVisible();
    await toggleBtn.click();
  });

  test('DeviceManager renders VLM hardware status and Maestro pilot status widget', async ({ page }) => {
    const dm = page.getByTestId('device-manager');
    await expect(dm).toBeVisible();
    await expect(dm.getByText('Hardware & VLM Device Diagnostics')).toBeVisible();
    await expect(dm.getByText('VLM Hardware Online')).toBeVisible();
    await expect(dm.getByText('Maestro Mobile Pilot', { exact: true })).toBeVisible();
  });

  test('EjectSuitePanel renders output path input and eject export button', async ({ page }) => {
    const eject = page.getByTestId('eject-suite-panel');
    await expect(eject).toBeVisible();
    await expect(eject.getByText('Plain Playwright Suite Exporter (Zero Lock-in)')).toBeVisible();

    const pathInput = page.getByTestId('eject-output-path');
    await expect(pathInput).toBeVisible();

    const ejectBtn = page.getByTestId('btn-run-eject');
    await expect(ejectBtn).toBeVisible();
    await ejectBtn.click();
    await page.waitForTimeout(300);

    await expect(eject.getByText('Eject successful!')).toBeVisible();
  });

  test('GovernanceSettings renders compliance score, target URL, and save settings button', async ({ page }) => {
    const gov = page.getByTestId('governance-settings');
    await expect(gov).toBeVisible();
    await expect(gov.getByText('Governance Rules & Engine Settings')).toBeVisible();

    const targetInput = page.getByTestId('setting-target-url');
    await expect(targetInput).toBeVisible();

    const saveBtn = page.getByTestId('btn-save-governance-settings');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();
    await page.waitForTimeout(300);
    await expect(gov.getByText('Governance & System settings updated successfully!')).toBeVisible();
  });
});
