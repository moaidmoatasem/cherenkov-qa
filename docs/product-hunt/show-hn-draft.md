# Show HN: CHERENKOV – Open-source API conformance testing powered by local LLMs

CHERENKOV reads your OpenAPI spec and generates Playwright conformance tests automatically using local LLMs (qwen2.5-coder via Ollama). Point it at your spec and live API, and it catches drift before it hits production.

Features:
- Generates 200+ tests per endpoint covering happy path, edge cases, auth, pagination
- OpenAPI, GraphQL, and gRPC support
- Tests are fully ejectable — vanilla Playwright, no lock-in
- Built-in MCP server for Claude Desktop / Cursor integration
- OpenTelemetry export for Datadog, Grafana, Jaeger
- Backstage plugin for service catalog dashboards
- Runs 100% offline — no API costs, no data leaving your machine

Stack: Python, Ollama, Playwright, MCP protocol, OpenTelemetry. MIT licensed.

https://github.com/moaidmoatasem/cherenkov-qa
