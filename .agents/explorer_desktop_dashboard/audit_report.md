# Subsystem 5 Deep-Dive Audit Report: Desktop Host (Tauri 2) & Dashboard UI

**Target Subsystem:** Desktop Host (Tauri 2 App) & Web/Dashboard UI  
**Target Path:** `Z:\home\moaid\cherenkov-qa\desktop\` & `Z:\home\moaid\cherenkov-qa\cherenkov\web\ui\`  
**Auditor:** Explorer 5  
**Date:** 2026-08-02  

---

## 1. Executive Summary

Subsystem 5 provides the cross-platform desktop host application (Tauri v2 + Rust) and the single-page web dashboard (React 19 + TypeScript 5.8 + Vite 6 + Tailwind CSS v4). It enables developers and QA engineers to operate CHERENKOV-QA either as a standalone desktop app or as a web application backed by an engine sidecar process.

### Key Audit Findings
1. **Dual-Execution Architecture:** The frontend (`cherenkov/web/ui`) is decoupled from the desktop wrapper (`desktop/src-tauri`) and runs identically in pure browser mode or embedded within Tauri 2 WebKit/WebView2 views. A zero-cost JS adapter (`lib/tauri.ts`) probes `window.__TAURI__` dynamically to route commands without hard runtime dependencies.
2. **Native Sidecar Lifecycle Management:** The Rust core spawns `cherenkov-launcher` as an async sidecar, parses NDJSON streams over stdout/stderr for port discovery and health readiness, and auto-navigates the Tauri webview to dynamic engine ports.
3. **5 Workspaces & 9 Specialized UI Screens:** The UI features a clean, tabbed 5-Workspace layout (`Dashboard`, `Authoring`, `Triage`, `Intelligence`, `Settings`) integrating 9 high-level functional screens (`DeviceManagerScreen`, `KnowledgeExplorerScreen`, `HealthWidget`, `MobilePilotScreen`, `SseChatAssistant`, `SddDashboardScreen`, `VerdictHistoryTable`, `DivergenceTable`, `HitlReviewQueue`).
4. **Resilient Hardware & Doctor Probe:** Hardware detection in Rust (`hardware.rs`) and health diagnostics in Python (`/api/v1/doctor`) work together to detect CPUs, ADB, Maestro, Node.js, Python, and Ollama/LocalAI VLM runtimes.
5. **Real-time SSE & Desktop Event Streaming:** Streaming AI answers (`/api/v1/chat/sessions/{id}/stream`), file watcher events (`spec-changed`), and engine state transitions (`engine-ready`, `engine-healthy`) synchronize via standard Server-Sent Events (SSE) and Tauri window events.

---

## 2. Desktop Tauri 2 Architecture

The desktop host resides under `desktop/src-tauri/` and is built using **Tauri v2.0**.

### 2.1 Cargo Manifest & Dependencies
- **Manifest Path:** `desktop/src-tauri/Cargo.toml`
- **Key Dependencies:**
  - `tauri = { version = "2", features = ["devtools"] }`
  - `tauri-plugin-shell = "2"` (Sidecar execution and process management)
  - `tauri-plugin-updater = "2"` (In-app updates via GitHub Releases)
  - `tauri-plugin-notification = "2"`, `tauri-plugin-dialog = "2"`, `tauri-plugin-fs = "2"`, `tauri-plugin-http = "2"`, `tauri-plugin-process = "2"`
  - `notify = "8"` (Native filesystem watcher)
  - `which = "8"` (Executable path resolution on system PATH)
  - `reqwest = { version = "0.13", features = ["json"] }` (HTTP health check client)
  - `tokio = { version = "1", features = ["full"] }` (Async runtime)

### 2.2 Core Rust Binary (`src/main.rs`)
The entry point `main()` configures the Tauri builder, registers plugin modules, initializes shared state (`SharedSidecar`), and handles window lifecycle events.

```rust
// File: desktop/src-tauri/src/main.rs (Lines 20-26)
#[derive(Debug, Default)]
struct SidecarState {
    port: Option<u16>,
    child: Option<CommandChild>,
}
type SharedSidecar = Arc<Mutex<SidecarState>>;
```

#### Sidecar Spawning & NDJSON Event Streaming
When the desktop application launches, `spawn_sidecar()` spawns the external sidecar binary `cherenkov-launcher` with `CHERENKOV_NO_BROWSER=1`.

```rust
// File: desktop/src-tauri/src/main.rs (Lines 134-147)
let (mut rx, child) = match shell
    .sidecar("cherenkov-launcher")
    .expect("cherenkov-launcher sidecar not configured")
    .env("CHERENKOV_NO_BROWSER", "1")
    .spawn()
{
    Ok(pair) => pair,
    Err(e) => { ... }
};
```

The launcher emits newline-delimited JSON (NDJSON) events over standard output. `main.rs` parses these into `LauncherEvent` enums:

```rust
// File: desktop/src-tauri/src/main.rs (Lines 30-41)
#[derive(Debug, Deserialize)]
#[serde(tag = "event", content = "data", rename_all = "snake_case")]
enum LauncherEvent {
    Ready { version: String },
    Port { port: u16 },
    Shutdown { signal: serde_json::Value },
    Progress { step: String, pct: u8, detail: Option<String> },
    DemoMode { reason: String },
}
```

Upon receiving `LauncherEvent::Port { port }`:
1. The port is stored in `SharedSidecar`.
2. A background Tokio task polls `http://127.0.0.1:<port>/healthz` (up to 30 attempts, 500ms intervals).
3. Once healthy, `engine-healthy` is emitted to the webview.
4. If the port differs from the default (8000), `window.navigate(url)` redirects the webview dynamically.

