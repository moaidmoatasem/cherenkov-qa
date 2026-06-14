# CHERENKOV QA — Business Regression Suite (100% Screen Coverage)

**Version:** 1.0
**Date:** 2026-06-05
**Audience:** QA validation user (manual, business-level — no code knowledge required)
**System under test:** CHERENKOV "Forensic QA Protocol" dashboard — `cherenkov/web/ui` (canonical Track A UI)
**Backend:** FastAPI `cherenkov.py review --port 8000` · **Frontend:** Vite dev :3000 · **LLM:** Ollama `qwen2.5-coder:7b`

---

## 0. How To Use This Document

Each test case is written so a QA user can run it by **clicking the UI** and comparing what they see to the **Expected Result**. No code is required.

**Legend — integration status of each screen** (this determines what "pass" means):

| Tag | Meaning | Pass means |
|-----|---------|-----------|
| 🟢 **LIVE** | Screen calls the real backend API | Real data flows; backend state actually changes |
| 🟡 **HYBRID** | Calls backend *best-effort*, silently falls back to local state on failure | Screen behaves correctly; **note**: a backend failure is invisible to the user (known defect) |
| ⚪ **MOCK** | No backend call — renders built-in demo data | Screen renders and is interactive; data is **not** real |

**Result codes:** `PASS` / `FAIL` / `BLOCKED` / `N/A`. A regression run is **100% complete** only when every TC below has a recorded result.

**Standard preconditions (apply to all TCs unless overridden):**
- P1. Backend is running and `GET /api/v1/health` returns `{"status":"online"}`.
- P2. Frontend is reachable at `http://localhost:3000` and the page loads with no red console errors.
- P3. Browser is Chromium-based, viewport ≥ 1440×900, dark theme (the only supported theme).
- P4. Ollama is up with `qwen2.5-coder:7b` pulled (required for LIVE generation TCs only).

---

## 1. Screen Inventory & Integration Map

| # | Screen (Nav label) | Tag | Backend endpoints used |
|---|--------------------|-----|------------------------|
| 1 | Global Shell (Sidebar / TopBar / Command Palette) | 🟢/⚪ | `GET /health` (poll) |
| 2 | New Spec Run → **Setup** (Spec Ingest) | 🟢 LIVE | `POST /ingest` |
| 3 | **Pipeline** (Live-Run drawer) | 🟢 LIVE | `POST /run` |
| 4 | **Review Queue** (HITL) | 🟢 LIVE | `GET /review/queue`, `POST /review/approve|reject|edit` |
| 5 | **Divergences** (Triage Hub) | 🟢 LIVE | `GET /divergences`, `POST /divergences/act` |
| 6 | **Eject Suite** | 🟢 LIVE | `POST /eject` |
| 7 | **Healing Options** | 🟡 HYBRID | `POST /review/edit`, `POST /validate` (best-effort) |
| 8 | **Overview** (Release Readiness) | ⚪ MOCK | — |
| 9 | **Truth Map** (Claim Graph) | ⚪ MOCK | — |
| 10 | **Explore** (Crawler) | ⚪ MOCK | — |
| 11 | **Author by Intent** (Copilot) | ⚪ MOCK | — |
| 12 | **Signals** (Visual/Perf/Coverage) | ⚪ MOCK | — |
| 13 | **Governance** (KPI cert) | ⚪ MOCK | — |
| 14 | **Memory & Pairing** (Reflector) | ⚪ MOCK | — |
| 15 | **Projects** (workspace switcher) | ⚪ MOCK | — |
| 16 | **Settings** | ⚪ MOCK (localStorage) | — |
| 17 | **UI Kit Gallery** | ⚪ MOCK | — |

> **Material limitation for sign-off:** Of 17 surfaces, only **6 are LIVE** and **1 is HYBRID**. The flagship analytics screens (Overview, Truth Map, Signals, Governance, Memory) and Explore/Author are **MOCK**. A passing regression run proves the UI *functions*; it does **not** prove those screens reflect real engine output. Reviewers must not interpret MOCK screens as validated business data.

---

## 2. Global Shell & Navigation

