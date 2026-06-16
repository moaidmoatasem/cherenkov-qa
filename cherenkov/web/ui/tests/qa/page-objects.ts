import { Page, Locator, expect } from '@playwright/test';
import { setupApiMocks } from '../api_mocks';

const SETTLE = 400;

export async function bootstrap(page: Page, overrides?: (page: Page) => Promise<void>) {
  page.on('pageerror', err => console.error(`[UNCAUGHT] ${err.message}`));
  await setupApiMocks(page);
  if (overrides) await overrides(page);
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('[copilot] tour_seen', 'true');
    localStorage.setItem('[cherenkov] onboarding_seen', 'true');
    localStorage.setItem('[cherenkov] sidebar_mode', 'expert');
  });
  await page.reload();
  await page.waitForSelector('#cherenkov-app-core');
  await page.waitForTimeout(SETTLE);
}

export class Sidebar {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#cherenkov-sidebar'); }
  async navTo(id: string) {
    await this.page.click(`#nav-item-${id}`);
    await this.page.waitForTimeout(SETTLE);
  }
  async newRun() { await this.page.click('#btn-sidebar-new-run'); await this.page.waitForTimeout(SETTLE); }
  get projectSelector() { return this.page.locator('#project-selector'); }
  get tokenPool() { return this.page.getByText('LLM Token Pool'); }
  get workspace() { return this.page.getByText('Active Workspace'); }
  async search(query: string) {
    await this.page.fill('#workspace-search-input', query);
    await this.page.waitForTimeout(200);
  }
  async clearSearch() {
    await this.page.fill('#workspace-search-input', '');
    await this.page.waitForTimeout(200);
  }
}

export class TopBar {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#cherenkov-topbar'); }
  get autonomyGroup() { return this.page.locator('[role="radiogroup"][aria-label="Autonomy Level Control"]'); }
  get autonomyButtons() { return this.autonomyGroup.locator('[role="radio"]'); }
  async setAutonomy(index: number) {
    await this.autonomyButtons.nth(index).click();
    await this.page.waitForTimeout(200);
  }
  get sessionCost() { return this.page.getByText('SESSION COST'); }
  get helpButton() { return this.page.locator('button[aria-label="Help Guide"]'); }
  get healthDevice() { return this.page.getByText('cpu').first(); }
  get healthModel() { return this.page.getByText('qwen2.5-coder:7b').first(); }
  async openPipelineDrawer() {
    await this.page.click('[title="Click to view live executing pipeline monitor"]');
    await this.page.waitForTimeout(300);
  }
}

export class ProjectsPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#projects-screen'); }
  get heading() { return this.page.locator('#projects-screen h1'); }
  card(id: string) { return this.page.locator(`#project-card-${id}`); }
  timerBar(id: string) { return this.page.locator(`#timer-bar-${id}`); }
  get newRunBtn() { return this.page.locator('#btn-projects-new-run'); }
  async assertCardVisible(id: string) { await expect(this.card(id)).toBeVisible(); }
  async assertCardHidden(id: string) { await expect(this.card(id)).not.toBeVisible(); }
}

export class SetupPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#setup-screen'); }
  get heading() { return this.page.locator('#setup-screen h1'); }
  get dragZone() { return this.page.getByText('Drag & Drop OpenAPI Spec'); }
  get urlInput() { return this.page.locator('#spec-url-input'); }
  get petstoreBtn() { return this.page.locator('#btn-shortcut-petstore'); }
  get checkoutBtn() { return this.page.locator('#btn-shortcut-checkout'); }
  get serverValidationToggle() { return this.page.locator('#btn-toggle-server-validation'); }
  get serverUrlInput() { return this.page.locator('#input-server-url'); }
  get authHeaderInput() { return this.page.locator('#input-auth-header'); }
  get launchBtn() { return this.page.locator('#btn-launch-generation'); }
  async loadPetstore() {
    await this.petstoreBtn.click();
    await this.page.waitForTimeout(500);
  }
  async toggleServerValidation() {
    await this.serverValidationToggle.click();
    await this.page.waitForTimeout(200);
  }
}

export class PipelinePage {
  constructor(private page: Page) {}
  get heading() { return this.page.getByText('Live Execution Pipeline Monitor'); }
  node(id: string) { return this.page.locator(`#pipeline-node-${id}`); }
  get pauseResumeBtn() { return this.page.locator('#pipeline-pause-resume-btn'); }
  get tokenBudget() { return this.page.getByText('TOKEN BUDGET'); }
  get promptAttention() { return this.page.getByText('PROMPT ATTENTION SPACE'); }
  async pause() {
    await this.pauseResumeBtn.click();
    await this.page.waitForTimeout(200);
  }
}