### 2.3 Tauri Command Handlers
`main.rs` registers 11 Tauri command handlers exposed to IPC:

| Command Handler | Return Type | Source File | Description |
|---|---|---|---|
| `get_api_port` | `Result<u16, String>` | `main.rs:45` | Returns bound backend port |
| `run_setup_wizard` | `Result<SetupState, String>` | `setup_wizard.rs:61` | Runs 5-stage setup verification |
| `install_ollama_command` | `Result<SetupStep, String>` | `setup_wizard.rs:82` | Installs Ollama via official script |
| `watch_spec_dir` | `Result<(), String>` | `file_watcher.rs:16` | Starts file system watcher on OpenAPI directory |
| `check_for_updates` | `async ()` | `updater.rs:24` | Checks GitHub releases for app update |
| `install_update` | `async ()` | `updater.rs:58` | Downloads update package and restarts |
| `detect_hardware` | `HardwareInfo` | `hardware.rs:64` | Probes system CPU, OS, ADB, Node, Python, Ollama |
| `check_prerequisites` | `HardwareInfo` | `hardware.rs:64` | Alias for hardware detection |
| `advance_wizard_step` | `WizardStepResult` | `wizard.rs:147` | Validates and steps through 7-step wizard |
| `get_settings` | `AppSettings` | `settings.rs:22` | Reads `settings.json` from app config dir |
| `save_settings` | `Result<(), String>` | `settings.rs:31` | Validates and writes `settings.json` |

### 2.4 System Hardware Detection (`src/hardware.rs`)
`hardware.rs` queries cross-platform system attributes and tool existence:

```rust
// File: desktop/src-tauri/src/hardware.rs (Lines 27-40)
fn has_binary(bin: &str) -> bool {
    #[cfg(target_os = "windows")]
    let checker = "where";
    #[cfg(not(target_os = "windows"))]
    let checker = "which";

    std::process::Command::new(checker)
        .arg(bin)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}
```

It classifies devices into `Desktop`, `Laptop`, `Server`, `Android`, `Ios`, or `Unknown` (e.g., checking `DISPLAY` or `WAYLAND_DISPLAY` environment variables on Linux to differentiate servers from GUI desktops).

### 2.5 Setup Wizard Engines (`src/wizard.rs` & `src/setup_wizard.rs`)
- **7-Step Wizard Validation (`wizard.rs`):** Validates wizard state machine step-by-step:
  1. *Check Prerequisites:* Ensures Node.js is present.
  2. *Select Work Directory:* Validates `work_dir` is non-empty.
  3. *Configure LLM:* Validates `ollama_host` format and `vlm_tier` (`small` \| `deep`).
  4. *Configure Egress:* Enforces policy values (`none`, `internal`, `any`).
  5. *Test Connection:* Verifies `connection_ok` boolean from frontend ping.
  6. *Select Devices:* Verifies array of selected target devices.
  7. *Complete:* Marks configuration completed.

- **System Installation Wizard (`setup_wizard.rs`):** Asynchronously verifies prerequisite runtimes (`python3`, `node`, `docker`, `ollama`), and pulls missing Ollama models (e.g., `ollama pull qwen2.5-coder`) while streaming step progress events (`setup-progress`) to the UI.