### TC-UI-001 — Application loads (cold start) · 🟢 · P1
**Steps:** Open `http://localhost:3000`.
**Expected:** Left sidebar with CHERENKOV logo + "THE FORENSIC QA PROTOCOL"; nav groups OVERVIEW / ENGINE / AUTHOR / SIGNALS / OPERATE / LEARN; TopBar shows workspace breadcrumb, AUTONOMY toggle, SESSION COST, NODE STATE. No blank screen, no red console error.
**Pass:** Full shell renders within 3s.

### TC-UI-002 — Health poll on load · 🟢 · P1
**Steps:** Load app with backend up. (Optionally watch Network for `GET /api/v1/health`.)
**Expected:** Page detects backend; if backend started with `--demo`, demo affordances appear; otherwise normal. No error toast.
**Pass:** `/health` returns 200; UI does not error if `demo_mode=false`.

### TC-UI-003 — Navigate to every screen · 🟢 · P1
**Steps:** Click each of the 12 nav items in turn: Overview, Truth Map, Divergences, Explore, Author by Intent, Review Queue, Signals, Healing Options, Eject Suite, Governance, Memory & Pairing — plus Settings and UI Kit Gallery (bottom).
**Expected:** Each loads its own screen; active item is highlighted; main panel header matches the nav label; no React crash.
**Pass:** All 14 destinations render distinct content.

### TC-UI-004 — Active-tab highlight & breadcrumb sync · 🟢
**Steps:** Click "Divergences".
**Expected:** Sidebar highlights "Divergences"; TopBar breadcrumb second segment updates (e.g. "DIVERGENCE ENGINE STAR").
**Pass:** Highlight and breadcrumb both reflect current screen.

### TC-UI-005 — Autonomy toggle persists · 🟢
**Steps:** Click AUTONOMY → "Augmented". Reload the page.
**Expected:** "Augmented" is selected before and after reload (persisted to `localStorage['[copilot] autonomy']`).
**Pass:** Selection survives reload.
**Regression guard:** Default is "Assisted" on a fresh profile.

### TC-UI-006 — Command Palette open / search / navigate · 🟢
**Steps:** Press `Cmd+K` (mac) or `Ctrl+K`. Type `divergences`. Use ↓/↑ to move highlight. Press `Enter`.
**Expected:** Palette opens with placeholder "Type page name or action command…"; list filters; arrows move selection; Enter navigates to Divergences; palette closes.
**Pass:** Keyboard-only navigation works end-to-end.

### TC-UI-007 — Command Palette dismiss · 🟢
**Steps:** Open palette, press `Esc`.
**Expected:** Palette closes, no navigation occurred.
**Pass:** Esc cancels.

### TC-UI-008 — New Spec Run entry point · 🟢
**Steps:** Click the ">_ NEW SPEC RUN" button (top of sidebar).
**Expected:** Routes to the Setup (Spec Ingest) screen; NODE STATE stays IDLE until a run starts.
**Pass:** Setup screen opens.

### TC-UI-009 — Session cost & token pool telemetry visible · ⚪
**Steps:** Observe TopBar SESSION COST and "Cloud equivalent"; observe sidebar "LLM TOKEN POOL … % USED".
**Expected:** Values render (simulated); token pool bar is drawn.
**Pass:** Telemetry renders. **Note:** values are simulated, not billed.

### TC-UI-010 — Settings & UI Kit affordances reachable · 🟢
**Steps:** Click "Settings", then "UI Kit Gallery".
**Expected:** Each opens its respective screen.
**Pass:** Both reachable from the sidebar footer.

### TC-UI-011 — Help (?) control · ⚪
**Steps:** Click the "?" icon top-right.
**Expected:** Help affordance responds (panel/tooltip) without crashing.
**Pass:** No error.

---

## 3. Setup — Spec Ingest (🟢 LIVE — `POST /ingest`)

### TC-UI-020 — Setup screen renders ingest controls · 🟢
**Steps:** New Spec Run → Setup.
**Expected:** "New Test Generation Run" header; "Ingest API Definition" drop zone ("Drag & Drop OpenAPI Spec .json/.yaml, up to 10MB"); "BROWSE STORAGE"; URL field with FETCH; preset chips "petstore-v2.yaml" / "checkout-gateway.json"; "Real-server Validation Configuration" with Testing Target Host URL (default `http://localhost:8080/v2`) and X-Auth-Token field; right-side "Spec Richness Analyzer".
**Pass:** All controls present.

