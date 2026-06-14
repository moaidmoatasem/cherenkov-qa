CHERENKOV is an open-source, AI-powered API conformance testing tool that reads your OpenAPI spec and generates Playwright tests automatically.

**The problem:** API specs drift from implementations constantly. Manual test suites can't keep up with hundreds of endpoints changing every sprint. Teams discover spec violations in production, not CI.

**How CHERENKOV solves it:**
- Point it at your OpenAPI 3.x spec and your live API
- It generates 200+ conformance tests per endpoint in seconds
- Tests cover positive paths, edge cases, null fields, missing required fields, type mismatches, auth scenarios, and pagination
- Results include a tightness score showing how well your API matches its spec
- Generated tests are fully ejectable — vanilla Playwright, no lock-in

**Why it's different:**
- Uses local LLMs (qwen2.5-coder via Ollama) — runs offline, no API costs
- MCP server for Claude Desktop / Cursor integration — test from your AI assistant
- 6-gate review system ensures quality before tests hit CI
- GraphQL and gRPC support in addition to OpenAPI
- OpenTelemetry export for observability pipelines
- Backstage plugin for service catalog integration

**Stack:** Python, Playwright, Ollama, Jinja2 templates, MCP protocol, OpenTelemetry. 100% open source (MIT).
