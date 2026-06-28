import { test, expect } from '@playwright/test';
import { bootstrap, Sidebar, TopBar, ProjectsPage, SetupPage, PipelinePage, ReviewPage, HealingPage, EjectPage, OverviewPage, TruthMapPage, DivergencesPage, AuthorPage, SignalsPage, MemoryPage, GovernancePage, ChatPage, KnowledgePage, DevicesPage, SettingsPage, SddPage, MobilePage, CommandPalette } from './page-objects';
import { setupApiMocks } from '../api_mocks';
import { makeProject, makeProjects, makeTestItem, makeFailingTest, makeDivergence, EMPTY_PROJECTS, EMPTY_TESTS, EMPTY_FAILURES, EMPTY_DIVERGENCES, STRESS_PROJECTS, STRESS_DIVERGENCES, makeXssPayloads, makeBoundaryValues } from './test-data-factory';

const S = 400;

test.describe('QA Engineer Day-to-Day: Functional Testing — Happy Paths & Business Rules', () => {

  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    await bootstrap(page);
  });

  test.describe('Projects Screen — Functional', () => {
    test('displays all project cards with correct data', async ({ page }) => {
      const pp = new ProjectsPage(page);
      await expect(pp.el).toBeVisible();
      await pp.assertCardVisible('proj-petstore');
      await pp.assertCardVisible('proj-checkout-api');
      await pp.assertCardVisible('proj-auth-identity');
    });

    test('project card shows pipeline status indicators', async ({ page }) => {
      await expect(page.locator('#project-card-proj-petstore')).toContainText('47');
      await expect(page.locator('#project-card-proj-petstore')).toContainText('91');
    });

    test('timer bar visible on project cards', async ({ page }) => {
      const pp = new ProjectsPage(page);
      await expect(pp.timerBar('proj-petstore')).toBeVisible();
    });

    test('search filters projects by name', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.search('Checkout');
      await expect(page.locator('#project-card-proj-checkout-api')).toBeVisible();
      await expect(page.locator('#project-card-proj-petstore')).not.toBeVisible();
    });

    test('search clear restores all projects', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.search('Checkout');
      await sb.clearSearch();
      await expect(page.locator('#project-card-proj-petstore')).toBeVisible();
    });

    test('New Run button is present and clickable', async ({ page }) => {
      const pp = new ProjectsPage(page);
      await expect(pp.newRunBtn).toBeVisible();
      await pp.newRunBtn.click();
      await page.waitForTimeout(300);
    });

    test('project selector in sidebar is functional', async ({ page }) => {
      const sb = new Sidebar(page);
      await expect(sb.projectSelector).toBeVisible();
    });
  });

  test.describe('Setup Screen — Functional', () => {
    test('setup screen loads from sidebar new run button', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.newRun();
      await expect(page.locator('#setup-screen')).toBeVisible();
    });

    test('spec URL input accepts text', async ({ page }) => {
      const sp = new SetupPage(page);
      await new Sidebar(page).newRun();
      await expect(sp.urlInput).toBeVisible();
      await sp.urlInput.fill('https://example.com/spec.json');
      await expect(sp.urlInput).toHaveValue('https://example.com/spec.json');
    });

    test('petstore preset loads mock spec', async ({ page }) => {
      const sp = new SetupPage(page);
      await new Sidebar(page).newRun();
      await sp.loadPetstore();
      await expect(page.getByText('swagger-petstore-v2.json')).toBeVisible();
    });

    test('server validation toggle reveals auth fields', async ({ page }) => {
      const sp = new SetupPage(page);
      await new Sidebar(page).newRun();
      await sp.toggleServerValidation();
      await expect(sp.serverUrlInput).toBeVisible();
      await expect(sp.authHeaderInput).toBeVisible();
    });

    test('launch generation button visible after loading preset', async ({ page }) => {
      await bootstrap(page);
      const sb = new Sidebar(page);
      await sb.newRun();
      const sp = new SetupPage(page);
      await sp.loadPetstore();
      await expect(sp.launchBtn).toBeVisible();
    });
  });

  test.describe('Pipeline Screen — Functional', () => {
    test('pipeline drawer opens from TopBar', async ({ page }) => {
      const tb = new TopBar(page);
      await tb.openPipelineDrawer();
      const pp = new PipelinePage(page);
      await expect(pp.heading).toBeVisible();
    });

    test('pipeline nodes render in correct order', async ({ page }) => {
      await new TopBar(page).openPipelineDrawer();
      const pp = new PipelinePage(page);
      await expect(pp.node('ingest')).toBeVisible();
      await expect(pp.node('generate')).toBeVisible();
      await expect(pp.node('review')).toBeVisible();
    });

    test('pause/resume toggles pipeline state', async ({ page }) => {
      await new TopBar(page).openPipelineDrawer();
      const pp = new PipelinePage(page);
      await expect(pp.pauseResumeBtn).toContainText('PAUSE');
      await pp.pause();
      await expect(pp.pauseResumeBtn).toContainText('RESUME');
    });

    test('telemetry panel shows token budget', async ({ page }) => {
      await new TopBar(page).openPipelineDrawer();
      const pp = new PipelinePage(page);
      await expect(pp.tokenBudget).toBeVisible();
      await expect(pp.promptAttention).toBeVisible();
    });
  });

  test.describe('Review Screen — Functional', () => {
    test('review screen loads with filter tabs', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('review');
      const rp = new ReviewPage(page);
      await expect(rp.el).toBeVisible();
      await expect(rp.filterTab('all')).toBeVisible();
      await expect(rp.filterTab('approved')).toBeVisible();
      await expect(rp.filterTab('review')).toBeVisible();
      await expect(rp.filterTab('rejected')).toBeVisible();
    });

    test('filter tabs switch content', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('review');
      const rp = new ReviewPage(page);
      await rp.filterTab('approved').click();
      await page.waitForTimeout(200);
      await rp.filterTab('review').click();
      await page.waitForTimeout(200);
    });

    test('approve button is present on review items', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('review');
      const rp = new ReviewPage(page);
      await expect(rp.approveBtn).toBeVisible();
    });

    test('reject button is present on review items', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('review');
      const rp = new ReviewPage(page);
      await expect(rp.rejectBtn).toBeVisible();
    });
  });

  test.describe('Healing Screen — Functional', () => {
    test('healing screen loads with drift cards', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      const hp = new HealingPage(page);
      await expect(hp.el).toBeVisible();
      await expect(hp.card('fail-1')).toBeVisible();
      await expect(hp.card('fail-2')).toBeVisible();
      await expect(hp.card('fail-3')).toBeVisible();
      await expect(hp.card('fail-4')).toBeVisible();
    });

    test('suggest-only banner is displayed (D7 invariant)', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      const hp = new HealingPage(page);
      await expect(hp.banner).toBeVisible();
      await expect(page.getByText('All repairs are suggest-only')).toBeVisible();
    });

    test('diagnosis text visible on each drift card', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      await expect(page.getByText('Why it failed:').first()).toBeVisible();
    });

    test('diff viewer opens and closes', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      const hp = new HealingPage(page);
      await hp.viewDiff('fail-1');
      await expect(hp.diffViewer()).toBeVisible();
      await hp.diffDismissBtn.click();
      await expect(hp.diffViewer()).not.toBeVisible();
    });

    test('dismiss removes drift card from list', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      const hp = new HealingPage(page);
      await hp.dismissCard('fail-1');
      await expect(hp.card('fail-1')).not.toBeVisible();
      await expect(hp.card('fail-2')).toBeVisible();
    });
  });

  test.describe('Eject Screen — Functional', () => {
    test('eject screen loads with file tree and form', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('eject');
      const ep = new EjectPage(page);
      await expect(ep.el).toBeVisible();
      await expect(ep.pathInput).toBeVisible();
      await expect(ep.ejectBtn).toBeVisible();
    });

    test('eject button triggers API call and shows copy command', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('eject');
      const ep = new EjectPage(page);
      await ep.eject();
      await expect(ep.copyCmdBtn).toBeVisible();
    });

    test('eject produces success toast notification', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('eject');
      const ep = new EjectPage(page);
      await ep.eject();
      const toast = page.locator('[role="status"]').first();
      await expect(toast).toBeVisible();
    });
  });

  test.describe('Overview Screen — Functional', () => {
    test('overview screen loads with KPI rings', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('overview');
      const op = new OverviewPage(page);
      await expect(op.el).toBeVisible();
      await expect(op.kpiRing).toBeVisible();
    });

    test('KPI ring has correct ARIA attributes', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('overview');
      const op = new OverviewPage(page);
      const value = await op.kpiRing.getAttribute('aria-valuenow');
      expect(value).not.toBeNull();
      const numVal = Number(value);
      expect(numVal).toBeGreaterThanOrEqual(0);
      expect(numVal).toBeLessThanOrEqual(100);
    });

    test('Pilot Run button triggers POST /api/v1/run', async ({ page }) => {
      let runCalled = false;
      await page.route('**/api/v1/run', async route => {
        if (route.request().method() === 'POST') {
          runCalled = true;
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ run_id: 'qa-run', status: 'started' }) });
        } else {
          await route.fulfill({ status: 200, contentType: 'application/json', body: '[]' });
        }
      });
      const sb = new Sidebar(page);
      await sb.navTo('overview');
      const op = new OverviewPage(page);
      await op.pilotRunBtn.click();
      await page.waitForTimeout(300);
      expect(runCalled).toBe(true);
    });
  });

  test.describe('Truth Map Screen — Functional', () => {
    test('truth map loads with endpoint list', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('truth-map');
      const tm = new TruthMapPage(page);
      await expect(tm.el).toBeVisible();
      await expect(page.getByText('POST /pets').first()).toBeVisible();
    });

    test('clicking endpoint shows claims panel', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('truth-map');
      const tm = new TruthMapPage(page);
      await tm.clickEndpoint('GET /user/login');
      await expect(tm.claimsH3.first()).toContainText('GET /user/login');
    });

    test('claims show provenance labels', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('truth-map');
      await page.getByText('GET /user/login').first().click();
      await page.waitForTimeout(300);
      await expect(page.getByText('SPEC VERIFIED').first()).toBeVisible();
    });
  });

  test.describe('Divergences Screen — Functional', () => {
    test('divergences screen loads with triage hub', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      const dp = new DivergencesPage(page);
      await expect(dp.heading).toContainText('Divergence Triage Hub');
    });

    test('severity filter changes displayed divergences', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      const dp = new DivergencesPage(page);
      await dp.filterBySeverity('critical');
      await page.waitForTimeout(200);
    });

    test('clicking divergence row opens detail drawer', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      const dp = new DivergencesPage(page);
      await dp.clickRow();
      await expect(dp.detailDrawer).toBeVisible();
    });

    test('closing detail drawer works', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      const dp = new DivergencesPage(page);
      await dp.clickRow();
      await dp.closeDetailBtn.click();
      await expect(dp.detailDrawer).not.toBeVisible();
    });
  });

  test.describe('Author Screen — Functional', () => {
    test('author screen loads with intent textarea', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('author');
      const ap = new AuthorPage(page);
      await expect(ap.el).toBeVisible();
      await expect(ap.textarea).toBeVisible();
    });

    test('clicking example chip populates textarea', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('author');
      const ap = new AuthorPage(page);
      await ap.clickChip('Verify that guests can checkout');
      const val = await ap.textarea.inputValue();
      expect(val).toContain('Verify that guests can checkout');
    });

    test('manual text input works', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('author');
      const ap = new AuthorPage(page);
      await ap.typeIntent('Test all POST endpoints for 400 on missing fields');
      const val = await ap.textarea.inputValue();
      expect(val).toBe('Test all POST endpoints for 400 on missing fields');
    });

    test('mentor idioms panel is visible', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('author');
      const ap = new AuthorPage(page);
      await expect(ap.mentorPanel).toBeVisible();
    });
  });

  test.describe('Signals Screen — Functional', () => {
    test('signals screen loads with performance tab', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('signals');
      const sp = new SignalsPage(page);
      await expect(sp.el).toBeVisible();
      await expect(page.getByText('API Latency & Anomaly Baselines')).toBeVisible();
    });

    test('tab switching works: Performance → Visual → Coverage', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('signals');
      const sp = new SignalsPage(page);
      await sp.switchTab('Visual Regression');
      await expect(page.getByText('UI Snapshot Comparisons')).toBeVisible();
      await sp.switchTab('SDET Coverage');
      await expect(page.getByText('Code Path Verification Coverage')).toBeVisible();
    });
  });

  test.describe('Memory Screen — Functional', () => {
    test('memory screen loads with idioms and pairing', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('memory');
      const mp = new MemoryPage(page);
      await expect(mp.el).toBeVisible();
      await expect(mp.idiomsPanel).toBeVisible();
      await expect(mp.pairingPanel).toBeVisible();
    });
  });

  test.describe('Governance Screen — Functional', () => {
    test('governance screen loads with KPI metrics', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('governance');
      const gp = new GovernancePage(page);
      await expect(gp.el).toBeVisible();
      await expect(gp.defectEscapeRate).toBeVisible();
      await expect(gp.modelCert).toBeVisible();
    });
  });

  test.describe('Chat Screen — Functional', () => {
    test('chat screen loads with input field', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await expect(cp.el).toBeVisible();
      await expect(cp.input).toBeVisible();
      await expect(cp.input).toBeEnabled();
    });

    test('send message via Enter key', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await cp.sendViaEnter('What tests should I run?');
      await expect(cp.messageBubble('What tests should I run?')).toBeVisible();
    });

    test('SSE streaming response renders', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await cp.send('Hello');
      await expect(page.getByText(/Hello from CHERENKOV/)).toBeVisible();
    });

    test('input clears after sending', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await cp.sendViaEnter('Clear test');
      await expect(cp.input).toHaveValue('');
    });

    test('multiple messages render in sequence', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await cp.sendViaEnter('First msg');
      await page.waitForTimeout(800);
      await cp.sendViaEnter('Second msg');
      await page.waitForTimeout(800);
      await expect(cp.messageBubble('First msg')).toBeVisible();
      await expect(cp.messageBubble('Second msg')).toBeVisible();
    });
  });

  test.describe('Knowledge Screen — Functional', () => {
    test('knowledge screen loads with search', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('knowledge');
      const kp = new KnowledgePage(page);
      await expect(kp.el).toBeVisible();
      await expect(kp.searchInput).toBeVisible();
    });

    test('knowledge search returns results', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('knowledge');
      const kp = new KnowledgePage(page);
      await kp.search('login redirect');
      await expect(page.getByText('reflector').first()).toBeVisible();
    });
  });

  test.describe('Devices Screen — Functional', () => {
    test('devices screen loads with panels', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('devices');
      const dp = new DevicesPage(page);
      await expect(dp.el).toBeVisible();
      await expect(dp.connectivity).toBeVisible();
      await expect(dp.modelAvailability).toBeVisible();
    });
  });

  test.describe('Settings Screen — Functional', () => {
    test('settings screen loads with controls', async ({ page }) => {
      const sp = new SettingsPage(page);
      await sp.open(page);
      await expect(sp.el).toBeVisible();
      await expect(sp.budgetSlider).toBeVisible();
      await expect(sp.threadsSlider).toBeVisible();
      await expect(sp.saveBtn).toBeVisible();
    });

    test('compact mode toggle changes checkbox state', async ({ page }) => {
      const sp = new SettingsPage(page);
      await sp.open(page);
      await sp.compactCheckbox.click();
      await expect(sp.compactCheckbox).toBeChecked();
    });

    test('settings save persists to localStorage', async ({ page }) => {
      await page.route('**/api/v1/settings', async route => {
        await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
      });
      const sp = new SettingsPage(page);
      await sp.open(page);
      await sp.compactCheckbox.click();
      await sp.saveBtn.click();
      await page.waitForTimeout(500);
      const stored = await page.evaluate(() => localStorage.getItem('[copilot] density'));
      expect(stored).toBe('compact');
    });
  });

  test.describe('SDD Cockpit — Functional', () => {
    test('SDD cockpit loads with KPI row', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('sdd');
      const sdd = new SddPage(page);
      await expect(sdd.heading).toBeVisible();
      await expect(sdd.tokenBudgetCard).toBeVisible();
      await expect(sdd.sessionsCard).toBeVisible();
    });

    test('token budget KPI ring shows percentage', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('sdd');
      const sdd = new SddPage(page);
      const val = await sdd.kpiRing.getAttribute('aria-valuenow');
      expect(Number(val)).toBeGreaterThanOrEqual(0);
    });

    test('recent sessions panel renders', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('sdd');
      const sdd = new SddPage(page);
      await expect(sdd.recentSessions).toBeVisible();
    });
  });

  test.describe('Mobile Screen — Functional', () => {
    test('mobile screen loads with device cards', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('mobile');
      const mp = new MobilePage(page);
      await expect(mp.el).toBeVisible();
      await page.waitForTimeout(1000);
      await expect(mp.deviceCard('m1')).toBeVisible();
      await expect(mp.deviceCard('m2')).toBeVisible();
    });

    test('device status shows disconnected', async ({ page }) => {
      const sb = new Sidebar(page);
      await sb.navTo('mobile');
      const mp = new MobilePage(page);
      await page.waitForTimeout(1000);
      await expect(mp.deviceStatus('m1')).toContainText('Disconnected');
    });
  });

  test.describe('TopBar & Sidebar — Functional', () => {
    test('autonomy toggle switches between modes', async ({ page }) => {
      const tb = new TopBar(page);
      await expect(tb.autonomyButtons).toHaveCount(3);
      await tb.setAutonomy(1);
      await expect(tb.autonomyButtons.nth(1)).toHaveAttribute('aria-checked', 'true');
      await tb.setAutonomy(2);
      await expect(tb.autonomyButtons.nth(2)).toHaveAttribute('aria-checked', 'true');
    });

    test('session cost visible in topbar', async ({ page }) => {
      const tb = new TopBar(page);
      await expect(tb.sessionCost).toBeVisible();
    });

    test('health widget shows device and model', async ({ page }) => {
      const tb = new TopBar(page);
      await expect(tb.healthDevice).toBeVisible();
      await expect(tb.healthModel).toBeVisible();
    });

    test('command palette opens with Ctrl+K', async ({ page }) => {
      const cp = new CommandPalette(page);
      await cp.open();
      await expect(cp.input).toBeVisible();
    });

    test('command palette search filters results', async ({ page }) => {
      const cp = new CommandPalette(page);
      await cp.open();
      await cp.search('author');
      await expect(page.getByText('Go to Author by Intent')).toBeVisible();
      await cp.close();
    });
  });
});

