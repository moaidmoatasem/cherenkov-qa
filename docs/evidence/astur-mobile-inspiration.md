# Astur Mobile — Architecture Inspiration for CHERENKOV

**Date:** 2026-06-19
**Target:** `Astur-mobile/Astur` (GitHub)
**Branch:** `claude/astur-mobile-inspiration-hj048a`
**Methodology:** Static analysis via GitHub code search (source, package manifests, README)
**Purpose:** Extract design patterns to guide CHERENKOV's mobile testing layer

---

## What Astur Is

Astur (`astur-mobile` on npm, v0.3.0-beta.0, Apache-2.0, author: Amr Salem) is a
**device-native mobile automation toolkit** that brings Playwright's ergonomics to
Android and iOS without an Appium server or WebDriver bridge. It controls devices
through the platforms' own automation engines:

- **Android:** ADB + a sideloaded Kotlin instrumentation agent (`AsturAgentServer.kt`)
  running UIAutomator commands exposed as JSON-RPC over ADB port-forward.
- **iOS:** XCTest runner hosting `AsturIOSAgent` (Swift), accessed via a Unix socket
  or TCP; WKWebView traffic goes through `ios-webkit-debug-proxy` (IWDP).
- **Flutter (Android):** APK-tail scan detects Flutter apps; `flutter_test` engine
  used instead of UIAutomator.

The test layer (`@astur-mobile/test`) wraps Playwright Test: `defineConfig`,
`test`, `expect`, retries, reporters, and parallel workers all come directly from
Playwright. The `device` fixture is a Playwright fixture that boots the agent and
tears it down automatically.

---

## Architecture Map

```
astur-monorepo/
├── packages/
│   ├── protocol/        # Pure TS types: PlatformName, DeviceKind, DeviceState,
│   │                    # ElementSelector, MobileElementSnapshot, Bounds, …
│   ├── core/            # AsturDevice class, MobileLocator, auto-wait, keyboard,
│   │                    # webBridge (CDP + IWDP), inspector (locator suggestions)
│   ├── android/         # AndroidPlatformSession — ADB commands, UIAutomator XML
│   │                    # parse, Flutter detect/process, screen recording
│   ├── android-agent/   # Kotlin instrumentation APK (sideloaded, JSON-RPC server)
│   ├── ios/             # iOSPlatformSession — simctl, xcrun, IWDP, screen record
│   ├── ios-xctest-agent/# XCUITest runner + Swift agent (built and pushed via CLI)
│   ├── test/            # @astur-mobile/test: Playwright fixture wiring (device,
│   │                    # defineConfig, expect extensions)
│   ├── cli/             # astur-mobile CLI: init/scaffold, inspector UI, agent push
│   └── create-astur/    # npm create astur project scaffolder
```

---

## Key Design Decisions Worth Borrowing

### 1. No Appium — native agent with JSON-RPC

Appium's architecture (WebDriver → Appium server → UIAutomator2 driver) adds two
hops. Astur sideloads a thin Kotlin agent that speaks JSON-RPC directly over ADB
port-forward. This eliminates the Appium server, reduces latency, and removes a
heavyweight dependency.

**CHERENKOV implication:** The current `mobile_routes.py` references "Appium" in
its mental model (APK install → app launch → run test). For a real implementation,
CHERENKOV should follow the same agent model: a thin Python-callable subprocess
that ADB-forwards to a native agent, not an Appium session.

### 2. Protocol package — types first

All wire types live in a standalone `@astur-mobile/protocol` package with zero
runtime dependencies. It defines:
- `PlatformName = 'android' | 'ios'`
- `DeviceKind = 'emulator' | 'simulator' | 'real'`
- `DeviceState = 'online' | 'offline' | ...`
- `MobileElementSnapshot` (parsed UIAutomator XML tree)
- `Bounds`, `Coordinates`, `ElementSelector`, `WebLocatorDescriptor`

This means consumers can depend on `protocol` without pulling in any native driver
code, and the same types flow from the Kotlin/Swift agent through the Node.js layer
to the test fixtures.

**CHERENKOV implication:** Define `cherenkov/mobile/contracts.py` with analogous
types before writing any driver code. This keeps the mobile seam clean.

### 3. Playwright fixture ergonomics on mobile

The API exposed on `AsturDevice` mirrors Playwright's `Page` exactly:

