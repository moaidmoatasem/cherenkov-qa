# CHERENKOV QA — Frontend Workflow Requirements

**Status:** Requirements Specification  
**Intended Audience:** Product Management, UI/UX Design, Solution Architecture, Frontend Engineering

---

## Executive Summary

CHERENKOV-QA's current dashboard (React 18 + Vite) delivers core capabilities but has UX friction points for QA practitioners. The **QA Reasoning Engine** (ADR-007) introduces artifact-adaptive workflows that vary by testing stage and context. This document specifies FE requirements to make the dashboard **QA-first**, **agent-augmented**, and **resilient** while preserving the existing backend and building on top.

---

## 1. QA Personas & Their Primary Journeys

| Persona | Role | Goal | Primary Journey |
|---------|------|------|-----------------|
| **Manual QA (Maya)** | Non-coder tester | "Test this without writing code." | J1 · Author by Intent + Quick Triage |
| **QA Lead (Sam)** | Test strategist | "Am I safe to ship? What's lying?" | J2 · Divergence Triage + Risk Assessment |
| **SDET (Jordan)** | Automation engineer | "What would a senior check here?" | J3 · Deep Analysis + Pattern Learning |
| **DevOps (Alex)** | CI/CD owner | "Automated conformance, zero maintenance." | J4 · Scheduled Validation + Reporting |

---

## 2. Journey J1 — Author by Intent (Manual QA Heart)

### Current State Analysis
- AuthorScreen.tsx exists but lacks real-time step preview and vision feedback
- No inline Mentor idiom suggestions from Knowledge Mesh
- Eject flow resets state without clear confirmation

### Required Workflows

#### J1-A: Intent Capture & Clarification
**Entry:** Sidebar → Author by Intent OR ⌘K → "author a test"  
**States:**
1. **Empty State** — Large focused textarea with 3 example chips, glow accent animation
2. **Typing** — Character-stream glow on Submit button, inline autocomplete suggestions
3. **Ambiguous Intent** — Clarification chip bar (e.g., "Which checkout — guest or member?") - never guess silently

**UX Requirements:**
```
Intent Input Component:
  - Placeholder: "Verify that guests can checkout with discount code..."
  - Example chips visible below input
  - Auto-focus on mount
  - Character count indicator (max 500 chars)
```

#### J1-B: Pilot Execution Preview
**Trigger:** Submit intent with Autonomy=Assisted (default for Maya)  
**States per Step:**
1. **pending** — Gray dot, no animation
2. **running** — Cyan pulse (glow-pulse), step number highlight
3. **done** — Success checkmark (success token)
4. **failed** — Warning color, inline retry/heal buttons

**Actions per Step (Assisted Mode):**
- `Confirm step` — Proceed with this action
- `Modify step` — Open inline editor (plain English only)
- `Skip & flag` — Log as potential divergence

**FE Changes Required:**
- PilotStep component with live screenshot thumbnail
- Step status pill using StatusDot primitive
- Inline action buttons that don't break flow state

#### J1-C: Result & Eject
**States:**
1. **Pass** — Success card with evidence disclosure (request/response)
2. **Fail** — Two-card view: Claim A (spec) vs Claim B (actual), red accent
3. **Partial** — Warning card with what succeeded/failed

**Actions:**
- `Save & Eject` — Primary button, toast confirmation with file path
- `Heal Suggestion` — Secondary, links to HealingScreen with context
- `Try Again` — Reset intent, preserve Mentor suggestions

---

## 3. Journey J2 — Divergence Triage (Lead's Money Path)

### Current State Analysis
- DivergencesScreen.tsx has full implementation but lacks risk scoring
- No connection to QA Reasoning Engine's workflow selection
- Missing quick actions (approve/reject without opening drawer)

### Required Workflows

#### J2-A: Divergence List with Risk Prioritization
**Filters:**
- Class (D1-D5) — Current implementation
- Severity — Current implementation  
- Status — Current implementation
- **NEW: Risk Score** (high/medium/low) — From QA Reasoning Engine
- **NEW: Confidence** (0-100%) — From pilot execution

