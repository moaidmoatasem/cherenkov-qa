import { test } from '@playwright/test';
import * as fs from 'fs';

// Written outside Playwright's `test-results/` dir (which is wiped at the start of
// every run). Override with PLAYBOOK_OUT if you want a different location.
const OUT = process.env.PLAYBOOK_OUT || 'playbook';
fs.mkdirSync(OUT, { recursive: true });

const SCREENS: { id: string; nav: string; file: string }[] = [
  { id: 'overview',    nav: '#nav-item-overview',    file: '01-overview' },
  { id: 'truth-map',   nav: '#nav-item-truth-map',   file: '02-truth-map' },
  { id: 'divergences', nav: '#nav-item-divergences', file: '03-divergences' },
  { id: 'author',      nav: '#nav-item-author',      file: '04-author' },
  { id: 'signals',     nav: '#nav-item-signals',     file: '05-signals' },
  { id: 'memory',      nav: '#nav-item-memory',      file: '06-memory' },
  { id: 'governance',  nav: '#nav-item-governance',  file: '07-governance' },
];

test('capture all screens to playbook', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console:' + m.text()); });

  await page.goto('/');
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/00-landing.png`, fullPage: true });

  for (const s of SCREENS) {
    try {
      await page.click(s.nav, { timeout: 5000 });
      await page.waitForTimeout(900);
      await page.screenshot({ path: `${OUT}/${s.file}.png`, fullPage: true });
    } catch (e) {
      errors.push(`nav ${s.id}: ${(e as Error).message}`);
    }
  }

  // Settings (button, not nav id)
  try {
    await page.click('button:has-text("Settings")', { timeout: 5000 });
    await page.waitForTimeout(700);
    await page.screenshot({ path: `${OUT}/08-settings.png`, fullPage: true });
  } catch (e) { errors.push(`settings: ${(e as Error).message}`); }

  // Command palette
  try {
    await page.keyboard.press('Control+KeyK');
    await page.waitForTimeout(500);
    await page.screenshot({ path: `${OUT}/09-command-palette.png` });
    await page.keyboard.press('Escape');
  } catch (e) { errors.push(`palette: ${(e as Error).message}`); }

  fs.writeFileSync(`${OUT}/_errors.json`, JSON.stringify(errors, null, 2));
  console.log(`CAPTURED. page/console errors: ${errors.length}`);
  if (errors.length) console.log(JSON.stringify(errors, null, 2));
});
