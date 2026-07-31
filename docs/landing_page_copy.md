# CHERENKOV-QA: The AI-Native API Conformance Engine

**Catch API drift before production.**
CHERENKOV is the first testing tool that reads your OpenAPI spec, generates typed Playwright tests, executes them against your real server, and tells you exactly where your implementation diverges from your spec.

[ **Get Started (npx cherenkov init)** ] [ **View on GitHub** ]

---

## 3 Pains We Solve

### 1. Spec Drift is Invisible
**The Problem:** Your spec says `422 Unprocessable Entity`. Your server returns `400 Bad Request`. Clients break, but your CI is green.
**The Fix:** CHERENKOV validates your live server against the exact constraints of your OpenAPI spec. Every run is a conformance audit.

### 2. Writing API Tests is Tedious
**The Problem:** You have 50 endpoints. Writing happy-path, edge-case, and security tests for all of them takes months.
**The Fix:** Give CHERENKOV your spec. Our local LLM (qwen2.5-coder) generates typed, executable Playwright tests in seconds. No hallucination—the LLM writes the structure, your spec provides the truth.

### 3. Tool Lock-in is Real
**The Problem:** Adopting a new testing platform means migrating to their proprietary format. If you leave, you lose your tests.
**The Fix:** `cherenkov eject`. One command strips out all CHERENKOV dependencies, leaving you with vanilla Playwright tests and standard `openapi-fetch` clients. Zero lock-in.

---

## How It Works

1. **Ingest:** Feed CHERENKOV your OpenAPI (REST), GraphQL, or gRPC spec.
2. **Generate:** The LLM generates typed test scenarios.
3. **Review:** Tests pass through a rigorous 6-gate review (syntax, AST, compilation, Prism mock validation).
4. **Execute:** Tests run against your live staging or dev server.
5. **Report:** You get a detailed conformance report highlighting exactly where the server violated the spec.
6. **Heal (Optional):** CHERENKOV suggests targeted value assertions to tighten your tests without auto-editing your code.

---

## The AI Ecosystem Built-in

- **Local First:** Runs `qwen2.5-coder:7b` locally via Ollama. Zero data leaves your machine. Privacy by default.
- **MCP Server:** Use Cursor, Windsurf, or Claude Desktop? CHERENKOV is a native MCP server. Just ask your assistant to "generate tests for the payment API."
- **Knowledge Mesh:** A GraphRAG second brain remembers your team's testing idioms and past incidents to write better tests over time.

---

## Ready for the Enterprise

- **K8s Native:** Deploy the `ConformanceCheck` CRD and let the Go operator test every service in your cluster automatically.
- **CI/CD Ready:** Use our GitHub Actions marketplace action to block PRs that introduce spec drift.
- **Integrations:** Jira, Slack, Teams, OpenTelemetry, Xray, and more.

[ **Start Testing Now - npx cherenkov init** ]