**Sorting:**
1. **Default:** Severity DESC, Risk Score DESC
2. **QA Lead:** Confidence DESC (show what's certain)
3. **SDET:** Age ASC (show what's aging)

#### J2-B: Drawer Detail with Evidence
**Content Structure:**
```
Divergence Detail Drawer:
  ├─ Header: SeverityPill + StatusDot + ProvenanceChips
  ├─ Endpoint: <method> <path> (click to copy)
  ├─ Claim A: Spec-derived expected behavior (green)
  ├─ Claim B: Actual observed behavior (red)
  ├─ Evidence Diff: Request/response or screenshot comparison
  ├─ Repro Steps: Numbered list with copy button
  └─ Actions: Close with Test | Mark Intended | Reject (Noise)
```

#### J2-C: Quick Actions (Power User)
**Keyboard shortcuts:**
- `a` — Approve/emit test
- `i` — Mark intended  
- `r` — Reject with reason prompt
- `c` — Copy repro steps to clipboard

**Hover actions on row:**
- Right-side chevron appears on hover
- Quick approve/reject icons without opening drawer

---

## 4. Journey J3 — Deep Analysis (SDET/QA Engineer)

### QA Reasoning Engine Integration

The QA Reasoning Engine (ADR-007) outputs a `QAPlan` with:
- `analysis` — Artifact weaknesses/gaps
- `review_findings` — Contradictions and test smells  
- `risk_register` — Ranked risks with rationale
- `designed_cases` — Test cases linked to requirements/risks

**Required Screens:**

#### J3-A: QA Plan Viewer
**Component:** `QAPlanScreen.tsx`  
**Displays:**
- Risk heatmap (KpiRing style for risk count)
- Analysis findings list (sorted by severity)
- Designed cases table (requirement, risk, priority, status)

#### J3-B: Risk Register
**Component:** Embedded in QA Plan or separate `RiskScreen.tsx`  
**Columns:**
- Risk ID | Description | Requirement Link | Priority | Mitigation Status

#### J3-C: Pattern Learning
**Component:** `MemoryScreen.tsx` (exists)  
**Enhancements:**
- Show patterns learned THIS session vs ALL
- Decay indicator (patterns not seen recently fade)
- "Apply this pattern" quick action per idiom

---

## 5. Journey J4 — Scheduled Validation (DevOps)

### Required Workflows

#### J4-A: ConformanceCheck CRD Integration
**View:** Governance screen enhancement  
**Shows:**
- K8s Job status (running/done/failed)
- Last run timestamp
- Drift count from last run
- Quick link to run now (opens SetupScreen)

#### J4-B: Report Exporter
**Actions:**
- Export JUnit XML
- Export JSON findings
- Export trace bundle (with evidence)

---

## 6. System Integrity Requirements (Solution Architect)

### 6.1 Zero Lock-in Preservation
- Every screen must work with mocked data (lib/api.ts pattern)
- `eject` produces vanilla Playwright (verify via smoke_test_eject.py)
- No CHERENKOV imports in ejected files

### 6.2 Resilience Patterns
**Backend Offline Handling:**
- OfflineOverlay (exists) blocks interaction
- Cache previous state for 24h view
- All actions disabled with tooltip explanation

**Model Offline Handling:**
- Demo mode auto-activates when Ollama unreachable
- Toast: "Switched to demo mode — limited capabilities"
- Reasoning Engine falls back to HeuristicReasoner

### 6.3 Data Flow Integrity
```
User Action → API Call → Optimistic Update → Reconciliation
  ↓              ↓             ↓                ↓
  Command       /api/v1/*    Immediate UI     3s timeout
  Palette                     change          Rollback + toast on fail
```

---

## 7. FE Implementation Backlog

### Priority 1 — Core QA Flows (Week 1)

| Task | Screen | FE Points | BE Contract |
|------|--------|-----------|-------------|
| FE-R01 | AuthorScreen | Live step preview, vision feedback | POST /api/v1/pilot/step |
| FE-R02 | DivergencesScreen | Risk score column, confidence sort | GET /api/v1/divergences?sort=risk |
| FE-R03 | OverviewScreen | Release readiness KPI uses risk score | GET /api/v1/overview (augment) |
| FE-R04 | QAPlanScreen | NEW screen for QA Reasoning output | GET /api/v1/reasoning/plan |

### Priority 2 — Intelligence Integration (Week 2)

| Task | Screen | FE Points | BE Contract |
|------|--------|-----------|-------------|
| FE-R05 | AuthorScreen | Mentor idioms from knowledge mesh | GET /api/v1/memory/idioms |
| FE-R06 | MemoryScreen | Session-scoped learning counter | GET /api/v1/memory/session |
| FE-R07 | SignalsScreen | Risk-annotated regressions | GET /api/v1/signals?annotated=true |

### Priority 3 — DevOps Enablement (Week 3)

| Task | Screen | FE Points | BE Contract |
|------|--------|-----------|-------------|
| FE-R08 | GovernanceScreen | K8s ConformanceCheck status | GET /api/v1/governance/k8s |
| FE-R09 | All screens | Report export endpoints | POST /api/v1/export/* |

---

## 8. User Scenarios (Acceptance Criteria)

### Scenario 1: Manual QA — First Run
```
Given: Maya opens CHERENKOV dashboard for first time
When: She sees OverviewScreen with "Run your first map" CTA
Then: She clicks Author by Intent, types "check login flow works"
And: Steps appear with preview, she confirms each
And: Result shows pass, she clicks "Save & Eject"
And: Toast confirms: "Test ejected to tests/login.spec.ts — runs standalone"
```

### Scenario 2: QA Lead — Divergence Triage
```
Given: Sam opens Divergences screen
When: He filters to "D1: Spec ↔ Code" and severity "critical"  
Then: List shows 3 items, sorted by confidence
When: He opens a divergence, sees Claim A vs B with evidence
And: He clicks "Close with Test"
Then: Drawer closes, row shows success ripple animation
And: Toast: "Divergence resolved by emitting test suite"
```

### Scenario 3: SDET — Pattern Learning
```
Given: Jordan rejects 3 divergences as noise with same pattern
When: He navigates to Memory screen
Then: Counter shows "3 new patterns learned this session"
And: The common rejection pattern is listed with "Apply to similar" action
```

### Scenario 4: DevOps — Scheduled Validation
```
Given: Alex configures K8s ConformanceCheck CRD
When: He opens Governance screen
Then: He sees "Last run: 2 hours ago, 0 drifts detected"
And: Status shows "✓ Healthy"
When: He clicks "Run Now"
Then: SetupScreen opens with CRD-target prefilled
```

---

## 9. Integration Points

### 9.1 QA Reasoning Engine
```
Backend: cherenkov/reasoning/qa_engine.py
API: /api/v1/reasoning/analyze
API: /api/v1/reasoning/plan
API: /api/v1/reasoning/risks
```

### 9.2 Knowledge Mesh
```
Backend: cherenkov/knowledge/
API: /api/v1/memory (existing)
API: /api/v1/memory/session (new)
```

### 9.3 K8s Operator
```
Backend: operator/
API: /api/v1/governance/k8s-status (new)
```

---

## 10. Non-Negotiable Design Invariants

| Invariant | Meaning |
|-----------|---------|
| D7 | Never auto-edit test code. FE shows suggestions, BE runs reports only. |
| Anti-lock-in | Eject produces vanilla Playwright + openapi-fetch, no CHERENKOV imports. |
| Spec-derived | Expected values come from spec, not LLM. FE reflects this in claim displays. |
| Suggest-only Healing | Healing never auto-commits. FE shows diff, user decides. |

---

## 11. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Glow-heavy theme fails WCAG AA | text-primary for body text only, glow for accents/borders |
| Too many screens overwhelm users | First-run onboarding tour, progressive disclosure |
| Backend not ready for new endpoints | Mock-first contract, build screens with mocks |
| Risk scoring not implemented | Start with static priority, mark as coming from reasoning |

---

## 12. Definition of Done (Per Screen)

✅ Loads with mock data  
✅ Has empty/loading/error states  
✅ Keyboard navigable (j/k, Enter, a/r/c shortcuts)  
✅ Passes `npm run build` and lint  
✅ Matches existing design system tokens  
✅ Works with reduced-motion preference  
✅ Mobile-responsive (< lg icon rail)  
✅ Autonomy settings respected (Assisted default)  

---

## 13. Detailed User Scenarios (Human Pillar Realization)

### Scenario E10-A: Manual QA — Intent to Ejected Test (Non-Coder)

**Persona:** Maya (manual QA, non-coder)

**Precondition:** Explorer has already crawled the target app and surfaced risks (second pair of eyes)

```
1. Maya opens dashboard → sees OverviewScreen with risk digest
2. She types intent: "check guest can checkout with discount code"
3. System shows: 
   - Step-by-step plan (via LLM or heuristic)
   - Mentor idioms: "Seniors also check tenant isolation on checkout flows"
4. Pilot executes live with vision confirmation
5. Step 1 fails (element not found) → Fallback banner: "3 candidates, pick one"
6. Maya selects correct button → execution continues
7. All steps pass → Toast: "Test ejected to tests/checkout.spec.ts"
8. Maya runs ejected test independently: npx playwright test
```

**FE Points:**
- AuthorScreen needs live step preview (not just start/stop)
- Vision-relocate fallback must be prominent
- Eject confirmation must show file path + one-click open

### Scenario E11-A: SDET — Coverage-Guided Generation

**Persona:** Jordan (SDET)

**Precondition:** Coverage data available from unit test runs

```
1. Jordan opens Signals → Coverage tab
2. Sees 3 uncovered endpoints flagged with risk scores
3. Click "Generate tests for uncovered" on an endpoint
4. System shows designed cases with requirement traceability
5. Cases execute → report shows coverage gain
6. Jordan refines one case → system records verdict + idiom
```

**FE Points:**
- SignalsScreen needs coverage drill-down
- Cases table with requirement/risk links
- Refinement without auto-edit (D7 invariant)

### Scenario E12-A: Governance — Model Certification

**Persona:** Sam (QA Lead)

**Precondition:** Multiple LLM tiers configured

```
1. Sam opens Governance screen
2. Sees Model Certification table:
   - qwen2.5-coder:7b → PASS (faithfulness 94%)
   - deepseek-r1:8b → FAIL (faithfulness 72%, below threshold)
3. Status indicator: "Using fallback model"
4. Confidence bands on all risk scores (from §8)
5. Traceability view shows: prompt → model → claims → evidence
```

**FE Points:**
- GovernanceScreen: Certification tab
- Status badges with confidence scores
- Traceability explorer component

### Scenario E13-A: Pairing — Junior Inherits Senior Judgement

**Persona:** Junior QA paired with CHERENKOV

**Precondition:** Idioms stored from senior verdicts

```
1. Junior opens AuthorScreen for "user signup flow"
2. Mentor panel shows:
   - "On signup endpoints, check email verification flow (confirmed 23 times)"
   - "On POST /users, verify 422 on weak passwords (confirmed 41 times)"
3. Junior uses idiom as template → saves time
4. Junior rejects divergence as "intended" → system learns
5. Next junior sees this idiom ranked higher
```

**FE Points:**
- MemoryScreen must show idioms with confirmation count
- AuthorScreen must surface relevant idioms in context
- Idioms must be copyable into intent field

---

## 14. API Contracts Required (BE → FE)

### 14.1 QA Reasoning Endpoints

```typescript
// GET /api/v1/reasoning/plan
// Response: QAPlan for current spec/context
{
  context: {
    artifact: 'openapi_spec',
    maturity: 'production',
    stage: 'release_gate'
  },
  analysis: [
    { id: 'gap-1', type: 'missing_error_response', endpoint: '/pets', 
      severity: 'high', finding: 'No 422 schema defined for invalid input' }
  ],
  risk_register: [
    { id: 'risk-1', description: 'Password validation bypass',
      likelihood: 0.7, impact: 0.9, priority: 'critical',
      requirement_refs: ['req-auth-3'], case_refs: ['case-15'] }
  ],
  designed_cases: [
    { id: 'case-15', title: 'Reject weak passwords',
      requirement_ref: 'req-auth-3', risk_refs: ['risk-1'],
      priority: 'P0', rationale: 'Validates security requirement R-12',
      status: 'planned' }
  ]
}

// POST /api/v1/reasoning/analyze
// Request: { artifact_path, artifact_kind }
// Response: analysis findings array

// POST /api/v1/pilot/step/confirm
// Request: { step_id, confirmed_action }
// Response: { success, next_step_id }
```

### 14.2 Risk Score Integration

```typescript
// Extend Divergence type
interface Divergence {
  // ... existing fields
  riskScore?: number;     // 0-100
  confidence?: number;    // 0-100, from reproduction
  idiomRefs?: string[];   // Idioms that flagged this
}
```

### 14.3 Idiom/Verdict Endpoints

```typescript
// GET /api/v1/memory/idioms?context=<endpoint|flow>
// Response: Idioms ranked by relevance + confirmation
[
  { id: 'idiom-1', 
    pattern: 'On POST endpoints, verify 422 on invalid payload',
    confirmations: 23, decay: 0.1, last_seen: '2026-06-10',
    context: { endpoint: '/users', method: 'POST' } }
]

// POST /api/v1/memory/verdicts
// Request: { divergence_id, action, reason? }
// Response: { success, idiom_created?: boolean }
```

---

## 15. Component Architecture Changes

### 15.1 New UI Primitives

| Component | Purpose | Location |
|-----------|---------|----------|
| `RiskBadge` | Displays risk score 0-100 with color coding | ui/RiskBadge.tsx |
| `ConfidenceBar` | Horizontal bar for confidence % | ui/ConfidenceBar.tsx |
| `StepPreview` | Live Pilot step with action confirmation | ui/StepPreview.tsx |
| `EvidenceDiff` | Side-by-side request/response or visual diff | ui/EvidenceDiff.tsx |
| `TraceabilityTrail` | artifact → prompt+model+claims+evidence | ui/TraceabilityTrail.tsx |
| `MentorPanel` | Context-aware idiom suggestions | ui/MentorPanel.tsx |

### 15.2 Screen State Machines

#### AuthorScreen SM
```
EMPTY → INTUITIVE_TYPING → PLANNING (skeleton) → PENDING_CONFIRMATION → RUNNING (step preview) → COMPLETE/FAIL → EJECTED
```

#### DivergencesScreen SM
```
LOADING → FILTERED_LIST → ROW_HOVER (quick actions) → DRAWER_OPEN (detail) → ACTION_APPLIED (optimistic) → RECONCILED
```

---

## 16. Performance & Resilience Requirements

### 16.1 Loading States
- Skeleton shimmer for all async content
- First meaningful paint < 1s (mock/cache)
- Progressive loading for large divergence lists (>500 items)

### 16.2 Error States
- Backend offline → OfflineOverlay (exists)
- Model timeout → "Inference slow, retry or lower tier" toast
- Large evidence payload → "Loading evidence..." skeleton

### 16.3 Offline Graceful Degradation
```typescript
// lib/api.ts pattern to extend
const withFallback = async<T>(apiCall: () => Promise<T>, mockData: T): Promise<T> => {
  try {
    return await apiCall();
  } catch {
    return mockData;
  }
};
```

---

## 17. Accessibility Requirements

| Requirement | Implementation |
|-------------|----------------|
| WCAG AA contrast | text-primary only for body, glow for accents |
| Keyboard nav | j/k for list, Enter for open, a/r/c for actions |
| Reduced motion | All looping glows disabled, slide/fade instant |
| Screen reader | ARIA roles on nav/lists/dialogs, aria-label on icons |
| Focus management | Visible focus rings with glow-blue, focus-trap in drawers |

---

## 18. Security & Sovereignty Requirements

| Requirement | Implementation |
|-------------|----------------|
| Sovereign mode badge | 🔒 Local-only badge when `egress:none` |
| Evidence sanitization | No raw headers/secrets in evidence payloads |
| Audit trail | Every verdict/action logged with timestamp/user |
| RBAC readiness | Action buttons check permissions before enabling |

---

## 19. Defect Mapping (FE_RECOMMENDATIONS.md → Requirements)

| Def in FE_RECOMMENDATIONS | Req Section | Fix Description | Priority |
|--------------------------|-------------|---------------|----------|
| D-1 `ReviewScreen` setState in render | - | Move parent updates to `useEffect` | MUST (correctness) |
| D-2 `EjectScreen` false success | FE-R01, §6.1 | Honor backend error, show honest state | MUST (integrity) |
| D-3 `actOnDivergence` swallows errors | J2-C | Add rollback + toast on failure | MUST (integrity) |
| D-4 `AuthorScreen` mock replay | J1-B | Wire to real `runPipeline()` + step preview | MUST (flagship) |
| D-5 `HealingScreen` no-op apply | - | Wire to `validateSuite()` stub | SHOULD |
| D-6 TopBar telemetry fiction | - | Label as "Demo" or back with `/cost` | MUST (honesty) |
| D-7 `SetupScreen` raw 400 logs | - | Use toast path, `console.debug` | SHOULD |
| D-9 `OfflineOverlay` retry path | §16 | Ensure `refresh` re-runs `fetchHealth` | MUST (UX) |
| N-1 Breadcrumbs | - | Add `Breadcrumbs` primitive below TopBar | SHOULD |
| N-4 Recent items in ⌘K | - | Extend `CommandPalette` with localStorage history | SHOULD |

---

## 20. Quick Reference — FE Build Order

```
Week 1: Defect fixes (D-1, D-2, D-3, D-4, D-9) + Risk score integration
Week 2: QA Plan screen + Mentor idioms integration  
Week 3: Coverage tab + Governance certification
Week 4: Testing, polish, accessibility audit
```

---

*End of requirements document.*