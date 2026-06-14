# Changelog

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
