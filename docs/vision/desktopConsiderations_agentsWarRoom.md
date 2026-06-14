<!--
⚠️ AGENT SCRATCH FILE — DO NOT CITE

Filename and content are artifacts of a multi-agent "war room" session.
This is not a maintained spec. For the live desktop-host plan see
[../../docs/PHASE_PLAN.md](../../PHASE_PLAN.md) (Phase 3) and
[../vision/18_DESKTOP_HOST.md](../vision/18_DESKTOP_HOST.md).
-->

#agent1:
# CHERENKOV Desktop Application Analysis & Recommendation

## Executive Summary

**Verdict: YES, but with strategic constraints.** CHERENKOV's architecture is already 80% desktop-ready. The existing React dashboard + FastAPI backend + Docker containerization provides a natural path to desktop. However, the **validation gate (5 real QA users)** must pass first—desktop packaging won't fix the current friction: the CLI workflow isn't human-validated yet.

---

## Current Architecture Analysis

### ✅ Desktop-Friendly Components (Already Built)

| Component | Location | Desktop Readiness | Notes |
|-----------|----------|-------------------|-------|
| **React Dashboard** | `cherenkov/web/ui/` | 90% | Prebuilt dist, 17 screens, but uses mock data (#224) |
| **FastAPI Backend** | `cherenkov/web/api.py` | 85% | Real HitlQueue wired, WebSocket broadcast ready |
| **Docker Container** | `Dockerfile`, `docker-compose.yml` | 100% | Multi-stage build, UI + Python + Playwright bundled |
| **CLI Orchestrator** | `cherenkov.py` | 100% | Already unified entry point |
| **State Management** | SQLite (`hitl.db`, `verdicts.db`) | 100% | Local-first, WAL mode for concurrency |

### ⚠️ Blockers (Not Desktop-Specific)

```
Issue #224: 10/17 dashboard surfaces render mockData.ts
Issue #222: Silent catch(console.warn) instead of user toasts
Issue #223: "Initialize Pilot Run" not wired to POST /run
Issue #239: Demo mode not honest (masks reality)
```

**These kill desktop value.** A desktop app with mock data is a PowerPoint deck.

---

## Desktop Strategy Options

### Option A: Electron Wrapper (Recommended for MVP)

**Pros:**
- Reuses existing React dashboard (zero rewrite)
- Single executable distribution
- Native menu bar, tray integration
- Access to local filesystem (for spec files, output dirs)
- Mature ecosystem (VS Code, Slack, Figma use it)

**Cons:**
- Bundle size (~100-150MB with Node + Chromium)
- Memory footprint (2 processes: main + renderer)
- Not native look/feel on all platforms

**Effort:** 2-3 weeks
- `electron-builder` packaging
- Native file picker for spec selection
- Auto-launch backend (FastAPI) on port 8000
- Tray menu: Validate / Eject / Review / Quit
- Native notifications for validation results

### Option B: Tauri (Rust-based Alternative)

**Pros:**
- Tiny bundle size (~5-10MB)
- Native look/feel
- Better security model (no Node in renderer)
- WebView-based (uses system browser engine)

**Cons:**
- Rust toolchain dependency for builds
- Less mature than Electron
- More complex native feature integration

**Effort:** 3-4 weeks (Rust learning curve)

### Option C: Native PyQt/PySide + QtWebEngine

**Pros:**
- Single Python process
- Native file dialogs
- Mature Python ecosystem

**Cons:**
- QtWebEngine adds ~50MB
- React dashboard would need significant adaptation
- Less modern UX

**Effort:** 4-5 weeks (requires dashboard rewrite)

---

## Desktop-Specific Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop App (Electron)                    │
├─────────────────────────────────────────────────────────────┤
│  Main Process          │  Renderer Process (React Dashboard) │
│  ├── File Watcher      │  ├── Existing UI components        │
│  ├── Auto-launch API   │  ├── WebSocket client               │
│  ├── Native Menu       │  └── Toast notifications            │
│  ├── Tray Icon         │                                      │
│  └── Update Checker    │                                      │
└────────────┬────────────┴──────────────────┬───────────────┘
              │                                   │
              ▼                                   ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│  FastAPI Backend (port 8000) │◄──►│  SQLite DBs (.cherenkov/)    │
│  └── hitl/v1 API              │    └── hitl.db                  │
│  └── validate endpoints       │    └── verdicts.db              │
│  └── eject endpoints          │    └── perf_metrics.db         │
└─────────────────────────────┘    └─────────────────────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Ollama (optional)           │
│  └── qwen2.5-coder:7b        │
│  └── deepseek-r1:8b          │
└─────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Honest Dashboard (Prerequisite) - 1-2 weeks

**Must complete before desktop packaging:**
- [ ] Replace all `mockData.ts` with real API calls to `cherenkov/web/api.py`
- [ ] Wire "Initialize Pilot Run" to `POST /api/v1/run`
- [ ] Implement loading/error/empty states (#221, #222)
- [ ] Add rejection reason capture (#182)
- [ ] Prebuild `dist/` in repo (no `npm install` for users)

**Exit Criteria:** Golden path works end-to-end in browser at `http://localhost:8000`

### Phase 2: Electron MVP - 2-3 weeks

**Package structure:**
```
cherenkov-desktop/
├── src/
│   ├── main/          # Electron main process
│   │   ├── index.ts   # App lifecycle, auto-launch API
│   │   ├── menu.ts    # Native menu
│   │   └── tray.ts    # System tray
│   ├── renderer/      # Existing React dashboard (symlinked)
│   └── preload.ts     # Bridge between main/renderer
├── package.json
├── electron.builder.json
└── forge.config.js
```

**Key files:**

`main/index.ts`:
```typescript
import { app, BrowserWindow, Tray, Menu } from 'electron'
import { spawn } from 'child_process'

let apiProcess: ChildProcess
let mainWindow: BrowserWindow
let tray: Tray

function createWindow() {
  // Launch FastAPI backend
  apiProcess = spawn('python', ['cherenkov.py', 'review', '--web'], {
    cwd: __dirname
  })

  // Wait for API to be healthy
  await waitForHealthy('http://localhost:8000')

  // Create browser window
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadURL('http://localhost:8000')
}

app.whenReady().then(createWindow)
```

`forge.config.js`:
```javascript
module.exports = {
  packagerConfig: {
    name: 'Cherenkov',
    executableName: 'cherenkov',
    icon: 'icons/icon',
    platforms: ['darwin', 'win32', 'linux']
  },
  publishers: [
    {
      name: '@electron-forge/publisher-github',
      config: {
        repository: { owner: 'moaidmoatasem', name: 'cherenkov-qa' }
      }
    }
  ]
}
```

### Phase 3: Native Integrations - 1 week

- [ ] **File watcher:** Auto-detect spec changes, prompt to re-generate
- [ ] **Native notifications:** Validation complete, findings ready
- [ ] **Tray menu:**
  - Validate against last target
  - Open Review Dashboard
  - Eject tests
  - Check for updates
  - Quit
- [ ] **Recent projects:** MRU list in tray menu
- [ ] **Auto-update:** Electron updater

### Phase 4: Polish & Distribution - 1 week

- [ ] Code signing (macOS/Windows)
- [ ] Notarization (macOS)
- [ ] Installer packages (.dmg, .exe, .deb, .rpm)
- [ ] CI/CD pipeline for builds
- [ ] Sentry/telemetry (opt-in)

---

## Technical Considerations

### GPU Requirement Challenge

Current design **requires GPU** (RTX 5060, 8GB VRAM) for acceptable performance.

**Desktop solutions:**

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Bundle Ollama** | Full offline | +800MB, complex | ❌ Not viable |
| **Cloud inference** | No local GPU | Privacy concerns, costs | ⚠️ Opt-in only |
| **CPU fallback** | Works everywhere | 10x slower (~40s/test) | ✅ Default with warning |
| **Model quantization** | Smaller, faster | Quality drop | ⚠️ Experimental |
| **Remote Ollama** | User provides endpoint | Setup complexity | ✅ For advanced users |

**Recommended:** Ship with **CPU fallback enabled by default**, loud warning:
```
⚠️  GPU not detected. Generation will be ~10x slower (~40s per test).
   For optimal performance, install Ollama with GPU support.
```

### Cross-Platform Issues

| Platform | Challenge | Solution |
|----------|-----------|----------|
| **Windows** | Path handling, antivirus | Use `%LOCALAPPDATA%` for `.cherenkov/`, sign executable |
| **macOS** | Notarization, permissions | Entitlements for file access, hardened runtime |
| **Linux** | AppImage vs deb vs snap | Provide all three, recommend AppImage for simplicity |

### Security Considerations

- **SQLite encryption:** Already supported via `CHERENKOV_DB_KEY` + SQLCipher
- **API authentication:** `CHERENKOV_HITL_API_KEY` header check already implemented
- **File access:** Electron needs explicit permissions in `webPreferences`
- **Network:** Only allow connections to `localhost` by default

---

## Resource Requirements

### Development
- Node.js 18+
- Python 3.10+
- Electron Forge
- macOS/Windows/Linux build machines

### Runtime (Desktop App)
- **Minimum:**
  - 512MB RAM
  - 200MB disk
  - CPU-only inference
- **Recommended:**
  - 2GB RAM
  - 1GB disk
  - NVIDIA GPU with 8GB VRAM
  - Ollama installed separately

### Distribution Size
- **Electron app:** ~120-150MB
- **With embedded Ollama:** ~900MB+ (not recommended)
- **With embedded Python:** ~50MB

**Recommendation:** Distribute as **slim Electron app (150MB)** + **separate Ollama installer guide**

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Electron bundle too large | Medium | Medium | Offer Tauri alternative, explain tradeoffs |
| macOS notarization rejection | High | High | Start process early, use hardened runtime |
| Windows antivirus false positives | Medium | Medium | Code signing, submit to vendors |
| GPU detection unreliable | Medium | Low | Multiple detection methods, user override |
| Performance on low-end machines | High | High | CPU warning, progress indicators, cancellation |
| Desktop-specific bugs | High | Medium | Beta testing program, telemetry (opt-in) |

---

## Competitive Landscape

| Tool | Desktop App | OpenAPI → Tests | Local LLM | Zero Lock-in |
|------|-------------|-----------------|-----------|--------------|
| **CHERENKOV** | ✅ (proposed) | ✅ | ✅ | ✅ |
| Postman | ✅ | ❌ (manual) | ❌ | ❌ |
| Newman | ✅ | ❌ | ❌ | ✅ |
| Schemathesis | ❌ | ✅ | ❌ | ✅ |
| Robocorp | ✅ | ❌ | ❌ | ❌ |
| Testim | ✅ | ❌ | ❌ | ❌ |

**Differentiator:** CHERENKOV is the **only** tool combining:
1. OpenAPI → automatic test generation
2. Local LLM (privacy-first)
3. Zero lock-in (eject to plain Playwright)
4. Desktop-native experience

---

## Go/No-Go Decision Matrix

| Factor | Weight | Score (1-5) | Weighted |
|--------|--------|-------------|----------|
| Market demand (QA pain is real) | 25% | 5 | 1.25 |
| Technical feasibility | 20% | 5 | 1.00 |
| Development effort | 15% | 4 | 0.60 |
| Maintenance burden | 15% | 3 | 0.45 |
| Competitive advantage | 15% | 5 | 0.75 |
| Revenue potential | 10% | 3 | 0.30 |
| **Total** | **100%** | - | **4.35/5** |

**Recommendation: GO** (score > 4.0)

---

## Recommended Action Plan

### Immediate (Next 2 weeks)
1. **Fix the honesty debt** - Complete Phase 1: wire dashboard to real API
2. **Validate with 5 QA users** - Prove the web workflow works
3. **Create desktop prototype** - Basic Electron wrapper with auto-launch

### Short-term (Next month)
1. **Build Electron MVP** - Phases 2-3
2. **Set up CI/CD** - Automated builds for all platforms
3. **Beta testing** - Internal + early adopters

### Long-term (Next quarter)
1. **Tauri alternative** - Offer slim build option
2. **Cloud sync** - Optional anonymous usage analytics
3. **Marketplace** - Publish to Electron app stores

---

## Final Recommendation

**Build the desktop app, but only AFTER the web dashboard passes the validation gate.**

The desktop packaging is the **easiest part** of this equation. The hard part is making the workflow **real and frictionless**—which the current roadmap (ROADMAP_NEXT.md) already addresses. Desktop is the natural next step once Phase 2 (5 QA users) is achieved.

**Priority order:**
1. ✅ Fix mock data, wire real API (Phase 0-1)
2. ✅ Validate with 5 real users (Phase 2)
3. ✅ Then: Electron packaging (2-3 weeks)
4. ⏸️ Tauri alternative (optional, post-MVP)

The codebase is already architected for desktop. The question isn't *can* we do it—it's *should* we do it *now*. And the answer is: **not until the core workflow proves itself with real users.**

---

**Bottom line:** Desktop CHERENKOV is a natural evolution, not a pivot. The foundation is solid. The timing depends on validating the current workflow, not on technical feasibility.


#agent2:
Based on my codebase analysis, here's my assessment on converting CHERENKOV to a desktop application:

---

## Code Analysis Summary

**Project Overview:**
CHERENKOV is an API conformance testing tool that:
- Takes OpenAPI specs → generates Playwright tests via local LLM (Ollama/Qwen 2.5-coder)
- Runs tests against real servers → produces conformance drift reports
- Features suggest-only healing, zero-lock-in ejection to vanilla Playwright

**Current Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│  Python Backend (FastAPI)                                       │
│  ├─ cherenkov.py (CLI with 15+ subcommands)                     │
│  ├─ cherenkov/web/api.py (REST API + WebSocket for live events)   │
│  ├─ cherenkov/core/orchestrator.py (INGEST→PLAN→GENERATE→REVIEW) │
│  └─ cherenkov/execution/validate.py, eject.py                     │
├─────────────────────────────────────────────────────────────────┤
│  React Frontend (Vite)                                           │
│  ├─ cherenkov/web/ui/src/App.tsx (BrowserRouter, multiple screens)  │
│  ├─ ReviewScreen, SetupScreen, PipelineScreen, GovernanceScreen   │
│  ├─ TypeScript + TailwindCSS, Zustand state                       │
│  └─ Already builds to static dist                               │
├─────────────────────────────────────────────────────────────────┤
│  Desktop Spike (Tauri - exists but skeletal)                     │
│  ├─ desktop/src-tauri/tauri.conf.json (configured for web UI)     │
│  └─ desktop/src-tauri/src/main.rs (spawns Python sidecar)       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Desktop Feasibility Assessment

### Strengths ✅

1. **Frontend Already Built**: React/Vite app exists with:
   - Full routing (17+ screens)
   - WebSocket live progress updates
   - Native integrations (drag-drop, file selection UI)
   - Responsive design with dark theme

2. **Architectural Alignment**: The roadmap already identifies desktop as a goal:
   - Ticket #230: "Desktop launcher (one-file binary)"
   - Ticket #231: "Tauri desktop app + native installers"

3. **Sidecar Pattern Ready**: The Tauri config references `cherenkov-launcher` as external bin, indicating intent to bundle Python as a native sidecar.

4. **Demo Mode**: CPU-friendly fallback exists when Ollama unavailable (enabling demo on any machine).

### Challenges ⚠️

1. **Resource Requirements**:
   - Ollama/Qwen 2.5-coder:7b requires ~8GB VRAM on GPU for optimal performance
   - CPU fallback is ~10x slower (~40s per scenario)
   - Large models need ~15GB disk space

2. **Build Complexity**:
   - Python to native binary: requires PyInstaller/cx_Freeze with proper dependency bundling
   - Node.js + npm still needed for the frontend
   - SQLite persistence for HITL queue adds file system considerations

3. **Platform-Specific Issues**:
   - macOS signing/notarization required for distribution (#231 notes this)
   - Linux AppImage needs Electron-compatible packaging
   - Windows MSI needs proper manifest signing

### Current Desktop Implementation Status

The Tauri scaffold exists but is incomplete:

| Component | Status | Notes |
|-----------|--------|-------|
| tauri.conf.json | ✅ exists | Configured but lacks icons, macOS signing config |
| main.rs | ✅ exists | Sidecar spawn logic ready |
| cherenkov-launcher binary | ❌ missing | Requires PyInstaller build |
| Native installers | ❌ missing | .msi/.dmg/.AppImage not generated |
| One-click launch | ❌ pending | Ticket #230 open |

---

## Recommendation

**Desktop is viable and strategically aligned** — here's why:

1. **Product-Market Fit**: QA engineers prefer GUI over CLI (#230, #231 in roadmap target this)

2. **Architecture Supports It**: The Python backend + static web UI pattern maps directly to Tauri's sidecar model

3. **Lower Friction**: Eliminates `npm install` and manual server startup barriers

### Recommended Approach

```
Phase A: MVP Desktop (Week 1-2)
├─ Bundle Python backend with PyInstaller (--onefile)
├─ Add to Tauri externalBin as sidecar
├─ Wire Tauri shell APIs for file dialogs
└─ Package as .msi/.dmg/AppImage (no signing initially)

Phase B: Enhanced Distribution (Week 3-4)
├─ Code signing via GitHub Actions
├─ Auto-update integration (Tauri updater)
├─ Bundled Ollama installer (optional, ~500MB download)
└─ Silent install options

Phase C: Resource Management
├─ Model download manager (progress UI)
├─ GPU/CPU auto-detection on startup
└─ Demo mode as default when LLM unavailable
```

### Technical Notes

- The `packaging/launcher.py` already has demo mode fallback logic — reuse this
- API uses `http://127.0.0.1:{port}` binding — compatible with Tauri's webview
- WebSocket events will work seamlessly in desktop context
- Anti-lock-in invariant (eject to vanilla Playwright) remains intact

### Risk Mitigation

If resource constraints are prohibitive:
1. **Hybrid approach**: Desktop UI + cloud LLM backend (changes zero-lock-in invariant less)
2. **Electron consideration**: Would increase binary size (~200MB+) but offers more native APIs
3. **Progressive delivery**: Start with web UI + auto-launch browser (#230), add native packaging later

---

The project already has 70% of the desktop foundation in place. Completing the Tauri sidecar integration and native installers would directly serve tickets #230 and #231, unblocking the "one-click QA engineer workflow" goal in the roadmap.

#agent3:
Based on our exploration of desktop frameworks and the need for a rigorous, production-ready system, here is the finalized, concrete architecture and implementation plan for the Cherenkov-QA project.

This blueprint synthesizes the best approach for building a high-performance, cross-platform desktop application with an ironclad Quality Assurance and testing infrastructure built right in.

1. Core Architectural Decision: Tauri over Electron
For a project focused on QA, performance, and potentially resource-intensive system/data analysis, I strongly recommend using Tauri instead of Electron.

Why Tauri? It ditches the heavy Chromium bundle in favor of the operating system's native webview. This results in drastically smaller binary sizes (often under 10MB) and significantly lower memory/CPU overhead.
Backend Power: Tauri uses Rust for the backend, which gives you memory safety, bare-metal performance, and secure, direct access to the file system and OS-level APIs—perfect for building reliable QA tooling.
2. The Cherenkov-QA Technology Stack
To ensure maximum code clarity, maintainability, and performance, the stack should be divided into a clear frontend and backend:

Frontend (UI & Visualization): React with TypeScript. TypeScript is non-negotiable for a QA-focused project to catch type errors at compile time.
Backend (Core Logic & OS Interop): Rust.
State Management: Zustand or Redux Toolkit (for complex UI state).
Local Storage: SQLite (via Tauri's SQL plugin) for storing QA logs, test results, and metrics locally.
3. QA & Testing Infrastructure (The "QA" in Cherenkov)
A QA tool must itself be flawlessly tested. We will implement a multi-tiered testing strategy.

A. Backend Unit Testing (Rust)
Rust has a built-in, highly ergonomic testing framework. You should write tests alongside your commands to ensure data payloads are validated before they ever reach the frontend.

rust
// src-tauri/src/qa_validator.rs

#[tauri::command]
pub fn validate_qa_payload(payload: &str) -> Result<bool, String> {
    if payload.trim().is_empty() {
        return Err("Validation Error: Payload cannot be empty".to_string());
    }

    // Additional complex QA validation logic here...

    Ok(true)
}

// Concrete code suggestion: Keep tests in the same file for clarity and immediate feedback
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_qa_payload_empty() {
        let result = validate_qa_payload("   ");
        assert!(result.is_err());
        assert_eq!(result.unwrap_err(), "Validation Error: Payload cannot be empty");
    }

    #[test]
    fn test_validate_qa_payload_valid() {
        let result = validate_qa_payload("valid_telemetry_data_001");
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), true);
    }
}
B. Frontend Unit & Integration Testing
Tooling: Use Vitest (faster than Jest) alongside React Testing Library.
Strategy: Test user interactions and ensure the UI correctly handles the data passed from the Rust backend. Mock the Tauri IPC (Inter-Process Communication) calls during these tests.
C. Automated CI/CD Pipeline
Continuous Integration is the backbone of any QA architecture. Here is a concrete GitHub Actions workflow that automatically lints and tests both the Rust backend and the Node/React frontend on every push.

yaml
# .github/workflows/cherenkov-ci.yml
name: Cherenkov-QA CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test-frontend:
    name: Frontend Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install Dependencies
        run: npm ci
      - name: Run Linter
        run: npm run lint
      - name: Run Vitest
        run: npm run test

  test-backend:
    name: Backend (Rust) Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Rust Toolchain
        uses: dtolnay/rust-toolchain@stable
      - name: Cache Cargo Registry
        uses: actions/cache@v3
        with:
          path: ~/.cargo/registry
          key: ${{ runner.os }}-cargo-registry-${{ hashFiles('**/Cargo.lock') }}
      - name: Run Cargo Format Check
        run: cargo fmt --manifest-path src-tauri/Cargo.toml -- --check
      - name: Run Cargo Tests
        run: cargo test --manifest-path src-tauri/Cargo.toml
4. Concrete Execution Plan
Phase 1: Foundation & Scaffolding (Weeks 1-2)

Initialize the Tauri project using the create-tauri-app CLI with the React/TypeScript template.
Establish the project repository, branch protection rules, and merge request requirements.
Implement the CI/CD pipeline (using the YAML structure above) so testing is enforced from commit zero.
Phase 2: Core Development & IPC Bridging (Weeks 3-6)

Develop the core UI components in React.
Write the heavy-lifting logic in Rust (data processing, system monitoring, or file parsing).
Crucial Step: Establish secure IPC interfaces. Ensure contextIsolation is utilized and validate all inputs coming from the React frontend into the Rust backend to prevent injection attacks.
Phase 3: E2E Testing, Hardening, & Release (Weeks 7-8)

Implement End-to-End (E2E) testing using a tool like WebDriverIO, which has great support for testing compiled desktop apps (both Electron and Tauri).
Run profiling on the Rust backend to ensure memory consumption stays flat during heavy QA workloads.
Configure the deployment pipeline to automatically compile and sign binaries for Windows (.msi / .nsis), macOS (.dmg / .app), and Linux (.AppImage / .deb).
This final architecture gives you the rich UI capabilities of web development, the performance and safety of Rust, and a QA methodology that ensures the application remains rock-solid as it scales

#agent4:


# CHERENKOV-QA → Desktop App: Final Plan

## TL;DR
Turn CHERENKOV into a **double-click Windows desktop app** that owns its engine and hosts the existing React dashboard in a native window. We **complete the half-built Tauri 2 + PyInstaller sidecar shell already in the repo** (`desktop/src-tauri/`, `packaging/launcher.py`, `packaging/cherenkov.spec`) instead of starting from scratch. The CLI stays the source of truth, every Track A invariant is preserved, and the desktop shell is a **host**, not a new execution path.

---

## What already exists in the repo (verified, not assumed)

| Artifact | State | What it gives us for free |
|---|---|---|
| `desktop/src-tauri/tauri.conf.json` | Tauri 1-era config, mis-shaped for Tauri 2, but the **intent is right**: sidecar model, `http://127.0.0.1:8000` URL, 1200×800 window | Direction, naming, identifier (`com.cherenkov.dev`) |
| `desktop/src-tauri/src/main.rs` | 29-line placeholder: spawns the sidecar but **never reads its output, never knows the port, never closes cleanly** | Confirms the sidecar pattern was already chosen |
| `packaging/launcher.py` | 61 lines: finds a free port, starts uvicorn, `webbrowser.open(url)`, sleeps forever | Real engine bootstrap; the only thing missing is the IPC contract to the host |
| `packaging/cherenkov.spec` | Real PyInstaller spec bundling the UI + engine + stubs | The build pipeline is proven — we just harden it |
| `packaging/dist/cherenkov-launcher.exe` | Already built once | We can reuse the build cache |
| `cherenkov/web/ui/dist/` | Pre-built React UI | The window content is ready |

## What "having it as a desktop application" actually means here

A non-technical QA lead installs `cherenkov-desktop-setup.exe`, double-clicks the Start Menu icon, and gets:
1. A **real native window** (no browser, no `webbrowser.open`).
2. The CHERENKOV FastAPI engine auto-started on a free localhost port.
3. The existing React dashboard rendered in that window, talking to the in-process engine.
4. If Ollama is missing → **Demo Mode** (matches what the existing launcher already does) so the window still has data to show.
5. Closing the window → engine stops cleanly within 5s, no orphan `python.exe` or `uvicorn` left running.

## Why Tauri 2 + PyInstaller sidecar (vs Electron, vs pure Python)

- **Already half-built in the repo.** Throwing it away to start Electron or PyWebView would be a regression.
- **Smallest binary that still gives a real native window.** Tauri 2 uses the system WebView (Edge WebView2 on Windows, WebKit on macOS, WebKitGTK on Linux) — no Chromium bundled, no Node runtime in production.
- **Sidecar pattern is the right model.** The engine is Python; the host is Rust; the contract is a small NDJSON line protocol on stdout. This is the same shape Electron's `child_process` users adopt, but with a fraction of the binary size.
- **Anti-lock-in preserved.** The eject workflow stays exactly the same. The desktop app is a *delivery vehicle*, not a new execution path.

---

## The plan (8 sections, exact changes)

### 1. Overview
Single sentence: a one-click Windows desktop app that hosts the existing engine + dashboard in a native Tauri 2 window, built from a PyInstaller sidecar, with the CLI as the source of truth and all Track A invariants preserved.

### 2. Types
A small Rust state struct + a small Python event-enum. No new types in the engine; the FastAPI surface stays exactly as `docs/HANDOVER.md` describes it.

```rust
// desktop/src-tauri/src/state.rs
pub struct EngineHandle { pub child: tokio::process::Child, pub port: u16,
    pub api_base: String, pub demo_mode: bool, pub started_at: SystemTime }
pub struct AppState { pub engine: Mutex<Option<EngineHandle>>,
    pub port: AtomicU16, pub shutdown_token: tokio_util::sync::CancellationToken }
```

```python
# packaging/launcher.py additions (NDJSON over stdout)
class LauncherEvent:
    READY  = "READY"     # {"event":"READY","port":8123,"demo_mode":true}
    LOG    = "LOG"       # {"event":"LOG","level":"info","msg":"..."}
    ERROR  = "ERROR"     # {"event":"ERROR","msg":"..."}
    # GET /healthz returns {"ok": true, "version": "1.1.0"} once uvicorn is bound
```

### 3. Files

**New (Rust host)**
- `desktop/src-tauri/Cargo.toml` — Tauri 2, tokio, reqwest, serde, tokio-util, thiserror, once_cell.
- `desktop/src-tauri/build.rs` — `tauri_build::build()`.
- `desktop/src-tauri/src/main.rs` — replaces placeholder: Tauri 2 builder + `WindowEvent::CloseRequested` → `state.stop_engine().await`.
- `desktop/src-tauri/src/state.rs` — `EngineHandle` + `AppState`.
- `desktop/src-tauri/src/sidecar.rs` — `spawn_engine`, `wait_for_health`, `stop_engine`.
- `desktop/src-tauri/src/types.rs` — `SidecarConfig`, `HealthCheck`, `DesktopEvent`.
- `desktop/src-tauri/capabilities/default.json` — Tauri 2 capability: `core:default` + `shell:allow-execute` for the sidecar.
- `desktop/src-tauri/icons/{icon.ico,icon.png,Square*Logo.png}` — generated by `cargo tauri icon` from a single 1024×1024 source.

**New (build / docs / tests)**
- `desktop/scripts/build-sidecar.ps1` — runs PyInstaller, stages the .exe into `desktop/src-tauri/binaries/cherenkov-launcher-${triple}.exe`.
- `desktop/scripts/build-desktop.ps1` — orchestrates: build UI → build sidecar → `cargo tauri build` → copy MSI/NSIS to `desktop/dist/`.
- `desktop/scripts/run-dev.ps1` — `cargo tauri dev` against the Vite dev server.
- `desktop/tests/smoke_desktop.py` — headless sidecar test (see §7).
- `desktop/tests/manual_window_checklist.md` — human checklist for the real native window.
- `docs/DESKTOP_APP.md` — end-user doc: install, log location, how to enable real Ollama mode, how to file a bug.
- `docs/engineering/DESKTOP_BUILD.md` — dev doc: toolchain, build matrix, icon regen, code-signing TODO.

**Modified (minimal, additive)**
- `packaging/launcher.py` — emit NDJSON `READY`/`LOG`/`ERROR`; honor `CHERENKOV_NO_BROWSER=1`; trap `SIGTERM`/`SIGBREAK`; wait for `/healthz` instead of blind `time.sleep(2)`.
- `packaging/cherenkov.spec` — add `cherenkov.execution.desktop_logging` to `hiddenimports`; add a runtime hook that redirects logs to `%APPDATA%\com.cherenkov.dev\logs\engine.log` when `CHERENKOV_DESKTOP=1`.
- `desktop/src-tauri/tauri.conf.json` — migrate to Tauri 2 schema (`frontendDist` not `devPath`/`distDir`); add `capabilities`, `minWidth/Height`, `productName`, `version` aligned with `pyproject.toml`.
- `cherenkov/web/api.py` — **one** new route: `GET /healthz → {"ok": true, "version": app.version}`. No other change.
- `AGENTS.md` — one new line under Track Status naming the desktop track and reasserting the invariants.
- `docs/SCOPE_LEDGER.md` — one new row: Desktop Packaging → `in-progress`, `not externally validated`.
- `.gitignore` — add `desktop/src-tauri/target/`, `binaries/`, `dist/`, `packaging/build/`, `packaging/dist/*.exe`.
- `pyproject.toml` — optional `[project.optional-dependencies] desktop = ["pyinstaller>=6.10"]`.

**Deleted**: nothing. The placeholder `main.rs` and old `tauri.conf.json` are *replaced*, not removed.

**Files not touched (by design)**: every file under `cherenkov/core/`, `cherenkov/stages/`, `cherenkov/execution/`, `cherenkov/hitl/`, `cherenkov/ai/`, the React UI source under `cherenkov/web/ui/src/`, and the 60+ Playwright/smoke tests. **The desktop shell is a host, not a new execution path. This is what protects D7, anti-lock-in, spec-derived, and suggest-only.**

### 4. Functions

**New (Rust)**
- `fn run() -> tauri::Result<()>` in `main.rs` — builder + close-handler.
- `pub async fn spawn_engine(cfg: SidecarConfig, state: &AppState) -> Result<u16, SidecarError>` in `sidecar.rs`.
- `pub async fn wait_for_health(api_base: &str, hc: HealthCheck) -> Result<(), SidecarError>` in `sidecar.rs`.
- `pub async fn stop_engine(handle: &mut EngineHandle) -> Result<()>` in `sidecar.rs`.

**New (Python)**
- `def emit(event: str, **payload) -> None` in `launcher.py` — NDJSON line writer.
- `def install_signal_handlers(loop) -> None` in `launcher.py` — SIGINT/SIGTERM/SIGBREAK → clean uvicorn shutdown.

**Modified**
- `packaging/launcher.py::main()` — detect `CHERENKOV_NO_BROWSER`; replace blind sleep with `wait_for_health`; `emit("READY", ...)`; wrap idle loop so SIGTERM exits with code 0.
- `cherenkov/web/api.py` — add `/healthz` route (3 lines).
- `desktop/src-tauri/tauri.conf.json` — Tauri 2 schema migration.
- `desktop/src-tauri/src/main.rs` — full host replacing the 29-line placeholder.

**Removed**: none. The CLI keeps using the same `main()` — only additions are "don't pop a browser if env var is set" and "emit NDJSON". Both are CLI-safe.

### 5. Classes

**New**
- `class DesktopRunner` in `desktop/tests/smoke_desktop.py` — context manager: build/use-cached sidecar, spawn with `CHERENKOV_NO_BROWSER=1`, capture NDJSON, expose `.wait_for_ready(10)` and `.shutdown()`.

**Modified**: none. `EngineHandle` / `AppState` are pure additions in Rust.

**Removed**: none.

### 6. Dependencies

**New (optional, dev-only)**
- Python: `pyinstaller>=6.10` (declared as `[project.optional-dependencies] desktop` in `pyproject.toml` and in `desktop/scripts/requirements-desktop.txt`).

**New (Rust host)**
```
tauri = { version = "2", features = ["protocol-asset"] }
tauri-build = { version = "2" }
tokio = { version = "1", features = ["full"] }
tokio-util = "0.7"
reqwest = { version = "0.12", default-features = false, features = ["rustls-tls","json"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"  thiserror = "1"  once_cell = "1"
```

**Build-time only** (not vendored, not shipped): Rust ≥ 1.78, `cargo install tauri-cli --version '^2.0'`, MSVC Build Tools, Windows 10/11 SDK, WebView2 (preinstalled on Win10 22H2+ and Win11), Node ≥ 20 for the UI build step.

**Removed**: none. `requirements.txt` and `cherenkov/web/ui/package-lock.json` are unchanged. New `Cargo.lock` lives at `desktop/src-tauri/Cargo.lock`.

### 7. Testing

**Strategy**: keep every existing smoke test untouched; add a headless sidecar test and a human checklist for the native window. The desktop app is a host, so its tests are mostly about *process lifecycle*, not feature logic.

**New file: `desktop/tests/smoke_desktop.py`**
1. `test_sidecar_emits_ready` — spawn sidecar, assert `READY` line within 10s.
2. `test_healthz_returns_200` — wait READY, hit `/healthz`, assert `{"ok": true}`.
3. `test_frontend_served` — wait READY, hit `/`, assert HTML contains dashboard root div.
4. `test_graceful_shutdown` — spawn, wait READY, send `CTRL_BREAK`/`SIGTERM`, assert exit code 0 within 5s.
5. `test_demo_mode_default_when_no_ollama` — spawn with `PATH` stripped of ollama, assert `demo_mode: true`.
6. `test_no_browser_popup` — assert no Chrome/Edge/msedge child processes spawned by the launcher.

**New file: `desktop/tests/manual_window_checklist.md`** — human-only, on real Windows desktop: install → launch → click through every dashboard tab → close → verify no orphan `python.exe` in Task Manager → relaunch → verify previous HITL queue state restored.

**Test runs**:
- `pytest desktop/tests/smoke_desktop.py` in CI on `windows-latest`.
- The 60+ existing smoke tests continue to run untouched (`run_tests.py`, `smoke_test_*.py`).

**Validation gate honesty**: per `AGENTS.md`, the 5-QA-user gate is unrun. The desktop track inherits that — we will not claim it is "validated" or "QA-approved" until real evidence lands in `docs/process/VALIDATION_EVIDENCE_LEDGER.md`. `docs/SCOPE_LEDGER.md` will be updated to say so.

### 8. Implementation order

Numbered to minimize conflicts and let each step be a clean feature branch (per `AGENTS.md` workflow rule 1).

1. **`feat/desktop-sidecar-protocol`** — modify `packaging/launcher.py` (NDJSON + healthz wait + signal handlers) and `cherenkov/web/api.py` (`/healthz`). Add `desktop/tests/smoke_desktop.py`. Run it. **This step ships a CLI-safer, NDJSON-emitting engine with a green test. The desktop shell is not even started yet.**
2. **`feat/desktop-sidecar-build`** — add `desktop/scripts/build-sidecar.ps1`, update `packaging/cherenkov.spec` (log redirection hook), `.gitignore`, `pyproject.toml` extras. Manually run end-to-end: build sidecar → launch → hit `/healthz` → close.
3. **`feat/desktop-tauri-host`** — write `Cargo.toml`, `build.rs`, `src/{main,state,sidecar,types}.rs`, `capabilities/default.json`, generate icons. Rewrite `tauri.conf.json` to Tauri 2 schema. Wire window-close → engine-stop.
4. **`feat/desktop-installer`** — add `desktop/scripts/build-desktop.ps1` (UI build → sidecar build → `cargo tauri build` → MSI/NSIS staging). First installer artifact lands in `desktop/dist/`.
5. **`feat/desktop-docs`** — write `docs/DESKTOP_APP.md` (end-user) and `docs/engineering/DESKTOP_BUILD.md` (dev). Update `AGENTS.md` Track Status, `docs/SCOPE_LEDGER.md`.
6. **`feat/desktop-ci`** — GitHub Actions job on `windows-latest`: build sidecar, build Tauri installer, run `smoke_desktop.py`, upload the MSI as a workflow artifact.
7. **Manual QA on real Windows** — install the MSI on a clean Win11 VM, follow `manual_window_checklist.md`, file issues for any friction.
8. **macOS / Linux follow-on** (separate branches, not in v1 scope): same `Cargo.toml` and Tauri config work; the Rust code is portable by design; only platform-specific bits are the signal handler and the log path.

Each step ends with a green test, a clean commit, and a push to a feature branch — never `main` — per `AGENTS.md` workflow rule 3.

---

## What I need from you before I start coding

Only one real call: the **implementation order above assumes the half-built Tauri 2 + PyInstaller sidecar is the direction**. The four questions I asked before the interruption were about (a) Tauri vs Electron vs pure-Python, (b) target platforms, (c) Ollama handling, (d) native window vs browser pop-out. I'd like to lock those down before I write the task and switch to Act mode.

If you want me to proceed as planned:
- (a) **Complete the existing Tauri + PyInstaller sidecar** (the half-built shell wins by default because it's already in the repo).
- (b) **Windows-first**, macOS/Linux as documented follow-on (matches the existing `packaging/build.ps1` and `.exe` artifact).
- (c) **Ollama is optional, demo mode is the default** when Ollama isn't on `PATH` (matches the existing `launcher.py` behavior).
- (d) **Real native window** — no `webbrowser.open` in desktop mode. The env var `CHERENKOV_NO_BROWSER=1` keeps the CLI's "pop the dashboard in your browser" behavior for users who want it.

If any of those four are wrong, tell me which one and I'll adjust the plan before I start. Otherwise, **toggle to Act mode** and I'll execute steps 1–5 in order on feature branches, with raw evidence (commit hashes, test runs, MSI paths) per `AGENTS.md` workflow rule 2.
