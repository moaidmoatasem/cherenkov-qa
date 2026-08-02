# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0](https://github.com/moaidmoatasem/cherenkov-qa/compare/v1.2.0...v1.3.0) (2026-08-02)


### Features

* **cli:** add guardian start CLI entrypoint for Spec Guardian daemon ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([c5ca28a](https://github.com/moaidmoatasem/cherenkov-qa/commit/c5ca28a15365dcac08cdf25d44cd922bd8611da9))
* **cli:** add guardian start CLI entrypoint for Spec Guardian daemon ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([#823](https://github.com/moaidmoatasem/cherenkov-qa/issues/823)) ([296d4d5](https://github.com/moaidmoatasem/cherenkov-qa/commit/296d4d505f74c07a4bebbc20dd3e28a8353bf7f3))
* **cli:** give the Spec Guardian daemon a CLI entrypoint ([#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811)) ([4ac1f1e](https://github.com/moaidmoatasem/cherenkov-qa/commit/4ac1f1e1d151d20085f07de42c6a26067160f2d2))
* **cli:** wire SAML/RBAC commands to real modules ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)) ([352153d](https://github.com/moaidmoatasem/cherenkov-qa/commit/352153dcd9b21b6e36d530e5a3eaf86df448dcf8))
* **cli:** wire SAML/RBAC commands to real modules ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)) ([#824](https://github.com/moaidmoatasem/cherenkov-qa/issues/824)) ([f86d624](https://github.com/moaidmoatasem/cherenkov-qa/commit/f86d624b9370f6e8aeea9ddd70dc104cef5eff71))
* **mcp:** expose check-suite/verify/generate as agent-invokable tools ([#812](https://github.com/moaidmoatasem/cherenkov-qa/issues/812)) ([c2b1bf2](https://github.com/moaidmoatasem/cherenkov-qa/commit/c2b1bf2730392c4f8b385a442ca33ad264a532f2))
* **mcp:** expose check-suite/verify/generate as agent-invokable tools ([#812](https://github.com/moaidmoatasem/cherenkov-qa/issues/812)) ([#821](https://github.com/moaidmoatasem/cherenkov-qa/issues/821)) ([39d592d](https://github.com/moaidmoatasem/cherenkov-qa/commit/39d592d3e28b6dd76a78f9e156227c6c0850d4ae))
* **mcp:** registry manifest + publish instructions, ready for submission ([#792](https://github.com/moaidmoatasem/cherenkov-qa/issues/792)) ([69b8540](https://github.com/moaidmoatasem/cherenkov-qa/commit/69b854025cb828284ef3298fec044386f0c23d5f))
* **ui:** Complete 5-Workspace UI/UX Revamp, FastAPI Backend Wiring, and Playwright E2E Test Suite ([2e66658](https://github.com/moaidmoatasem/cherenkov-qa/commit/2e6665888d4a735f7a0dadb0be0e9bfdf1695de6))
* **validate:** add --tests filter to scope runs ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([e35e3ba](https://github.com/moaidmoatasem/cherenkov-qa/commit/e35e3bae3c316e3b527061b995ea29d20bfbea4a))


### Bug Fixes

* fix:  ([ea555e7](https://github.com/moaidmoatasem/cherenkov-qa/commit/ea555e72485fec904e62b60a43d82adf4da732cd))
* **core:** Resolve top 6 technical debt items identified in architecture review ([#832](https://github.com/moaidmoatasem/cherenkov-qa/issues/832)) ([00d277e](https://github.com/moaidmoatasem/cherenkov-qa/commit/00d277e876461f0f8dc27bd3712699c237422a2d))
* **generate:** persist one distinct file per scenario ([#828](https://github.com/moaidmoatasem/cherenkov-qa/issues/828)) ([7c77fb4](https://github.com/moaidmoatasem/cherenkov-qa/commit/7c77fb4cf574b89eec40073b3c2d7afc4427444a))
* **M1:** resolve friction bugs, tests, and ui automation ([6c7335b](https://github.com/moaidmoatasem/cherenkov-qa/commit/6c7335ba67cf162486f651d97f9c9c531c79f71a))
* **sdd:** repair agent_sync MemSearch workspace_dir API mismatch ([c7b2008](https://github.com/moaidmoatasem/cherenkov-qa/commit/c7b20080ad000320253692c77241ee5ed645ed38))
* **validate:** accept OpenAPI 3.0.x patch versions ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([fc48936](https://github.com/moaidmoatasem/cherenkov-qa/commit/fc48936e914aa35e897f07cfab59252140790f6c))


### Documentation

* add comprehensive architecture review report ([349d438](https://github.com/moaidmoatasem/cherenkov-qa/commit/349d43857e9b30e4b2112fa377c693c8f5b9fd07))
* **cli:** document audit + record commands, update MCP config examples ([#814](https://github.com/moaidmoatasem/cherenkov-qa/issues/814)) ([ac6b977](https://github.com/moaidmoatasem/cherenkov-qa/commit/ac6b9777c9262ea1f8c363279ff46f3f16cb4ac7))
* **getting-started:** document the `guardian` CLI command ([7a8a9a2](https://github.com/moaidmoatasem/cherenkov-qa/commit/7a8a9a26aabff47d8ddab918e213c14c29381c76))
* **handover:** note [#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811) PR status ([02ef89b](https://github.com/moaidmoatasem/cherenkov-qa/commit/02ef89b02add2e4ad0242aae80d465332e084f4c))
* lead verification pass — main certified, PAT expiry blocker recorded ([2483feb](https://github.com/moaidmoatasem/cherenkov-qa/commit/2483feb5ce724e9750a61f6620867079b29f1ceb))
* **onboarding:** add prerequisites + tool install steps, fix cold-run blocker ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826), [#827](https://github.com/moaidmoatasem/cherenkov-qa/issues/827)) ([4fab3c1](https://github.com/moaidmoatasem/cherenkov-qa/commit/4fab3c11e8f07a5118db40779d78483b7128be39))
* **onboarding:** align init visual with real cold-run output ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826)) ([8b13145](https://github.com/moaidmoatasem/cherenkov-qa/commit/8b131454bf4f2a348e3ce8694db7836e4ad5b83e))
* **onboarding:** fix Act 4 transcript and scoping guidance ([#829](https://github.com/moaidmoatasem/cherenkov-qa/issues/829)) ([8c9c215](https://github.com/moaidmoatasem/cherenkov-qa/commit/8c9c215f4151e6d2e858d6772ef83dbc1c36d86e))
* **onboarding:** fix stale refs in FAQ + init transcript ([#830](https://github.com/moaidmoatasem/cherenkov-qa/issues/830), [#831](https://github.com/moaidmoatasem/cherenkov-qa/issues/831)) ([e3b77a7](https://github.com/moaidmoatasem/cherenkov-qa/commit/e3b77a7c90a8c70640449abb79388ace138023aa))
* reconcile phase 13/14 status with wired CLI ([#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810) [#811](https://github.com/moaidmoatasem/cherenkov-qa/issues/811) [#824](https://github.com/moaidmoatasem/cherenkov-qa/issues/824) [#823](https://github.com/moaidmoatasem/cherenkov-qa/issues/823)) ([307e9c4](https://github.com/moaidmoatasem/cherenkov-qa/commit/307e9c4b9a8a8e6a293db7a3c797ba04553b33f9))
* reconcile release docs with v1.2.0 ([9f62a9a](https://github.com/moaidmoatasem/cherenkov-qa/commit/9f62a9a161960c0fdf215d76b28c89182379a11c))
* **refactor:** map dual AI routing layers, propose consolidation ([#815](https://github.com/moaidmoatasem/cherenkov-qa/issues/815)) ([b23581f](https://github.com/moaidmoatasem/cherenkov-qa/commit/b23581fca06475e218d0b9759c786733e55871e7))
* **refactor:** map dual AI routing layers, propose consolidation ([#815](https://github.com/moaidmoatasem/cherenkov-qa/issues/815)) ([#820](https://github.com/moaidmoatasem/cherenkov-qa/issues/820)) ([11a6c52](https://github.com/moaidmoatasem/cherenkov-qa/commit/11a6c524219fe4b3242fc10bcdaf89525a09c30f))
* round-2 swarm result — friction fixes merged, M1 prep unblocked ([da97789](https://github.com/moaidmoatasem/cherenkov-qa/commit/da9778989560f786afb9d9828e460920e67bc6fa))
* round-3 swarm result — wiki env-var refs fixed, tree hygiene, fresh verification ([d9a161f](https://github.com/moaidmoatasem/cherenkov-qa/commit/d9a161fad6c70faaffbc2891108d6874ec63dfba))
* T-track swarm result — [#810](https://github.com/moaidmoatasem/cherenkov-qa/issues/810)-[#816](https://github.com/moaidmoatasem/cherenkov-qa/issues/816) done, friction logs filed ([#826](https://github.com/moaidmoatasem/cherenkov-qa/issues/826)-831), [#819](https://github.com/moaidmoatasem/cherenkov-qa/issues/819) tracked ([fe6f37b](https://github.com/moaidmoatasem/cherenkov-qa/commit/fe6f37b6164cca08a9c73f17464370b73a53bfbc))
* **wiki:** replace stale env vars with real settings names ([156dba0](https://github.com/moaidmoatasem/cherenkov-qa/commit/156dba073d1823d28bf2edecaed0772eb685dd5d))

## [Unreleased]

### Added
- **Enterprise CLI wiring** (Phase 13): `cherenkov enterprise` now wires SAML (`enterprise saml configure`), RBAC (`enterprise rbac assign`), org management (`enterprise org create/list`), audit export (`enterprise audit export`), and SOC2 compliance reports (`enterprise compliance generate`) to the real `cherenkov/enterprise/` modules. 114 tests in `tests/unit/test_enterprise_cli.py` (#810/#824).
- **Spec Guardian CLI entrypoint** (Phase 14): `cherenkov guardian start --spec <spec> --base-url <url>` polls every declared endpoint (repeatable `--endpoint METHOD:PATH` to override, `--interval` and `--db` to tune) and persists drift events via `SpecGuardianDaemon`, giving the previously caller-less daemon its first real caller. 147 tests in `tests/unit/test_guardian_cmd.py` (#811/#823).

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
