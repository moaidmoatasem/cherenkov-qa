# CHERENKOV QA M1 Audit — Codebase, UI/UX, Backend API, and Test Infrastructure

**Audit Timestamp**: 2026-08-02T04:25:00Z  
**Subagent**: Explorer (`explorer_m1_audit`)  
**Working Directory**: `Z:\home\moaid\cherenkov-qa\.agents\explorer_m1_audit`  
**SSOT Baseline**: `docs/` & `AGENTS.md` (Clean Architecture, Ports/Adapters, SDD Protocol)

---

## 1. Executive Summary

This comprehensive audit evaluates the CHERENKOV QA platform across four domains to prepare for the M1 UI Revamp project:
1. **Frontend & UI Architecture**: Unified React + TypeScript + Vite web app hosted at `cherenkov/web/ui/` and packaged into Tauri 2 desktop shell (`desktop/src-tauri/`).
2. **Backend API & Services**: FastAPI backend at `cherenkov/web/api.py` offering 22 mounted API routers across REST, SSE streaming, and IPC channels.
3. **Test Infrastructure**: Playwright 1.61.0 setup configured in `cherenkov/web/ui/playwright.config.ts` with 35+ test spec files.
4. **Architectural Revamp Blueprint**: Strategic consolidation from **28 fragmented tabs** down to **5 core logical workspaces**, removing legacy/fake overlays and wiring all UI controls directly into live backend APIs.

---

## 2. Frontend / Dashboard Inspection

### 2.1 UI Code Location & Target Tree
* **Primary Frontend Directory**: `cherenkov/web/ui/`
* **Desktop Shell Entry**: `desktop/src-tauri/tauri.conf.json` (loads `../../cherenkov/web/ui/dist` in production, `http://127.0.0.1:8000` in dev mode)
* **Main UI Entry Points**:
  * `cherenkov/web/ui/src/main.tsx` — React DOM render root
  * `cherenkov/web/ui/src/App.tsx` — Top-level router, state container, and layout manager
  * `cherenkov/web/ui/src/components/Sidebar.tsx` — Navigation panel

### 2.2 UI Framework, Build Tools, & Dependencies
* **Framework**: React 19.0.1 + React DOM 19.0.1
* **Language & Router**: TypeScript 5.8.2 + React Router DOM 6.20.0
* **Build Tooling**: Vite 6.2.3 + `@vitejs/plugin-react` 5.0.4 + esbuild 0.25.0
* **Styling & CSS**: Tailwind CSS 4.1.14 + `@tailwindcss/vite` 4.1.14 + Autoprefixer 10.4.21
* **Icons**: `lucide-react` 0.546.0
* **Testing Setup**: `@playwright/test` 1.56.1 / 1.61.0 + `@axe-core/playwright` 4.11.3

### 2.3 Comprehensive UI Screen Inventory (28 Existing Tabs)

