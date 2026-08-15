# Release Notes: CHERENKOV-QA v1.0.0

**Date:** 2026-06-19
**Tag:** `v1.0.0`

We are thrilled to announce the `v1.0.0` release of CHERENKOV-QA, the first AI-native API conformance testing engine.

## What is CHERENKOV?

CHERENKOV reads your OpenAPI specification, uses a local LLM to generate typed Playwright API tests, executes them against a real server, and delivers conformance violation reports—all with **zero vendor lock-in**. If you want to leave CHERENKOV, a single `eject` command strips our framework and leaves you with vanilla, human-readable Playwright tests that run forever.

## Key Features in v1.0.0

This release marks the completion of the Core API Track alongside 5 parallel extension tracks:

### 1. 🤖 Offline-First Local LLM Generation
- Defaults to `qwen2.5-coder:7b` for code generation.
- No cloud dependencies. No API keys. Your spec never leaves your machine.
- 6-gate review process (syntax, AST, TypeScript compilation, Prism mock) ensures generated tests are strictly valid.

### 2. 🔌 Zero Lock-In (`cherenkov eject`)
- Automatically compile generated tests into standalone Playwright specs.
- Ejected tests use `openapi-fetch` and run without CHERENKOV dependencies.

### 3. 🎯 CI/CD Native Capabilities
- **Fail-on-Drift Mode:** Returns exit code `1` if the live server drifts from the OpenAPI spec.
- **JUnit XML & SARIF:** Standardized reporting output formats for seamless CI/CD pipeline integrations and GitHub Security tab integration.
- **GitHub Action & Templates:** Plug-and-play `.gitlab-ci.yml` and `cherenkov-circleci-orb.yml` available in the repository.

### 4. 📱 Multi-Platform Extension Tracks
- **Desktop Host (Tauri):** Fast native desktop wrapper (308MB payload) built in Rust.
- **Mobile Execution Core:** Scaffolded Maestro and Appium device-flow runners.
- **Web Dashboard:** Interactive React UI for visualizing execution results and divergence metrics.
- **K8s Operator:** In-cluster scheduled conformance scanning.

## Quick Start

```bash
npx cherenkov-cli init
```

## Community and Next Steps

We are entering the **Reality Engine** phase. Try CHERENKOV today to automate the tedious parts of QA, entirely locally. Join our Discord community, star the repository, and help us redefine API testing.
