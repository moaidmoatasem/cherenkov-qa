# ADR-002: Tauri 2 + PyInstaller Sidecar Desktop

**Date:** 2026-06-08
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related EPIC:** #277 (Phase -1), #282 (Phase 3)

---

## Context

The consolidated plan requires a desktop host application to make CHERENKOV accessible to non-technical QA engineers. The desktop app should:
- Provide one-click installation (MSI/DMG/AppImage)
- Run a 7-step setup wizard
- Detect hardware (GPU/CPU/RAM) for VLM tier routing
- Manage devices (emulators, physical devices, browsers)
- Stream pipeline progress via NDJSON

Options considered:
1. **Electron** (JavaScript/TypeScript, Chromium-based)
2. **Tauri 2** (Rust, WebView-based)
3. **Native GUI frameworks** (Qt, GTK, WinUI)

## Decision

**Tauri 2 + PyInstaller sidecar**: Tauri 2 as the host window (Rust), CHERENKOV CLI as a PyInstaller-bundled sidecar process, communicating via NDJSON on stdin/stdout.

### Rationale

1. **Already half-built**: `desktop/src-tauri/` scaffold exists (29-line placeholder)
2. **Smaller binary**: Tauri 2 produces ~10MB vs Electron's ~150MB
3. **Rust native**: Better performance for hardware detection, GPU queries
4. **Windows-first**: Tauri 2 has excellent Windows support (primary target)
5. **NDJSON protocol**: Simple, streamable, debuggable (human-readable)
6. **Sidecar pattern**: CHERENKOV CLI remains the source of truth, desktop is just a host

### Architecture

```
┌─────────────────────────────────────┐
│  Tauri 2 Desktop App (Rust)         │
│  - Window management                │
│  - Hardware detection               │
│  - Device management                │
│  - Settings UI                      │
└──────────────┬──────────────────────┘
               │ NDJSON (stdin/stdout)
               │ Commands: run, stop, status, config_set, config_get
               │ Events: progress, result, error, health_change
               ▼
┌─────────────────────────────────────┐
│  CHERENKOV CLI (PyInstaller)        │
│  - Pipeline execution               │
│  - Knowledge queries                │
│  - Chat agent                       │
│  - Mobile testing                   │
└─────────────────────────────────────┘
```

### IPC Protocol

**Commands (desktop → CLI):**
```json
{"command": "run", "args": {"spec_path": "/path/to/spec.yaml"}}
{"command": "stop", "args": {}}
{"command": "status", "args": {}}
{"command": "config_set", "args": {"key": "vlm_tier", "value": "mid"}}
{"command": "config_get", "args": {"key": "vlm_tier"}}
```

**Events (CLI → desktop):**
```json
{"event": "progress", "data": {"stage": "ingest", "progress": 0.5}}
{"event": "result", "data": {"tests_generated": 42}}
{"event": "error", "data": {"code": "dependency_unavailable", "message": "LocalAI not available"}}
{"event": "health_change", "data": {"status": "degraded", "dependencies": {"localai": "unavailable"}}}
```

### Consequences

**Positive:**
- Small binary size (~10MB vs ~150MB for Electron)
- Fast startup (<2s cold)
- Native performance for hardware detection
- Sidecar pattern keeps CLI as source of truth
- NDJSON protocol is simple and debuggable

**Negative:**
- Tauri 2 is pre-1.0 (API may change)
- Rust learning curve for contributors
- WebView limitations (no full Chromium features)
- Sidecar crash requires auto-restart logic

**Mitigations:**
- 2-day validation sprint (ticket #338) before full rewrite
- Comprehensive error handling (auto-restart with exponential backoff)
- Fallback to CLI-only mode if desktop fails
- Clear documentation of IPC protocol

## Alternatives Considered

### Alternative 1: Electron
Use Electron (JavaScript/TypeScript, Chromium-based).

**Rejected because:**
- Large binary size (~150MB vs ~10MB for Tauri 2)
- Slow startup (>5s cold)
- High memory usage (Chromium overhead)
- JavaScript performance for hardware detection
- Overkill for simple host window

### Alternative 2: Native GUI (Qt/GTK/WinUI)
Use native GUI frameworks (Qt for cross-platform, WinUI for Windows-only).

**Rejected because:**
- Complex build system (CMake, qmake)
- Large binary size (~50MB for Qt)
- Steep learning curve (C++ or platform-specific languages)
- Harder to maintain (3 codebases for 3 platforms)
- No existing scaffold (would start from scratch)

### Alternative 3: Web App (PWA)
Use Progressive Web App (PWA) with service worker.

**Rejected because:**
- Requires browser (not standalone app)
- Limited hardware access (no GPU detection)
- No native installer (user must "install" from browser)
- Offline support is complex
- Doesn't meet "one-click installation" requirement

## Implementation Plan

### Phase 2: Validation Sprint (2 days)
- Build minimal Tauri 2 prototype
- Verify NDJSON communication with sidecar
- Test on Windows, macOS, Linux
- Document any API changes or issues

### Phase 3: Full Rewrite (4 weeks)
- Full `main.rs` rewrite with all features
- Hardware detection (`hardware.rs`)
- OS-specific setup (`setup/windows.rs`, `setup/macos.rs`, `setup/linux.rs`)
- 7-step setup wizard
- DeviceManager screen
- Settings screen
- Tauri IPC protocol
- Desktop packaging (MSI/DMG/AppImage)

## References

- EPIC #282 (Phase 3: Desktop Host)
- `desktop/src-tauri/src/main.rs` (existing scaffold)
- `packaging/launcher.py` (existing NDJSON launcher)
- Tauri 2 documentation: https://v2.tauri.app/

## Notes

This ADR establishes the desktop architecture. All Phase 3 tickets must follow the Tauri 2 + PyInstaller sidecar pattern.

If Tauri 2 validation sprint fails (ticket #338), this ADR will be revisited and an alternative (Electron or native GUI) will be chosen.