export class ReviewPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#review-screen'); }
  get heading() { return this.page.locator('#review-screen h1'); }
  filterTab(name: string) { return this.page.locator(`#filter-tab-${name}`); }
  get approveBtn() { return this.page.locator('[data-testid="review-approve-btn"]'); }
  get rejectBtn() { return this.page.locator('[data-testid="review-reject-btn"]'); }
  get explainBtn() { return this.page.locator('#review-screen button:has-text("Explain")'); }
}

export class HealingPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#healing-screen'); }
  get heading() { return this.page.locator('#healing-screen h1'); }
  get banner() { return this.page.locator('#healing-banner'); }
  card(id: string) { return this.page.locator(`#drift-card-${id}`); }
  diffViewer() { return this.page.locator('#read-only-diff-viewer'); }
  get diffCopyBtn() { return this.page.locator('#btn-diff-copy'); }
  get diffDownloadBtn() { return this.page.locator('#btn-diff-download'); }
  get diffDismissBtn() { return this.page.locator('#btn-diff-dismiss'); }
  async viewDiff(cardId: string) {
    await this.card(cardId).getByText('VIEW SUGGESTION DIFF').click();
    await this.page.waitForTimeout(300);
  }
  async dismissCard(cardId: string) {
    await this.card(cardId).getByText('Dismiss').click();
    await this.page.waitForTimeout(300);
  }
  async openTrace(cardId: string) {
    await this.card(cardId).getByText('OPEN EXPLAINER TRACE').click();
    await this.page.waitForTimeout(300);
  }
}

export class EjectPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#eject-screen'); }
  get heading() { return this.page.locator('#eject-screen h1'); }
  get pathInput() { return this.page.locator('#eject-path'); }
  get ejectBtn() { return this.page.locator('#btn-confirm-eject'); }
  get copyCmdBtn() { return this.page.locator('#btn-copy-command'); }
  async eject() {
    await this.ejectBtn.click();
    await this.page.waitForTimeout(300);
  }
}

export class OverviewPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#overview-screen'); }
  get heading() { return this.page.locator('#overview-screen h1'); }
  get kpiRing() { return this.page.locator('[role="progressbar"]').first(); }
  get pilotRunBtn() { return this.page.locator('#btn-pilot-run'); }
  get newAnalysisBtn() { return this.page.locator('button:has-text("New Analysis Run")').first(); }
}

export class TruthMapPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#truth-map-screen'); }
  get heading() { return this.page.locator('#truth-map-screen h1'); }
  async clickEndpoint(name: string) {
    await this.page.getByText(name).first().click();
    await this.page.waitForTimeout(300);
  }
  get claimsH3() { return this.page.locator('#truth-map-screen h3'); }
}

export class DivergencesPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#divergences-screen'); }
  get heading() { return this.page.locator('h1'); }
  get severitySelect() { return this.page.locator('select:has(option[value="critical"])'); }
  async filterBySeverity(value: string) {
    await this.severitySelect.selectOption(value);
    await this.page.waitForTimeout(200);
  }
  async clickRow() {
    await this.page.getByText('D-').first().click();
    await this.page.waitForTimeout(300);
  }
  get detailDrawer() { return this.page.getByText('Divergence Detail').first(); }
  get closeDetailBtn() { return this.page.locator('button[aria-label="Close details"]'); }
}

export class AuthorPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#author-screen'); }
  get heading() { return this.page.locator('#author-screen h1'); }
  get textarea() { return this.page.locator('#txt-author-intent'); }
  chip(text: string) { return this.page.getByText(text).first(); }
  get mentorPanel() { return this.page.getByText('Mentor Context Idioms'); }
  async typeIntent(text: string) {
    await this.textarea.fill(text);
    await this.page.waitForTimeout(200);
  }
  async clickChip(text: string) {
    await this.chip(text).click();
    await this.page.waitForTimeout(200);
  }
}

export class SignalsPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#signals-screen'); }
  get heading() { return this.page.locator('#signals-screen h1'); }
  tab(name: string) { return this.page.locator(`#signals-screen button:has-text("${name}")`); }
  async switchTab(name: string) {
    await this.tab(name).click();
    await this.page.waitForTimeout(200);
  }
}

