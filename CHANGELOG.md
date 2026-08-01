# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-08-01

### Added
- **GraphQL/gRPC/AsyncAPI ingest + generation** (Phase 12): schema/proto ingest, test generation, conformance validation, and Buf schema registry integration are real and wired into the CLI.
- **VS Code extension** (Phase 11): inline conformance indicators, healing suggestions, drift-on-save, test explorer, and quick-fix are all wired into the extension.
- **Enterprise audit log** and **LangChain tool package**: real, wired implementations.
- **Desktop auto-setup wizard**: real Tauri state machine.
- **Market Launch Documentation**: Added `docs/landing_page_copy.md` and `docs/demo_script.md`.
- **UX Redesign**: 5-hub information architecture, Kanban triage, live-wired Spec vs. Reality / Coverage & Certification / Test Management screens, real chat session history.

### Corrected
- **The previous entry in this changelog claimed Phase 11-16 was "fully implemented," including Enterprise tier, Spec Guardian, and the Phase 16 marketplace/webhook/analytics ecosystem. That claim was false.** A code-level audit (2026-08-01) against the corresponding GitHub issues found: Enterprise SAML/RBAC/GDPR (Phase 13) have real logic modules but are not wired into any route or CLI command (several are literal `"""Placeholder"""` stubs); the Spec Guardian daemon (Phase 14) exists but has zero callers anywhere in the codebase; the fine-tuning pipeline (Phase 15) is an explicit simulation (`"SIMULATION: would train..."`, a fake `"SIMULATED_LORA_WEIGHTS"` marker file); and the Phase 16 platform/marketplace layer is almost entirely absent or stub data. See the tracking issues on GitHub for the current, per-item status.

### Fixed
- **Repository Alignment**: Resolved merge conflicts in `HANDOVER.md` and fully synchronized `feat/qa-headless-locator-alignment` with `origin/main`.
- **Ruff Compliance**: Resolved 383 linting issues (primarily `E402` and `F401`) across `tests/` and `cherenkov/`.
- **Release/tag reconciliation**: `.release-please-manifest.json` and `package.json` had drifted to `1.0.0`; the `v1.1.1` release was tagged `v.1.1.1` (stray dot), breaking the docs-deploy version-extraction step.

## [1.1.2] - 2026-07-31

### Added
- **Unprobed-endpoint reporting** — `unprobed_endpoints()` (`cherenkov/divergence/probe_planner.py`) lists every operation probe planning produced nothing for, with the real reason, and `cherenkov verify` prints them before running. A zero-probe endpoint contributes no divergences, so a clean exit code previously implied coverage that never happened. Applied to `petstore.json` this reports **7 of 19 operations unprobed** — coverage was 12/19, not 19/19. Most causes are deliberate limits and are labelled as such: happy-path probes are GET-only (sampled data would mutate state), skipped on templated paths (a sampled identifier need not exist, and its 404 would read as a divergence), and skipped when query parameters are required. Truncation by `--max-probes` is reported rather than silent. Advisory, not fatal.
- **`RecordingProxy`** (`cherenkov/verdict/traffic_capture.py`) — a forwarding HTTP proxy that records what a test suite actually receives from a live target. Where `CapturingWitnessAgent` records CHERENKOV's own probe traffic, this records someone else's suite: point their `API_URL` at the proxy and every request is forwarded while the response is captured. `recorded_base()` feeds straight into `synthesize_mutant_battery(base=...)`, completing a **record-then-perturb** audit that needs no known-honest baseline suite — only a live target, which `verify` already requires. Demonstrated end to end against a live server with no hand-supplied values: 3 of 3 cheat classes detected, 0 false alarms; hallucinated suites are caught by the green run itself, before any mutation.
- **`synthesize_mutant_battery()`** (`cherenkov/divergence/mutant_synth.py`) — emits one mutant per failure axis (status, single-value, enum, missing-field) plus a conforming control, so a test's failure is attributable to a specific weak assertion. Validated against the labelled cheat corpus in `demos/catch-the-ai-cheating/`: 3 of 3 cheat classes detected with no false alarm on the honest suite, where the existing single coarse mutant detects none. Takes an optional `base` — the response actually recorded from the target — because a spec constrains types, not instance values, and mutating a schema-sampled body makes an honest suite fail its own control.