```ts
device.getByText('Welcome')           // ← same as page.getByText(...)
device.getByLabel('Email')
device.getByRole('button', { name: 'Login' })
device.locator(by.id('com.example:id/submit'))  // ← low-level escape hatch
```

Auto-waiting is built into every locator interaction (tap, fill, expect). The
`by.*` selectors map to UIAutomator resource-id, content-desc, text, and XCTest
accessibility identifiers.

**CHERENKOV implication:** The mobile test generator (`stages/generate_mobile.py`)
should emit Playwright-compatible TS that uses `device.*` instead of raw Appium
commands. This means generated tests are automatically runnable with Astur and
ejectable — zero lock-in.

### 4. Per-worker device locking

Astur reserves a device per Playwright worker and fails fast if another worker
attempts to claim the same device. Each worker gets an isolated session and its
own artifact directory (screenshots, traces, recordings).

**CHERENKOV implication:** The mobile pilot needs a device registry with claim/
release semantics. The current `_mobile_pilot_status` global dict is a single-
device stub — it should become a proper `DeviceRegistry` with per-session state.

### 5. Inspector for locator suggestions

`packages/core/src/inspector.ts` scores candidate locators by specificity and
cross-platform compatibility. For example, `by.text()` scores 0.84 and is
`crossPlatform: true`; `by.id('com.foo:id/btn')` is Android-only. The inspector
feeds a live UI in the CLI so a user can tap an element and get the best selector.

**CHERENKOV implication:** When CHERENKOV generates mobile test scenarios from a
spec + accessibility snapshot, the same scoring heuristic should prefer semantic
locators (`by.text`, `by.testId`) over brittle resource IDs.

### 6. WebView bridge — CDP on Android, IWDP on iOS

Both platforms support hybrid apps (WebView + native). Astur opens a CDP session
into the WebView (Android: ADB + Chrome DevTools Protocol; iOS: IWDP via
`ios-webkit-debug-proxy`) and exposes the same `webContext` API on `AsturDevice`.
This lets one test switch between native and web contexts without a separate
Playwright browser.

**CHERENKOV implication:** The existing `stages/visual/` and web conformance
pipeline could share state with a mobile session when the target is a hybrid app.

---

## Gap Analysis

| Area | Astur | CHERENKOV today | Gap |
|------|-------|-----------------|-----|
| Device driver | Native UIAutomator + XCUITest agent | Stub step list | Full driver needed |
| Locator model | `by.id / by.text / getByText / getByRole` | None | Needs `cherenkov/mobile/locators.py` |
| Test generation | (not in scope — Astur runs, doesn't generate) | `stages/generate_mobile.py` planned | Must emit Astur-compatible TS |
| Session isolation | Per-worker device lock | Global `_mobile_pilot_status` dict | Needs `DeviceRegistry` |
| WebView support | CDP + IWDP bridge | None | Deferred |
| Flutter | APK tail-scan + flutter_test | None | Deferred |

---

## What CHERENKOV Should Implement Now (Minimal Slice)

The mobile Source Adapter seam is already open (`ROADMAP_AQE.md`, `SCOPE_LEDGER.md`).
The minimum viable first step before building a real driver is:

1. **`cherenkov/mobile/contracts.py`** — domain types mirroring Astur's protocol
   package: `PlatformName`, `DeviceKind`, `DeviceState`, `DeviceInfo`, `MobileSession`
2. **`cherenkov/mobile/registry.py`** — `DeviceRegistry` with claim/release so the
   REST routes can support concurrent sessions without global state collisions
3. **Improved `mobile_routes.py`** — expose `/api/v1/mobile/devices` (list),
   `/api/v1/mobile/session` (create, status, close) backed by `DeviceRegistry`
4. **Generated test template** — the mobile generate stage should emit Astur-
   compatible `@astur-mobile/test` fixtures (not raw Appium), so tests are ejectable

Items 1–3 are pure Python and can be built and tested without a real device.
Item 4 requires the generate stage, which depends on the existing LLM prompt pipeline.

---

## Honest Scope Statement

This document is **inspiration and design input**, not an implementation claim.
The code changes on this branch (`cherenkov/mobile/contracts.py`,
`cherenkov/mobile/registry.py`, improved `mobile_routes.py`) add the type layer
and a proper session registry. No real device driver is implemented — that requires
ADB, a sideloaded agent, or Appium, none of which are available in the CI sandbox.
The value is: the domain model is now correct so future driver work has a clean
surface to implement against.
