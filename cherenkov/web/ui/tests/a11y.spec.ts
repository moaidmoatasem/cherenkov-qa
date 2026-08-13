/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Accessibility audit of the workspaces CHERENKOV actually ships.
 *
 * The previous version of this file audited the pre-revamp screen IA —
 * Projects, Sidebar/TopBar, Review, Setup, Healing, Governance, Memory, Truth
 * Map, Eject, Devices, Signals, Author. Those screens were removed in the UI
 * revamp, and `playwright.config.ts` already archives its sibling specs for
 * exactly that reason; this file was simply left off the list. Because the
 * whole suite could not load (missing `api_mocks.ts`, restored in #978),
 * nobody saw it fail — so a11y coverage of the shipping UI read as green while
 * being zero.
 *
 * Rewritten against the five workspaces plus Enterprise. Two rules hold here:
 *
 * 1. **Assertions are not weakened to make the suite pass.** If axe reports a
 *    violation on a live surface, that is a UI bug to fix, not a threshold to
 *    raise. The one exemption is `color-contrast`, which the previous file also
 *    carried and which is a deliberate property of the dark theme — it is
 *    excluded explicitly and visibly, per test, rather than by lowering the bar.
 * 2. **Real backend, not mocks.** These run through `bootstrapReal`, the same
 *    path the e2e specs use, so the audit sees the DOM the user gets.
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { bootstrapReal } from './qa/page-objects';

const SETTLE = 500;

/** The workspaces in the shipping IA: nav id → container id. */
const WORKSPACES: ReadonlyArray<{ id: string; container: string; label: string }> = [
  { id: 'dashboard', container: '#dashboard-workspace', label: 'Dashboard' },
  { id: 'authoring', container: '#authoring-workspace', label: 'Generate Tests' },
  { id: 'triage', container: '#triage-workspace', label: 'Triage' },
  { id: 'intelligence', container: '#intelligence-workspace', label: 'Knowledge' },
  { id: 'settings', container: '#settings-workspace', label: 'Settings' },
];

/**
 * Run axe over the current page and return violations that matter here.
 *
 * `color-contrast` is filtered out — the dashboard's dark theme is
 * intentionally low-contrast and the previous spec carried the same exemption.
 * Everything else (roles, names, labels, landmarks, focus order) is reported.
 */
async function auditViolations(page: import('@playwright/test').Page) {
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  return results.violations.filter((v) => v.id !== 'color-contrast');
}

/** Render violations as something a reader can act on, not just a count. */
function describeViolations(violations: Awaited<ReturnType<typeof auditViolations>>): string {
  return violations
    .map((v) => `${v.id} (${v.impact}) — ${v.help}\n    ${v.nodes.map((n) => n.target.join(' ')).join('\n    ')}`)
    .join('\n  ');
}

test.describe('Accessibility — shipping workspaces', () => {
  test.beforeEach(async ({ page }) => {
    page.on('pageerror', (err) => console.error(`[UNCAUGHT] ${err.message}`));
    await bootstrapReal(page);
  });

  for (const workspace of WORKSPACES) {
    test(`${workspace.label} workspace has no critical a11y violations`, async ({ page }) => {
      await page.getByTestId(`nav-workspace-${workspace.id}`).click();
      await page.waitForSelector(workspace.container);
      await page.waitForTimeout(SETTLE);

      const violations = await auditViolations(page);
      expect(
        violations.length,
        `${workspace.label}:\n  ${describeViolations(violations)}`,
      ).toBe(0);
    });
  }

  test('every workspace is reachable by keyboard from the navigation bar', async ({ page }) => {
    for (const workspace of WORKSPACES) {
      const navItem = page.getByTestId(`nav-workspace-${workspace.id}`);
      await navItem.focus();
      await expect(navItem).toBeFocused();
      await page.keyboard.press('Enter');
      await page.waitForSelector(workspace.container);
      await expect(page.locator(workspace.container)).toBeVisible();
    }
  });

  test('navigation items expose an accessible name', async ({ page }) => {
    for (const workspace of WORKSPACES) {
      const navItem = page.getByTestId(`nav-workspace-${workspace.id}`);
      const name = await navItem.getAttribute('aria-label');
      const text = (await navItem.textContent())?.trim() ?? '';
      // An icon-only rail collapses the label, so either source counts —
      // what must not happen is a control with no name at all.
      expect(
        (name ?? '') + text,
        `nav-workspace-${workspace.id} has neither aria-label nor text`,
      ).not.toBe('');
    }
  });

  test('the page exposes a main landmark and a single h1', async ({ page }) => {
    await expect(page.locator('main')).toHaveCount(1);
    const h1s = page.getByRole('heading', { level: 1 });
    expect(await h1s.count()).toBeLessThanOrEqual(1);
  });

  test('Brain Map panel exposes its controls with accessible names', async ({ page }) => {
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForSelector('#intelligence-workspace');
    await page.waitForTimeout(SETTLE);

    // The panel renders either its empty state or the built map; both carry
    // named controls, and neither may render a nameless button.
    const panel = page.getByTestId('brainmap-panel').or(page.getByTestId('brainmap-empty'));
    await expect(panel).toBeVisible();

    const buttons = panel.getByRole('button');
    const count = await buttons.count();
    for (let i = 0; i < count; i += 1) {
      const button = buttons.nth(i);
      const label = (await button.getAttribute('aria-label')) ?? '';
      const text = (await button.textContent())?.trim() ?? '';
      expect(label + text, `Brain Map button ${i} has no accessible name`).not.toBe('');
    }
  });

  test('the graph canvas is hidden from assistive tech and mirrored by a list', async ({ page }) => {
    await page.getByTestId('nav-workspace-intelligence').click();
    await page.waitForSelector('#intelligence-workspace');
    await page.waitForTimeout(SETTLE);

    const canvas = page.getByTestId('brainmap-canvas');
    if (await canvas.count()) {
      // A canvas cannot be read by a screen reader, so it must not pretend to
      // be content: it is aria-hidden, and the node list carries the same
      // information in a focusable form.
      await expect(canvas).toHaveAttribute('aria-hidden', 'true');
      await expect(page.getByTestId('brainmap-node-list')).toBeVisible();
    }
  });
});