### Fixed

- **Soundness: `verify` could report a clean run on an endpoint it never probed.** OpenAPI 3.x allows a path parameter to be declared once on the PathItem and inherited by every operation beneath it. Probe planning read only `operation.parameters`, so on the inherited form the path placeholder was never filled and the endpoint was dropped from planning entirely — yielding zero divergences and exit code 0. The same API written the two legal ways planned 1 probe and 0 probes respectively. `merge_path_item_parameters()` is now the single definition of the `(name, in)` precedence rule, applied both in `cherenkov/divergence/probe_planner.py` and at the ingestion slicing point in `cherenkov/stages/ingest.py`, so every downstream consumer — probe planning, the meaningful-assertion gate, `truth/sources/openapi.py` — receives inherited parameters. 11 regression tests.
- **Misleading gate skip message.** `synthesize_mutant_response()` returns `None` for two unrelated reasons — no documented 2xx response, or path parameters that cannot be sampled — and both were reported as "spec has no documented success response to mutate". `explain_unmutatable()` now names the real cause, and for unfillable parameters says where to declare them.
- **Hanging unit test.** `test_returns_suggested_patch_not_applied` patched the handler with `wraps=`, which mocks nothing, so the real inference router opened a live LLM connection and the test hung until the suite timed out.

### Documentation

- **`docs/ROADMAP_2026H2.md`** — consolidated forward plan (milestones M0–M5) with verifiable exit criteria, derived from `HANDOVER.md`. Supersedes the scattered roadmap documents as the forward reference; `PRODUCT_STRATEGY_ROADMAP.md` is reclassified as a hypothesis register rather than a plan.
- **`docs/evidence/e0.5e_oracle_discrimination.md`** — measured the baseline-free integrity oracle against the labelled cheat corpus. Isolated single-axis mutants plus a conforming run separate all three cheat classes with no false alarm on the honest suite; the coarse status-plus-field mutation currently used by the meaningful-assertion gate separates none of them. Building the mutation battery is tracked as roadmap item E0.5f.
- `HANDOVER.md` status anchor refreshed — the stale "788+ tests" figure corrected to a measured 1753, and the "mypy runs clean" claim corrected to record the gate as failing.

### Known issues

- **Mypy gate is failing** — 7 errors across `cherenkov/ai/openai_client.py`, `cherenkov/ai/nemoclaw_client.py` and `cherenkov/substrate/providers/localai.py`.
- **Release tags are inconsistent with the package version.** `pyproject.toml` declares `1.1.1`, while the tag list contains `v1.2.0`, `v3.1-delta` and a malformed `v.1.1.1`. Reconcile before the next publish — a release cut from this state is not reproducible.
- **The meaningful-assertion gate under-detects.** See the evidence document above; it is sound as a per-test check behind the prism-dryrun precondition, but its single coarse mutant does not catch a deliberately weakened suite.

## [1.1.1] - 2026-06-29

### Added

- **Auto-Memory + Hooks (CC-1)**: SQLite FTS5 memory repository, HookRegistry with 10 hook events, SubprocessHookExecutor with warn/abort fail modes. ADR-011, ADR-012.
- **Multi-Agent Conductor (CC-2)**: Fan-out/fan-in agent orchestration over MCP mesh.
- **MCP Ecosystem Expansion (CC-3)**: MCP marketplace, push events, JWT auth, 5 new integrations.
- **Scheduling + Routines (CC-4)**: APScheduler integration, web UI, GitHub webhook trigger.
- **Remote Control + Teleport (CC-5)**: Session snapshot, QR-code join, SSH/Docker remote runner.
- **CLI Composability (CC-6)**: `--json`/`--quiet` on all commands, pipe mode, shell completions.
- **Phase 9 — Semantic Memory**: MemSearch repository integration with SDD protocol.
- **Phase 10 — CI/CD Native**: CI/CD reorganization + Jenkins Shared Library.
- **Phase 11 — VS Code Extension**: Full extension wiring with 11 commands.
- **Phase 12 — gRPC Support**: Buf Schema Registry integration.
- **Phase 13 — Drift Reconciliation**: L2 maker/checker, CLI autonomy flag.
- **Phase 14 — Eval Pipeline**: generate→grade→compare→optimize loop.
- **Phase 15 — Synthetic Suite Generation**: STORM-inspired multi-persona suite generation.
- **Multi-Agent Verdict Engine**: Rich verdict engine with resume-inspired web UI.
- **JWT + RBAC Auth Layer**: Opt-in authentication across all backend routes.
- **Public Documentation Site**: Material for MkDocs site hosted on GitHub Pages.
- **`cherenkov demo` command**: Offline 60-second onboarding.
- **`cherenkov drift` command**: Spec-drift CLI with reconciliation.
- **`cherenkov report` command**: Divergence JSON summary + diff.
- **`cherenkov check-suite` command**: AI cheating detection in test suites.
- **Coverage gap reporting**: `--coverage-report` flag on verify/certify.

