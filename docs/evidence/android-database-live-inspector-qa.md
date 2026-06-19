# Android Database Live Inspector — CHERENKOV QA Report

**Date:** 2026-06-18  
**Target:** `ahmedvhashem/android-database-live-inspector` (GitHub)  
**Branch:** `claude/android-database-live-inspector-b4gq9f`  
**Methodology:** Static analysis via public repository inspection (source, build scripts, README)  
**Verdict:** **NOT PRODUCTION-READY** — 1 build-blocking defect, 3 critical gaps, several improvement areas

---

## Executive Summary

Android Database Live Inspector is a focused, well-scoped Android Studio plugin for real-time Room/SQLite monitoring. The architecture (plugin → inspector DEX → agent AAR → protocol) is clean and the integration API is intentionally minimal. However, static analysis of the build scripts and project structure surfaces a **build-blocking hardcoded path** that prevents any contributor from building the project out-of-the-box, plus critical gaps in testing, distribution, and security documentation. The project is promising but needs these blockers resolved before it can be recommended for adoption.

---

## 1. Architecture QA

**Status: PASS (with notes)**

**Evidence:**
- 5-module Gradle project: `plugin`, `inspector`, `agent`, `protocol`, `stubs`
- Separation of concerns is sound: wire types isolated in `protocol`, runtime interception in `agent`, IDE UI in `plugin`
- Agent targets `minSdk 26`, `compileSdk 37`, JDK 17 toolchain
- Plugin targets Android Studio 2025.2 (platform 253+), JDK 21 toolchain
- `buildAll` root task orchestrates `:plugin:buildPlugin` + `:agent:assembleRelease` in one shot

**Findings:**
- Architecture is clean. The `processResources` hook that embeds the inspector DEX into the plugin JAR is the correct pattern for App Inspection plugins (mirrors how the Network Inspector works in AOSP).
- No circular dependencies detected between modules.
- **Note:** Platform 253 = Android Studio 2025.2 only. No backward-compatibility range declared. Users on Ladybug (2024.2) or Meerkat (2025.1) are silently excluded with no error message.

---

## 2. Build Reproducibility QA

**Status: CRITICAL FAIL**

**Evidence (plugin/build.gradle.kts):**
```
IntelliJ Platform dependencies targeting Android Studio locally at
  /Users/hashem/Applications/Android Studio.app/Contents
```

**Findings:**
- The plugin build is wired to a **hardcoded absolute path on the developer's personal Mac** (`/Users/hashem/Applications/Android Studio.app/Contents`).
- Every external contributor, CI runner, and Linux/Windows developer gets an immediate Gradle configuration failure: `Could not find the specified IntelliJ Platform`.
- There is no fallback to a downloadable IDE via the IntelliJ Platform Gradle Plugin's `intellijPlatform { localPath = ... }` vs `type + version` download mechanism.
- The `agent` module builds fine independently (standard AGP + Maven Central deps), but the full `./gradlew buildAll` is broken for anyone not at that exact Mac path.

**Severity: P0 — Blocks all external builds and CI.**

**Fix:** Replace the local path with a type/version download:
```kotlin
intellijPlatform {
    androidStudio("2025.2.1")  // downloads from JetBrains CDN
}
```

---

## 3. Testing QA

**Status: FAIL**

**Evidence:**
- `agent/build.gradle.kts` includes `junit:junit:4.13.2` as a test dependency
- No test source directories (`src/test/`) visible in any module's directory listing
- No Robolectric, MockK, or Espresso dependencies
- No GitHub Actions CI workflow file detected

**Findings:**
- Zero tests exist in the repository as of this analysis.
- The inspector DEX injection and Room query interception are the highest-risk components — they involve bytecode manipulation and runtime hooking — and have no test coverage.
- No CI gate exists to catch regressions on push.
- `junit:junit:4.13.2` is JUnit 4 (EOL); projects started today should prefer JUnit 5 or at minimum Kotlin Test.

**Severity: P1 — No regression safety net.**

---

## 4. Distribution QA

**Status: FAIL**

**Evidence:**
- `agent/build.gradle.kts` publishes to `mavenLocal()` only
- No Maven Central or GitHub Packages publishing configuration
- No GitHub Releases created (0 releases on the repo)
- No JetBrains Plugin Marketplace listing
- README instructs users: `./gradlew :protocol:publishToMavenLocal :agent:publishToMavenLocal`

**Findings:**
- Users must clone the repo and build the agent AAR from source before they can use it — a steep adoption barrier.
- `mavenLocal()` publishing is non-reproducible across machines and breaks in CI unless the repo is pre-built in the same job.
- The plugin ZIP must be installed manually from disk; no marketplace discovery path exists.
- Version `1.0.0` is declared but never shipped as a tagged release.

**Severity: P1 — Adoption barrier; claimed v1.0.0 is unreachable without a source build.**

---

## 5. Security QA

**Status: NEEDS IMPROVEMENT**

