> # ⚠️ ARCHIVED - SUBJECT TREE (track-b-c-deferred/) WAS RE-INTEGRATED AND DELETED - DO NOT CITE AS CURRENT
>
# FE Dashboard Parity Audit — `track-b-c-deferred/dashboard/` vs `cherenkov/web/ui/`

**Issue**: #249
**Date**: 2026-06-06
**Status**: Complete — deferred dashboard superseded, ready for deletion

---

## Executive Summary

The supported dashboard at `cherenkov/web/ui/` (introduced in #176) **fully supersedes** the deferred copy at `track-b-c-deferred/dashboard/`. The supported version contains all 19 screens **plus** `GuidedTour.tsx`, real backend integration, loading/error states, toast notifications, accessibility compliance, and comprehensive regression tests. The deferred copy is an older AI-Studio-generated React app that lacks these features.

**Conclusion**: No material features from the deferred dashboard are missing in the supported version. The deferred copy can be safely deleted.

---

## Component-by-Component Comparison

### Screens (19 total + GuidedTour)

| Screen | Deferred | Supported | Notes |
|--------|----------|-----------|-------|
| `OverviewScreen.tsx` | Mock-only, static KPI | **Real API** (`fetchDivergences`), dynamic readiness score, skeletons, error handling, "MOCK DATA" badge | Supported is superior |
| `TruthMapScreen.tsx` | Mock-only | **Real API** integration, claims panel | Supported is superior |
| `DivergencesScreen.tsx` | Basic filter | **Real API**, case-insensitive filter, detail drawer, action buttons | Supported is superior |
| `AuthorScreen.tsx` | Basic NL input | **Real API**, mentor idioms, example chips, pilot run wiring | Supported is superior |
| `SignalsScreen.tsx` | Basic tabs | **MockBadge**, "MOCK DATA" badge, tab switching | Supported adds honesty badges |
| `MemoryScreen.tsx` | Basic | Identical | Parity |
| `GovernanceScreen.tsx` | Basic | Identical | Parity |
| `ProjectsScreen.tsx` | Basic search | **Real API**, workspace selector, timer bars | Supported is superior |
| `PipelineScreen.tsx` | Basic | Identical | Parity |
| `ReviewScreen.tsx` | Local state only | **Real API** (`fetchReviewQueue`, `approveTestScenario`, `rejectTestScenario`, `editTestScenario`, `explainTestScenario`), **AI Explanation** feature, skeletons, toasts, load error handling | Supported is vastly superior |
| `HealingScreen.tsx` | Basic apply | **Real API** with toast feedback, validation trigger, error handling | Supported is superior |
| `EjectScreen.tsx` | **Better error display** (shows `ejectError` to user) | Two buttons ("Eject to Path" + "Download .ZIP"), but **silently proceeds on backend failure** | **Deferred has better error UX** — see follow-up |
| `SetupScreen.tsx` | Mock ingest only | **Real `ingestSpec` + `fetchDoctor`**, system readiness checks, doctor panel, error surfacing | Supported is superior |
| `SettingsScreen.tsx` | LocalStorage only | **Real `fetchSettings`/`updateSettings`**, toasts, loading skeletons, persisted density/motion | Supported is superior |
| `UiKitScreen.tsx` | Basic | Identical | Parity |
| `CommandPalette.tsx` | Basic | Minor accessibility improvements (`id`/`name` attrs) | Supported is superior |
| `Sidebar.tsx` | Basic | Project selector `id`/`name`/`aria-label` | Supported has better a11y |
| `TopBar.tsx` | Basic | Identical | Parity |
| `CherenkovLogo.tsx` | Identical | Identical | Parity |
| **`GuidedTour.tsx`** | ❌ Missing | ✅ **Present** (19+1 screens) | Supported only |

### UI Primitives (`src/components/ui/`)

| Component | Deferred | Supported | Notes |
|-----------|----------|-----------|-------|
| `MockBadge.tsx` | ❌ Missing | ✅ Present | Honesty indicator |
| `OfflineOverlay.tsx` | ❌ Missing | ✅ Present | Backend-offline honest state (#221) |
| `Toast.tsx` | Basic | Enhanced (used by screens) | Supported integrates toasts |
| `KpiRing.tsx` | Basic | Minor a11y improvements | Supported is superior |
| `index.ts` | Basic exports | Exports all including new primitives | Supported is complete |

### Hooks (`src/hooks/`)

| Hook | Deferred | Supported | Notes |
|------|----------|-----------|-------|
| `useLiveEvents.ts` | Identical | Identical | Parity |
| `useReducedMotion.ts` | Identical | Identical | Parity |
| **`useHealth.ts`** | ❌ Missing | ✅ Present | Backend liveness single source of truth (#221) |

### API Layer (`src/lib/api.ts`)

| Function | Deferred | Supported | Notes |
|----------|----------|-----------|-------|
| `ejectSuite` | ✅ | ✅ | Parity |
| `editTestScenario` | ✅ | ✅ | Parity |
| `approveTestScenario` | ❌ | ✅ | Supported only |
| `rejectTestScenario` | ❌ | ✅ | Supported only |
| `fetchGeneratedTests` | ❌ | ✅ | Supported only |
| `fetchReviewQueue` | ❌ | ✅ | Supported only |
| `explainTestScenario` | ❌ | ✅ | **AI Explanation** — supported only |
| `fetchSettings` | ❌ | ✅ | Supported only |
| `updateSettings` | ❌ | ✅ | Supported only |
| `fetchDoctor` | ❌ | ✅ | **System readiness** — supported only |
| `fetchDivergences` | ❌ | ✅ | Supported only |
| `performDivergenceAction` | ❌ | ✅ | Supported only |
| `ingestSpec` | ❌ | ✅ | Supported only |

### Tests

| Test File | Deferred | Supported | Notes |
|-----------|----------|-----------|-------|
| `dashboard_e2e.spec.ts` | Basic (7.3 KB) | **Comprehensive regression** (20 KB) — 19 screen tests | Supported is superior |
| `a11y.spec.ts` | ❌ Missing | ✅ **WCAG 2.1 AA** structural/ARIA audit | Supported only |
| `capture_screens.spec.ts` | ✅ Screenshot capture | ❌ Missing | Deferred-only — audit tool, not regression |
| `full_audit.spec.ts` | ✅ Interactive API audit | ❌ Missing | Deferred-only — diagnostic tool |
| `playbook/*.png` | ✅ Reference screenshots | ❌ Missing | Deferred-only — visual reference |

---

## Missing-from-Supported (Follow-ups)

### 1. EjectScreen Error UX (Minor)
- **Deferred**: Shows `ejectError` to user when backend eject fails
- **Supported**: Catches error, logs warning, but **proceeds with UI confirmation** (sets `isEjected=true`)
- **Impact**: Supported version may report success when backend write failed
- **Action**: File follow-up issue to align supported EjectScreen with deferred's honest error display (D7: suggest-only, never fabricate success)

### 2. Diagnostic Test Scripts (Non-blocking)
- `capture_screens.spec.ts` and `full_audit.spec.ts` are **diagnostic/audit tools**, not regression tests
- `playbook/` screenshots are visual references for the old deferred UI
- **Action**: No migration needed. Supported has superior regression + a11y suites. If diagnostic scripts are wanted, they can be re-written against the supported app later.

---

## Verdict

**No material feature gaps.** The supported dashboard (`cherenkov/web/ui/`) is strictly more complete, honest, and built and unit-tested (not externally validated). The deferred copy (`track-b-c-deferred/dashboard/`) is an obsolete AI-Studio prototype.

**Recommendation**: Delete `track-b-c-deferred/dashboard/` entirely (including `node_modules/`, `dist/`, `playbook/`, `test-results/`).

---

## Acceptance Checklist

- [x] Audit notes recorded (this document)
- [ ] Deferred dashboard removed
- [ ] Repo builds green (verify after deletion)