| Section Label | Tab ID | Component Name | Description | Status / Data Source |
| :--- | :--- | :--- | :--- | :--- |
| **OVERVIEW** | `overview` | `OverviewScreen.tsx` | Release readiness dashboard & KPIs | Real API (`/api/v1/overview`) + `MockBadge` fallback |
| | `truth-map` | `TruthMapScreen.tsx` | Endpoint claim graph visualization | Real API (`/api/v1/truth-map`) + `MockBadge` fallback |
| | `signals` | `SignalsScreen.tsx` | Performance & coverage signals | Marked `isDemo: true` in sidebar |
| | `verdict` | `VerdictScreen.tsx` | Run grades & verdict history | Real API (`/api/v1/runs`) |
| **AUTHOR & GENERATE** | `setup` | `SetupScreen.tsx` | Spec upload, doctor check, endpoint selector | Real API (`/api/v1/ingest`, `/api/v1/doctor`) |
| | `pipeline` | `PipelineScreen.tsx` | Live test generation DAG & log stream | Real API (`/api/v1/run`) |
| | `author` | `AuthorScreen.tsx` | Natural language intent-driven test authoring | Real API (`/api/v1/run`) |
| | `healing` | `HealingScreen.tsx` | API drift auto-healing suggestions | Real API (`/api/v1/divergences`) |
| **TRIAGE** | `review` | `ReviewScreen.tsx` | HITL test approval queue & diffs | Real API (`/api/v1/review/*`) |
| | `divergences` | `DivergencesScreen.tsx` | Risk-scored divergence triage | Real API (`/api/v1/divergences`) |
| | `spec-vs-reality` | `SpecVsRealityScreen.tsx` | Side-by-side spec vs server response diff | Duplicate view of `DivergencesScreen` |
| **COVERAGE & CERTIFICATION** | `coverage` | `CoverageScreen.tsx` | Integrity heatmap & coverage metrics | Real API (`/api/v1/metrics`) |
| | `test-management` | `TestManagementScreen.tsx` | Generated test suite viewer | Real API (`/api/v1/tests`) |
| | `certificate` | `CertificateVerificationScreen.tsx` | Verification badge & certificate viewer | Static verification viewer |
| **KNOWLEDGE** | `memory` | `MemoryScreen.tsx` | Reflector memory & QA idioms | Real API (`/api/v1/memory`) |
| | `knowledge` | `KnowledgeExplorerScreen.tsx` | GraphRAG Second Brain explorer | Real API (`/api/v1/chat/knowledge/query`) + `MockBadge` |
| | `chat` | `ChatScreen.tsx` | AI assistant with SSE streaming | Real API (`/api/v1/chat/*`) |
| | `explore` | `ExplorerScreen.tsx` | Autonomous spec-optional web crawler | Real API (`/api/v1/explore`) |
| **SYSTEM** | `governance` | `GovernanceScreen.tsx` | Governance KPI report & compliance | Real API (`/api/v1/governance`) |
| | `devices` | `DeviceManagerScreen.tsx` | VLM execution device status | Real API (`/api/v1/health`) + `MockBadge` |
| | `mobile` | `MobileScreen.tsx` | Mobile testing & Maestro pilot status | Real API (`/api/v1/mobile/pilot`) + `MockBadge` |
| | `eject` | `EjectScreen.tsx` | Plain Playwright exporter | Real API (`/api/v1/eject`) |
| | `sdd` | `SddDashboardScreen.tsx` | SDD agent memory cockpit & tokens | Real API (`/api/v1/sdd/*`) |
| | `setup-wizard` | `SetupWizard.tsx` | Desktop setup wizard stepper | Duplicate view of `SetupScreen` |
| | `visual-regression` | `VisualRegressionScreen.tsx` | VLM screenshot diff viewer | Marked `isDemo: true`, hardcoded fake diff |
| | `projects` | `ProjectsScreen.tsx` | Workspace project switcher & manager | Real API (`/api/v1/projects`) |
| | `settings` | `SettingsScreen.tsx` | System settings & model configuration | Real API (`/api/v1/settings`) |
| | `ui-kit` | `UiKitScreen.tsx` | Primitive UI component gallery | Dev-only design system sandbox |

### 2.4 Legacy, Mocked, Obsolete, or Disconnected Features Target List

1. **`MockBadge.tsx` Component Overlays**:
   * Currently rendered across 6 screens (`OverviewScreen`, `TruthMapScreen`, `KnowledgeExplorerScreen`, `DeviceManagerScreen`, `MobileScreen`, `VisualRegressionScreen`).
   * **Action**: Remove `MockBadge` component entirely; bind UI views directly to live API endpoints and display empty/loading states when unpopulated.
2. **Hardcoded Spec Mockups in `SetupScreen.tsx`**:
   * Preset mock buttons for `swagger-petstore-v2.json` and `checkout-gateway-api.json`.
   * **Action**: Replace hardcoded presets with real repository spec auto-detection (`/api/v1/projects`).
3. **Fake Visual Regression Screenshots in `VisualRegressionScreen.tsx`**:
   * Uses hardcoded base64 placeholders and static diff boxes.
   * **Action**: Replace with live visual scenario inspector (`/api/v1/visual/scenarios`).
4. **Duplicated & Overlapping Views**:
   * `SpecVsRealityScreen` (line-by-line diff) overlaps 100% with `DivergencesScreen` and `HealingScreen`.
   * `SetupWizard` overlaps with `SetupScreen`.
   * `TruthMapScreen` overlaps with `KnowledgeExplorerScreen`.
   * **Action**: Consolidate redundant screens into 5 primary workspace views.
