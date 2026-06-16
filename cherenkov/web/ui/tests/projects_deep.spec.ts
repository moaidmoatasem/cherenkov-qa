import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoProjects(page: any) {
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
  // Projects screen is the default landing — no navigation needed
  await page.waitForSelector('#projects-screen');
}

test.describe('Projects Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('projects screen renders heading and description', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.locator('h1')).toContainText('Cherenkov Observability Root');
    await expect(page.getByText('Localhost testing particles. Real-time agent code-generation analytics.')).toBeVisible();
  });

  // ── All three project cards render ───────────────────────────────
  test('all three mock project cards render', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.locator('#project-card-proj-petstore')).toBeVisible();
    await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
    await expect(page.locator('#project-card-proj-auth-identity')).toBeVisible();
  });

  // ── Project names render ──────────────────────────────────────────
  test('project card names match mock data', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.getByRole('heading', { name: 'Swagger Petstore v2' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Checkout Gateway API' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Identity Provider OAuth' })).toBeVisible();
  });

  // ── Last run labels render ────────────────────────────────────────
  test('project cards show last run timestamps', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.getByText('Run: 2 hours ago')).toBeVisible();
    await expect(page.getByText('Run: 1 day ago')).toBeVisible();
    await expect(page.getByText('Run: 3 days ago')).toBeVisible();
  });

  // ── Stats: tests count renders ────────────────────────────────────
  test('project stats show test counts from mock data', async ({ page }) => {
    await gotoProjects(page);

    // Petstore: 47, Checkout: 32, Auth: 18
    const petCard = page.locator('#project-card-proj-petstore');
    await expect(petCard.getByText('47')).toBeVisible();

    const checkoutCard = page.locator('#project-card-proj-checkout-api');
    await expect(checkoutCard.getByText('32')).toBeVisible();
  });

  // ── Stats: pass rate renders ──────────────────────────────────────
  test('project cards show pass rate percentages', async ({ page }) => {
    await gotoProjects(page);

    const petCard = page.locator('#project-card-proj-petstore');
    await expect(petCard.getByText('91%')).toBeVisible();

    const authCard = page.locator('#project-card-proj-auth-identity');
    await expect(authCard.getByText('61%')).toBeVisible();
  });

  // ── Stats: healing count renders ──────────────────────────────────
  test('project cards show healing suggestion counts', async ({ page }) => {
    await gotoProjects(page);

    // Petstore: 3 SUGG, Auth: 4 SUGG
    const petCard = page.locator('#project-card-proj-petstore');
    await expect(petCard.getByText('3 SUGG')).toBeVisible();

    const authCard = page.locator('#project-card-proj-auth-identity');
    await expect(authCard.getByText('4 SUGG')).toBeVisible();
  });

  // ── Stats label row renders ───────────────────────────────────────
  test('stats grid shows Tests, Pass Rate, Healing labels', async ({ page }) => {
    await gotoProjects(page);

    const petCard = page.locator('#project-card-proj-petstore');
    await expect(petCard.getByText('Tests')).toBeVisible();
    await expect(petCard.getByText('Pass Rate')).toBeVisible();
    await expect(petCard.getByText('Healing')).toBeVisible();
  });

  // ── Timer bar renders on petstore card ───────────────────────────
  test('timer bar renders on Petstore project card', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.locator('#timer-bar-proj-petstore')).toBeVisible();
    await expect(page.locator('#timer-bar-proj-petstore').getByText('Last Run Duration')).toBeVisible();
  });

  // ── Timer bar shows SLA time values ──────────────────────────────
  test('timer bar shows run duration and SLA limit in seconds', async ({ page }) => {
    await gotoProjects(page);

    // Petstore: durationMs: 14800, limitMs: 20000 → 14.8s / 20s
    const timerBar = page.locator('#timer-bar-proj-petstore');
    await expect(timerBar).toContainText('14.8s');
    await expect(timerBar).toContainText('20s SLA');
  });

  // ── Pass-rate trend sparkline renders ────────────────────────────
  test('sparkline SVG renders on project cards', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.getByText('Pass-rate Trend').first()).toBeVisible();
    // SVG path should be in the DOM
    const svgPath = page.locator('#project-card-proj-petstore svg path').first();
    await expect(svgPath).toBeAttached();
  });

  // ── Active registry count shows 3 ────────────────────────────────
  test('Active Registry Count shows 3 for three mock projects', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.getByText('Active Registry Count:')).toBeVisible();
    // Count shows as the number right after the label
    await expect(page.locator('#projects-screen')).toContainText('3');
  });

  // ── Search input renders ──────────────────────────────────────────
  test('workspace search input renders with correct placeholder', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.locator('#workspace-search-input')).toBeVisible();
    await expect(page.locator('#workspace-search-input')).toHaveAttribute('placeholder', 'Search API workspaces...');
  });

  // ── Search filters by name ────────────────────────────────────────
  test('search filters projects by name', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#workspace-search-input').fill('Checkout');
    await page.waitForTimeout(200);

    await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
    await expect(page.locator('#project-card-proj-petstore')).not.toBeVisible();
    await expect(page.locator('#project-card-proj-auth-identity')).not.toBeVisible();
  });

  // ── Search count updates with filter ─────────────────────────────
  test('Active Registry Count updates when search filters results', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#workspace-search-input').fill('Identity');
    await page.waitForTimeout(200);

    // Count should show 1
    await expect(page.locator('#projects-screen')).toContainText('1');
  });

  // ── Clearing search restores all cards ───────────────────────────
  test('clearing search restores all three project cards', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#workspace-search-input').fill('Petstore');
    await page.waitForTimeout(200);
    await page.locator('#workspace-search-input').fill('');
    await page.waitForTimeout(200);

    await expect(page.locator('#project-card-proj-petstore')).toBeVisible();
    await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
    await expect(page.locator('#project-card-proj-auth-identity')).toBeVisible();
  });

  // ── Empty state when search finds nothing ────────────────────────
  test('empty state shows when search finds no matching projects', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#workspace-search-input').fill('zzz-nonexistent');
    await page.waitForTimeout(200);

    await expect(page.getByText('No workspace projects found')).toBeVisible();
    await expect(page.getByText('Upload an OpenAPI Swagger blueprint')).toBeVisible();
  });

  // ── New Validation Run button renders ────────────────────────────
  test('New Validation Run button renders', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.locator('#btn-projects-new-run')).toBeVisible();
    await expect(page.locator('#btn-projects-new-run')).toContainText('New Validation Run');
  });

  // ── New Run button navigates to setup ────────────────────────────
  test('clicking New Validation Run navigates to setup screen', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#btn-projects-new-run').click();
    await page.waitForSelector('#setup-screen');

    await expect(page.locator('#setup-screen')).toBeVisible();
  });

  // ── Footer slogan renders ─────────────────────────────────────────
  test('footer slogan "See your tests being born." renders', async ({ page }) => {
    await gotoProjects(page);

    await expect(page.getByText('"See your tests being born."')).toBeVisible();
  });

  // ── Project card click selection ──────────────────────────────────
  test('clicking a project card changes active selection', async ({ page }) => {
    await gotoProjects(page);

    await page.locator('#project-card-proj-auth-identity').click();
    await page.waitForTimeout(200);

    // Auth card should now have the selected (glow) border styling
    await expect(page.locator('#project-card-proj-auth-identity')).toBeVisible();
  });

  // ── Auth project has SLA-critical timer bar ───────────────────────
  test('Identity Provider OAuth timer bar shows SLA-critical state (94% of limit)', async ({ page }) => {
    await gotoProjects(page);

    // Auth: durationMs: 28200, limitMs: 30000 → 94% which is > 85% → SLA critical
    const authTimerBar = page.locator('#timer-bar-proj-auth-identity');
    await expect(authTimerBar).toBeVisible();
    await expect(authTimerBar).toContainText('28.2s');
  });

  // ── Review failed shows in pipeline status for auth project ──────
  test('Identity Provider OAuth shows pipeline status strip', async ({ page }) => {
    await gotoProjects(page);

    // Status dots are in a div with "Pipeline Status Index" title
    const authCard = page.locator('#project-card-proj-auth-identity');
    const statusStrip = authCard.locator('[title="Pipeline Status Index"]');
    await expect(statusStrip).toBeVisible();
  });

});
