---
last_updated: 2026-06-07
source: cherenkov/web/ui/src/components/, cherenkov/web/ui/tests/dashboard_e2e.spec.ts
scope: UI component inventory and state descriptions for the CHERENKOV dashboard web UI
---

# Dashboard States

## Screen Components (20)

| Component | Local State | Key Props | Purpose |
|-----------|------------|-----------|---------|
| `ProjectsScreen` | `searchTerm` | --- | Landing page: searchable project grid with sparklines, timer bars, pipeline status dots |
| `OverviewScreen` | `overview`, `divergences`, `isLoading`, `error` | --- | KPI ring gauge, top divergences, Reflector verdict feed |
| `SetupScreen` | `dragActive`, `specUrl`, `endpoints`, `serverUrl`, `doctorChecks`, `systemReady` | --- | OpenAPI spec ingestion with drag-drop/URL fetch, richness analysis, system readiness |
| `PipelineScreen` | `stages[]`, `isPaused`, `elapsedTime`, `tokensSpent`, `shownDrawerId`, `typedCode` | --- | Live DAG: Ingest -> Generate -> Review nodes, streaming code, telemetry |
| `ReviewScreen` | `tests[]`, `isLoading`, `activeFilter`, `selectedTestId`, `isEditing`, `editedCode` | --- | HITL gate: filter tabs, code editor, keyboard shortcuts j/k/a/e/r, rejection modal |
| `EjectScreen` | `outputPath`, `isEjected`, `copySuccess`, `expandedNodes{}` | --- | Two-stage export wizard: file tree -> output path -> eject -> copy command |
| `DivergencesScreen` | `divergences[]`, `selectedDiv`, `classFilter`, `severityFilter`, `searchQuery` | --- | Triage hub: filterable list, keyboard nav, drawer with evidence diff |
| `AuthorScreen` | `MOCK_MENTOR_IDIOMS[]`, `intent`, `isRunning`, `runResult`, `runError` | --- | NL test intent -> Playwright spec via pilot pipeline |
| `SignalsScreen` | `MOCK_SIGNALS[]`, `activeTab` | --- | Performance latency, visual snapshots, SDET coverage |
| `HealingScreen` | `failures[]`, `appliedIds[]`, `confirmingId`, `activeTraceLog` | --- | Drift cards with side-by-side diffs, apply/dismiss, trace modal |
| `SettingsScreen` | `model`, `tier`, `egress`, `budget`, `threadLimit`, `isSaving` | --- | Model provider, substrate tiers, egress policy, budget sliders |
| `GovernanceScreen` | `MOCK_GOVERNANCE` | --- | Defect escape rate, false positive rate, model cert tiers |
| `MemoryScreen` | `mem.idioms[]`, `mem.pairing[]` | --- | Senior testing idioms with confidence/decay, mentor pairing |
| `TruthMapScreen` | `selectedIdx`, `nodes[]` | --- | Endpoint claims graph with provenance verification |
| `ExploreScreen` | --- | --- | Inline crawler: "Configure Scope & Target" button |
| `UiKitScreen` | `isDrawerOpen`, `activeTab`, `isSkeletonLoading` | --- | Consistency gallery of all UI primitives |
| `Sidebar` | --- | section groups, project, token budget | Left nav shell: sections, project selector, status indicator |
| `TopBar` | --- | project, tab, autonomy level, session cost | Autonomy toggle (3 levels), node status (Live/Idle) |
| `CommandPalette` | `isOpen`, `search`, `selectedIndex` | --- | Ctrl+K modal: keyboard-navigable action search |
| `GuidedTour` | `currentStep` (0-3) | --- | Fixed-bottom 4-step onboarding overlay |

## UI Primitives (`components/ui/`, 15 files)

| Component | State Model | Variants |
|-----------|------------|----------|
| `Panel` | Props-driven | Glassmorphism container |
| `Card` | Props-driven | Default, hoverable (cyan glow) |
| `PageHeader` | Props-driven | Title + description + action + tabs |
| `KpiRing` | Props-driven | 0-100 SVG gauge, colors: blue/success/warning/danger |
| `SeverityPill` | Props-driven | Colors: critical(red)/high(orange)/medium(yellow)/low(cyan)/info(gray) |
| `StatusDot` | Props-driven | States: reproduced(green)/pending(yellow)/rejected(gray)/live(cyan,pulse) |
| `ProvenanceChip` | Props-driven | Sources: spec(blue)/code(purple)/traffic(emerald)/db(amber) |
| `Tabs` | Props-driven | Arrow key nav, optional count badges |
| `Drawer` | Controlled (`isOpen`) | Slide-in, ESC close, focus trap, backdrop blur |
| `Toast/ToastProvider` | Context queue (useState) | Auto-dismiss 4s, max 3 stacked, types: success/warning/danger/info |
| `Skeleton` | Props-driven | Variants: text/rect/circle/card/list |
| `EmptyState` | Props-driven | Icon + title + description + up to 2 actions |
| `MockBadge` | Stateless | Yellow warning badge: "MOCK DATA" |
| `OfflineOverlay` | Controlled (`checking`, `onRetry`) | Full-screen when backend unreachable |
| `CherenkovLogo` | Props-driven | Variants: icon(full hexagon)/full(hexagon+logotype)/wireframe(isometric) |

## E2E Test Coverage (`dashboard_e2e.spec.ts`, 436 lines, 20 test cases)

| Screen | Tests |
|--------|-------|
| Projects | Cards display, search filtering, timer bar rendering, New Run button |
| Setup | Drag-drop area, URL input, spec parsing, doctor checks |
| Pipeline | Stage nodes, pause/resume, code streaming |
| Review | Filter tabs, approve/reject flow, code editor, reject modal |
| Eject | File tree, output path, eject action, copy command |
| Overview | KPI ring, divergences list, memory feed |
| Divergences | Filter controls, drawer detail, severity colors |
| Signals | Tab switching (performance/visual/coverage) |
| Governance | KPI metrics display |
| Memory | Idioms list, confidence/decay indicators |
| Healing | Drift cards, apply/dismiss, trace modal |
| Author | NL textarea, example chips, run output |
| Truth Map | Endpoint list, claim panel |
| UI Kit | Drawer open/close, tab switch, skeleton loading state |
| Settings | Form interactions, save flow |
| Sidebar | Nav item clicks, project switcher |
| Command Palette | Open/close, keyboard navigation |
| Guided Tour | Step progression, exit on finish |
| Top Bar | Autonomy toggle, help button |
| OfflineOverlay | Mock API failure triggers overlay |

---

*Cross-ref: [endpoints.md](endpoints.md) for backend API endpoints consumed by these screens*
