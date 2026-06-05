import { test, expect, Page, Request } from '@playwright/test';
import * as fs from 'fs';

/**
 * FULL INTERACTIVE AUDIT
 * Drives every flow and records which actions actually hit the backend.
 * Output: ../../scratch/audit/report.json  (+ screenshots)
 */

const OUT = process.env.AUDIT_OUT || '/home/moaid/cherenkov-qa/scratch/audit';
fs.mkdirSync(OUT, { recursive: true });

type Rec = { flow: string; action: string; apiCalls: string[]; note: string; ok: boolean };
const log: Rec[] = [];
const errors: string[] = [];

// Capture API calls made during a given action
async function track(page: Page, flow: string, action: string, fn: () => Promise<void>, note = ''): Promise<string[]> {
  const calls: string[] = [];
  const handler = (req: Request) => {
    const u = req.url();
    if (u.includes('/api/v1') || u.includes('/ws/live')) calls.push(`${req.method()} ${u.split('/api/v1')[1] || '/ws/live'}`);
  };
  page.on('request', handler);
  let ok = true;
  try { await fn(); } catch (e) { ok = false; errors.push(`${flow}/${action}: ${(e as Error).message}`); }
  await page.waitForTimeout(700);
  page.off('request', handler);
  log.push({ flow, action, apiCalls: calls, note, ok });
  return calls;
}

