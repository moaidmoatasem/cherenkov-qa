# Desktop Panel Integration Spike — Qwen Code in Tauri

## Goal
Embed the Qwen Code interactive UI within the CHERENKOV Desktop Tauri 2 application.

## Current State
- CHERENKOV Desktop is built on Tauri 2 (`desktop/`).
- Qwen Code provides a web-based UI (`qwen serve`) or can be embedded as a terminal component via xterm.js.

## Proposed Architecture

### Option 1: Webview Embedded `qwen serve` (Recommended)
Run `qwen serve` as a background sidecar process in Tauri. Embed a WebView panel in the React frontend pointing to `localhost:<port>`.

**Pros**:
- Native Qwen Code UI with all features.
- Very little frontend code required in CHERENKOV Desktop.

**Cons**:
- Requires shipping Node.js or a compiled Qwen Code binary with the Tauri app.

### Option 2: Terminal Emulator (xterm.js)
Embed `xterm.js` in the Tauri frontend and spawn `qwen` as a local PTY process.

**Pros**:
- Feels like a true terminal experience.
- Easy to integrate with existing terminal-based workflows.

**Cons**:
- Handling PTY resizing and ANSI escape codes in Tauri can be tricky.

## Next Steps
1. Test running `qwen serve` manually and accessing it via browser.
2. If stable, add a Tauri command to spawn `qwen serve --port 8989`.
3. Add a new route/panel in `desktop/src/` to host an iframe pointing to `http://localhost:8989`.