### TC-UI-021 — Ingest a valid spec via preset · 🟢 · P4-N/A
**Steps:** Click preset "petstore-v2.yaml" (or upload a valid OpenAPI file).
**Expected:** `POST /ingest` is called; Spec Richness Analyzer populates with endpoint richness (no longer "Please load or drop a spec configuration").
**Pass:** Analyzer shows parsed endpoints; backend log shows `POST /api/v1/ingest 200`.

### TC-UI-022 — Ingest via URL fetch · 🟢
**Steps:** Paste a spec URL in "PASTE SPEC CONFIGURATION URL", click FETCH.
**Expected:** Spec is fetched/ingested; analyzer updates or a clear error is shown if unreachable.
**Pass:** Success populates analyzer; failure shows a message (does not hang).

### TC-UI-023 — Ingest invalid / malformed spec · 🟢
**Steps:** Upload a non-spec file or malformed YAML.
**Expected:** Backend returns 400; UI surfaces a validation error, does not crash.
**Pass:** Graceful error. **Regression guard:** backend log previously showed `POST /api/v1/ingest 400` for bad input — confirm UI reflects it rather than silently ignoring.

### TC-UI-024 — Real-server validation config carried into run · 🟢
**Steps:** Change Testing Target Host URL, add an auth token, then start a run.
**Expected:** Target URL + auth header are passed to `POST /run` (not lost). Auth header "never escapes localhost context" per the on-screen note.
**Pass:** Run uses the configured target.

### TC-UI-025 — Start run transitions to Pipeline · 🟢
**Steps:** With a spec ingested, start the run.
**Expected:** Routes to Pipeline screen; NODE STATE → "Live".
**Pass:** Pipeline opens, status Live.

---

## 4. Pipeline — Live-Run Drawer (🟢 LIVE — `POST /run`)

### TC-UI-030 — Pipeline launches generation · 🟢 · P4
**Steps:** Start a run from Setup.
**Expected:** `POST /run` fires; LLM (`qwen2.5-coder:7b`) generates tests; live character-stream/stage animation renders; NODE STATE "Live".
**Pass:** Generation completes; backend log shows run + GENERATE stage.

### TC-UI-031 — Pipeline backend-failure fallback · 🟢
**Steps:** Stop the backend, then start a run.
**Expected:** Per design, a failed `/run` falls back to a mock pipeline animation (console warns "falling back to mock pipeline"). **Known UX gap:** the user is *not* told the real run failed.
**Pass:** UI does not crash. **Defect to log if business requires visible failure.**

### TC-UI-032 — Pipeline completion routes to Review · 🟢
**Steps:** Let the pipeline finish.
**Expected:** Auto-navigates to Review Queue; NODE STATE → Idle.
**Pass:** Review screen opens with generated tests.

### TC-UI-033 — Token/cost counters advance during run · ⚪
**Steps:** Observe SESSION COST / token pool during a run.
**Expected:** Counters increment in proportion to streamed output (simulated).
**Pass:** Values move; no negative/NaN.

---

## 5. Review Queue — HITL (🟢 LIVE — `GET /review/queue`, approve/reject/edit)

### TC-UI-040 — Review queue loads pending items · 🟢
**Steps:** Open Review Queue.
**Expected:** `GET /review/queue?status=pending` is called; generated tests (e.g. `happy_path`, `password_too_short`, `golden_edit`) appear with state badges.
**Pass:** Real queue items render.

### TC-UI-041 — Approve advances state REVIEW → APPROVED · 🟢
**Steps:** Select a test, click Approve.
**Expected:** `POST /review/approve` 200; item moves to APPROVED.
**Pass:** Backend state advances (verify via `cherenkov hitl list` or re-fetch).

### TC-UI-042 — Reject with reason · 🟢
**Steps:** Reject a test, supply a reason.
**Expected:** `POST /review/reject` 200; item marked REJECTED with reason stored.
**Pass:** State + reason persist.

### TC-UI-043 — Edit generated test · 🟢
**Steps:** Open a test, edit the code, save.
**Expected:** `POST /review/edit` 200; edited content persists.
**Pass:** Edit saved server-side.

### TC-UI-044 — HYBRID silent-failure guard (negative) · 🟡
**Steps:** Stop backend, then Approve/Reject/Edit.
**Expected (current):** UI optimistically updates local state and only `console.warn`s — **no user-visible error**.
**Pass criteria for regression:** behavior matches design (local fallback). **Flag as defect** if business requires the user to know the server did not record the verdict (silent divergence between UI and backend).

