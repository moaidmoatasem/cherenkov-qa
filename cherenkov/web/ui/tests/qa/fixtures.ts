import { test as base, expect, Page } from '@playwright/test';
import { bootstrap, Sidebar, TopBar, ProjectsPage, SetupPage, PipelinePage, ReviewPage, HealingPage, EjectPage, OverviewPage, TruthMapPage, DivergencesPage, AuthorPage, SignalsPage, MemoryPage, GovernancePage, ChatPage, KnowledgePage, DevicesPage, SettingsPage, SddPage, MobilePage, CommandPalette } from './page-objects';
import { setupApiMocks } from '../api_mocks';

type QaFixtures = {
  sidebar: Sidebar;
  topbar: TopBar;
  projectsPage: ProjectsPage;
  setupPage: SetupPage;
  pipelinePage: PipelinePage;
  reviewPage: ReviewPage;
  healingPage: HealingPage;
  ejectPage: EjectPage;
  overviewPage: OverviewPage;
  truthMapPage: TruthMapPage;
  divergencesPage: DivergencesPage;
  authorPage: AuthorPage;
  signalsPage: SignalsPage;
  memoryPage: MemoryPage;
  governancePage: GovernancePage;
  chatPage: ChatPage;
  knowledgePage: KnowledgePage;
  devicesPage: DevicesPage;
  settingsPage: SettingsPage;
  sddPage: SddPage;
  mobilePage: MobilePage;
  commandPalette: CommandPalette;
  bootstrappedPage: Page;
};

export const test = base.extend<QaFixtures>({
  sidebar: async ({ page }, use) => { await use(new Sidebar(page)); },
  topbar: async ({ page }, use) => { await use(new TopBar(page)); },
  projectsPage: async ({ page }, use) => { await use(new ProjectsPage(page)); },
  setupPage: async ({ page }, use) => { await use(new SetupPage(page)); },
  pipelinePage: async ({ page }, use) => { await use(new PipelinePage(page)); },
  reviewPage: async ({ page }, use) => { await use(new ReviewPage(page)); },
  healingPage: async ({ page }, use) => { await use(new HealingPage(page)); },
  ejectPage: async ({ page }, use) => { await use(new EjectPage(page)); },
  overviewPage: async ({ page }, use) => { await use(new OverviewPage(page)); },
  truthMapPage: async ({ page }, use) => { await use(new TruthMapPage(page)); },
  divergencesPage: async ({ page }, use) => { await use(new DivergencesPage(page)); },
  authorPage: async ({ page }, use) => { await use(new AuthorPage(page)); },
  signalsPage: async ({ page }, use) => { await use(new SignalsPage(page)); },
  memoryPage: async ({ page }, use) => { await use(new MemoryPage(page)); },
  governancePage: async ({ page }, use) => { await use(new GovernancePage(page)); },
  chatPage: async ({ page }, use) => { await use(new ChatPage(page)); },
  knowledgePage: async ({ page }, use) => { await use(new KnowledgePage(page)); },
  devicesPage: async ({ page }, use) => { await use(new DevicesPage(page)); },
  settingsPage: async ({ page }, use) => { await use(new SettingsPage(page)); },
  sddPage: async ({ page }, use) => { await use(new SddPage(page)); },
  mobilePage: async ({ page }, use) => { await use(new MobilePage(page)); },
  commandPalette: async ({ page }, use) => { await use(new CommandPalette(page)); },
  bootstrappedPage: async ({ page }, use) => {
    await bootstrap(page);
    await use(page);
  },
});

export { expect };
