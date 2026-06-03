# CHERENKOV — Frontend Redesign: Workflows, UX & Agent Build Prompts

**Targets:** `track-b-c-deferred/dashboard/` (React 18 + Vite + Tailwind v4 + lucide-react, mock-first `lib/api.ts`).
**Purpose:** realign the FE from the old *generator* flow (Projects→Pipeline→Review→Heal→Eject) to the **Reality-Engine master plan** ([`../vision/07_MASTER_PLAN.md`](../vision/07_MASTER_PLAN.md)) — truth → divergence → author/learn — while **keeping one consistent design system**, easy navigation, and a manual-QA-first experience.
**How to use:** §1–§6 are the design of record. **§7 is the agent backlog** — self-contained prompts you hand to coding agents in order. Every prompt inherits the **Consistency Contract (FE-0)**.

> Status note: the dashboard currently lives under `track-b-c-deferred/`. **Pre-req (FE-0):** relocate/activate it to `dashboard/` (or wire it into the build) before the screen work, OR keep the path and just build in place. Pick one and keep it consistent.

---

## 1. Design goals (what "good" means here)

1. **Land on value, not a list.** First screen answers *"is my system lying to itself, and am I safe to ship?"* — not "pick a project."
2. **Manual-QA-first.** A non-coder can author and run a real test by typing intent. No selectors, no YAML.
3. **One consistent system.** Every screen reuses the same shell, tokens, card, pill, empty-state, and motion language. Zero bespoke styling.
4. **Easy to reach.** ⌘K command palette + always-present primary action + grouped, labeled nav (≤6 groups).
5. **Trust is visible.** Every finding/test shows provenance, evidence, and "why" inline — autonomy you can audit.
6. **Accessible & calm.** WCAG AA contrast, full keyboard nav, `prefers-reduced-motion` honored (the theme is glow-heavy).

---

## 2. Current-state audit (what exists — reuse, don't rebuild)