### TC-UI-045 — Concurrency / no cross-corruption · 🟢
**Steps:** Approve two different items in quick succession.
**Expected:** Each updates independently; no item's verdict overwrites another (HITL streams isolated).
**Pass:** Both verdicts correct.

---

## 6. Divergences — Triage Hub (🟢 LIVE — `GET /divergences`, `POST /divergences/act`)

### TC-UI-050 — Divergence list loads from backend · 🟢
**Steps:** Open Divergences.
**Expected:** "Divergence Triage Hub"; `GET /divergences` returns rows D-01…D-NN; each shows severity (HIGH/MEDIUM/LOW), class tag (D1 Spec↔Code, D2 Code↔Prod, D5 Spec↔Prod), endpoint (e.g. `GET /pet/findByStatus`), description, evidence source chip (spec/traffic), status (Reproduced). Header "Showing N of N active findings".
**Pass:** Real divergences render with correct counts.

### TC-UI-051 — Open divergence detail drawer · 🟢
**Steps:** Click a divergence row (or press `Enter` after `j`/`k` navigation).
**Expected:** Detail drawer opens with claimA / claimB, evidence, repro steps, confidence.
**Pass:** Drawer shows full detail.
**Regression guard (KNOWN FAILURE):** The deferred-tree E2E (`dashboard_e2e.spec.ts`) fails here — `text=D-` rows not found after the "filter anomalies" step. **Explicitly re-verify the drawer opens in the canonical UI and that filtering does not hide all rows.**

### TC-UI-052 — Keyboard navigation (j/k/Enter) · 🟢
**Steps:** Use `j`/`k` to move selection, `Enter` to open.
**Expected:** Selection moves; Enter opens the highlighted finding.
**Pass:** Keyboard-only triage works.

### TC-UI-053 — Filters: Class / Severity / Status · 🟢
**Steps:** Use ALL CLASSES, ALL SEVERITIES, ALL STATUSES dropdowns; set Severity = HIGH.
**Expected:** List filters to matching rows; "Showing X of N" updates; clearing restores full list.
**Pass:** Each filter narrows correctly; combined filters AND together.

### TC-UI-054 — Search endpoints/details · 🟢
**Steps:** Type an endpoint fragment (e.g. `findByStatus`) in "Search endpoints or details…".
**Expected:** List filters live.
**Pass:** Matching rows only; empty query restores all.

### TC-UI-055 — Act on a divergence · 🟢
**Steps:** From a finding, take an action (resolve/dismiss) with a reason.
**Expected:** `POST /divergences/act` 200; list re-fetches (`GET /divergences`); the acted item's status changes.
**Pass:** Backend records action; UI refreshes.

### TC-UI-056 — Empty / zero-finding state · 🟢
**Steps:** With no divergences (or all resolved), open the screen.
**Expected:** Graceful "no active findings" rather than a broken list.
**Pass:** Empty state renders.

---

## 7. Eject Suite (🟢 LIVE — `POST /eject`)

### TC-UI-060 — Eject standalone Playwright suite · 🟢
**Steps:** Open Eject Suite, choose output path, trigger Eject.
**Expected:** `POST /eject` 200; backend copies spec files, generated types, clean `client.ts`, `playwright.config.ts`, `package.json`, `tsconfig.json` to the output dir; no 400/500.
**Pass:** Suite emitted; success state shown.

### TC-UI-061 — Ejected suite is self-contained (anti-lock-in) · 🟢
**Steps:** After eject, inspect the output dir (`./playwright-suite`).
**Expected:** `.spec.ts` tests + `client.ts` + config; runs natively `npx playwright test` outside CHERENKOV.
**Pass:** No CHERENKOV runtime dependency remains.

### TC-UI-062 — Eject error handling · 🟢
**Steps:** Eject to an invalid/locked path.
**Expected:** Clear error; UI does not hang.
**Pass:** Graceful failure.

---

## 8. Healing Options (🟡 HYBRID — `POST /review/edit`, `POST /validate`)

### TC-UI-070 — Healing screen renders drift/repair context · 🟡
**Steps:** Open Healing Options.
**Expected:** API drift / self-repair context; target shown as `http://localhost:8080/v2`; proposed-fix items with proposed code.
**Pass:** Screen renders.