### 2.6 Native File System Watcher (`src/file_watcher.rs`)
Monitors target spec directories using the `notify` crate. On file creation or modification of `.yaml`, `.yml`, or `.json` files, emits `spec-changed` events to the UI:

```rust
// File: desktop/src-tauri/src/file_watcher.rs (Lines 45-55)
if matches!(ext, "yaml" | "yml" | "json") {
    let payload = SpecChanged {
        path: path.display().to_string(),
        kind: format!("{:?}", event.kind),
    };
    let _ = app.emit("spec-changed", payload);
}
```

---

## 3. Dashboard UI Architecture

The Web Dashboard is implemented in `cherenkov/web/ui/` using **React 19**, **TypeScript 5.8**, **Vite 6**, and **Tailwind CSS v4**.

### 3.1 Component Hierarchy & Workspace Structure

```
App (src/App.tsx)
 ├── BrowserRouter & AuthProvider (src/contexts/AuthContext.tsx)
 └── InnerApp
      ├── GlobalShortcuts (Hotkeys & Navigation listeners)
      ├── ErrorBoundary (React Error Catching Layer)
      ├── CommandPalette (Global Palette: Cmd+K / Ctrl+K)
      ├── OnboardingWizard & GuidedTour
      ├── OfflineOverlay (Backend Health Status Interceptor)
      ├── AppHeader (Top bar with project selector & token gauge)
      └── NavigationBar (5 Workspaces sidebar navigation)
           ├── DashboardWorkspace (`/dashboard`, `/overview`)
           │    ├── ReleaseReadinessCard
           │    ├── IntegrityHeatmap
           │    └── VerdictHistoryTable
           ├── AuthoringWorkspace (`/authoring`, `/setup`)
           │    ├── SpecIngestPanel
           │    ├── IntentAuthoringPanel
           │    ├── LivePipelineMonitor
           │    └── DoctorCheckWidget
           ├── TriageWorkspace (`/triage`, `/review`)
           │    ├── HitlReviewQueue
           │    ├── DivergenceTable
           │    └── SpecVsRealityDiffViewer
           ├── IntelligenceWorkspace (`/intelligence`, `/knowledge`)
           │    ├── KnowledgeGraphExplorer
           │    ├── SddMemoryCockpit
           │    └── SseChatAssistant
           └── SettingsWorkspace (`/settings`, `/devices`)
                ├── DeviceManager
                ├── ProjectManager
                ├── EjectSuitePanel
                └── GovernanceSettings
```

### 3.2 Breakdown of the 9 UI Screens & Core Components

1. **`OverviewScreen` / `DashboardWorkspace`:** High-level executive view displaying release readiness score (0-100%), defect escape rate, coverage heatmaps (`IntegrityHeatmap.tsx`), and historical run verdicts (`VerdictHistoryTable.tsx`).
2. **`AuthoringWorkspace`:** OpenAPI spec file upload dropzone, rich endpoint coverage analysis (`SpecIngestPanel.tsx`), natural language intent prompt studio (`IntentAuthoringPanel.tsx`), and real-time generation logs (`LivePipelineMonitor.tsx`).
3. **`TriageWorkspace`:** Human-In-The-Loop (HITL) approval queue (`HitlReviewQueue.tsx`), spec vs. implementation diff viewer (`SpecVsRealityDiffViewer.tsx`), and divergence tracking table (`DivergenceTable.tsx`).
4. **`IntelligenceWorkspace`:** GraphRAG Second Brain graph navigator (`KnowledgeGraphExplorer.tsx`), SDD semantic memory token budget cockpit (`SddMemoryCockpit.tsx`), and streaming AI Copilot (`SseChatAssistant.tsx`).
5. **`SettingsWorkspace` / `DeviceManager`:** Multi-device detection inspector (`DeviceManager.tsx`), VLM tier router configuration, project management (`ProjectManager.tsx`), and zero-lockin spec ejector (`EjectSuitePanel.tsx`).
6. **`DeviceManagerScreen.tsx`:** Dedicated standalone view fetching `/api/v1/doctor` checks to display system prerequisites (Python, Node, Docker, Ollama) and provider statuses (`LocalAI`, `Ollama`, `OpenAI`).
7. **`KnowledgeExplorerScreen.tsx`:** Standalone Second Brain knowledge mesh explorer querying `/api/v1/chat/knowledge/query`.
8. **`MobilePilotScreen.tsx` / `MobileScreen.tsx`:** Automated mobile test runner executing ADB/Maestro device sweeps via `/api/v1/mobile/pilot/*`.
9. **`SddDashboardScreen.tsx` / `MemoryScreen.tsx`:** Specialized view for monitoring SDD (Sync-Driven Development) session logs, Milvus shadow index state, and token usage metrics.