5. **Legacy Text-Based Dashboard CLI Renderer (`cherenkov/dashboard/render.py`)**:
   * Contains hardcoded `MOCK_CLAIMS` and `MOCK_DIVERGENCES` arrays.
   * **Action**: Deprecate CLI text renderer or delegate CLI dashboard output to FastAPI live data.
6. **Obsolete Web Root Files (`website/`)**:
   * Unused static HTML/CSS/JS files in root `website/`.
   * **Action**: Mark as obsolete; `cherenkov/web/ui/` is the single SSOT frontend.

---

## 3. Backend API & Service Inspection

### 3.1 Backend Architecture & Entry Point
* **Framework**: FastAPI 1.3.0
* **API Entry Point**: `cherenkov/web/api.py`
* **Execution Command**: `cherenkov review` (launches `uvicorn.run(app, host=0.0.0.0, port=8000)`)
* **Core Middlewares**:
  1. `CORSMiddleware` (outermost, permitting `localhost:3000`, `localhost:5173`, `127.0.0.1:3000`)
  2. `SecurityHeadersMiddleware`
  3. `JWTAuthMiddleware`
  4. `RateLimitMiddleware`

### 3.2 Backend Routers & Endpoint Map (22 Routers)

| Router / Module | Path Prefix | Key Endpoints | Backend Capability / Service |
| :--- | :--- | :--- | :--- |
| `auth_router` | `/api/v1/auth` | `POST /login`, `POST /logout`, `GET /me`, `POST /refresh` | JWT User Authentication & RBAC |
| `conformance_router` | `/api/v1` | `POST /ingest`, `POST /run`, `POST /validate`, `POST /eject`, `GET /doctor`, `GET /tests` | Spec Richness Ingest, LLM Pipeline Run, Playwright Validation, Eject Suite |
| `review_router` | `/api/v1/review` | `GET /queue`, `POST /approve`, `POST /reject`, `POST /explain`, `POST /edit` | HITL Verdict Memory & Gate Review |
| `divergence_router` | `/api/v1/divergences` | `GET /`, `POST /act` | Risk-Scored Divergence Triage & Resolution |
| `workspace_router` | `/api/v1/projects` | `GET /`, `POST /`, `PATCH /{id}` | Workspace & Project Management |
| `ops_router` | `/api/v1/settings` | `GET /`, `PUT /` | Engine Config, Security Egress, Model Routing |
| `chat_router` | `/api/v1/chat` | `POST /sessions`, `POST /sessions/{id}/stream`, `GET /sessions/{id}/messages` | Tool-Calling Chat Agent with SSE Token Streaming |
| `knowledge_router` | `/api/v1/knowledge` | `POST /query`, `GET /mesh` | GraphRAG Second Brain & Knowledge Mesh |
| `sdd_router` | `/api/v1/sdd` | `GET /status`, `GET /sessions`, `GET /tokens`, `GET /context`, `POST /compact`, `GET /graph/export` | SDD Protocol Cockpit & Token Budget Tracking |
| `health_router` | `/api/v1/health` | `GET /health` | Backend Liveness & HW Device Diagnostics |
| `metrics_router` | `/api/v1/metrics` | `GET /metrics` | Observability Token Pool & Maintenance Metrics |
| `data_router` | `/api/v1` | `GET /overview`, `GET /truth-map`, `GET /failures`, `GET /signals`, `GET /governance`, `GET /memory` | Aggregated Analytics & State Snapshots |
| `mobile_router` | `/api/v1/mobile` | `GET /pilot/status`, `POST /pilot/start` | Maestro Mobile Device Pilot Controller |
| `runs_router` | `/api/v1/runs` | `GET /runs` | Run History Records & Verdict Grades |
| `ocr_router` | `/api/v1/ocr` | `GET /review/{id}`, `POST /review/{id}`, `GET /status` | Vision-Language OCR Code Review |
| `integrity_router` | `/api/v1/integrity` | `GET /status`, `POST /verify` | Integrity-as-a-Service Signatures |
| `teleport_router` | `/api/v1/teleport` | `POST /session`, `GET /qr` | Remote Session Teleport & QR Code Join |
| `routines_router` | `/api/v1/routines` | `GET /`, `POST /` | Scheduled Test Routines & Cron Triggers |