### TC-UI-071 — Apply healing suggestion (suggest-only honored) · 🟡
**Steps:** Apply a proposed fix.
**Expected:** `POST /review/edit` called with proposed code; a best-effort `POST /validate` follows. Per the suggest-only invariant, no files are auto-committed without approval.
**Pass:** Suggestion applied through the review path; git stays clean of un-approved commits.

### TC-UI-072 — Healing backend-failure is silent (negative) · 🟡
**Steps:** Stop backend, apply a suggestion.
**Expected (current):** `editTestScenario`/`validateSuite` fail and are swallowed by `.catch(console.warn)` — **no user feedback**.
**Pass criteria:** matches current design. **Flag as defect (UX-C1):** healing appears to succeed but silently failed.

### TC-UI-073 — Hardcoded endpoint guard · 🟡
**Steps:** Note the target URL on screen.
**Expected:** It is hardcoded `localhost:8080/v2`.
**Regression guard:** This breaks in Docker/production (UX-H1). Log as known issue; not configurable from the UI.

---

## 9. Overview — Release Readiness (⚪ MOCK)

### TC-UI-080 — Overview renders KPI ring · ⚪
**Steps:** Open Overview.
**Expected:** "Release Readiness & Learning"; circular Readiness score (e.g. 94%); "FP Rate" and "Target"; "RUN DISCOVERY SCAN" button.
**Pass:** Ring + metrics render. **Note:** values are mock.

### TC-UI-081 — Top Unresolved Divergences panel · ⚪
**Steps:** View the "Top Unresolved Divergences" list (D1/D5 entries).
**Expected:** Shows mock divergences with severity badges; "View All Divergences →" navigates to the Divergences screen.
**Pass:** Renders; link routes correctly.

### TC-UI-082 — Reflector Verdict Memory panel · ⚪
**Steps:** View "Reflector Verdict Memory"; click "Manage Reflector Memory →".
**Expected:** Mock learning entries; link routes to Memory & Pairing.
**Pass:** Renders; link works.

### TC-UI-083 — KPI ring accessibility (negative) · ⚪
**Steps:** Inspect the ring with a screen reader / check for `aria-label`.
**Expected:** Currently no `role`/`aria-label` (UX-M3) and no tooltip explaining the score (UX-H4).
**Pass criteria:** record as known a11y gap.

---

## 10. Truth Map — Claim Graph (⚪ MOCK)

### TC-UI-090 — Truth Map renders endpoint claims · ⚪
**Steps:** Open Truth Map.
**Expected:** "Endpoint Truth Graph"; left "MONITORED ENDPOINT CLAIMS" list (POST /pets, GET /pet/findByStatus, GET /store/inventory, GET /user/login) each tagged DIVERGENT with claim count.
**Pass:** List renders.

### TC-UI-091 — Select endpoint shows provenance claims · ⚪
**Steps:** Click "POST /pets".
**Expected:** Right panel shows SPEC VERIFIED / CODE VERIFIED / TRAFFIC VERIFIED claims (e.g. spec requires name+photoUrls; traffic observed POST lacking photoUrls succeeding 200).
**Pass:** Three-source claims render for the selected endpoint.

### TC-UI-092 — Hunt Divergences link · ⚪
**Steps:** Click "HUNT DIVERGENCES →".
**Expected:** Routes to Divergences (or triggers mock hunt).
**Pass:** No crash; navigation/behavior consistent.

---

## 11. Explore — Crawler (⚪ MOCK)

### TC-UI-100 — Explore empty/configure state · ⚪
**Steps:** Open Explore.
**Expected:** "Explore Crawler" card describing autonomous crawling; "CONFIGURE SCOPE & TARGET" button.
**Pass:** Card + CTA render.

### TC-UI-101 — Configure Scope & Target · ⚪
**Steps:** Click "CONFIGURE SCOPE & TARGET".
**Expected:** Opens a scope/target configuration affordance (mock).
**Pass:** Responds without error. **Note:** no real crawl runs (no backend).

---

## 12. Author by Intent — Copilot (⚪ MOCK)

### TC-UI-110 — Author screen renders prompt surface · ⚪
**Steps:** Open Author by Intent.
**Expected:** NL-intent prompt input + copilot surface render.
**Pass:** Renders; input accepts text.

