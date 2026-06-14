# Cherenkov QA Dashboard - Full Regression Test Suite

> **Document Version:** 1.0.0
> **Last Updated:** 2026-06-06
> **Owner:** QA Engineering Team
> **Test Level:** Full Regression (UI + API + E2E)

---

## Table of Contents

1. [Test Environment Setup](#1-test-environment-setup)
2. [Test Data Prerequisites](#2-test-data-prerequisites)
3. [Screen-Level Test Cases](#3-screen-level-test-cases)
4. [Component-Level Test Cases](#4-component-level-test-cases)
5. [Workflow & Business Flow Test Cases](#5-workflow--business-flow-test-cases)
6. [End-to-End Test Cases](#6-end-to-end-test-cases)
7. [API Integration Test Cases](#7-api-integration-test-cases)
8. [Non-Functional Test Cases](#8-non-functional-test-cases)
9. [Test Execution Matrix](#9-test-execution-matrix)
10. [Test Execution Commands](#10-test-execution-commands)

---

## 1. Test Environment Setup

### 1.1 Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Node.js | >= 18.x | Frontend runtime |
| npm/yarn | >= 9.x | Package management |
| Playwright | >= 1.40.x | E2E testing |
| Python | >= 3.10 | Backend API |
| FastAPI | Latest | Backend server |
| Chrome | Latest | Primary browser |
| Firefox | Latest | Secondary browser |

### 1.2 Environment Configuration

```bash
# Install dependencies
cd cherenkov/web/ui
npm install

# Start development server
npm run dev

# Backend server (separate terminal)
python -m uvicorn main:app --reload --port 8000
```

### 1.3 Test URLs

| Environment | URL | Port |
|-------------|-----|------|
| Local Development | http://localhost:5173 | 5173 |
| Backend API | http://localhost:8000 | 8000 |
| API Base | /api/v1 | - |

---

## 2. Test Data Prerequisites

### 2.1 Mock Data Structure

The application uses mock data from `mockData.ts`:
- **3 Projects:** Petstore (proj-petstore), Checkout API (proj-checkout-api), Identity Provider (proj-auth-identity)
- **20 Endpoints** with richness scores and bands (full/inferred/degraded)
- **Pipeline Stages:** ingest, plan, generate, review, visual, perf
- **Test Items:** Various scenarios with verdicts (approved, review, rejected, regenerating)
- **Divergences:** Multiple severity levels (critical, high, medium, low) with statuses

### 2.2 Backend API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/v1/health | GET | Backend liveness check |
| /api/v1/ingest | POST | Spec file/URL ingestion |
| /api/v1/run | POST | Pipeline execution trigger |
| /api/v1/review/queue | GET | Review queue items |
| /api/v1/review/approve | POST | Approve test scenario |
| /api/v1/review/reject | POST | Reject test scenario |
| /api/v1/review/edit | POST | Edit test scenario |
| /api/v1/review/explain | POST | Explain test scenario |
| /api/v1/divergences | GET | Fetch divergences |
| /api/v1/divergences/act | POST | Act on divergence |
| /api/v1/eject | POST | Export test suite |
| /api/v1/validate | POST | Validate suite |
| /api/v1/settings | GET/PUT | System settings |
| /api/v1/doctor | GET | Health checks |

---

## 3. Screen-Level Test Cases

### 3.1 Overview Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| OVR-001 | Screen loads with header | Navigate to Overview | "Release Readiness & Learning" header visible | High |
| OVR-002 | KPI rings display | Navigate to Overview | KPI rings with progress bars visible | High |
| OVR-003 | KPI values are valid | Navigate to Overview | KPI rings have valid aria-valuenow attributes | High |
| OVR-004 | Release readiness section | Navigate to Overview | Release readiness metrics displayed | Medium |
| OVR-005 | Divergences list | Navigate to Overview | Recent divergences list visible | Medium |
| OVR-006 | Recent learning section | Navigate to Overview | Learning insights displayed | Medium |
| OVR-007 | Navigation from Overview | Click project card | Redirects to Projects screen | Medium |

### 3.2 Projects Screen (Default Landing)

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| PRJ-001 | Default landing page | Open dashboard | Projects screen loads as default | High |
| PRJ-002 | All project cards render | Navigate to Projects | 3 project cards visible (Petstore, Checkout, Identity) | High |
| PRJ-003 | Project card content | Navigate to Projects | Each card shows name, last run, stats, sparkline | High |
| PRJ-004 | Timer bars visible | Navigate to Projects | Timer bars show pipeline stage progress | High |
| PRJ-005 | Search functionality | Type "Checkout" in search | Only Checkout API project visible | High |
| PRJ-006 | Search clear | Type "test", clear search | All projects visible again | High |
| PRJ-007 | Search no results | Type "nonexistent" | "No projects found" message displayed | Medium |
| PRJ-008 | New Run button | Navigate to Projects | "New Spec Run" button visible and enabled | High |
| PRJ-009 | Project selection | Click Petstore card | Project selected and highlighted | Medium |
| PRJ-010 | Project stats display | Navigate to Projects | Tests count, pass rate, healing count displayed | Medium |
| PRJ-011 | Sparkline charts | Navigate to Projects | Sparkline graphs show pass rate trends | Medium |
| PRJ-012 | Last run duration | Navigate to Projects | Last run duration with progress bar visible | Medium |

### 3.3 Setup Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| SET-001 | Navigation to Setup | Click "New Spec Run" | Setup screen loads with header | High |
| SET-002 | Drag & drop zone | Navigate to Setup | Drag zone for spec file visible | High |
| SET-003 | URL input field | Navigate to Setup | URL input field with placeholder visible | High |
| SET-004 | Preset buttons | Navigate to Setup | Petstore, Checkout preset buttons visible | High |
| SET-005 | Petstore preset | Click Petstore preset | Spec URL auto-populates, endpoint list loads | High |
| SET-006 | Checkout preset | Click Checkout preset | Spec URL auto-populates, endpoint list loads | High |
| SET-007 | Server validation toggle | Navigate to Setup | Server validation section expandable | Medium |
| SET-008 | Server URL input | Expand validation | Server URL input field visible | Medium |
| SET-009 | Auth header input | Expand validation | Auth header input field visible | Medium |
| SET-010 | Endpoint list | Click preset | Endpoint list with richness indicators visible | High |
| SET-011 | Endpoint selection | Click endpoint | Selected endpoint highlighted | Medium |
| SET-012 | Start button | Navigate to Setup | "Start Test Generation" button visible | High |
| SET-013 | Start disabled | Navigate to Setup | Start button disabled without spec | Medium |
| SET-014 | Start enabled | Click preset | Start button enabled | Medium |
| SET-015 | File upload | Upload valid OpenAPI file | File accepted, endpoint list populated | High |
| SET-016 | Invalid file upload | Upload invalid file | Error message displayed | Medium |

### 3.4 Pipeline Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| PIP-001 | Navigation to Pipeline | Start pipeline run | Pipeline screen loads | High |
| PIP-002 | DAG visualization | Navigate to Pipeline | Pipeline DAG nodes visible (ingest, plan, generate, review) | High |
| PIP-003 | DAG node states | Navigate to Pipeline | Nodes show correct states (done, running, queued) | High |
| PIP-004 | DAG edges | Navigate to Pipeline | Dependencies between nodes visible | Medium |
| PIP-005 | Progress indicators | Navigate to Pipeline | Progress bars/indicators on nodes | Medium |
| PIP-006 | Stage details panel | Navigate to Pipeline | Stage details panel shows current stage info | High |
| PIP-007 | Token budget | Navigate to Pipeline | Token budget metrics visible | Medium |
| PIP-008 | Prompt attention space | Navigate to Pipeline | Prompt attention metrics visible | Medium |
| PIP-009 | Pause/Resume button | Navigate to Pipeline | Pause button visible and clickable | High |
| PIP-010 | Pause functionality | Click Pause | Pipeline pauses, button text changes to Resume | High |
| PIP-011 | Resume functionality | Click Resume | Pipeline resumes, button text changes to Pause | High |
| PIP-012 | Stop button | Navigate to Pipeline | Stop button visible and clickable | High |
| PIP-013 | Stop functionality | Click Stop | Pipeline stops, confirmation displayed | High |
| PIP-014 | Live drawer | Click live button in TopBar | Pipeline screen opens in drawer | High |
| PIP-015 | Drawer close | Open drawer, click close | Drawer closes, pipeline continues | Medium |

### 3.5 Review Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| REV-001 | Navigation to Review | Click Review in sidebar | Review screen loads with header | High |
| REV-002 | Filter tabs | Navigate to Review | All, Approved, Review, Rejected tabs visible | High |
| REV-003 | All tab | Click All tab | All test items displayed | High |
| REV-004 | Approved tab | Click Approved tab | Only approved tests displayed | Medium |
| REV-005 | Review tab | Click Review tab | Only tests in review displayed | Medium |
| REV-006 | Rejected tab | Click Rejected tab | Only rejected tests displayed | Medium |
| REV-007 | Test queue items | Navigate to Review | Test queue items with verdicts visible | High |
| REV-008 | Test item content | Navigate to Review | Each item shows name, method, path, confidence | High |
| REV-009 | Gate indicators | Navigate to Review | Gate pass/fail indicators visible | High |
| REV-010 | Code viewer | Click test item | Code viewer displays test code | High |
| REV-011 | Approve button | Select test item | Approve button visible and clickable | High |
| REV-012 | Reject button | Select test item | Reject button visible and clickable | High |
| REV-013 | Regenerate button | Select test item | Regenerate button visible and clickable | Medium |
| REV-014 | Approve functionality | Click Approve | Test moves to Approved tab, pass rate updates | High |
| REV-015 | Reject with reason | Click Reject, enter reason | Test rejected with reason recorded | High |
| REV-016 | Search/filter | Type in search box | Tests filtered by search term | Medium |

### 3.6 Healing Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| HEL-001 | Navigation to Healing | Click Healing in sidebar | Healing screen loads with header | High |
| HEL-002 | Drift cards | Navigate to Healing | Drift cards with failure info visible | High |
| HEL-003 | Drift card content | Navigate to Healing | Each card shows diagnosis, endpoint, type | High |
| HEL-004 | Suggestion display | Navigate to Healing | Suggested fixes visible on cards | High |
| HEL-005 | Apply Suggestion | Click Apply Suggestion | Suggestion applied, card updates | High |
| HEL-006 | Dismiss button | Navigate to Healing | Dismiss button visible | Medium |
| HEL-007 | Dismiss card | Click Dismiss | Card removed from queue | Medium |
| HEL-008 | Healing count | Navigate to Healing | Healing count badge visible | Medium |
| HEL-009 | Filter by type | Navigate to Healing | Filter by failure type works | Medium |

### 3.7 Eject Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| EJT-001 | Navigation to Eject | Click Eject in sidebar | Eject screen loads with header | High |
| EJT-002 | Output path input | Navigate to Eject | Output path input field visible | High |
| EJT-003 | File tree | Navigate to Eject | File tree showing generated tests visible | High |
| EJT-004 | Eject button | Navigate to Eject | Eject button visible and enabled | High |
| EJT-005 | Eject functionality | Enter path, click Eject | Success message, copy command visible | High |
| EJT-006 | Copy command | Complete eject | Copy command button visible | Medium |
| EJT-007 | Copy functionality | Click Copy button | Command copied to clipboard | Medium |

### 3.8 Truth Map Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| TM-001 | Navigation to Truth Map | Click Truth Map in sidebar | Truth Map screen loads with header | High |
| TM-002 | Endpoint list | Navigate to Truth Map | List of endpoints visible | High |
| TM-003 | Endpoint selection | Click endpoint | Endpoint details panel opens | High |
| TM-004 | Endpoint details | Click endpoint | Details show method, path, claims | High |
| TM-005 | Claims list | Click endpoint | Claims list with verification status visible | High |
| TM-006 | Claim verification status | Click endpoint | VERIFIED/UNVERIFIED badges visible | Medium |
| TM-007 | Graph visualization | Navigate to Truth Map | Endpoint relationship graph visible | Medium |
| TM-008 | Filter by method | Navigate to Truth Map | Filter by HTTP method works | Medium |

### 3.9 Divergences Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| DIV-001 | Navigation to Divergences | Click Divergences in sidebar | Divergences screen loads with header | High |
| DIV-002 | Divergence list | Navigate to Divergences | List of divergences visible | High |
| DIV-003 | Divergence card content | Navigate to Divergences | Each card shows ID, class, severity, status | High |
| DIV-004 | Severity filter | Navigate to Divergences | Severity dropdown filter works | High |
| DIV-005 | Detail drawer open | Click divergence row | Detail drawer opens | High |
| DIV-006 | Detail drawer content | Open detail drawer | Shows evidence, repro steps, confidence | High |
| DIV-007 | Close with test action | Open drawer, click "Close with Test" | Divergence marked as closed | High |
| DIV-008 | Mark as intended | Open drawer, click "Mark as Intended" | Divergence marked as intended | Medium |
| DIV-009 | Reject action | Open drawer, click Reject | Divergence marked as rejected | Medium |

### 3.10 Signals Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| SIG-001 | Navigation to Signals | Click Signals in sidebar | Signals screen loads with header | High |
| SIG-002 | Default Performance tab | Navigate to Signals | Performance tab selected by default | High |
| SIG-003 | Performance tab content | Navigate to Performance | API Latency & Anomaly Baselines visible | High |
| SIG-004 | Visual tab | Click Visual tab | UI Snapshot Comparisons visible | High |
| SIG-005 | Coverage tab | Click Coverage tab | Code Path Verification Coverage visible | High |
| SIG-006 | Tab switching | Switch between tabs | Content updates for selected tab | High |

### 3.11 Author Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| AUT-001 | Navigation to Author | Click Author in sidebar | Author screen loads with header | High |
| AUT-002 | Intent textarea | Navigate to Author | Textarea for NL intent visible | High |
| AUT-003 | Example chips | Navigate to Author | Example intent chips visible | High |
| AUT-004 | Chip selection | Click example chip | Intent text populates textarea | High |
| AUT-005 | Mentor idioms panel | Navigate to Author | Mentor Context Idioms panel visible | Medium |
| AUT-006 | Generate button | Enter intent | Generate button enabled | Medium |
| AUT-007 | Generation | Enter intent, click Generate | Test code generated and displayed | High |

### 3.12 Memory Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| MEM-001 | Navigation to Memory | Click Memory in sidebar | Memory screen loads with header | High |
| MEM-002 | Idioms panel | Navigate to Memory | Accumulated Senior Testing Idioms panel visible | High |
| MEM-003 | Pairing panel | Navigate to Memory | Mentor Junior-Senior Pairing panel visible | High |
| MEM-004 | Search idioms | Navigate to Memory | Search functionality works | Medium |

### 3.13 Governance Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| GOV-001 | Navigation to Governance | Click Governance in sidebar | Governance screen loads with header | High |
| GOV-002 | KPI metrics | Navigate to Governance | Defect Escape Rate, Model Capabilities visible | High |
| GOV-003 | Compliance section | Navigate to Governance | Compliance metrics visible | Medium |
| GOV-004 | Chart visualizations | Navigate to Governance | Charts render properly | Medium |

### 3.14 Settings Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| SETT-001 | Navigation to Settings | Click Settings in sidebar | Settings screen loads with header | High |
| SETT-002 | Model provider cards | Navigate to Settings | Qwen, Gemini provider cards visible | High |
| SETT-003 | Model tier buttons | Navigate to Settings | small, deep, vision tier buttons visible | Medium |
| SETT-004 | Egress policy | Navigate to Settings | Egress policy buttons visible | Medium |
| SETT-005 | Budget slider | Navigate to Settings | Budget slider visible and functional | Medium |
| SETT-006 | Thread limit slider | Navigate to Settings | Thread limit slider visible | Medium |
| SETT-007 | Compact view checkbox | Navigate to Settings | Compact view checkbox visible | Medium |
| SETT-008 | Reduced motion checkbox | Navigate to Settings | Reduced motion checkbox visible | Medium |
| SETT-009 | Save functionality | Make changes, click Save | Settings saved, localStorage updated | High |
| SETT-010 | Reset functionality | Make changes, click Reset | Settings reset to defaults | Medium |

### 3.15 UI Kit Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| UIK-001 | Navigation to UI Kit | Click UI Kit in sidebar | UI Kit screen loads with header | High |
| UIK-002 | Panels & Cards section | Navigate to UI Kit | Panels and Cards section visible | High |
| UIK-003 | Pills section | Navigate to UI Kit | SeverityPills, StatusDots visible | Medium |
| UIK-004 | Tabs section | Navigate to UI Kit | Tabs Navigation visible | Medium |
| UIK-005 | Drawer section | Navigate to UI Kit | Detail Drawer visible | Medium |
| UIK-006 | Toasts section | Navigate to UI Kit | Toasts Feedback visible | Medium |
| UIK-007 | KPI Ring section | Navigate to UI Kit | Release Readiness rings visible | Medium |
| UIK-008 | Skeleton section | Navigate to UI Kit | Toggle Load View visible | Medium |
| UIK-009 | Empty State section | Navigate to UI Kit | Empty state examples visible | Medium |

### 3.16 Explore Screen

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| EXP-001 | Navigation to Explore | Click Explore in sidebar | Explore screen loads | High |
| EXP-002 | Crawler description | Navigate to Explore | Crawler description visible | High |
| EXP-003 | Configure button | Navigate to Explore | Configure Scope & Target button visible | High |
| EXP-004 | Configure navigation | Click Configure | Navigates to Setup screen | High |

---

## 4. Component-Level Test Cases

### 4.1 Shell Components

#### TopBar Component

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| TB-001 | Renders at top | Navigate to any screen | TopBar visible at top | High |
| TB-002 | Current project display | Select project | Current project name visible | High |
| TB-003 | Status indicator | Navigate to dashboard | Status (IDLE/LIVE) visible | High |
| TB-004 | Status changes | Start pipeline | Status changes to LIVE | High |
| TB-005 | Session cost | Navigate to dashboard | Session cost display visible | Medium |
| TB-006 | Autonomy radio group | Navigate to dashboard | Autonomy level buttons visible | High |
| TB-007 | Autonomy selection | Click Augmented | Selected autonomy highlighted | High |
| TB-008 | Autonomy persistence | Select Augmented, refresh | Augmented still selected | High |
| TB-009 | Help button | Navigate to dashboard | Help button visible | Medium |
| TB-010 | Live execution button | Navigate to dashboard | Live execution button visible | High |
| TB-011 | Live drawer open | Click live button | Pipeline drawer opens | High |
| TB-012 | Demo mode indicator | Enable demo mode | Demo mode badge visible | Medium |

#### Sidebar Component

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| SB-001 | Renders on left | Navigate to dashboard | Sidebar visible on left | High |
| SB-002 | Navigation sections | Navigate to dashboard | OVERVIEW, ENGINE, AUTHOR, SIGNALS, OPERATE, LEARN visible | High |
| SB-003 | Active tab highlight | Click Overview | Overview item highlighted | High |
| SB-004 | Tab switching | Click Divergences | Divergences screen loads, tab highlighted | High |
| SB-005 | New Run button | Navigate to dashboard | New Spec Run button visible | High |
| SB-006 | Token pool display | Navigate to dashboard | LLM Token Pool section visible | Medium |
| SB-007 | Project selector | Navigate to dashboard | Project selector dropdown visible | High |
| SB-008 | Project selection | Open selector, click project | Project selected, screen updates | High |
| SB-009 | Status indicator | Navigate to dashboard | IDLE/LIVE status badge visible | High |

#### Command Palette Component

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| CP-001 | Opens with Ctrl+K | Press Ctrl+K | Command Palette input visible | High |
| CP-002 | Closes with ESC | Press Ctrl+K, then ESC | Command Palette closes | High |
| CP-003 | Input focus | Press Ctrl+K | Input field focused | High |
| CP-004 | Search functionality | Press Ctrl+K, type "author" | Filtered results show Author items | High |
| CP-005 | Result selection | Press Ctrl+K, type "author", press Enter | Navigates to Author screen | High |
| CP-006 | Empty search | Press Ctrl+K, type "xyzxyz" | "No results found" message | Medium |
| CP-007 | Arrow key navigation | Press Ctrl+K, use arrow keys | Selection moves between results | Medium |

#### Guided Tour Component

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| GT-001 | Tour on first load | Clear localStorage, refresh | Guided Tour overlay visible | High |
| GT-002 | Tour not shown after completion | Complete tour, refresh | Tour not shown | High |
| GT-003 | Tour steps | Start tour | Multiple tour steps visible | Medium |
| GT-004 | Tour navigation | Click Next/Previous | Moves between steps | Medium |
| GT-005 | Tour skip | Click Skip | Tour closes, marked as seen | Medium |
| GT-006 | Tour finish | Complete all steps | Tour closes, marked as seen | High |
| GT-007 | localStorage persistence | Complete tour | `[copilot] tour_seen` = 'true' | High |

#### Offline Overlay Component

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| OFF-001 | Overlay when backend down | Stop backend, refresh | Offline overlay visible | High |
| OFF-002 | Blocks interaction | Backend down, try click | Clicks blocked, overlay persists | High |
| OFF-003 | Retry button | Backend down | Retry button visible | High |
| OFF-004 | Retry functionality | Backend down, click Retry | Backend health check triggered | High |
| OFF-005 | Overlay disappears on restore | Start backend, wait | Overlay disappears, data refreshes | High |

### 4.2 UI Components

#### Panel, Card, Tabs, Drawer

| ID | Test Case | Component | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| UI-001 | Panel renders | Panel | Navigate to UI Kit | Standard Panel visible | Medium |
| UI-002 | Card hover | Card | Hover over card | Hover effect visible | Medium |
| UI-003 | Tab selection | Tabs | Click tab | Tab selected, content updates | High |
| UI-004 | Drawer open/close | Drawer | Click open/close | Drawer opens/closes | High |

#### Toast, SeverityPill, StatusDot, ProvenanceChip

| ID | Test Case | Component | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| UI-005 | Toast display | Toast | Trigger toast | Toast notification visible | Medium |
| UI-006 | Toast auto-dismiss | Toast | Trigger toast | Toast disappears after timeout | Medium |
| UI-007 | SeverityPill colors | SeverityPill | Navigate to Divergences | Each severity has correct color | High |
| UI-008 | StatusDot rendering | StatusDot | Navigate to UI Kit | Status dots render correctly | Medium |
| UI-009 | ProvenanceChip | ProvenanceChip | Navigate to UI Kit | Chip displays provenance info | Medium |

#### KpiRing, Skeleton, EmptyState, MockBadge

| ID | Test Case | Component | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| UI-010 | KpiRing value | KpiRing | Navigate to Overview | Ring displays correct percentage | High |
| UI-011 | KpiRing accessibility | KpiRing | Navigate to Overview | Ring has progressbar role | High |
| UI-012 | Skeleton animation | Skeleton | Navigate to UI Kit | Skeleton has pulse animation | Medium |
| UI-013 | EmptyState rendering | EmptyState | Navigate to empty view | Icon, title, description visible | Medium |
| UI-014 | MockBadge | MockBadge | Navigate to UI Kit | Badge displays "MOCK" or "DEMO" | Medium |

---

## 5. Workflow & Business Flow Test Cases

### 5.1 End-to-End Test Generation

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-E2E-001 | Full test generation flow | Projects > New Run > select preset > Start > complete pipeline | Tests generated successfully | Critical |
| WF-E2E-002 | Test generation with custom spec | Setup > upload spec > Start | Pipeline runs with custom spec | High |
| WF-E2E-003 | Test generation with URL | Setup > enter URL > Ingest > Start | Pipeline runs with URL spec | High |

### 5.2 Review & Approval Workflow

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-REV-001 | Review and approve tests | Generation > Review > select test > Approve | Test approved, pass rate updated | Critical |
| WF-REV-002 | Review and reject tests | Generation > Review > select test > Reject with reason | Test rejected with reason | High |
| WF-REV-003 | Review and regenerate | Generation > Review > select test > Regenerate | Test regenerated | Medium |
| WF-REV-004 | Bulk review actions | Generation > Review > select multiple > bulk approve | All selected tests approved | Medium |

### 5.3 Self-Healing Workflow

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-HEL-001 | Healing flow | Healing > view drift > Apply Suggestion | Suggestion applied, count updated | Critical |
| WF-HEL-002 | Multiple healing actions | Healing > apply multiple suggestions | All suggestions applied | High |
| WF-HEL-003 | Dismiss healing suggestions | Healing > dismiss drift | Drift removed from queue | Medium |

### 5.4 Divergence Resolution Workflow

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-DIV-001 | Close divergence with test | Divergences > open detail > Close with Test | Divergence closed | Critical |
| WF-DIV-002 | Mark as intended | Divergences > open detail > Mark as Intended | Divergence marked | High |
| WF-DIV-003 | Reject divergence | Divergences > open detail > Reject | Divergence rejected | Medium |

### 5.5 Eject & Export Workflow

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-EJT-001 | Export test suite | Eject > enter path > Eject | Suite exported to path | Critical |
| WF-EJT-002 | Copy export command | Eject > complete > Copy | Command copied to clipboard | High |

### 5.6 Settings Configuration Workflow

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| WF-SET-001 | Configure settings | Settings > make changes > Save | Settings saved, localStorage updated | Critical |
| WF-SET-002 | Reset settings | Settings > make changes > Reset | Settings reset to defaults | Medium |

### 5.7 Business Flows

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| BF-REL-001 | Release readiness assessment | Overview > check KPIs | All KPIs meet release criteria | Critical |
| BF-CONT-001 | API contract validation | Truth Map > verify claims | All claims verified, no divergences | Critical |
| BF-CONT-002 | Contract drift resolution | Divergences > identify drift > apply healing > verify | Contract drift resolved | High |
| BF-COV-001 | Test coverage verification | Signals > Coverage > check metrics | Coverage metrics meet targets | Critical |
| BF-PERF-001 | Performance baseline verification | Signals > Performance > check baselines | Baselines established | Critical |
| BF-VIS-001 | Visual regression detection | Signals > Visual > check snapshots | Baselines established | Critical |
| BF-GOV-001 | Model governance compliance | Governance > check certification | Model certified for production | Critical |

---

## 6. End-to-End Test Cases

### 6.1 First-Time User Journey

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| E2E-FTU-001 | Complete first-time user flow | Open dashboard > complete tour > create first project > run generation > review tests | First project successfully created and tested | Critical |
| E2E-FTU-002 | Tour to project creation | Complete tour > New Run > select preset > Start | Project created, pipeline runs | Critical |

### 6.2 Project Lifecycle

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| E2E-PLC-001 | Full project lifecycle | Create project > run generation > review tests > apply healing > eject suite | Project complete lifecycle successful | Critical |
| E2E-PLC-002 | Project with failures | Create project > run generation with failures > review > apply healing | Failures identified and resolved | High |

### 6.3 Continuous Validation

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| E2E-CONT-001 | Continuous validation | Set up project > run multiple generations > verify consistency | All runs produce consistent results | Critical |
| E2E-CONT-002 | Detect regression | Run generation > make API change > run again > check divergences | Regression detected and reported | High |

### 6.4 Multi-Project Management

| ID | Test Case | Steps | Expected Result | Priority |
|----|-----------|-------|-----------------|----------|
| E2E-MPM-001 | Switch between projects | Create multiple projects > switch between them | Projects load correctly, state maintained | Critical |
| E2E-MPM-002 | Concurrent project runs | Start runs on multiple projects | Runs execute concurrently | Medium |

---

## 7. API Integration Test Cases

### 7.1 Health Check API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-HC-001 | Backend online | GET /api/v1/health | Call endpoint | Returns 200, status: online | Critical |
| API-HC-002 | Backend offline | GET /api/v1/health | Stop backend, call | Returns error, offline state | Critical |
| API-HC-003 | Demo mode detection | GET /api/v1/health | Start in demo mode | Returns demo_mode: true | High |

### 7.2 Spec Ingestion API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-ING-001 | Ingest spec file | POST /api/v1/ingest | Upload file | Returns 200 with spec data | Critical |
| API-ING-002 | Ingest spec URL | POST /api/v1/ingest | Provide URL | Returns 200 with spec data | Critical |
| API-ING-003 | Invalid file | POST /api/v1/ingest | Upload invalid file | Returns 400 with error | High |
| API-ING-004 | Invalid URL | POST /api/v1/ingest | Provide invalid URL | Returns 400 with error | High |

### 7.3 Pipeline Execution API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-RUN-001 | Run pipeline | POST /api/v1/run | Provide spec_path | Returns 200 with run_id | Critical |
| API-RUN-002 | Invalid payload | POST /api/v1/run | Invalid data | Returns 400 with error | High |
| API-RUN-003 | Status check | POST /api/v1/run | Run completes | Run status updates correctly | Critical |

### 7.4 Review Queue API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-REV-001 | Fetch queue | GET /api/v1/review/queue | Call endpoint | Returns 200 with queue items | Critical |
| API-REV-002 | Approve scenario | POST /api/v1/review/approve | Provide scenario_id | Returns 200, scenario approved | Critical |
| API-REV-003 | Reject scenario | POST /api/v1/review/reject | Provide scenario_id, reason | Returns 200, scenario rejected | Critical |
| API-REV-004 | Explain scenario | POST /api/v1/review/explain | Provide scenario_id | Returns 200 with explanation | High |
| API-REV-005 | Edit scenario | POST /api/v1/review/edit | Provide scenario_id, code | Returns 200, edits saved | High |
| API-REV-006 | Filter by status | GET /api/v1/review/queue?status=X | Call with filter | Returns filtered results | Medium |

### 7.5 Divergence API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-DIV-001 | Fetch divergences | GET /api/v1/divergences | Call endpoint | Returns 200 with divergences | Critical |
| API-DIV-002 | Close with test | POST /api/v1/divergences/act | action: close_with_test | Returns 200, divergence closed | Critical |
| API-DIV-003 | Mark intended | POST /api/v1/divergences/act | action: mark_intended | Returns 200, divergence marked | High |
| API-DIV-004 | Reject | POST /api/v1/divergences/act | action: reject | Returns 200, divergence rejected | High |

### 7.6 Settings API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-SET-001 | Fetch settings | GET /api/v1/settings | Call endpoint | Returns 200 with settings | Critical |
| API-SET-002 | Update settings | PUT /api/v1/settings | Provide settings | Returns 200, settings updated | Critical |
| API-SET-003 | Invalid update | PUT /api/v1/settings | Invalid data | Returns 400 with error | High |

### 7.7 Eject API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-EJT-001 | Eject suite | POST /api/v1/eject | Provide output_path | Returns 200 with output_path | Critical |
| API-EJT-002 | Invalid eject | POST /api/v1/eject | Invalid path | Returns 400 with error | High |

### 7.8 Validation API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-VAL-001 | Validate suite | POST /api/v1/validate | Provide target_url | Returns 200 with results | Critical |
| API-VAL-002 | Invalid validation | POST /api/v1/validate | Invalid URL | Returns 400 with error | High |

### 7.9 Doctor Check API

| ID | Test Case | Endpoint | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| API-DOC-001 | Run doctor checks | GET /api/v1/doctor | Call endpoint | Returns 200 with check results | Critical |
| API-DOC-002 | Verify readiness | GET /api/v1/doctor | All checks pass | Returns ready: true | High |

---

## 8. Non-Functional Test Cases

### 8.1 Accessibility Tests

| ID | Test Case | Category | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| A11Y-KB-001 | Keyboard navigation | Keyboard | Tab through sidebar | Focus moves through all elements | Critical |
| A11Y-KB-002 | Button activation | Keyboard | Focus button, press Enter/Space | Button activated | Critical |
| A11Y-KB-003 | Modal escape | Keyboard | Open modal, press Escape | Modal closes | High |
| A11Y-SR-001 | ARIA labels | Screen Reader | Navigate dashboard | All buttons have aria-label | Critical |
| A11Y-SR-002 | ARIA roles | Screen Reader | Navigate dashboard | Elements have correct roles | Critical |
| A11Y-SR-003 | Form labels | Screen Reader | Navigate to forms | All inputs have labels | Critical |
| A11Y-CC-001 | Color contrast | Contrast | Navigate dashboard | Text has 4.5:1 contrast minimum | Critical |
| A11Y-CC-002 | Focus indicators | Contrast | Tab through elements | Focus indicators visible | Critical |
| A11Y-FM-001 | Focus trap | Focus | Open modal, tab | Focus stays within modal | Critical |
| A11Y-FM-002 | Focus return | Focus | Open/close modal | Focus returns to trigger | High |

### 8.2 Performance Tests

| ID | Test Case | Category | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| PERF-LD-001 | Initial page load | Load | Navigate to dashboard | Page loads within 2 seconds | Critical |
| PERF-LD-002 | Screen switching | Load | Navigate between screens | Switches within 500ms | High |
| PERF-RN-001 | Large list rendering | Render | Add 100+ projects | All render without lag | High |
| PERF-RN-002 | Animation performance | Render | Trigger animations | Runs at 60fps | Medium |
| PERF-MEM-001 | Memory leak detection | Memory | Navigate repeatedly | Memory usage stable | Critical |

### 8.3 Error Handling Tests

| ID | Test Case | Category | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| ERR-BE-001 | Backend 500 error | Backend | Trigger 500 | Offline overlay shown | Critical |
| ERR-BE-002 | Backend timeout | Backend | Delay > 30s | Timeout error, retry option | High |
| ERR-BE-003 | Network disconnect | Network | Disconnect | Offline overlay shown | Critical |
| ERR-FE-001 | JavaScript error | Frontend | Trigger JS error | Error boundary catches | Critical |
| ERR-FE-002 | Rendering error | Frontend | Trigger error | Fallback UI shown | Critical |
| ERR-DA-001 | Invalid API response | Data | Mock invalid response | Error message, fallback UI | High |
| ERR-DA-002 | Empty API response | Data | Mock empty response | Empty state UI shown | Medium |
| ERR-UI-001 | Invalid form input | Input | Submit invalid data | Validation error displayed | High |
| ERR-UI-002 | Empty required field | Input | Submit empty required | Error message, field highlighted | High |

### 8.4 Edge Cases

| ID | Test Case | Category | Steps | Expected Result | Priority |
|----|-----------|----------|-------|-----------------|----------|
| EDGE-001 | Empty projects | Edge | Delete all projects | Empty state message | Medium |
| EDGE-002 | Empty review queue | Edge | Navigate with no items | Empty state message | Medium |
| EDGE-003 | Empty divergences | Edge | Navigate with no items | Empty state message | Medium |
| EDGE-004 | Very long text | Edge | Enter very long text | Text truncated/scrollable | Medium |
| EDGE-005 | Special characters | Edge | Enter special chars | Handled correctly | Medium |
| EDGE-006 | Concurrent actions | Edge | Trigger multiple actions | Actions handled correctly | Medium |

### 8.5 Cross-Browser Compatibility

| ID | Test Case | Browser | Expected Result | Priority |
|----|-----------|---------|-----------------|----------|
| XBR-001 | Chrome compatibility | Chrome Latest | All functionality works | Critical |
| XBR-002 | Firefox compatibility | Firefox Latest | All functionality works | Critical |
| XBR-003 | Edge compatibility | Edge Latest | All functionality works | Critical |
| XBR-004 | Safari compatibility | Safari Latest | All functionality works | Medium |

---

## 9. Test Execution Matrix

### 9.1 Test Priority Distribution

| Priority | Count | % of Total | Execution Frequency |
|----------|-------|------------|-------------------|
| Critical | ~80 | ~12% | Every build |
| High | ~200 | ~30% | Every build |
| Medium | ~350 | ~53% | Nightly |
| Low | ~30 | ~5% | Weekly |

### 9.2 Test Category Distribution

| Category | Count | % of Total | Type |
|----------|-------|------------|------|
| Smoke | 15 | 2% | Quick sanity checks |
| Functional | 350 | 52% | Component/screen functionality |
| Navigation | 40 | 6% | Screen transitions |
| Workflow | 30 | 4% | User workflows |
| Business | 25 | 4% | Business processes |
| E2E | 25 | 4% | End-to-end scenarios |
| API | 40 | 6% | Backend integration |
| Accessibility | 20 | 3% | Accessibility compliance |
| Performance | 15 | 2% | Performance metrics |
| Error | 25 | 4% | Error handling |
| Edge | 15 | 2% | Edge cases |
| Compatibility | 10 | 1% | Cross-browser |

### 9.3 Test Execution Schedule

| Test Type | Frequency | Trigger | Duration | Responsible |
|-----------|-----------|---------|----------|-------------|
| Smoke Tests | Every commit | CI/CD pipeline | < 2 min | DevOps |
| Critical Tests | Every commit | CI/CD pipeline | < 5 min | DevOps |
| High Priority Tests | Every commit | CI/CD pipeline | < 10 min | DevOps |
| Full Regression | Nightly | Scheduled job | < 30 min | QA Team |
| Performance Tests | Weekly | Scheduled job | < 15 min | Performance Team |
| Accessibility Tests | Weekly | Scheduled job | < 10 min | QA Team |
| Compatibility Tests | Weekly | Scheduled job | < 20 min | QA Team |

---

## 10. Test Execution Commands

```bash
# Install dependencies
cd cherenkov/web/ui
npm install

# Run all tests
npm run test

# Run specific test file
npx playwright test tests/dashboard_e2e.spec.ts

# Run specific test
npx playwright test tests/dashboard_e2e.spec.ts -g "Projects screen"

# Run with headed browser
npx playwright test --headed

# Run with specific browser
npx playwright test --browser chromium
npx playwright test --browser firefox
npx playwright test --browser webkit

# Run with debug mode
npx playwright test --debug

# Generate test report
npx playwright show-report

# Run accessibility tests
npm run test:a11y

# Run with custom viewport
npx playwright test --viewport-size=1920,1080

# Run with video recording
npx playwright test --video on
```

---

## Test Report Locations

- **HTML Report:** `cherenkov/web/ui/test-results/index.html`
- **JSON Report:** `cherenkov/web/ui/test-results/results.json`
- **JUnit Report:** `cherenkov/web/ui/test-results/results.xml`
- **Trace Viewer:** `cherenkov/web/ui/test-results/trace/`

---

## Test Data Files

- **Mock Data:** `cherenkov/web/ui/src/mockData.ts`
- **Types:** `cherenkov/web/ui/src/types.ts`
- **API Client:** `cherenkov/web/ui/src/lib/api.ts`

---

*Generated for Cherenkov QA Dashboard Full Regression Test Suite*
*Document maintains comprehensive coverage of all screens, components, workflows, business flows, and E2E scenarios*