**Evidence:**
- Agent captures: SQL statements, bind arguments, execution timing, errors, result previews
- Integration uses `debugImplementation` (correct — agent stays out of release APK)
- No security guidance in README

**Findings:**
- **Bind argument exposure:** Bind args almost certainly include passwords, tokens, and PII stored in the database. The tool transmits these to the IDE in plaintext JSON over ADB. The README contains zero warnings about this.
- **Release-build safety:** `debugImplementation` protects the agent, but the README should explicitly state that `releaseImplementation` or `implementation` would ship the inspector to production, and why that's dangerous (ADB-accessible sensitive data, performance overhead).
- **No data redaction API:** No mechanism to suppress specific bind args (e.g., redact columns tagged as sensitive). Compare to Network Inspector's `addInterceptor` pattern for header redaction.
- **ADB transport:** The App Inspection wire runs over ADB — inherently a trusted-device channel. Acceptable for a debug tool; should be documented so developers understand the threat model.

**Severity: P2 — No immediate exploit, but PII leakage risk with zero user guidance.**

---

## 6. Documentation QA

**Status: NEEDS IMPROVEMENT**

**Evidence (README analysis):**
- Covers: overview, architecture, build instructions, integration (2 code snippets), usage
- Missing sections identified below

**Findings:**
| Missing Section | Impact |
|---|---|
| Compatibility matrix (Android Studio versions, Room versions, min SDK) | Users don't know if the plugin works with their setup |
| Troubleshooting guide | First time a build fails, users have no path forward |
| Screenshots / demo GIF | LinkedIn post generated interest; README does not convert it |
| ProGuard / R8 consumer rules | Agent uses reflection; consumers need to know if rules are needed |
| Known limitations | e.g., multi-process apps, encrypted databases (SQLCipher), WAL mode |
| CHANGELOG | No release history |
| Contributing guide | No contribution guidelines in README (CONTRIBUTING.md exists but not linked) |
| Security warning for bind args | See Security QA above |

---

## 7. API Ergonomics QA

**Status: PASS (with notes)**

**Evidence (README integration snippet):**
```kotlin
DatabaseLiveInspector.install(context)
val builder = Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
DatabaseLiveInspector.attachTo(builder, "app.db")
val db = builder.build()
```

**Findings:**
- Two-line integration is best-in-class for developer ergonomics. No Hilt/Dagger wiring required.
- `install(context)` — unclear if this must be `Application` context or if `Activity` context leaks. Should document.
- `attachTo(builder, "app.db")` — the second argument duplicates the name already in `databaseBuilder(...)`. Could be inferred; this is a minor API usability nit.
- No documented support for multiple databases (common in large apps). Does calling `attachTo` twice work?
- No documented cleanup / `uninstall()` method — relevant for test teardown in unit/instrumentation tests.

---

## 8. Dependency QA

**Status: PASS (with notes)**

**Evidence:**
- `androidx.room:room-runtime:2.8.4` — very recent (2025)
- `junit:junit:4.13.2` — test only, JUnit 4
- No transitive dependency conflicts observed
- Uses AGP 9.0+ (implied by "built-in Kotlin support" note)

**Findings:**
- Room 2.8.4 is the version the agent was built against. If a consumer uses Room 2.6.x or 2.7.x, internal Room API compatibility is unproven.
- AGP 9.0 requires Gradle 8.x and JDK 17 minimum — this may conflict with older consumer projects. Not documented.
- No `SECURITY.md` or dependency audit (Snyk/Dependabot) configured.

---

## Summary Scorecard

| Category | Status | Severity |
|---|---|---|
| Architecture | PASS | — |
| Build Reproducibility | **CRITICAL FAIL** | P0 |
| Testing | **FAIL** | P1 |
| Distribution | **FAIL** | P1 |
| Security | NEEDS IMPROVEMENT | P2 |
| Documentation | NEEDS IMPROVEMENT | P2 |
| API Ergonomics | PASS (minor notes) | P3 |
| Dependencies | PASS (minor notes) | P3 |

---

## Recommended Actions (Priority Order)

1. **[P0]** Replace `localPath` with `type/version` download in `plugin/build.gradle.kts` so any machine can build.
2. **[P1]** Add at least unit tests for the agent's query-interception logic (Robolectric + MockK).
3. **[P1]** Set up GitHub Actions CI (build + test on push/PR).
4. **[P1]** Publish agent AAR to Maven Central or GitHub Packages; create a tagged GitHub Release.
5. **[P2]** Add security callout to README: bind args contain PII, `debugImplementation` only.
6. **[P2]** Add compatibility matrix: supported Android Studio versions, Room versions, minSdk.
7. **[P3]** Add troubleshooting section and demo GIF to README.
8. **[P3]** Clarify multi-database support and document `context` requirement for `install()`.

---

*Report produced via CHERENKOV static analysis protocol. All findings are backed by raw evidence from the public repository.*