### Changed

- Architecture improvements across Phases 0-2: port dedup, orchestrator decomposition, event bus, use cases layer.
- All CLI commands support `--json` and `--quiet` flags.
- Config consolidated with structured errors and validation.

### Fixed

- 8 P0 fixes across security, code quality, stability, and governance.
- Windows WSL SQLite UNC path handling.
- Node.js detection and Ollama onboarding false negatives.
- Test staleness detection.
- Lint cleanup across 30+ files.

## [1.1.0] - 2026-06-19

### Added

- **Multi-Protocol Support**: GraphQL schema ingestion, gRPC/Protobuf via Buf CLI, AsyncAPI/WebSocket.
- **Enterprise Tier**: SAML 2.0 / SSO (Okta, Azure AD, Google Workspace), SOC2 readiness, GDPR compliance, RBAC, audit logging, org management, BYO-LLM (Azure OpenAI, AWS Bedrock).
- **VS Code Extension**: 11 commands, gutter indicators, CodeLens, diagnostics, test explorer.
- **GitHub Actions**: `cherenkov-qa/action@v1` with SARIF output.
- **GitLab CI / CircleCI**: Templates for both platforms.
- **Jira Integration**: REST v3 client with `--export-jira` CLI flag.
- **Pre-commit hook**: `.pre-commit-hooks.yaml` for drift detection.
- **Spec Guardian**: Continuous conformance monitoring daemon.
- **Training Pipeline**: Dataset collector, LoRA fine-tune trainer, evaluation harness.
- **Launch Materials**: Product Hunt kit, demo script, Discord setup guide.

### Changed

- Upgraded from v1.0.0 core to full extended roadmap (Phases 9-16).

### Fixed

- Various K8s operator deployment and RBAC fixes.
- CRD extension validation.

## [1.0.0] - 2026-06-20

### Added
- **Core Engine**: AI-native API conformance testing engine.
- **Spec-derived Validation**: OpenAPI ingest → LLM tests → Conformance Validation.
- **Suggest-only Healing**: Provides code suggestions without auto-applying to maintain invariants.
- **Eject Capability**: Strip all CHERENKOV imports to export vanilla Playwright tests (Zero lock-in).
- **Security Check**: Embedded OWASP mutation payloads (DAST lite).
- **VLM & Visual Oracle**: Support for Ollama and local model tier routing. Visual validation of the Dashboard via `qwen2.5-coder:7b`.
- **GraphRAG Second Brain**: Knowledge mesh for idioms, incidents, and verdicts.
- **Chat Agent**: Conversational agent with tool-calling capabilities and SSE streaming.
- **Dashboard UI**: Comprehensive React dashboard with 9 screens, including Device Manager, Health Widget, and Truth Map.
- **K8s Operator**: `ConformanceCheck` CRD and Go operator for Kubernetes-native CI/CD runs.
- **Quickstart CLI**: `npx cherenkov init` zero-install script.
- **Comprehensive QA Suite**: Integrated UI testing with Playwright for the Dashboard.

### Changed
- Transitioned default LLM to offline-first `qwen2.5-coder:7b` via Ollama.

### Fixed
- Stabilized and integrated K8s fixes.
- Validated CRD extensions and device env vars.