#### Core UI Primitives & Utilities
- **`Toast.tsx`:** Context-driven toast notifications (`toast(msg, 'success' | 'danger' | 'info')`).
- **`HealthWidget.tsx`:** Compact indicator reflecting backend liveness and active VLM model tier.
- **`ErrorBoundary.tsx`:** React component trapping unexpected render exceptions with a formatted recovery panel.
- **`CommandPalette.tsx`:** Keyboard-accessible modal enabling rapid workspace switching and project selection.

### 3.3 State Management & Liveness Monitoring
- **Authentication State (`AuthContext.tsx`):** Tracks JWT tokens stored in `localStorage['[cherenkov] auth_token']`. Handles auth requirement checks and login redirects (`LoginPage.tsx`).
- **Engine Liveness (`useHealth.ts`):** Polls `/api/v1/health` every 10 seconds. When backend is down or unreachable, renders `OfflineOverlay.tsx`.
- **Tauri Event Bridge Listener (`App.tsx:86-93`):** Subscribes to desktop events (`engine-healthy`, `engine-demo-mode`, `engine-stopped`) to trigger health re-checks immediately without waiting for poll intervals.

```typescript
// File: cherenkov/web/ui/src/App.tsx (Lines 86-93)
React.useEffect(() => {
  const subs = ['engine-healthy', 'engine-demo-mode', 'engine-stopped'].map((evt) =>
    listenDesktop(evt, () => refresh())
  );
  return () => {
    subs.forEach((p) => p.then((unlisten) => unlisten()));
  };
}, [refresh]);
```

### 3.4 SSE Real-Time Streaming Integration
Real-time AI Chat responses are delivered via Server-Sent Events (SSE) in `streamChatMessage()` (`lib/api.ts`).

```typescript
// File: cherenkov/web/ui/src/lib/api.ts (Lines 515-558)
export async function streamChatMessage(
  sessionId: string,
  content: string,
  onToken: (token: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/stream`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ content }),
    signal,
  });
  if (!res.ok) throw new Error(`Chat stream failed: ${res.status}`);

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let accumulated = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';
    for (const part of parts) {
      if (!part.trim()) continue;
      const dataLine = part.split('\n').find((l) => l.startsWith('data:'));
      if (!dataLine) continue;
      try {
        const parsed = JSON.parse(dataLine.slice(5).trim());
        if (parsed.token) {
          accumulated += parsed.token;
          onToken(parsed.token);
        }
      } catch {
        // ignore malformed SSE frames
      }
    }
  }
  return accumulated;
}
```

The chunk reader buffers raw byte streams, parses `data:` SSE frames containing `{ token: "..." }`, and invokes the `onToken` callback to dynamically update UI chat bubbles token-by-token.

---

## 4. Design Patterns

### 4.1 Tauri IPC Bridge Pattern (`lib/tauri.ts`)
The application uses a **Proxy / Dynamic Bridge Pattern** for Tauri IPC commands. Instead of coupling the React build to `@tauri-apps/api`, `lib/tauri.ts` inspects `window.__TAURI__`:

```typescript
// File: cherenkov/web/ui/src/lib/tauri.ts (Lines 34-59)
function tauri(): TauriGlobal | null {
  return (window as unknown as { __TAURI__?: TauriGlobal }).__TAURI__ ?? null;
}

export function isDesktop(): boolean {
  return tauri() !== null;
}