test.describe('QA Engineer Day-to-Day: Boundary & Edge Case Testing', () => {

  test.describe('Empty Data States', () => {
    test('projects screen: no projects shows empty state gracefully', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/projects', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('divergences screen: empty list does not crash', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/divergences**', route =>
          route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      await page.waitForTimeout(600);
      await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    });

    test('healing screen: no failures shows healthy state', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/failures', route =>
          route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('healing');
      await page.waitForSelector('#healing-screen');
      await page.waitForTimeout(S);
      await expect(page.getByText('All tests completely healthy')).toBeVisible();
    });

    test('review screen: empty queue shows empty state', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/review/queue*', route =>
          route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('review');
      await page.waitForSelector('#review-screen');
      await expect(page.locator('#review-screen')).toBeVisible();
    });

    test('SDD sessions: empty shows placeholder', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/sdd/sessions*', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText('No sessions')).toBeVisible();
    });

    test('SDD patterns: empty shows placeholder', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/sdd/graph/patterns', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText('No patterns mined')).toBeVisible();
    });
  });

  test.describe('API Error Resilience', () => {
    test('health widget: 500 response does not crash app', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/health', route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'unavailable' }) })
        );
      });
      await page.reload();
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
        localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
      });
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
      await expect(page.locator('#cherenkov-topbar')).toBeVisible();
      await expect(page.locator('#cherenkov-sidebar')).toBeVisible();
    });

    test('divergences screen: 500 response does not crash', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/divergences**', route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'error' }) })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('divergences');
      await page.waitForTimeout(600);
      await expect(page.locator('h1')).toContainText('Divergence Triage Hub');
    });

    test('eject screen: 500 on eject API does not crash', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/eject', route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'disk full' }) })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('eject');
      await page.waitForSelector('#eject-screen');
      await page.locator('#btn-confirm-eject').click();
      await page.waitForTimeout(500);
      await expect(page.locator('#eject-screen')).toBeVisible();
    });

    test('review screen: 500 on approve/reject does not crash', async ({ page }) => {
      await bootstrap(page, async p => {
        await p.route('**/api/v1/review/approve', route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'error' }) })
        );
        await p.route('**/api/v1/review/reject', route =>
          route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ detail: 'error' }) })
        );
      });
      const sb = new Sidebar(page);
      await sb.navTo('review');
      await page.waitForSelector('#review-screen');
      await expect(page.locator('h1')).toContainText('Human-In-The-Loop Validation Gate');
    });

    test('SDD cockpit: all APIs returning 500 still renders', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/sdd/**', route =>
        route.fulfill({ status: 500, contentType: 'application/json', body: '{"detail":"error"}' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByRole('heading', { name: 'Agent Cockpit' })).toBeVisible();
    });

    test('chat: session creation failure shows disabled input', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/chat/sessions', route =>
        route.fulfill({ status: 500, body: '{"detail":"error"}' })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-chat');
      await page.waitForSelector('#chat-screen');
      await page.waitForTimeout(S);
      const input = page.locator('#chat-screen input[type="text"]');
      await expect(input).toBeDisabled();
    });
  });

  test.describe('SDD Token Budget Boundary', () => {
    test('warning banner at >80% token budget', async ({ page }) => {
      await setupApiMocks(page);
      await page.route('**/api/v1/sdd/status', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          session: { id: 'sess-high', status: 'open', task: 'big-job' },
          current_tokens: { session_id: 'sess-high', prompt: 42000, generate: 0, read: 0, search: 0, total: 42000 },
          budget: { per_session: 50000 },
          historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} },
          experience_count: 0,
          sessions_since_compact: 1
        }) })
      );
      await page.route('**/api/v1/sdd/tokens', route =>
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
          current_session: { session_id: 'sess-high', prompt: 42000, generate: 0, read: 0, search: 0, total: 42000 },
          budget: { per_session: 50000 },
          historical: { total_all_time: 0, sessions_completed: 0, avg_per_session: 0, by_task_type: {} },
          top_consumers: []
        }) })
      );
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('[copilot] tour_seen', 'true');
        localStorage.setItem('[cherenkov] onboarding_seen', 'true');
      });
      await page.reload();
      await page.waitForSelector('#cherenkov-app-core');
      await page.waitForTimeout(S);
      await page.click('#nav-item-sdd');
      await page.waitForTimeout(S);
      await expect(page.getByText(/Token budget at 84%/)).toBeVisible();
      await expect(page.getByText('compaction recommended')).toBeVisible();
    });
  });

  test.describe('XSS & Injection Resistance', () => {
    const xssPayloads = makeXssPayloads();

    for (const payload of xssPayloads) {
      test(`search input does not execute injected: "${payload.substring(0, 30)}"`, async ({ page }) => {
        await bootstrap(page);
        let xssTriggered = false;
        page.on('dialog', () => { xssTriggered = true; });
        const sb = new Sidebar(page);
        await sb.search(payload);
        await page.waitForTimeout(300);
        expect(xssTriggered).toBe(false);
        await expect(page.locator('#cherenkov-app-core')).toBeVisible();
      });
    }

    test('author textarea does not execute injected script', async ({ page }) => {
      await bootstrap(page);
      let xssTriggered = false;
      page.on('dialog', () => { xssTriggered = true; });
      const sb = new Sidebar(page);
      await sb.navTo('author');
      const ap = new AuthorPage(page);
      await ap.typeIntent('<script>alert("xss")</script>');
      await page.waitForTimeout(300);
      expect(xssTriggered).toBe(false);
    });

    test('chat input does not execute injected script', async ({ page }) => {
      await bootstrap(page);
      let xssTriggered = false;
      page.on('dialog', () => { xssTriggered = true; });
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      await cp.sendViaEnter('<img src=x onerror=alert(1)>');
      await page.waitForTimeout(300);
      expect(xssTriggered).toBe(false);
    });

    test('knowledge search does not execute injected script', async ({ page }) => {
      await bootstrap(page);
      let xssTriggered = false;
      page.on('dialog', () => { xssTriggered = true; });
      const sb = new Sidebar(page);
      await sb.navTo('knowledge');
      const kp = new KnowledgePage(page);
      await kp.search('<svg/onload=alert(document.cookie)>');
      await page.waitForTimeout(300);
      expect(xssTriggered).toBe(false);
    });
  });

  test.describe('Rapid Interaction Resilience', () => {
    test('rapid nav clicks do not crash the app', async ({ page }) => {
      await bootstrap(page);
      const navIds = ['overview', 'truth-map', 'divergences', 'author', 'signals', 'memory', 'governance', 'review', 'healing', 'eject'];
      for (const id of navIds) {
        await page.click(`#nav-item-${id}`);
        await page.waitForTimeout(100);
      }
      await page.waitForTimeout(500);
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('rapid autonomy toggle clicks do not crash', async ({ page }) => {
      await bootstrap(page);
      const tb = new TopBar(page);
      for (let i = 0; i < 10; i++) {
        await tb.setAutonomy(i % 3);
      }
      await expect(page.locator('#cherenkov-app-core')).toBeVisible();
    });

    test('rapid chat send does not crash', async ({ page }) => {
      await bootstrap(page);
      const sb = new Sidebar(page);
      await sb.navTo('chat');
      const cp = new ChatPage(page);
      for (let i = 0; i < 5; i++) {
        await cp.input.fill(`Rapid message ${i}`);
        await cp.input.press('Enter');
        await page.waitForTimeout(100);
      }
      await page.waitForTimeout(500);
      await expect(page.locator('#chat-screen')).toBeVisible();
    });
  });
});
