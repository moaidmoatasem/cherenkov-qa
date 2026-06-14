import { test, expect } from '@playwright/test';
import { setupApiMocks } from './api_mocks';

const SETTLEMENT = 500;

async function gotoTruthMap(page: any) {
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
  await page.click('#nav-item-truth-map');
  await page.waitForSelector('#truth-map-screen');
  await page.waitForTimeout(SETTLEMENT);
}

test.describe('Truth Map Screen — Deep Coverage', () => {

  // ── Screen heading and description ────────────────────────────────
  test('truth map screen renders heading and description', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByText('Endpoint Truth Graph')).toBeVisible();
    await expect(page.getByText('Unified claims graph mapping the alignment between OpenAPI specifications')).toBeVisible();
  });

  // ── Monitored Endpoint Claims panel renders ───────────────────────
  test('Monitored Endpoint Claims panel renders', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByText('Monitored Endpoint Claims')).toBeVisible();
  });

  // ── Four endpoints appear in the list ────────────────────────────
  test('all four mock endpoints are listed in the endpoint panel', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByText('POST /pets')).toBeVisible();
    await expect(page.getByText('GET /pet/findByStatus')).toBeVisible();
    await expect(page.getByText('GET /store/inventory')).toBeVisible();
    await expect(page.getByText('GET /user/login')).toBeVisible();
  });

  // ── All endpoints show DIVERGENT badge ───────────────────────────
  test('all endpoints show DIVERGENT badge since hasDivergence is true', async ({ page }) => {
    await gotoTruthMap(page);

    const divergentBadges = page.getByText('DIVERGENT');
    await expect(divergentBadges.first()).toBeVisible();
    expect(await divergentBadges.count()).toBe(4);
  });

  // ── Default endpoint selection: POST /pets ────────────────────────
  test('POST /pets is selected by default and shows its claims', async ({ page }) => {
    await gotoTruthMap(page);

    // Claims panel header shows the selected endpoint
    await expect(page.getByText('POST /pets').first()).toBeVisible();
    await expect(page.getByText('Provenanced Verification Claims')).toBeVisible();
  });

  // ── Claims for POST /pets show ────────────────────────────────────
  test('three claims render for the default POST /pets endpoint', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByText('Requires property "name" and "photoUrls"')).toBeVisible();
    await expect(page.getByText('Schema validation checks fields on incoming requests')).toBeVisible();
    await expect(page.getByText('Observed POST requests lacking photoUrls succeeding with 200 OK')).toBeVisible();
  });

  // ── Provenance labels render ──────────────────────────────────────
  test('provenance labels SPEC VERIFIED, CODE VERIFIED, TRAFFIC VERIFIED show for POST /pets', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByText('SPEC VERIFIED')).toBeVisible();
    await expect(page.getByText('CODE VERIFIED')).toBeVisible();
    await expect(page.getByText('TRAFFIC VERIFIED')).toBeVisible();
  });

  // ── HUNT DIVERGENCES button renders ──────────────────────────────
  test('HUNT DIVERGENCES button renders in the claims panel', async ({ page }) => {
    await gotoTruthMap(page);

    await expect(page.getByRole('button', { name: /HUNT DIVERGENCES/i })).toBeVisible();
  });

  // ── Click endpoint switches claims panel ──────────────────────────
  test('clicking GET /pet/findByStatus shows its claims', async ({ page }) => {
    await gotoTruthMap(page);

    await page.getByText('GET /pet/findByStatus').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Accepts query parameters enum: [available, pending, sold]')).toBeVisible();
    await expect(page.getByText('Observed 200 OK responses with empty list for arbitrary status strings')).toBeVisible();
  });

  // ── Click GET /store/inventory shows its claims ───────────────────
  test('clicking GET /store/inventory shows its claims', async ({ page }) => {
    await gotoTruthMap(page);

    await page.getByText('GET /store/inventory').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Returns object mapping status tags to integer counts')).toBeVisible();
    await expect(page.getByText('Querying store inventory shows internal test state leaks')).toBeVisible();
  });

  // ── DB provenance shows for store/inventory ───────────────────────
  test('DB VERIFIED provenance label shows for store inventory endpoint', async ({ page }) => {
    await gotoTruthMap(page);

    await page.getByText('GET /store/inventory').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('DB VERIFIED')).toBeVisible();
  });

  // ── Click GET /user/login shows its claims ────────────────────────
  test('clicking GET /user/login shows its claims', async ({ page }) => {
    await gotoTruthMap(page);

    await page.getByText('GET /user/login').click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Spec requires rate limit and expiration headers on 200 OK')).toBeVisible();
    await expect(page.getByText('API responses do not contain X-Rate-Limit or X-Expires-After headers')).toBeVisible();
  });

  // ── Endpoint Multi-source Claims count ───────────────────────────
  test('endpoint list shows Multi-source Claims count per endpoint', async ({ page }) => {
    await gotoTruthMap(page);

    // POST /pets has 3 claims
    await expect(page.getByText('3 Multi-source Claims')).toBeVisible();
  });

  // ── Switching back to POST /pets restores claims ──────────────────
  test('clicking POST /pets again after switching restores its claims', async ({ page }) => {
    await gotoTruthMap(page);

    // Switch away
    await page.getByText('GET /user/login').click();
    await page.waitForTimeout(300);

    // Switch back
    await page.getByText('POST /pets').first().click();
    await page.waitForTimeout(300);

    await expect(page.getByText('Requires property "name" and "photoUrls"')).toBeVisible();
  });

  // ── Error state renders correctly ─────────────────────────────────
  test('error state shows when truth-map API returns 500', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/truth-map', route =>
      route.fulfill({ status: 500, body: '{"detail":"error"}' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-truth-map');
    await page.waitForSelector('#truth-map-screen');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('Failed to load truth map')).toBeVisible();
  });

  // ── Empty state: no endpoints ─────────────────────────────────────
  test('empty state shows when truth-map returns empty array', async ({ page }) => {
    await setupApiMocks(page);
    await page.route('**/api/v1/truth-map', route =>
      route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
    );

    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('[copilot] tour_seen', 'true');
      localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
    });
    await page.reload();
    await page.waitForSelector('#cherenkov-app-core');
    await page.waitForTimeout(SETTLEMENT);
    await page.click('#nav-item-truth-map');
    await page.waitForSelector('#truth-map-screen');
    await page.waitForTimeout(SETTLEMENT);

    await expect(page.getByText('No endpoints mapped yet')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Go to Spec Ingest' })).toBeVisible();
  });

});
