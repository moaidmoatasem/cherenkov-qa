# FE/Dashboard — User Journey, Tabs, Screens, Routes
## Detailed Recommendations & Enhancements Report (additive-only)

### 0. Executive Summary
The supported dashboard is **structurally complete** with 19 screens, providing a solid grouped information architecture, command palette, live drawer, autonomy ladder, health checking, and offline support. The engine half is functional (ingest → generate → review → eject). However, the observability half currently acts more as a presentation layer and contains several "honesty" defects where UI states diverge from true backend states. 

The recommendations in this report outline **additive-only, non-breaking enhancements** that fix silent failures (honoring the D7 rule), improve the routing architecture, introduce crucial missing views, and polish the user journey (navigation, a11y, and motion).

### 1. Defects & Honesty Issues (MUST — high-impact, low-risk)
These issues violate the D7 design invariants or present misleading states. Fixing them is non-breaking and crucial for trustworthiness:
- **D-1** `ReviewScreen` setState-in-render (correctness): Fix `ReviewScreen.tsx` L60/L136 by moving parent updates into `useEffect` or event handlers.
- **D-2** `EjectScreen` reports success on backend failure: Surface the `ejectError` properly so the UI mirrors the true backend state.
- **D-3** `actOnDivergence` swallows backend errors: This optimistic UI pattern results in lies. Add rollback and toast notifications on failure.
- **D-4** `AuthorScreen` "INITIALIZE PILOT RUN" is a mock replay: Wire this to `runPipeline()` (as used in `SetupScreen`) to back the flagship feature with real execution.
- **D-5** `HealingScreen` "APPLY HEALING SUGGESTION" is a no-op: Wire to the `validateSuite()` stub.
- **D-6** TopBar telemetry fiction: Either back with `/cost` and `/metrics` or label it clearly as "**Demo telemetry**".
- **D-7** `SetupScreen` raw 400 logs: Demote `console.error` to `console.debug` and rely on the `SetupScreen` toast path.
- **D-8** `Status` hardcoded "PORT 3000": Read from `import.meta.env.VITE_PORT` or remove it from `Sidebar.tsx`.
- **D-9** `OfflineOverlay` retry path: Ensure `refresh` from `useHealth` genuinely re-runs `fetchHealth` and updates the "last checked at" timestamp.
- **D-10** TopBar `Notifications` popover fake text: Wire to a `/notifications` endpoint, or remove the bell entirely to maintain D7 honesty.

### 2. Navigation / IA Enhancements (Additive)
- **N-1 Breadcrumbs:** Implement a deep-linkable `Breadcrumbs` primitive below the TopBar.
- **N-2 Section landing links on Overview:** Quick links to "Resume run", "Open recent divergence", etc.
- **N-3 Deep-linking:** Add query parameters `?divergence=div_123` & `?run=run_xyz` to automatically open contextual drawers on load.
- **N-4 Recent items in ⌘K:** Extend `CommandPalette.tsx` with last visited routes from `localStorage`.
- **N-5 Pinned items in Sidebar:** Introduce a "Pinned" row for quick access (mirroring favorites pattern for projects).
- **N-6 Keyboard Map Overlay (`?`):** Implement a modal showing all keyboard shortcuts (e.g., `Cmd+K`, `j/k`, `g d`).
- **N-7 Sidebar default state & Routing Metadata:** Make the `ENGINE` section collapsed by default on small viewports and persist state. Enhance `routes.tsx` with a rich metadata object (paths, labels, icons) instead of a simple key-value map.
- **N-8 Workspace switcher honesty:** Clarify the cosmetic nature of the project dropdown or back it with isolated state slices in the global store.

### 3. Journey-Specific Enhancements
#### J1: Author by Intent (Manual-QA)
- **Live Preview:** Show live skeleton rows during the planning phase before pilot execution.
- **Vision Fallback Banner:** Click-to-pick alternative candidates when elements aren't confidently located.
- **Evidence Disclosure:** Show inline request/response + screenshots after execution.
- **Reflector Learning:** Show an "idiom learned" chip post-eject.

#### J2: Triage Divergence (Lead Path)
- **Virtualization:** Apply `react-window` for scaling to 500+ findings in the list.
- **Confidence Indicator:** Badge showing reproduction stability (e.g., "reproduced 4/5 runs").
- **Diff Visualization:** Add a side-by-side claim-vs-claim visual diff with lazy loading for heavy evidence payload.

#### J3: Pairing & Memory
- **Action CTA:** Inline "Author this check" button pre-filling the Author screen intent.
- **Memory Hotkey:** `g + m` to jump to memory.
- **Decay Visualization:** Faded opacity for decaying/older idioms.

### 4. Per-Screen Architectural Enhancements
- **App/Routing:** Transition from flat conditional rendering in `<main>` to standard `react-router-dom` `<Routes>` with `React.lazy()` for code splitting.
- **Explore Screen:** Replace inline placeholder with a real `ExploreScreen.tsx` wizard targeting URL/scope configurations.
- **Governance:** Add SVG-based KPI trend charts and detailed Model Certification pass/fail statuses. Add an artifact traceability drill-down.
- **Signals:** Integrate ML anomaly confidence bands on Performance charts, semantic diff callouts on Visual, and apply a severity pill system.
- **Settings:** Extend settings with tier descriptions, autonomy defaults (persisted to global store), and "Reset to defaults" action.

### 5. New Additive Routes
These routes expand capabilities safely without altering existing paths:
- `/runs/:runId` — Detailed run metadata, stage DAG, and verdict history.
- `/divergences/:divId` — Deep-linkable divergence detail view complementing the drawer.
- `/explore/:runId` — Live explore digests.
- `/settings/:section` — Direct linking to substrate, egress, budgets, or a11y settings.
- `/diff/:artifactId` — Provenance/traceability viewer backing the Governance traceability CTA.

### 6. Global UX, Motion, A11y, Density
- **Density Toggle:** Add Comfortable / Compact mode toggles, controlled globally and persisted.
- **Reduced-Motion Override:** Support an explicit override alongside system `prefers-reduced-motion` settings.
- **Progressive Loading & Streaming:** Ensure perceived speed (FMP < 1s) and stream step rows as they execute rather than waiting for full completion.
- **Offline & Cost UX:** Deploy an amber offline banner, handle inference timeouts gracefully, and implement explicit blast-radius cost confirmations before expensive generative tasks.
- **WCAG AA Compliance:** Ensure contrast minimums (cyan-on-dark), rigorous focus management inside modals/drawers, and accurate heading hierarchies across the app.