### 3.3 UI-to-Backend Communication Channels
1. **REST HTTP API**: Synchronous JSON payloads over `/api/v1/*` (configured via Vite proxy `/api/v1` -> `http://127.0.0.1:8000/api/v1`).
2. **Server-Sent Events (SSE)**: Event streams over HTTP for real-time chat token streaming (`streamChatMessage` in `lib/api.ts`).
3. **IPC (Tauri Sidecar Bridge)**: Desktop IPC events via `listenDesktop()` listening for `engine-healthy`, `engine-stopped`, `engine-demo-mode`.
4. **Polled Liveness & Metrics**: Client-side polling via `useHealth` (5s interval) and metrics ticker (30s interval).

---

## 4. UI Automation & Test Infrastructure Inspection

### 4.1 Node Environment & Dependencies
* **Playwright Version**: `@playwright/test` 1.56.1 / 1.61.0 (verified CLI binary installed)
* **Accessibility Testing**: `@axe-core/playwright` 4.11.3
* **Target Base URL**: `http://localhost:3000` (auto-launches Vite dev server via `webServer` config)

### 4.2 Existing Playwright Test Suites
* **Configuration**: `cherenkov/web/ui/playwright.config.ts`
* **Test Directory**: `cherenkov/web/ui/tests/`
* **Key Spec Suites**:
  * `dashboard_e2e.spec.ts` — Core end-to-end user navigation flow.
  * `a11y.spec.ts` — Automated WCAG accessibility audit using Axe.
  * `qa/e2e-journeys.spec.ts` — End-to-end user journey tests across projects and pipelines.
  * `qa/api-contract-integration.spec.ts` — Integration tests validating UI against backend API contracts.
  * `qa/functional-suite.spec.ts` — Deep functional UI assertions.
  * Screen-specific deep specs: 20 `*_deep.spec.ts` files covering individual screens.
* **Page Object Model Patterns**: Centralized page objects in `cherenkov/web/ui/tests/qa/page-objects.ts` and test data factories in `qa/test-data-factory.ts`.

---

## 5. Architectural Blueprint for UI Revamp (R1, R2, R3)

### 5.1 Proposed 5-Workspace Component Architecture

```
cherenkov/web/ui/src/
├── App.tsx                     # Top-level Router & Provider Shell
├── main.tsx                    # React Root Mount
├── index.css                   # Tailwind v4 Base Styles & Theme Tokens
├── types.ts                    # Strongly Typed Domain & API Models
├── context/
│   ├── AuthContext.tsx         # JWT Auth State & Session Management
│   └── WorkspaceContext.tsx    # Active Workspace & Project State Store
├── lib/
│   ├── api.ts                  # Clean API Client Layer
│   ├── useHealth.ts            # Backend Health & Offline Overlay Hook
│   └── tauri.ts                # Tauri Desktop IPC Bridge
├── components/
│   ├── layout/
│   │   ├── AppHeader.tsx       # Top Bar with Project Switcher & Health
│   │   ├── NavigationBar.tsx   # 5-Workspace Workspace Navigation Bar
│   │   ├── OfflineBanner.tsx   # Offline State Guard Overlay
│   │   └── CommandPalette.tsx  # Global Keyboard Shortcut Palette
│   ├── ui/                     # Reusable Primitives
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   ├── Table.tsx
│   │   └── Toast.tsx
│   └── workspaces/             # The 5 Core Revamped Workspaces
│       ├── DashboardWorkspace/ # Workspace 1: Dashboard & Release Gate
│       │   ├── ReleaseReadinessCard.tsx
│       │   ├── VerdictHistoryTable.tsx
│       │   └── IntegrityHeatmap.tsx
│       ├── AuthoringWorkspace/ # Workspace 2: Spec & Test Authoring
│       │   ├── SpecIngestPanel.tsx
│       │   ├── DoctorCheckWidget.tsx
│       │   ├── IntentAuthoringPanel.tsx
│       │   └── LivePipelineMonitor.tsx
│       ├── TriageWorkspace/    # Workspace 3: Triage & Healing Gate
│       │   ├── HitlReviewQueue.tsx
│       │   ├── DivergenceTable.tsx
│       │   └── SpecVsRealityDiffViewer.tsx
│       ├── IntelligenceWorkspace/# Workspace 4: Second Brain & AI
│       │   ├── SseChatAssistant.tsx
│       │   ├── KnowledgeGraphExplorer.tsx
│       │   └── SddMemoryCockpit.tsx
│       └── SettingsWorkspace/  # Workspace 5: Infrastructure & Config
│           ├── ProjectManager.tsx
│           ├── DeviceManager.tsx
│           ├── EjectSuitePanel.tsx
│           └── GovernanceSettings.tsx
```