### TC-UI-111 — Initialize Pilot Run (negative) · ⚪
**Steps:** Trigger "Initialize Pilot Run".
**Expected:** Per audit, this is a **no-api** action — it does not hit the backend.
**Pass criteria:** UI responds (mock), but record that authoring is **not** wired to `orchestrator` (known gap; backlog item to wire to `/run`).

---

## 13. Signals — Visual / Perf / Coverage (⚪ MOCK)

### TC-UI-120 — Signals renders all three sub-panels · ⚪
**Steps:** Open Signals.
**Expected:** Visual, Performance, and Coverage sections all render mock charts/metrics.
**Pass:** Three panels render; no NaN/empty charts.

### TC-UI-121 — Signals interactions · ⚪
**Steps:** Toggle any tabs/filters within Signals.
**Expected:** Sub-views switch without crash.
**Pass:** Interactive controls work on mock data.

---

## 14. Governance — KPI Cert (⚪ MOCK)

### TC-UI-130 — Governance KPI panel renders · ⚪
**Steps:** Open Governance.
**Expected:** KPI certification / model-compliance panel renders mock KPIs.
**Pass:** Panel renders. **Note:** no `/governance` endpoint exists — data is mock only.

---

## 15. Memory & Pairing — Reflector (⚪ MOCK)

### TC-UI-140 — Memory screen renders idioms · ⚪
**Steps:** Open Memory & Pairing.
**Expected:** Reflector "senior idioms" / verdict memory entries render.
**Pass:** Renders. **Note:** mock; no live reflector store wired to this screen.

---

## 16. Projects — Workspace Switcher (⚪ MOCK)

### TC-UI-150 — Switch active workspace · ⚪
**Steps:** Use the "ACTIVE WORKSPACE" dropdown (bottom-left, e.g. "Checkout Gateway API") to switch projects; also try via Command Palette.
**Expected:** Active project changes; breadcrumb/header reflect the new workspace; "Active Registry Count" consistent.
**Pass:** Selection updates global context.

### TC-UI-151 — Project context persists across navigation · ⚪
**Steps:** Switch project, navigate to several screens.
**Expected:** Selected project stays selected across screens.
**Pass:** No reset on navigation.

---

## 17. Settings (⚪ MOCK — localStorage)

### TC-UI-160 — Settings render & persist · ⚪
**Steps:** Open Settings, change a setting, reload.
**Expected:** Setting persists (localStorage).
**Pass:** Survives reload.
**Regression guard (UX-C2):** persistence is localStorage-only — cleared on cache wipe, no migration, `[copilot]`-prefixed keys. Record as known limitation.

---

## 18. UI Kit Gallery (⚪ MOCK)

### TC-UI-170 — UI Kit renders component gallery · ⚪
**Steps:** Open UI Kit Gallery.
**Expected:** Design-system component showcase renders (buttons, badges, rings, cards) without error.
**Pass:** Gallery renders; used for visual-regression baselining.

---

## 19. Cross-Cutting Regression

### TC-UI-180 — Backend-offline global behavior · 🟢
**Steps:** Stop backend; navigate LIVE screens (Setup, Pipeline, Review, Divergences, Eject).
**Expected (current):** No global "Backend Offline" overlay exists; LIVE screens fail to load real data, HYBRID screens silently fall back.
**Pass criteria:** UI must not white-screen. **Recommended enhancement:** add a health-poll overlay (currently absent).

### TC-UI-181 — No console errors on any screen · 🟢
**Steps:** Visit all 17 surfaces with DevTools console open.
**Expected:** No uncaught errors. (Abundant `console.log`/`warn` is expected but should not include errors.)
**Pass:** Zero red errors. **Note (UX-L1):** verbose logging is a known low-severity issue.

### TC-UI-182 — Favicon / asset 404 guard · 🟢
**Steps:** Watch Network on load.
**Expected:** No persistent 404 for `favicon.ico` (a blank favicon was added to `public/`).
**Pass:** No favicon 404.

### TC-UI-183 — Responsive / viewport · ⚪
**Steps:** Resize to 1280×800 and 1920×1080.
**Expected:** Layout adapts; sidebar + main remain usable.
**Pass:** No overlap/clipping at supported sizes. **Note (UX-L3):** non-standard viewports uncharacterized.