export async function invokeDesktop<T>(
  cmd: string,
  args?: Record<string, unknown>,
): Promise<T | null> {
  const t = tauri();
  if (!t) return null;
  try {
    return await t.core.invoke<T>(cmd, args);
  } catch (err) {
    console.warn(`[desktop] invoke ${cmd} failed:`, err);
    return null;
  }
}
```
**Benefits:**
- **Zero Lock-In:** Allows the exact same compiled static assets (`dist/`) to run inside browser servers (FastAPI/Uvicorn) or inside the desktop shell.
- **Fail-safe Fallback:** If IPC fails or runs in browser mode, `invokeDesktop` returns `null`, allowing callers to seamlessly fall back to HTTP endpoints.

### 4.2 Component-Driven Workspace Architecture
The UI enforces a clean workspace layout pattern. Navigation routes (`/dashboard`, `/authoring`, `/triage`, `/intelligence`, `/settings`) select top-level Workspaces, each encapsulating domain-specific widgets, graphs, and action cards.

### 4.3 Proxy / Adapter Pattern for API Layer (`lib/api.ts`)
All backend interaction goes through `lib/api.ts`. It manages auth headers (`Authorization: Bearer <token>`), URL encoding, parameter serialization, and error transformations across over 40 structured API functions.

---

## 5. Code Quality, Security & Performance

### 5.1 Tauri Security Policy & Scope Restrictions
- **Capability Scopes (`desktop/src-tauri/capabilities/main.json`):**  
  Restricts host access explicitly to `http://127.0.0.1` and `http://localhost`. Granted permissions: `core:default`, `notification:default`, `dialog:default`, `process:default`, `updater:default`, `fs:default`, `http:default`, `shell:allow-spawn`, `shell:allow-kill`.
- **Global Tauri Scope (`tauri.conf.json:13`):**  
  `withGlobalTauri: true` injects `window.__TAURI__`.
- **Sidecar Execution Sandboxing:**  
  Shell execution is restricted exclusively to the `cherenkov-launcher` sidecar binary defined under `bundle.externalBin`.

### 5.2 Memory Footprint & Resource Consumption
- **Compiled Binary Size:** ~308MB debug binary (`desktop/src-tauri/target/debug/cherenkov-desktop`). Release builds stripped with LTO reduce this significantly.
- **Runtime Memory Usage:** WebKitGTK / WebView2 processes consume ~120-180MB RAM at idle, matching standard light desktop wrapper footprints.

### 5.3 Frontend Rendering Performance
- **Vite 6 + React 19:** Instant module hot-reloading (HMR) and optimized ES module bundling.
- **Deferred / Polled Data Fetching:** Polling intervals for non-critical telemetry (token counts, review queue size) are set to 30 seconds to prevent unnecessary re-renders.

### 5.4 Error Boundaries & Resiliency
- **`ErrorBoundary.tsx`:** Intercepts React runtime errors, preventing total app crashes and rendering a formatted recovery panel.
- **`OfflineOverlay.tsx`:** Gracefully overlays the app during engine disconnects or restarts, providing a manual "Retry Connection" action.

---

## 6. Architectural Strengths & Technical Debt / Improvements

### 6.1 Architectural Strengths
1. **Flawless Dual-Mode Operability:** Runs with equal capability in browser or desktop modes without conditional build splits.
2. **Robust Engine Process Lifecycle:** Spawns, monitors, and health-checks engine sidecars asynchronously, automatically handling dynamic port re-binding.
3. **Clean Architecture Adherence:** Desktop Rust core follows clean separation (`hardware`, `setup_wizard`, `wizard`, `settings`, `file_watcher`, `updater`), while the frontend follows strict modular workspace organization.

### 6.2 Technical Debt & Recommended Improvements
1. **Component Duplication between Screens and Workspaces:**  
   *Observation:* There is functional redundancy between standalone screen components (e.g. `DeviceManagerScreen.tsx`, `KnowledgeExplorerScreen.tsx`, `SddDashboardScreen.tsx`) and workspace panels (`DeviceManager.tsx`, `KnowledgeGraphExplorer.tsx`, `SddMemoryCockpit.tsx`).  
   *Recommendation:* Refactor standalone screens to wrap workspace subcomponents directly to eliminate duplicated JSX and state fetching logic.
2. **Polling vs WebSockets/SSE for Telemetry:**  
   *Observation:* Metrics (`fetchMetricsData`) and review queue badges (`fetchReviewQueue`) rely on 30-second interval polling in `App.tsx`.  
   *Recommendation:* Extend SSE stream endpoints or implement WebSocket events for live telemetry updates.
3. **Updater Endpoint Hardcoding:**  
   *Observation:* `tauri.conf.json` hardcodes `https://github.com/moaidmoatasem/cherenkov-qa/releases/latest/download/latest.json`.  
   *Recommendation:* Make updater endpoints configurable via environment variables or settings for enterprise deployment environments.

---

## 7. Verification Method & Commands

To independently verify the Subsystem 5 build and test status:

1. **Verify Desktop Tauri App Compilation:**
   ```bash
   cd desktop/src-tauri
   cargo check
   ```
2. **Verify Frontend Type-Checking & Unit/E2E Tests:**
   ```bash
   cd cherenkov/web/ui
   npm run lint
   python3 run_dashboard_tests.py
   ```