export class MemoryPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#memory-screen'); }
  get heading() { return this.page.locator('#memory-screen h1'); }
  get idiomsPanel() { return this.page.getByText('Accumulated Senior Testing Idioms'); }
  get pairingPanel() { return this.page.getByText('Mentor Junior-Senior Pairing'); }
}

export class GovernancePage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#governance-screen'); }
  get heading() { return this.page.locator('#governance-screen h1'); }
  get defectEscapeRate() { return this.page.getByText('Defect Escape Rate'); }
  get modelCert() { return this.page.getByText('Model Capabilities Certification'); }
}

export class ChatPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#chat-screen'); }
  get heading() { return this.page.locator('#chat-screen h1'); }
  get input() { return this.page.locator('#chat-screen input[type="text"]'); }
  get sendBtn() { return this.page.locator('#chat-screen button').last(); }
  async send(text: string) {
    await this.input.fill(text);
    await this.sendBtn.click();
    await this.page.waitForTimeout(500);
  }
  async sendViaEnter(text: string) {
    await this.input.fill(text);
    await this.input.press('Enter');
    await this.page.waitForTimeout(500);
  }
  messageBubble(text: string) { return this.page.getByText(text); }
}

export class KnowledgePage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#knowledge-screen'); }
  get heading() { return this.page.locator('#knowledge-screen h1'); }
  get searchInput() { return this.page.locator('#knowledge-screen input[type="text"]'); }
  get submitBtn() { return this.page.locator('#knowledge-screen button[type="submit"]'); }
  async search(query: string) {
    await this.searchInput.fill(query);
    await this.submitBtn.click();
    await this.page.waitForTimeout(500);
  }
}

export class DevicesPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#devices-screen'); }
  get heading() { return this.page.locator('#devices-screen h1'); }
  get connectivity() { return this.page.getByText('Device Connectivity'); }
  get modelAvailability() { return this.page.getByText('Model Availability'); }
  get providerStatus() { return this.page.getByText('Provider Status').first(); }
}

export class SettingsPage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#settings-screen'); }
  get heading() { return this.page.locator('#settings-screen h1'); }
  get budgetSlider() { return this.page.locator('input[type="range"]').first(); }
  get threadsSlider() { return this.page.locator('#threads-range-slider'); }
  get compactCheckbox() { return this.page.locator('input[type="checkbox"]').first(); }
  get saveBtn() { return this.page.locator('#btn-settings-save'); }
  get apiKeyInput() { return this.page.locator('#input-settings-key'); }
  async open(page: Page) {
    await page.click('[title="Open Settings"]');
    await page.waitForSelector('#settings-screen', { timeout: 10000 });
    await page.waitForTimeout(SETTLE);
  }
}

export class SddPage {
  constructor(private page: Page) {}
  get heading() { return this.page.getByRole('heading', { name: 'Agent Cockpit' }); }
  get tokenBudgetCard() { return this.page.getByText('Token Budget', { exact: true }); }
  get sessionsCard() { return this.page.getByText('Sessions', { exact: true }); }
  get experienceCard() { return this.page.getByText('Experience Records'); }
  get sessionStateCard() { return this.page.getByText('Session State', { exact: true }); }
  get kpiRing() { return this.page.locator('[role="progressbar"]').first(); }
  get recentSessions() { return this.page.getByText('Recent Sessions'); }
  get tokenBreakdown() { return this.page.getByText('Current Session Tokens'); }
  get experiencePanel() { return this.page.getByText('Recent Experience'); }
  get patternsPanel() { return this.page.getByText('Patterns'); }
  get compactionPanel() { return this.page.getByText('Compaction'); }
  get byTaskTypePanel() { return this.page.getByText('By Task Type'); }
}

export class MobilePage {
  constructor(private page: Page) {}
  get el() { return this.page.locator('#mobile-screen'); }
  get heading() { return this.page.locator('#mobile-screen h1'); }
  deviceCard(id: string) { return this.page.getByTestId(`device-card-${id}`); }
  deviceStatus(id: string) { return this.page.getByTestId(`device-status-${id}`); }
}

export class CommandPalette {
  constructor(private page: Page) {}
  get input() { return this.page.locator('#command-palette-input'); }
  async open() {
    await this.page.keyboard.press('Control+KeyK');
    await this.page.waitForTimeout(200);
  }
  async close() { await this.page.keyboard.press('Escape'); }
  async search(query: string) {
    await this.input.fill(query);
    await this.page.waitForTimeout(200);
  }
}