test('full interactive audit of every flow', async ({ page }) => {
  test.setTimeout(180000);
  page.on('pageerror', e => errors.push(`PAGEERROR: ${e.message}`));
  page.on('console', m => { if (m.type() === 'error') errors.push(`CONSOLE: ${m.text()}`); });

  await page.goto('/');
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(1200);

  // ---- 1. SETUP / INGEST (live expected) ----
  await track(page, 'Setup', 'open New Spec Run', async () => {
    await page.click('text=NEW SPEC RUN');
  });
  await track(page, 'Setup', 'click preset petstore-v2.yaml', async () => {
    const preset = page.locator('text=petstore-v2.yaml').first();
    if (await preset.count()) await preset.click();
  }, 'preset mock load');
  await track(page, 'Setup', 'paste URL + FETCH', async () => {
    const url = page.locator('input[placeholder*="petstore"], input[type="text"]').first();
    if (await url.count()) { await url.fill('http://127.0.0.1:8000/api/v1/health'); }
    const fetchBtn = page.locator('button:has-text("FETCH")').first();
    if (await fetchBtn.count()) await fetchBtn.click();
  }, 'expect POST /ingest');

  // ---- 2. AUTHOR BY INTENT (suspected fake) ----
  await track(page, 'Author', 'navigate', async () => { await page.click('#nav-item-author'); });
  await track(page, 'Author', 'click example chip', async () => {
    const chip = page.locator('text=/Verify that guests can checkout/').first();
    if (await chip.count()) await chip.click();
  });
  await track(page, 'Author', 'INITIALIZE PILOT RUN', async () => {
    const btn = page.locator('button:has-text("INITIALIZE PILOT RUN")').first();
    if (await btn.count()) await btn.click();
    await page.waitForTimeout(3500); // let the animation run
  }, 'CRITICAL: does flagship feature hit backend?');

  // ---- 3. DIVERGENCES (live + fallback) ----
  await track(page, 'Divergences', 'navigate', async () => { await page.click('#nav-item-divergences'); }, 'expect GET /divergences');
  await track(page, 'Divergences', 'filter severity=critical', async () => {
    const sel = page.locator('select:has(option[value="critical"])').first();
    if (await sel.count()) await sel.selectOption('critical');
  });
  await track(page, 'Divergences', 'reset filter to all', async () => {
    const sel = page.locator('select:has(option[value="critical"])').first();
    if (await sel.count()) await sel.selectOption({ index: 0 });
  });
  await track(page, 'Divergences', 'open detail drawer (D-)', async () => {
    const row = page.locator('text=D-').first();
    if (await row.count()) await row.click();
  });
  await track(page, 'Divergences', 'act: close_with_test', async () => {
    const btn = page.locator('button:has-text("Close"), button:has-text("close with test"), button:has-text("Mark")').first();
    if (await btn.count()) await btn.click();
  }, 'expect POST /divergences/act');
  await page.keyboard.press('Escape');

  // ---- 4. REVIEW QUEUE (live) ----
  await track(page, 'Review', 'navigate', async () => { await page.click('#nav-item-review'); }, 'expect GET /tests');
  await track(page, 'Review', 'select a card', async () => {
    const card = page.locator('text=happy_path.spec.ts').first();
    if (await card.count()) await card.click();
  });
  await track(page, 'Review', 'APPROVE SPEC TEST', async () => {
    const btn = page.locator('button:has-text("APPROVE SPEC TEST")').first();
    if (await btn.count()) await btn.click();
  }, 'expect POST /review/approve');

  // ---- 5. HEALING (partial) ----
  await track(page, 'Healing', 'navigate', async () => { await page.click('#nav-item-healing'); });
  await track(page, 'Healing', 'APPLY HEALING SUGGESTION', async () => {
    const btn = page.locator('button:has-text("APPLY HEALING")').first();
    if (await btn.count()) await btn.click();
  }, 'does apply hit backend?');

  // ---- 6. EJECT (live) ----
  await track(page, 'Eject', 'navigate', async () => { await page.click('#nav-item-eject'); });
  await track(page, 'Eject', 'EJECT AND WRITE DIRECTORIES', async () => {
    const btn = page.locator('button:has-text("EJECT AND WRITE")').first();
    if (await btn.count()) await btn.click();
  }, 'expect POST /eject');

  // ---- 7. OBSERVABILITY SCREENS (suspected pure mock) ----
  for (const [navId, flow] of [['#nav-item-overview','Overview'],['#nav-item-truth-map','TruthMap'],['#nav-item-signals','Signals'],['#nav-item-governance','Governance'],['#nav-item-memory','Memory'],['#nav-item-explore','Explore']] as const) {
    await track(page, flow, 'navigate', async () => { await page.click(navId); }, 'mock check: any API call?');
  }
  await track(page, 'Overview', 'RUN DISCOVERY SCAN', async () => {
    await page.click('#nav-item-overview');
    const btn = page.locator('button:has-text("RUN DISCOVERY SCAN")').first();
    if (await btn.count()) await btn.click();
  }, 'does discovery scan do anything?');
  await track(page, 'TruthMap', 'click endpoint + Hunt Divergences', async () => {
    await page.click('#nav-item-truth-map');
    const ep = page.locator('text=/POST \\/pets|\\/user\\/login/').first();
    if (await ep.count()) await ep.click();
    const hunt = page.locator('button:has-text("HUNT DIVERGENCES")').first();
    if (await hunt.count()) await hunt.click();
  }, 'does Hunt do anything but navigate?');
  await track(page, 'Signals', 'switch tabs', async () => {
    await page.click('#nav-item-signals');
    for (const t of ['Visual Regression','SDET Coverage','Performance']) {
      const b = page.locator(`button:has-text("${t}")`).first();
      if (await b.count()) { await b.click(); await page.waitForTimeout(300); }
    }
  });

  // ---- 8. WORKSPACE SWITCHER ----
  await track(page, 'Workspace', 'switch to Swagger Petstore v2', async () => {
    const sel = page.locator('select').filter({ hasText: /Checkout Gateway|Petstore|Identity/ }).first();
    if (await sel.count()) {
      await sel.selectOption({ label: 'Swagger Petstore v2' }).catch(()=>{});
    } else {
      // custom dropdown
      const dd = page.locator('text=Checkout Gateway API').first();
      if (await dd.count()) { await dd.click(); const opt = page.locator('text=Swagger Petstore v2').first(); if (await opt.count()) await opt.click(); }
    }
  }, 'does switching change data?');

  // ---- 9. SETTINGS ----
  await track(page, 'Settings', 'navigate', async () => { await page.click('text=Settings'); });
  await track(page, 'Settings', 'toggle Compact + Apply', async () => {
    const cb = page.locator('input[type="checkbox"]').first();
    if (await cb.count()) await cb.click();
    const apply = page.locator('button:has-text("APPLY PARAMETERS")').first();
    if (await apply.count()) await apply.click();
  }, 'does Apply persist anywhere?');

  // ---- 10. COMMAND PALETTE ----
  await track(page, 'Palette', 'Ctrl+K open + navigate', async () => {
    await page.keyboard.press('Control+KeyK');
    await page.waitForTimeout(300);
    const input = page.locator('[placeholder*="page name or action"]').first();
    if (await input.count()) { await input.fill('gov'); await page.waitForTimeout(200); await page.keyboard.press('Enter'); }
  });

  // ---- summary ----
  const liveFlows = log.filter(r => r.apiCalls.length > 0);
  const deadFlows = log.filter(r => r.apiCalls.length === 0 && r.action !== 'navigate');
  const summary = {
    totalActions: log.length,
    actionsHittingBackend: liveFlows.length,
    actionsWithNoBackend: deadFlows.length,
    pageErrors: errors.length,
    records: log,
    errors,
  };
  fs.writeFileSync(`${OUT}/report.json`, JSON.stringify(summary, null, 2));
  console.log('\n===== AUDIT SUMMARY =====');
  console.log(`actions=${log.length} hitBackend=${liveFlows.length} noBackend=${deadFlows.length} pageErrors=${errors.length}`);
  for (const r of log) {
    const tag = r.apiCalls.length ? `LIVE[${r.apiCalls.join('; ')}]` : 'no-api';
    console.log(`  ${r.ok?'✓':'✗'} ${r.flow} :: ${r.action} -> ${tag}${r.note?'  // '+r.note:''}`);
  }
  if (errors.length) { console.log('\n--- ERRORS ---'); errors.forEach(e=>console.log('  '+e)); }
});
