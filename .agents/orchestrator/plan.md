# Execution Plan: CHERENKOV QA UI Revamp

## Objectives
1. **R1: Complete UI/UX Revamp**: Modern aesthetic using Vanilla CSS (glassmorphism, vibrant colors, dynamic micro-animations, scalable architecture).
2. **R2: Backend Wiring & Cleanup**: FastAPI as single source of truth; wire all real backend endpoints (`/api/v1/*`); purge unused/mocked/fake code.
3. **R3: New UI Automation**: Updated/new Playwright UI automation specs (`cherenkov/web/ui/tests/qa/headless-qa-user.spec.ts` etc.) passing E2E.

## Phased Approach

### Phase 1: Exploration & Audit (M1)
- Dispatch Explorer subagent to examine:
  - Existing UI structure in `cherenkov/web/ui/src/` and `dashboard/`
  - Backend API routers and endpoints in `cherenkov/web/api.py` and `cherenkov/web/routes/`
  - Mock/fake UI code or mock overlays (`MockBadge.tsx`, hardcoded mock data, etc.)
  - Existing UI tests in `cherenkov/web/ui/tests/`

### Phase 2: Modern Vanilla CSS UI/UX Revamp (M2)
- Dispatch Worker subagent to implement:
  - Vanilla CSS design tokens (`theme.css`) with glassmorphism (`backdrop-filter: blur()`), vibrant accent gradients, glowing borders, smooth micro-animations (`@keyframes`).
  - Scalable component hierarchy: `AppHeader`, `NavigationBar`, and 5 Workspaces (`DashboardWorkspace`, `AuthoringWorkspace`, `TriageWorkspace`, `IntelligenceWorkspace`, `SettingsWorkspace`).

### Phase 3: Backend Wiring & Cleanup (M3)
- Dispatch Worker subagent to:
  - Wire FastAPI REST API endpoints to UI components.
  - Delete any legacy/mock components, mock overlays, or dead UI files.
  - Ensure FastAPI static route server properly serves SPA and fallback routing.

### Phase 4: UI Automation & Verification (M4 & M5)
- Dispatch Worker subagent to update/create Playwright test specs.
- Dispatch Reviewer, Challenger, and Forensic Auditor for verification.
- Execute Git commit & push for proof of work.
