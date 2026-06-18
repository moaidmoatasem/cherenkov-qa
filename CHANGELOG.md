# Changelog

## v1.1.0 — 2026-06-18

### Refactors
- Route split: `api.py` reduced 1577→47 lines; 10 route modules under `cherenkov/web/routes/`
- Legacy CLI deleted: 1148-line `legacy_cli.py` removed; report fns extracted to `legacy_reports.py`
- Codebase cleanup: 15 stale `track-b-c-deferred/` references removed across configs and scripts
- Fabricated "v3.1 + delta" spec references purged from source code

### Fixes
- Self-test tsc failure: `/self-test` → `/health` (wasn't in OpenAPI spec)
- Ruff F541: extraneous f-prefix removed from handlers.py
- Ruff F841/F401: unused variables/imports cleaned across benchmarks, scripts, tools
- E741: ambiguous variable `l` renamed in seed_github.py

### Gate G0
- E0.1: Real-divergence proof complete — 3/3 APIs (Petstore 4, HTTPBin 1, GitHub 1)
- E0.4: Differentiation sentence documented in NORTH_STAR.md §8

### Infrastructure
- Phase 3 Desktop unblocked: `libwebkit2gtk-4.1-dev` verified, `cargo check` passes
- Phase 5-6 Mobile unblocked: ADB at `~/.local/bin/adb`, Maestro 2.6.1 installed
- E2E golden path smoke test: 27/27 checks pass
- Pipeline E2E with real LLM: 6/6 scenarios, qwen2.5-coder:7b, 9537 tokens

### Docs
- `docs/phase9-kickoff.md`: Market launch checklist (landing page, npm publish, 4 gaps)
- `docs/healing/2026-06-18_route-split-test-patches.md`: D7-compliant healing report
- STATUS.md, HANDOVER.md: Updated for merged state, unblocked phases

## v1.0.0 — 2026-06-11

### Features
- AI-powered OpenAPI conformance test generation (qwen2.5-coder:7b via Ollama)
- 6-gate review system for generated tests
- `cherenkov validate` — run conformance tests against live API
- `cherenkov eject` — export standalone Playwright tests (zero lock-in)
- `cherenkov heal` — auto-fix failing tests
- `cherenkov doctor` — system health check
- MCP server for Claude Desktop / Cursor integration
- HTML and SARIF report formats
- GitHub Actions composite action
- Kubernetes operator
- Tauri desktop app
- GraphQL schema support — introspection to typed test generation
- gRPC / Protobuf support — proto to typed gRPC test generation
- OpenTelemetry export — conformance spans for Datadog/Grafana/Jaeger
- Backstage plugin — conformance status on service catalog pages
- MCP mesh registry — dynamic server discovery and tool routing
- Spec Guardian daemon — continuous conformance monitoring
- AsyncAPI Pub/Sub verification — Kafka/RabbitMQ schema validation
- Slack & Teams ChatOps — proactive divergence alerts and slash commands
- Buf Schema Registry (BSR) sync — auto-pull latest Protobuf schemas