### TC-UI-184 — Light-background legibility (negative) · ⚪
**Steps:** N/A — only dark theme supported.
**Expected:** Borders use `border-white/5`; near-invisible on light backgrounds (UX-M2).
**Pass criteria:** confirm dark theme only; record as known limitation.

### TC-UI-185 — Accessibility: form fields labelled · 🟢
**Steps:** Inspect the project selector and input fields for `id`/`name`/`label`.
**Expected:** Project selector has `label`, `id`, `aria-label` (prior A11y fix).
**Pass:** No "form field should have id or name" DevTools issue.

---

## 20. End-to-End Golden Path (🟢 Full-stack acceptance)

### TC-UI-190 — Spec → Generate → Review → Approve → Eject · 🟢 · P1–P4
**Steps:**
1. New Spec Run → Setup; ingest a valid spec (preset or upload). *(POST /ingest)*
2. Configure target host; Start run. *(POST /run, LLM generates)*
3. Pipeline completes → Review Queue. *(GET /review/queue)*
4. Approve at least one generated test. *(POST /review/approve)*
5. Open Eject Suite; eject standalone Playwright. *(POST /eject)*
6. (Optional) Run the ejected suite with `npx playwright test` outside CHERENKOV.

**Expected:** Each backend call returns 200; HITL state advances REVIEW→APPROVED; ejected suite runs natively.
**Pass:** Full chain completes with real backend state changes and a self-contained, runnable output.

---

## 21. Known-Defect Regression Guards (must re-verify each cycle)

| ID | Guard | Expected after fix |
|----|-------|--------------------|
| RG-1 | `cherenkov.py review` (no `--demo`) boots | No `NameError: os` (fixed: `import os`) — backend starts in non-demo mode |
| RG-2 | `validate` must not auto-edit test files | `smoke_test_validate.py` passes; git clean; **currently FAILS** (mutates `stub/generated_tests/*.spec.ts`) — **open defect** |
| RG-3 | Divergence detail-drawer opens | `text=D-` rows visible after filtering; **deferred-tree E2E currently FAILS** |
| RG-4 | HYBRID silent failures (Review/Healing) | Backend failure surfaces to user (currently swallowed by `.catch(console.warn)`) |
| RG-5 | Backend-offline overlay | Global health-poll overlay shown (currently absent) |
| RG-6 | WSL localhost forwarding | `localhost:3000`/`:8000` reachable from host (restored via `wsl --shutdown`) |
| RG-7 | Author "Initialize Pilot Run" wired | Hits `/run`/orchestrator (currently no-api) |

---

## 22. Traceability & Sign-off Matrix

| Screen | TC range | Integration | Result | Tester | Date |
|--------|----------|-------------|--------|--------|------|
| Global Shell | 001–011 | 🟢/⚪ | | | |
| Setup / Ingest | 020–025 | 🟢 | | | |
| Pipeline | 030–033 | 🟢 | | | |
| Review Queue | 040–045 | 🟢 | | | |
| Divergences | 050–056 | 🟢 | | | |
| Eject Suite | 060–062 | 🟢 | | | |
| Healing | 070–073 | 🟡 | | | |
| Overview | 080–083 | ⚪ | | | |
| Truth Map | 090–092 | ⚪ | | | |
| Explore | 100–101 | ⚪ | | | |
| Author | 110–111 | ⚪ | | | |
| Signals | 120–121 | ⚪ | | | |
| Governance | 130 | ⚪ | | | |
| Memory | 140 | ⚪ | | | |
| Projects | 150–151 | ⚪ | | | |
| Settings | 160 | ⚪ | | | |
| UI Kit | 170 | ⚪ | | | |
| Cross-cutting | 180–185 | mixed | | | |
| Golden Path E2E | 190 | 🟢 | | | |
| Known-Defect Guards | RG-1…RG-7 | — | | | |

**Definition of "100% regression complete":** every TC (001–190) and every guard (RG-1…RG-7) has a recorded result; all 🟢 LIVE TCs and TC-UI-190 are **PASS**; all ⚪/🟡 known-limitation TCs are either PASS or explicitly recorded as accepted known issues with a backlog reference.

**Gate note:** This suite proves UI function and the 6 LIVE + 1 HYBRID integrations. It does **not** substitute for the Track A validation gate (still 0/5). MOCK screens passing does **not** constitute business validation of those analytics.
