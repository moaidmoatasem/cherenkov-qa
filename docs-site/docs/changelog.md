# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-06-29

### Added

- **Auto-Memory + Hooks (CC-1)**: SQLite FTS5 memory repository, HookRegistry with 10 hook events, SubprocessHookExecutor with warn/abort fail modes.
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
- **`cherenkov demo`**, **`drift`**, **`report`**, **`check-suite`** commands.
- **Coverage gap reporting**: `--coverage-report` flag on verify/certify.

### Changed

- Architecture improvements across Phases 0-2: port dedup, orchestrator decomposition, event bus, use cases layer.
- All CLI commands support `--json` and `--quiet` flags.

### Fixed

- 8 P0 fixes across security, code quality, stability, and governance.
- Windows WSL SQLite UNC path handling.
- Test staleness detection.

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