### 5.2 View-to-API Endpoint Mapping Matrix

| Workspace | View / Tab | Primary API Endpoints | HTTP Method |
| :--- | :--- | :--- | :--- |
| **1. Dashboard** | Overview & Release Gate | `/api/v1/overview`, `/api/v1/runs` | `GET` |
| | Verdict History | `/api/v1/runs` | `GET` |
| | Integrity Heatmap | `/api/v1/metrics`, `/api/v1/signals` | `GET` |
| **2. Authoring** | Spec Ingest & Doctor | `/api/v1/ingest`, `/api/v1/doctor` | `POST`, `GET` |
| | Intent Authoring | `/api/v1/run` | `POST` |
| | Pipeline Execution | `/api/v1/run` (Live status) | `POST` |
| | Spec Explorer | `/api/v1/explore` | `POST` |
| **3. Triage** | HITL Review Queue | `/api/v1/review/queue`, `/api/v1/review/approve`, `/api/v1/review/reject` | `GET`, `POST` |
| | Divergence Triage & Diff | `/api/v1/divergences`, `/api/v1/divergences/act` | `GET`, `POST` |
| | Visual/OCR Triage | `/api/v1/ocr/review` | `GET`, `POST` |
| **4. Intelligence** | AI Chat Assistant | `/api/v1/chat/sessions`, `/api/v1/chat/sessions/{id}/stream` | `POST` (SSE) |
| | Knowledge Mesh | `/api/v1/chat/knowledge/query` | `POST` |
| | Reflector & SDD | `/api/v1/memory`, `/api/v1/sdd/status`, `/api/v1/sdd/tokens` | `GET` |
| **5. Settings** | Project Management | `/api/v1/projects` | `GET`, `POST`, `PATCH` |
| | Device Manager | `/api/v1/health`, `/api/v1/mobile/pilot` | `GET`, `POST` |
| | Eject Suite | `/api/v1/eject` | `POST` |
| | Governance & Settings | `/api/v1/settings`, `/api/v1/governance` | `GET`, `PUT` |

### 5.3 E2E UI Automation Test Strategy (Playwright)

We will structure the Playwright E2E suite to mirror the 5 revamped workspaces, placing specs under `cherenkov/web/ui/tests/e2e/`:

1. **`dashboard-workspace.spec.ts`**:
   * Validates loading release readiness score, verdict history table, and integrity heatmap.
2. **`authoring-workspace.spec.ts`**:
   * Validates uploading an OpenAPI spec, running `doctor` checks, triggering LLM test generation, and monitoring the live pipeline DAG.
3. **`triage-workspace.spec.ts`**:
   * Validates reviewing generated test scenarios, approving/rejecting queue items, and triaging API divergence reports.
4. **`intelligence-workspace.spec.ts`**:
   * Validates initializing a chat session, streaming assistant tokens via SSE, querying Second Brain knowledge, and inspecting SDD token metrics.
5. **`settings-workspace.spec.ts`**:
   * Validates switching projects, editing system settings, checking VLM device status, and running plain Playwright eject export.

---

## 6. Actionable Next Steps

1. **Clean Codebase Target Execution**:
   * Remove `MockBadge.tsx` and static mock fallback data.
   * Merge duplicated views (`SpecVsRealityScreen`, `SetupWizard`, `TruthMapScreen`).
2. **Implement 5-Workspace Layout**:
   * Refactor `App.tsx` and `Sidebar.tsx` to mount the 5 clean workspaces (`DashboardWorkspace`, `AuthoringWorkspace`, `TriageWorkspace`, `IntelligenceWorkspace`, `SettingsWorkspace`).
3. **Backend SPA Routing Fix**:
   * Add SPA fallback route (`/{full_path:path}`) in `cherenkov/web/routes/static_routes.py` so deep link refreshes load `index.html`.
4. **E2E Playwright Suite Execution**:
   * Add new Playwright workspace specs and verify all pass against live backend (`cherenkov review`).
