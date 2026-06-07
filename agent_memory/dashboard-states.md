# Dashboard States

UI component inventory for the CHEENKOV web review dashboard.
Source: `cherenkov/web/ui/src/components` + `ROADMAP_NEXT.md` #224/#239

## Current State (2026-06-07)

### Screens with Live Data
| Screen | Data Source | Status |
|--------|-------------|--------|
| Review Queue | Real `HitlQueue` (SQLite) | ✅ Live — Issue #173/#175 |
| Divergences Triage | Real divergence engine | ✅ Live — Issue #227/#236 |

### Screens Still Using Mock Data (10/17 flagship)
Per ROADMAP_NEXT.md #224/#239 — these screens render `mockData.ts` instead of live API calls:

| Screen | Target | Issue |
|--------|--------|-------|
| Overview | Replace mock with live aggregate | #224/#239 |
| TruthMap | Wire to real Truth Model | #224/#239 |
| Signals | Real divergence signal data | #224/#239 |
| Governance | Real KPI panel data | #224/#239 |
| Memory | Real agent memory persistence | #224/#239 |
| Explore | Real crawl results | #224/#239 |
| Author | Real intent-to-test pipeline | #224/#239 |
| (plus 3 more screens) | | #224/#239 |

### Honest States Implementation (Issue #222)
- Silent `catch(console.warn)` → visible toasts (P1)
- Backend-offline overlay with health polling (#221) ✅ Done
- Empty state: "No findings — run validate to populate" (P2)
- Error state: API down, target unreachable (P2)
- Guided 60-second first-run tour (P2)

### Mock Badge System (Issue #224/#239)
- Screens using mock data must display explicit `MOCK DATA` badge
- Badge color: amber/yellow
- Badge text: "Showing simulated data — real API not connected"
- Removed when screen is wired to live data

## FE Architecture
- Framework: React + Vite + TypeScript
- UI components: `cherenkov/web/ui/src/components/`
- Styling: Tailwind CSS
- Routing: React Router
- State management: React hooks + context
- Build: Prebuilt `dist/` shipped in repo (no `npm install` for users)

## Cross-references
- See ROADMAP_NEXT.md §8 Wave 2 for the honesty-debt tickets
- See `validation-gate.md` for the gate requirement conditions
