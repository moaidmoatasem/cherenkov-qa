# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
