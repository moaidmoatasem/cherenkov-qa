# Changelog

All notable changes to CHERENKOV QA are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### In Progress
- **Phase 8 — K8s + Cloud + Gate:** `ConformanceCheck` CRD sync, device environment variables, cloud readiness hardening

### Coming Next
- `make k3d-test` validation for K8s operator
- Open-source readiness checklist (Phase 8 close)

---

## [1.0.0] — 2026-06-08 — Track A Validated

**The validation gate has been passed.** Track A core engine is built, tested, and the 5-QA owner-decision gate passed on 2026-06-08. All six tracks are now open for active development.

### What's Included

#### Core Engine (Track A)
- **OpenAPI → Playwright generator** — reads any OpenAPI 3.x spec, outputs typed `openapi-fetch` test files via local LLM
- **6-gate review pipeline** — every generated test passes: syntax check → structure check → AST validation → assertion coverage → TypeScript compile → Prism mock dry-run
- **Spec-derived verdict oracle** — expected HTTP status is resolved from the OpenAPI spec, never hardcoded; caught a real `422 vs 400` conformance bug in the bundled sample API
- **Suggest-only healing** — `heal` command diagnoses failures and produces fix suggestions; never auto-commits or auto-applies changes
- **Zero-lock-in eject** — `eject` strips all CHERENKOV imports; the result is vanilla Playwright + `openapi-fetch` that runs independently

#### LLM Substrate (Track B)
- **Substrate Router** — model-agnostic routing by capability tier; agents emit `ReasoningRequest{capability_tier}`, router selects provider
- **Ollama integration** — `qwen2.5-coder:7b` for generation, `deepseek-r1:8b` for planning; fully local
- **LocalAI support** — VLM backend, GPU tier routing
- **OpenAI adapter** — optional cloud fallback
- **Cost/latency accounting** — token usage tracked per provider
- **Doctor CLI** — `cherenkov doctor` checks environment health (Ollama, Node, Python, Docker)

#### Desktop Host (Track C) *(runtime blocked on `cargo`)*
- Tauri 2 desktop application scaffold
- Hardware detection (GPU, memory, OS)
- 7-step setup wizard
- Unit-tested; runtime requires `cargo` on host

#### Mobile Testing (Track D) *(runtime blocked on ADB)*
- Maestro + Appium integration
- 4-tier device support (emulator → physical → cloud → CI)
- Semantic visual oracle (VLM-based screen comparison)
- RAG-indexed mobile schema
- Unit-tested; runtime requires ADB on host

#### Dashboard (Track E) — 9 screens shipped
- React 19 + Vite 6 + TypeScript + Tailwind CSS 4
- Screens: Run History · Test Explorer · Spec Viewer · Healing Queue · Knowledge Graph · Mobile Dashboard · Chat Interface · Settings · Governance
- Playwright E2E tests + accessibility (axe-core) tests
- `cherenkov review --web` launches the dashboard

#### Kubernetes Operator (Track F) — Phase 8 in progress
- Go 1.22.5 operator with `ConformanceCheck` CRD
- `k8s-run` CLI bridge
- k3d local cluster support
- Phase 8 active: CRD sync + device env vars coded; needs `make k3d-test`

#### Platform
- **Knowledge Mesh (Second Brain)** — GraphRAG-powered knowledge graph, idiom extraction, learning from verdicts
- **Chat Agent** — tool-calling agent with persona registry and SSE streaming
- **MCP Server** — Model Context Protocol server for IDE and agent integration
- **Federation scaffold** — cross-check protocol and knowledge corpus
- **Behavioral continuity** — PR diff tracking, behavioral-diff GitHub Action
- **HITL queue** — human-in-the-loop approval workflow
- **MENA compliance scanning** — regional regulatory checks
- **Governance/certification** — KPI tracking, E12 certification gate
- **Snyk security bridge** — dependency vulnerability scanning
- **k6 performance baseline** — load testing integration

#### CI/CD (5 workflows)
- `ci.yml` — 20+ invariant check jobs (healing, docs parity, eject, perf, type check, CodeQL, Snyk)
- `security-scan.yml` — CodeQL + Snyk
- `behavioral-diff.yml` — behavioral continuity on every PR
- `docs-parity.yml` — CLI docs parity verification
- `publish.yml` — release packaging

### Design Invariants (Codified)

These are non-negotiable and tested in CI:

| Invariant | Rule |
|-----------|------|
| **D7 — no auto-edit** | Validate and healing produce reports/suggestions only; test files are never modified by automation |
| **Anti-lock-in** | `eject` yields standalone Playwright with zero CHERENKOV imports |
| **Suggest-only healing** | Healing never auto-commits or auto-applies |
| **Spec-derived oracle** | Expected status from OpenAPI spec, not hardcoded |
| **Model-agnostic** | Agents emit `ReasoningRequest{capability_tier}`; no model name hardcoded |

---

## [foundation-v0] — Foundation (Pre-release)

The model-agnostic Reality Engine foundation. Built and smoke-tested before the validation gate.

### Added

- **L0 Substrate Router** (`substrate/`, `ai/`) — model-agnostic routing, cost/latency accounting *(Epoch 1)*
- **L1 Truth Model** (`core/truth_model.py`, `truth/sources/`) — OpenAPI, traffic, and DB schema sources *(Epoch 2)*
- **L2 Divergence Engine** (`divergence/`) — D1–D5 hypotheses, independent reproduction, adversarial self-play *(Epoch 3)*
- **L3 Artifacts** (`truth/emitters/`, `execution/`) — Playwright emitter, spec patcher, eject, validate *(Epoch 3)*
- **L4 Continuity** (`continuity/`, behavioral-diff Action) — PR diff tracking *(Epoch 4)*
- **Self-healing** (`healing/`) — suggest-only failure diagnosis
- **Federation scaffold** (`federation/`) — cross-check protocol *(Epoch 6)*
- **Track A generator** (`stages/`) — full ingest → plan → generate → review → validate pipeline

### Invariants Proven (Pre-validation)

- Spec-derived expected status: caught real `422 vs 400` conformance bug
- Suggest-only healing: `D7` holds in CI
- Eject runs standalone: zero CHERENKOV imports in ejected output
- Model never hardcoded: routed by capability tier

---

[Unreleased]: https://github.com/moaidmoatasem/cherenkov-qa/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/moaidmoatasem/cherenkov-qa/compare/foundation-v0...v1.0.0
[foundation-v0]: https://github.com/moaidmoatasem/cherenkov-qa/releases/tag/foundation-v0