**Design system (keep verbatim):** Tailwind v4 `@theme` in `src/index.css`:
`--color-bg-base #020617`, `--color-glow-blue/#22d3ee`, `--color-success #10b981`, `--color-warning #f59e0b`, `--color-danger #ef4444`; fonts Inter / Poppins (display) / JetBrains Mono; utility classes `.cherenkov-panel`, `.cherenkov-card`, `.cherenkov-glow`, `.glow-text`, `.grid-bg`, `.dashed-glow`; animations `glow-pulse`, `beam-flow`, `pulse-slow`.
**Shell (keep):** `Sidebar` (280px, grouped nav + budget meter + Live/Idle) + `TopBar` (project, status, cost) + `<main>` `activeTab` switch in `App.tsx`.
**Screens that survive (reframe, don't delete):** `SetupScreen` (→ New-Run wizard), `ReviewScreen` (→ HITL that feeds Reflector), `HealingScreen`, `EjectScreen`, `SettingsScreen`, `ProjectsScreen` (→ demoted to a switcher), `PipelineScreen` (→ demoted to a live-run drawer).
**Data layer (keep pattern):** `types.ts` + `mockData.ts` + `lib/api.ts` with graceful mock fallback (`runPipeline` already try/catch-falls back). **All new screens build mock-first.**

**The IA gap:** there is no surface for the product's actual deliverables — Truth Map, **Divergences**, intent authoring, perf/visual/coverage signals, **memory/pairing**, governance. That's the redesign.

---

## 3. Revised information architecture (the new navigation)

Grouped sidebar, section labels, ≤6 groups. ★ = new screen. Old names in (parens).

```
◇ OVERVIEW ★                     ← landing: release-readiness + critical divergences + recent learning

ENGINE
  ⊹ Truth Map ★                  ← the claim graph (what the system claims, w/ provenance)
  ⚡ Divergences ★  (the star)    ← confirmed "system lying to itself" findings
  🔍 Explore ★                   ← autonomous "second pair of eyes" run

AUTHOR
  ✦ Author by Intent ★           ← manual-QA: plain-English → live-executed test
  ☑ Review Queue (ReviewScreen)  ← HITL approve/reject → feeds Reflector

SIGNALS
  📈 Signals ★                   ← one screen, tabs: Performance · Visual · Coverage

OPERATE
  ✨ Healing (HealingScreen)
  ⬇ Eject (EjectScreen)
  🛡 Governance ★                 ← KPIs, model certification, traceability

LEARN
  🧠 Memory & Pairing ★          ← Reflector idioms + junior↔senior Mentor

─ pinned bottom ─
  Projects (switcher)  ·  Settings  ·  Live/Idle + budget meter
```

**Reachability layer (global, above nav):**
- **⌘K Command Palette** — jump to any screen, start a run, open a divergence, "author a test…", switch project.
- **Primary action** — `New Run` button (always visible, top of sidebar) opens the Setup wizard.
- **Live-run drawer** — clicking the TopBar `LIVE` status slides in the old `PipelineScreen` DAG as a drawer (contextual, not a nav tab).

**Autonomy ladder control (TopBar segmented control):** `Assisted · Augmented · Agentic` — sets how much the engine does unattended; persisted to `[copilot] autonomy`. Manual QAs start on **Assisted**.

---

## 4. Global UX patterns (apply on every screen)

| Pattern | Rule |
|---|---|
| **Page shell** | Every screen = `PageHeader` (title, 1-line purpose, primary action, optional tabs) + scrollable body in `.cherenkov-card` panels. No screen invents its own frame. |
| **Empty states** | Icon + one sentence + **one primary CTA** + a "Try the Petstore demo" secondary. Never a blank panel. |
| **Loading** | Skeleton shimmer (reuse glow tokens), never spinners-only; optimistic updates for approve/reject. |
| **Async feedback** | Toasts for every backend action (success/danger tokens); inline error with retry. |
| **Severity system** | `critical→danger`, `high→#fb923c`, `medium→warning`, `low→glow-blue`, `info→text-muted`. One `SeverityPill`. Used by Divergences, Signals, Governance — identical everywhere. |
| **Status system** | `reproduced→success`, `pending→warning`, `rejected→text-muted`, `live→glow pulse`. One `StatusDot`. |
| **Provenance/evidence** | Any claim/finding/test exposes `[spec|code|traffic|db]` provenance chips + an "evidence" disclosure (request/response diff, screenshot). |
| **Keyboard** | ⌘K palette; `j/k` to move in lists; `Enter` opens; `a`/`r` approve/reject in Review; visible focus rings (glow-blue). |
| **A11y** | WCAG AA contrast (verify cyan-on-dark for text ≥ 4.5:1 — use `text-primary`, reserve glow for accents/borders, not body text); ARIA roles on nav/lists/dialogs; `prefers-reduced-motion` disables `glow-pulse`/`beam-flow`/`pulse-slow`. |
| **Responsive** | `< lg`: sidebar collapses to icon rail with tooltips; panels stack single-column. |
| **Density** | Comfortable default; a compact toggle in Settings for power users (senior SDETs). |
| **Onboarding** | First run: a 3-step coachmark tour ending at "your first reproduced divergence" (mirrors the product's <10-min promise). |

---

## 5. Screen workflows (purpose · who · flow · states)

**Overview ★** — *Who: lead/anyone.* Three cards: **Release Readiness** (KPI ring: open critical divergences, false-positive rate), **Top Divergences** (3 worst, click → Divergences), **Recent Learning** (what the Reflector just learned — "stopped re-surfacing 4 known-noise findings"). Empty → "Run your first map" CTA.

**Truth Map ★** — *Who: SDET/lead.* Left: endpoint list (method+path). Right: selected endpoint's **claims** grouped by provenance `[spec|code|traffic|db]`. Highlights endpoints that have a divergence. CTA: "Hunt divergences here."

**Divergences ★ (the star)** — *Who: everyone.* Filterable list (by D1–D5 class, severity, status). Row = severity pill + one-line claim-vs-claim + provenance chips. Detail drawer: **Claim A vs Claim B**, **evidence** (real request/response diff or screenshot), **repro steps**, severity, and actions: `Close with test` (→ emitter), `Mark intended`, `Reject` (→ Reflector). This is the money screen — make it skimmable and trustworthy.

**Explore ★** — *Who: manual QA.* "Point me at your app" → autonomous crawl → results as a **"second pair of eyes" digest**: anomalies, 5xx, JS errors, visual breaks, each promotable to a divergence or an authored test. Live progress uses `beam-flow`.

**Author by Intent ★ (the manual-QA heart)** — *Who: non-coder QA.* Big plain-English input ("check a guest can checkout with a discount code and that the email arrives"), example chips, **Mentor idioms surface contextually** ("seniors on this service also check tenant isolation"). Run → **live Pilot execution preview** (vision) → result with evidence → `Save & Eject` to a real Playwright file. Never shows a selector. Autonomy = Assisted by default (human confirms each step).

**Review Queue (upgrade ReviewScreen)** — HITL approve/reject/edit, now: every decision writes a **verdict to the Reflector** with an optional reason; show "this teaches CHERENKOV" microcopy so users feel the compounding value.

**Signals ★** — tabs: **Performance** (latency history + ML anomaly confidence band, TTFT/cost for AI endpoints), **Visual** (baseline vs current, semantic diff), **Coverage** (SDET coverage + which paths got new tests). Shared chart components; severity system for regressions.

**Memory & Pairing ★** — *Who: junior + lead.* Two panes: **Idioms** (the team's accumulated senior checks, with confirm-count + decay), and **Pairing** — a junior view where Mentor explains *why* a senior would check X here. Surfaces the compounding moat as a human-facing feature.

**Governance ★** — KPI dashboard (defect-escape, false-positive, coverage-accuracy, maintenance-efficiency trends), **Model Certification** status per tier (Gold-Set pass/fail), and a **traceability** explorer (artifact → prompt+model+claims+evidence). Compliance-export button.

**Healing / Eject / Settings** — keep; restyle to the shared shell. Settings gains: substrate **tiers** (small/deep/vision/ml), **egress** dial (none/internal/any), **budgets**, **autonomy** default, density toggle, reduced-motion override.

---

## 6. Consistency contract (the rules every agent obeys — referenced by all prompts)

1. **Tokens only.** Use `@theme` CSS vars / Tailwind classes (`bg-bg-base`, `text-text-primary`, `text-text-muted`, `glow-blue`, `success/warning/danger-custom`). No raw hex except inside the existing `index.css`.
2. **Primitives only.** Build/great-reuse shared components (FE-0): `PageHeader`, `Panel` (`.cherenkov-panel`), `Card` (`.cherenkov-card`), `SeverityPill`, `StatusDot`, `ProvenanceChip`, `EmptyState`, `Skeleton`, `Toast`, `CommandPalette`, `Drawer`, `Tabs`, `KpiRing`. No screen restyles these.
3. **Icons:** lucide-react only; one icon per nav item; 16–20px.
4. **Motion:** reuse `glow-pulse/beam-flow/pulse-slow`; all wrapped so `prefers-reduced-motion: reduce` disables them.
5. **Data:** mock-first. New endpoints → add typed stub in `lib/api.ts` that try/catches and falls back to `mockData.ts` (match existing `runPipeline` pattern). Never block UI on a missing backend.
6. **Naming:** screens are `XxxScreen.tsx` in `src/components/`; shared primitives in `src/components/ui/`; types in `types.ts`; nav id == `activeTab` key.
7. **A11y/contrast:** body text never relies on glow color; every interactive element keyboard-reachable with a visible focus ring.
8. **Definition of done per screen:** loads with mock data, has empty + loading + error states, is keyboard navigable, matches the shell, passes `npm run build` and lint.

---

## 7. Agent build backlog — copy-paste prompts (run in order)

> Each prompt is self-contained. Prepend this line to every one you dispatch:
> *"Work in `track-b-c-deferred/dashboard/`. Obey the Consistency Contract in `docs/dashboard/FE_REDESIGN.md` §6. Build mock-first. Keep `npm run build` green. Do not restyle shared primitives."*

### FE-0 — Foundation: shared UI primitives + consistency kit
**Goal:** create the reusable kit every screen depends on, so consistency is structural.
**Create:** `src/components/ui/{PageHeader,Panel,Card,SeverityPill,StatusDot,ProvenanceChip,EmptyState,Skeleton,Toast,Tabs,Drawer,KpiRing}.tsx` and `src/components/ui/index.ts` barrel.
**Build:** each primitive uses only `@theme` tokens; `SeverityPill` maps `critical|high|medium|low|info` → the §4 color system; `StatusDot` maps `reproduced|pending|rejected|live`; `ProvenanceChip` renders `spec|code|traffic|db` with distinct subtle tints; all motion wrapped in a `useReducedMotion` guard (add `src/lib/useReducedMotion.ts`).
**Also:** add a `ToastProvider` and mount in `App.tsx`.
**Acceptance:** a `/ui-kit` dev story (or a temporary tab) renders every primitive in every state; reduced-motion verified; build green.
**Out of scope:** screens, nav.

### FE-1 — Information architecture & navigation refactor
**Goal:** implement the §3 grouped nav + reachability layer without breaking existing screens.
**Modify:** `Sidebar.tsx` (grouped sections with labels: OVERVIEW/ENGINE/AUTHOR/SIGNALS/OPERATE/LEARN + pinned Projects/Settings; collapsible to icon-rail `< lg`). `App.tsx` (extend `activeTab` union to new ids: `overview, truth-map, divergences, explore, author, review, signals, healing, eject, governance, memory, settings`; render placeholders for not-yet-built screens using `EmptyState` "Coming in this milestone"). `TopBar.tsx` (add **autonomy segmented control** + clickable `LIVE` status that opens a `Drawer` hosting the existing `PipelineScreen`).
**Create:** `src/components/CommandPalette.tsx` (⌘K / Ctrl-K, fuzzy nav + actions: "New run", "Author a test", "Open divergences", "Switch project"); mount globally.
**Acceptance:** every nav id routes; ⌘K works; Live drawer shows the DAG; nothing previously working is lost; keyboard + reduced-motion ok.

### FE-2 — Overview (landing) screen
**Create:** `src/components/OverviewScreen.tsx`. Three `Card`s: **Release Readiness** (`KpiRing` of open critical divergences + false-positive rate), **Top Divergences** (3 worst rows → deep-link to Divergences), **Recent Learning** (Reflector activity feed). Empty state → "Run your first map". Add `overviewMock` to `mockData.ts` + typed `fetchOverview()` stub.
**Acceptance:** default landing tab; all three cards populate from mock; CTAs deep-link.

### FE-3 — Truth Map screen
**Create:** `TruthMapScreen.tsx` — master/detail: endpoint list (badge endpoints with divergences) ↔ claims grouped by `ProvenanceChip`. CTA "Hunt divergences here" → Divergences filtered to that endpoint. Add `truthModelMock` + `fetchTruthModel()`.
**Acceptance:** selecting an endpoint shows its claims with provenance; divergence badges visible; empty state present.

### FE-4 — Divergences screen (priority — the star)
**Create:** `DivergencesScreen.tsx` — filter bar (D1–D5, severity, status), virtualized list of `SeverityPill` rows (claim-A vs claim-B one-liner + provenance chips + `StatusDot`), and a `Drawer` detail: Claim A vs B, **evidence** (req/resp diff or screenshot), repro steps, actions `Close with test` / `Mark intended` / `Reject (→ teaches Reflector)`. Add rich `divergencesMock` (cover all 5 classes + severities) + `fetchDivergences()`/`actOnDivergence()`.
**Acceptance:** filterable, skimmable, drawer shows evidence + provenance; actions toast + optimistic update; keyboard `j/k/Enter`.

### FE-5 — Author by Intent (manual-QA Copilot) + Mentor idioms
**Create:** `AuthorScreen.tsx` — large plain-English intent input + example chips; contextual **Mentor idiom** suggestions panel; "Run" → stepped **live Pilot preview** (use `beam-flow`), each step human-confirmable on Assisted; result card with evidence + `Save & Eject`. **No selector ever shown.** Add `mentorIdiomsMock`, `authorRunMock`, `submitIntent()` stub.
**Acceptance:** a non-coder flow: type intent → see steps → get a passing test → eject; idioms surface; fully keyboard-usable; empty state teaches with 2 example intents.

### FE-6 — Review Queue upgrade (feeds Reflector)
**Modify:** `ReviewScreen.tsx` — keep approve/reject/edit; add a **reason capture** on reject and "this teaches CHERENKOV" microcopy; emit verdicts via `recordVerdict()` stub; show a small "X idioms learned this session" counter.
**Acceptance:** decisions persist to mock verdict store; counter increments; a/r keyboard shortcuts.

### FE-7 — Signals (Performance / Visual / Coverage)
**Create:** `SignalsScreen.tsx` with `Tabs`. **Performance:** latency series + ML anomaly confidence band + TTFT/cost for AI endpoints. **Visual:** baseline vs current with semantic-diff callouts. **Coverage:** coverage % + newly-covered paths. Shared lightweight chart component `ui/Chart.tsx` (no heavy dep unless already present — check `package.json` first). Add `signalsMock`.
**Acceptance:** three tabs render from mock; regressions use the severity system; anomaly band visible; reduced-motion ok.

### FE-8 — Memory & Pairing
**Create:** `MemoryScreen.tsx` — **Idioms** list (text, confirm-count, decay, source endpoints) + **Pairing** pane (junior view: Mentor's "why a senior checks this here"). Add `idiomsMock`, `pairingMock`.
**Acceptance:** idioms sortable by confidence; pairing pane explains rationale; empty state for new projects.

### FE-9 — Governance
**Create:** `GovernanceScreen.tsx` — KPI trend cards (defect-escape, false-positive, coverage-accuracy, maintenance-efficiency), **Model Certification** table (per tier: Gold-Set pass/fail, faithfulness score), **Traceability** explorer (artifact → prompt+model+claims+evidence). Compliance-export button (mock download). Add `governanceMock`.
**Acceptance:** KPIs trend from mock; cert table shows pass/fail with the status system; traceability drill-down works.

### FE-10 — Settings + global polish + a11y/onboarding pass
**Modify:** `SettingsScreen.tsx` — substrate **tiers** (small/deep/vision/ml), **egress** dial, **budgets**, **autonomy** default, **density** + **reduced-motion** toggles (persist to localStorage; reflect the real `cherenkov.toml` shape).
**Global pass:** verify WCAG AA contrast on all text; ensure every screen has empty/loading/error; finalize the 3-step onboarding coachmark ("first reproduced divergence"); audit `prefers-reduced-motion`; responsive `< lg` icon-rail; run lint + `npm run build`.
**Acceptance:** settings map to config keys; contrast/keyboard/motion audited; onboarding fires once; build + lint green.

---

## 8. Sequencing & evaluation

**Order:** FE-0 → FE-1 (unblocks everything) → **FE-4 Divergences** (the star, do early to prove value) → FE-2 Overview → FE-5 Author (manual-QA heart) → FE-3 Truth Map → FE-6 Review → FE-7 Signals → FE-8 Memory → FE-9 Governance → FE-10 polish.

**Why this is the right FE:** it (a) reuses the entire existing design system and shell — *consistency by construction*; (b) reorganizes IA around the product's real deliverables so users land on value; (c) makes the manual-QA the protagonist (Author by Intent, Explore, plain-English everywhere); (d) keeps everything reachable (grouped nav + ⌘K + persistent primary action); (e) bakes trust in (provenance/evidence on every finding) and accessibility in (contrast, keyboard, reduced-motion).

**Top risks (FE):** glow-heavy theme can fail AA contrast on body text → rule: glow for accents/borders only. Scope is 11 screens → ship behind the existing `activeTab` placeholders so nav is whole even while screens land incrementally. New screens depend on backend that doesn't exist yet → mock-first contract makes every screen demoable today and live later by swapping the `lib/api.ts` stub.
