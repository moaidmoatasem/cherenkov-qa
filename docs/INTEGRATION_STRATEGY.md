# CHERENKOV-QA: Integration Strategy & Ecosystem Roadmap

> Every integration is a distribution channel. Every distribution channel is a growth flywheel.

---

## Honest Current State

Before strategy, truth:

| Integration | Code State | Reality |
|-------------|-----------|---------|
| **MCP Server** | ✅ Built | 14 tools, 3 resources, full JSON-RPC 2.0, policy engine |
| **Desktop App (Tauri)** | ⚠️ Shell | Browser wrapper + sidecar launcher. No native UI, no IPC. 30% done. |
| **VS Code Extension** | 🔧 Built | `vscode/` scaffold — commands, sidebar tree, CodeLens, status bar, ConformancePanel webview. Needs `npm install` + `vsce package` to publish. |
| **Slack** | ❌ Zero | `notification_endpoint` declared in config, never called |
| **Teams** | ❌ Zero | No code |
| **Jira** | ⚠️ Stub | Local Markdown export only. MCP tool returns "not implemented". |
| **Xray / Zephyr** | ❌ Zero | No code |
| **GitHub Actions** | ❌ Zero | No marketplace action |
| **Chat Agent** | ✅ Built | Ollama-only, 4 tools, SSE streaming, SQLite memory |
| **RAG / Knowledge** | ✅ Built | Dual-index (schema + mobile), cosine similarity, disk cache |
| **MENA Compliance** | ⚠️ Partial | SAMA/FinCSF scanner. MCP tool stubs. No SOC2/GDPR. |
| **Webhooks (outbound)** | ⚠️ Arch only | Internal callback pattern exists. No actual egress. |

---

## The Integration Stack — Tiered by Strategic Value

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 0: WHERE DEVELOPERS LIVE (Highest Leverage)                   │
│  VS Code · GitHub · CI/CD · Terminal                                │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 1: WHERE TEAMS WORK (Collaboration & Workflow)                │
│  Slack · Teams · Jira · Linear · GitHub Issues                      │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 2: WHERE QUALITY LIVES (QA Ecosystem)                         │
│  Xray · Zephyr · TestRail · Allure · Playwright Report              │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 3: WHERE AI LIVES (Model & Agent Ecosystem)                   │
│  MCP · Claude · Cursor · Copilot · LangChain · OpenAI              │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 4: WHERE ENTERPRISE LIVES (Infrastructure & Compliance)       │
│  K8s · ArgoCD · Datadog · Grafana · PagerDuty · OTEL · SOC2        │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 5: WHERE THE MARKET LIVES (Ecosystem Expansion)               │
│  GraphQL · gRPC · AsyncAPI · Buf · Postman · Stoplight              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## TIER 0 — Where Developers Live

### 1. VS Code Extension ❌ → Must Build Now

**Why it's the #1 priority:** VS Code has 73M+ monthly active users. Every backend developer opens their OpenAPI spec in VS Code. A right-click → "Generate conformance tests" is the highest-conversion funnel imaginable. It's also a **daily active use** driver — not just a one-off CLI command.

**What to build:**

```
vscode-cherenkov/
├── src/
│   ├── extension.ts           # Entry point
│   ├── commands/
│   │   ├── generate.ts        # "Generate tests from this spec"
│   │   ├── validate.ts        # "Run conformance check"
│   │   ├── eject.ts           # "Eject to vanilla Playwright"
│   │   └── doctor.ts          # "Check LLM health"
│   ├── providers/
│   │   ├── CodeLensProvider.ts  # Inline "Generate" / "Validate" / "N drift violations"
│   │   ├── DiagnosticsProvider.ts  # Red squiggles on drifting endpoints
│   │   ├── TreeDataProvider.ts  # Test explorer sidebar
│   │   └── HoverProvider.ts    # Hover on path → show last verdict
│   ├── views/
│   │   ├── ConformancePanel.ts  # WebView: conformance report
│   │   └── HealingPanel.ts     # WebView: tightening suggestions
│   └── api/
│       └── CherenkovClient.ts  # Calls local CLI / MCP server
├── package.json
└── .vscodeignore
```

**The killer feature:** When a `.yaml`/`.json` file is open and recognized as OpenAPI:
- **Gutter icons**: green dot (passing endpoint), red dot (drift detected), grey dot (untested)
- **Code lens above each path**: `▶ 4 tests passing  ⚠ 1 conformance violation  → Heal`
- **Problems panel**: Conformance violations appear as warnings with file/line attribution
- **Quick Fix**: `Ctrl+.` on a violation → "Add suggested value assertion"

**How it connects:** Via `cherenkov doctor` socket or direct MCP protocol (already built). Extension spawns CLI as a language server.

**Effort:** 3-4 weeks, TypeScript only.

---

### 2. GitHub Actions Marketplace Action ❌ → Ship in Week 1

**The single fastest path to viral adoption.** Every repo that adds:
```yaml
- uses: cherenkov-qa/action@v1
  with:
    spec: ./api/openapi.yaml
    target: http://localhost:8080
```
...is a public signal to every developer who forks or stars that repo.

**What to build:**

```yaml
# action.yml
name: CHERENKOV Conformance Check
description: Generate and run API conformance tests from your OpenAPI spec
inputs:
  spec:
    description: Path to OpenAPI spec
    required: true
  target:
    description: API server URL to test against
    required: true
  fail-on-drift:
    description: Exit code 1 if conformance violations found
    default: 'true'
  llm-provider:
    description: LLM provider (ollama|openai)
    default: 'openai'  # CI default; ollama for self-hosted
outputs:
  violations:
    description: Number of conformance violations found
  report-path:
    description: Path to generated conformance report
  sarif-path:
    description: Path to SARIF output (for GitHub Security tab)
runs:
  using: docker
  image: ghcr.io/cherenkov-qa/cli:latest
```

**SARIF output** is the multiplier: violations show up in the GitHub Security tab as code scanning alerts. Every PR gets conformance annotations directly in the diff.

**Effort:** 3 days. Already have Docker image.

---

### 3. Desktop App — What It Should Really Be

**Current state:** Tauri wrapper that opens a browser window. A shell.

**The real opportunity:** The desktop app is the onboarding funnel for non-technical users and teams. Think: what if a QA lead could drag-drop an OpenAPI spec, click "Run", and see a conformance report — no terminal, no Docker, no Ollama setup?

**What the desktop app must become:**

```
CHERENKOV Desktop = Auto-Setup Wizard + Native Performance + System Tray Agent

Phase 1 — Auto-Setup Wizard (eliminates the #1 adoption blocker):
  ✓ Detects: Ollama installed? Docker? Node? Python?
  ✓ One-click install of missing dependencies
  ✓ Downloads qwen2.5-coder:7b silently in background
  ✓ First run: drag OpenAPI spec → instant demo

Phase 2 — Native File Watcher (killer feature):
  ✓ Watch a spec file directory
  ✓ On file save → auto-regenerate affected tests
  ✓ Native macOS/Windows notification: "3 conformance violations found"
  ✓ System tray icon: green (passing) / red (drift)

Phase 3 — Offline-First Packaged Binary:
  ✓ Single .dmg / .exe / .AppImage with everything bundled
  ✓ Embedded Ollama binary (or download on first run)
  ✓ No Docker required
  ✓ Works on airplane
```

**To unblock it NOW:** The `cargo` dependency blocker is solvable. Use `tauri-action` in CI. For local dev, the CLI + web UI is already functional. Ship Phase 1 as a priority — the auto-setup wizard is the unlock.

**Effort to unblock + ship Phase 1:** 2 weeks after `cargo` is available.

---

## TIER 1 — Where Teams Work

### 4. Slack Integration ❌ → High ROI, Medium Effort

**The use case:** Your CI/CD runs CHERENKOV on every deploy. When drift is detected, a Slack message appears in `#api-quality` before the developer even notices the pipeline failed.

```
🔴 CHERENKOV: Conformance drift detected
   Service: payment-service  |  Spec: v2.3.1
   ┌─────────────────────────────────────────┐
   │ POST /payments/charge                   │
   │ Expected: 422 (spec)  Got: 400 (server) │
   │ Affected tests: 3                       │
   └─────────────────────────────────────────┘
   [View Report]  [Open in VS Code]  [Create Jira Ticket]
```

**Architecture:** The `openclaw/adapter.py` `notification_endpoint` config is already declared. This needs 3 things:
1. `SlackNotifier` adapter in `cherenkov/adapters/notifiers/slack.py`
2. Wire it into the `OpenClawAdapter.notification_endpoint`
3. Block action buttons (approve/reject HITL directly from Slack via slash commands)

**The Slack block kit format:**
```python
class SlackNotifier:
    def __init__(self, webhook_url: str): ...
    async def notify_drift(self, violation: ConformanceViolation) -> None: ...
    async def notify_hitl(self, item: HITLItem) -> None: ...  # approve/reject from Slack
    async def notify_healed(self, suggestion: HealingSuggestion) -> None: ...
```

**Effort:** 1 week (Slack SDK is trivial; the hard part is wiring to existing events).

---

### 5. Microsoft Teams Integration ❌ → Enterprise Gate-Opener

Teams is where enterprise engineering orgs live. A Teams connector is the difference between "interesting CLI tool" and "approved enterprise software."

Same architecture as Slack but using Teams Adaptive Cards (richer than Slack blocks). The conformance violation card becomes actionable: engineers approve/reject HITL directly from Teams.

**Effort:** 1 week (parallel with Slack; share the notification interface).

---

### 6. Jira Integration ⚠️ → Complete the Stub

**Current state:** `jira_exporter.py` writes local Markdown files. MCP tool returns "not implemented."

**What needs to change:**

```python
class JiraClient:
    """Real Jira API v3 integration."""

    async def create_issue(
        self,
        project_key: str,
        violation: ConformanceViolation,
        *,
        assignee: str | None = None,
        labels: list[str] = ["api-conformance", "cherenkov"],
        priority: str = "High",
    ) -> JiraIssue: ...

    async def link_test_run(
        self,
        issue_key: str,
        verdict_id: str,
    ) -> None: ...

    async def transition_issue(
        self,
        issue_key: str,
        transition: Literal["In Progress", "Done", "Won't Fix"],
    ) -> None: ...
```

**The feedback loop:** Jira issue created → developer fixes → fix pushed → CHERENKOV re-runs → violation resolved → Jira issue auto-closed. That closed loop is the enterprise upsell.

**Effort:** 1 week to complete the stub + wire MCP tool.

---

### 7. Linear Integration ❌ → Developer-Native Jira Alternative

Linear is Jira for engineers who hate Jira. Massive adoption at Series A-C startups. Same architecture as Jira but GraphQL API (simpler). Creates issues with:
- Epic: API Conformance
- Labels: `conformance-drift`, affected service name
- Auto-assigned to service owner (pulled from OpenAPI `info.x-owner` field)

**Effort:** 3 days (Linear GraphQL API is clean).

---

### 8. GitHub Issues Integration ❌ → Zero-Config Default

For open source projects and teams already on GitHub: auto-create issues from conformance failures. Zero setup (already has GitHub token in CI). Every violation becomes a tracked issue with spec diff attached.

**Effort:** 2 days (GitHub REST API).

---

## TIER 2 — Where Quality Lives

### 9. Xray (Jira Test Management) ❌ → Enterprise QA Unlock

Xray is the #1 test management tool for enterprise Jira shops. 8,000+ companies use it. Importing CHERENKOV test results into Xray means:
- QA leads see API conformance coverage on their test dashboards
- Compliance auditors get API test evidence without manual export
- Test execution history tracks conformance trend over time

**What to build:**
```python
class XrayExporter:
    """Exports CHERENKOV verdicts as Xray test execution results."""

    async def import_execution(
        self,
        verdicts: list[Verdict],
        test_plan_key: str,
        environment: str,
    ) -> XrayExecutionResult: ...

    # Xray JSON format: https://docs.getxray.app/display/XRAY/Import+Execution+Results
```

**Xray Cloud REST API** accepts JUnit XML (which CHERENKOV should already output from Phase 10 CI work). The incremental cost of Xray integration once JUnit output exists: 2 days.

---

### 10. Zephyr Scale (Jira) ❌ → #2 Enterprise QA Tool

Zephyr Scale is SmartBear's test management solution. 15,000+ companies. Same play as Xray but different API format. With both Xray and Zephyr covered, CHERENKOV integrates with 80%+ of enterprise QA tooling.

**Effort:** 3 days (similar to Xray but Zephyr-specific API format).

---

### 11. TestRail ❌ → Traditional QA Teams

TestRail is the legacy standard, especially in regulated industries. Older enterprise teams live here. REST API is well-documented.

**Effort:** 3 days.

---

### 12. Allure Report ❌ → Developer-Friendly Test Reports

Allure is open source, beautiful, and beloved by QA engineers. CHERENKOV conformance results as an Allure report = instant credibility with QA community.

```python
class AllureEmitter:
    def emit_verdict(self, verdict: Verdict) -> None:
        """Writes Allure JSON result file to allure-results/."""
```

**Effort:** 2 days (Allure result format is simple JSON).

---

## TIER 3 — Where AI Lives

### 13. MCP Server — Expand What's Already Built ✅ → 14 Tools → 40+ Tools

**This is already the most important integration and it's BUILT.** But 4 MCP tools return "not yet implemented." Complete them first:

| Tool | Current | Fix |
|------|---------|-----|
| `run_k6_perf` | stub | Wire to k6 executor |
| `export_jira_ticket` | stub | Wire to real Jira client (see above) |
| `scan_mena_compliance` | stub | Wire to `mena_scanner.py` |

**Then expand to 40+ tools:**

```python
# New MCP tools to add:

# Developer workflow
"generate_tests"           # trigger full generate pipeline
"run_validation"           # run validate against URL
"get_coverage_map"         # which endpoints are tested
"suggest_next_test"        # GraphRAG-powered test suggestions

# Integrations
"create_jira_issue"        # real Jira API
"post_slack_alert"         # Slack notification
"export_allure_results"    # Allure format export
"sync_xray_execution"      # Xray test execution import

# Knowledge
"search_idioms"            # semantic search in knowledge mesh
"get_verdict_history"      # endpoint-level test history
"find_similar_incidents"   # GraphRAG similarity search
"get_spec_diff"            # what changed since last run

# Agent-native
"plan_test_scenarios"      # plan without generating (dry run)
"explain_violation"        # human-readable violation explanation
"suggest_spec_fix"         # propose OpenAPI spec correction
"run_self_play"            # witness/skeptic divergence analysis
```

**Why MCP is the biggest multiplier:**
- Claude Desktop, Cursor, Windsurf, and every MCP-compatible AI assistant can now call CHERENKOV tools directly
- An AI agent can: read spec → generate tests → validate → explain violations → create Jira ticket — all in one conversation
- **This makes CHERENKOV the testing backbone of every AI coding assistant**

---

### 14. Claude / Anthropic API Integration ❌ → Premium Tier LLM

**Current gap:** Chat agent is Ollama-only. No Claude, no GPT-4o.

**What to add:**
```python
# cherenkov/substrate/providers/anthropic.py
class AnthropicProvider(LLMProvider):
    """Claude Sonnet/Opus via Anthropic API — highest quality test generation."""

    async def complete(self, request: ReasoningRequest) -> ReasoningResult:
        # Uses claude-sonnet-4-6 for test generation
        # Uses claude-haiku-4-5 for fast healing suggestions
        # Extended thinking for complex conformance analysis
```

**Why it matters:** Claude is significantly better at TypeScript test generation than `qwen2.5-coder:7b`. Offering Claude as a premium provider (BYOK) is the enterprise upsell. "Pay for better tests" is an easy value proposition.

**Effort:** 2 days (Anthropic SDK is straightforward).

---

### 15. Cursor / Windsurf / Copilot Integration → via MCP (Zero extra work)

The MCP server is already built. Cursor and Windsurf both support MCP natively. This means:
- **Cursor users** can call `cherenkov.generate_tests()` directly from their AI chat panel
- **Windsurf users** get CHERENKOV as a built-in tool
- **GitHub Copilot** (via MCP bridge) can suggest test generation when it sees an OpenAPI file

**Action required:** Publish the MCP server config to the official MCP registry. 1-day effort. Zero code changes.

---

### 16. LangChain / LlamaIndex Tool ❌ → Agent Ecosystem

Package CHERENKOV as a LangChain tool and LlamaIndex query engine. This means any team building an AI agent can add `from cherenkov import CherenkovTool` and get:
- `CherenkovTool.generate_tests(spec_path)`
- `CherenkovTool.validate(target_url)`
- `CherenkovTool.explain_violation(violation_id)`

**Why:** LangChain has 90K+ GitHub stars. Being a first-class LangChain tool means discovery by every AI engineer building agents.

**Effort:** 3 days.

---

## TIER 4 — Where Enterprise Lives

### 17. OpenTelemetry Export ❌ → Observability Standard

Every enterprise already has Datadog, Jaeger, or Grafana. OTEL spans from CHERENKOV test runs integrate natively:

```python
# Each test run emits OTEL spans:
# cherenkov.validate (root span)
#   cherenkov.generate (child: test generation)
#   cherenkov.review.gate (child: 6-gate review)
#   cherenkov.execute (child: Playwright run)
#   cherenkov.conformance (child: violation check)
```

Enterprises can correlate API conformance runs with deploy events, error rates, and SLO burns. **This is how CHERENKOV becomes part of the observability stack.**

**Effort:** 1 week (OTEL Python SDK is well-documented).

---

### 18. PagerDuty / OpsGenie Integration ❌ → On-Call Loop

When a production deploy triggers a conformance regression on a critical endpoint, page the on-call engineer immediately. Same notification adapter pattern as Slack.

```
CHERENKOV Alert → PagerDuty incident → On-call notified (5 min)
vs.
Conformance drift → production incident → postmortem (48 hours)
```

**Effort:** 2 days.

---

### 19. ArgoCD / FluxCD ApplicationSet ❌ → GitOps Native

The K8s operator (`ConformanceCheck` CRD) is in progress. The next step is an ArgoCD ApplicationSet that auto-creates a `ConformanceCheck` resource for every service deploying to the cluster.

```yaml
# ArgoCD ApplicationSet: auto-conformance for all services
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
spec:
  generators:
  - list:
      elements:
      - service: payment-api
        spec: services/payment-api/openapi.yaml
  template:
    spec:
      source:
        helm:
          values: |
            conformanceCheck:
              spec: {{ spec }}
              target: http://{{ service }}.prod.svc.cluster.local
```

This means: **every service that deploys gets conformance tests automatically, zero manual configuration.**

**Effort:** 1 week.

---

### 20. Backstage Plugin ❌ → Enterprise Developer Portal

78% of Fortune 500 engineering orgs use Backstage or plan to. A Backstage plugin means:
- Every service's catalog page shows its API conformance status
- Engineers see "Last checked: 2 hours ago | 0 violations" on the service card
- Drill-down to full conformance report from the catalog

**Architecture:**
```
cherenkov-backstage-plugin/
├── src/
│   ├── plugin.ts              # Plugin entry
│   ├── components/
│   │   ├── ConformanceBadge.tsx   # Status badge for catalog cards
│   │   ├── ConformanceCard.tsx    # Full card for entity page
│   │   └── ViolationTable.tsx    # Detailed violation list
│   └── api/
│       └── CherenkovClient.ts    # Calls CHERENKOV backend API
```

**Effort:** 2-3 weeks. High enterprise conversion value.

---

### 21. Grafana Dashboard ❌ → Conformance Observability

Pre-built Grafana dashboards for:
- Conformance coverage over time (% endpoints tested)
- Violation trend (are we getting better or worse?)
- Test generation latency (LLM performance)
- Endpoint health heatmap

Published as a Grafana dashboard JSON to grafana.com/dashboards. **Zero code in CHERENKOV** — just a JSON export. Grafana users discover CHERENKOV via the dashboard marketplace.

**Effort:** 2 days.

---

## TIER 5 — Where the Market Lives

### 22. GraphQL Schema Support ❌ → 3x Addressable Market

**This is the biggest market expansion move.** GraphQL powers: GitHub, Shopify, Twitter/X, Stripe, every modern frontend. Adding GraphQL support triples the addressable market.

**Pipeline:**
```
GraphQL Introspection / .graphql schema
  → Parse: operations, types, resolvers
  → Plan: query scenarios (happy path, nullability, pagination, error states)
  → Generate: Apollo/urql typed test code
  → Validate: response validates against schema
  → Report: resolver-level conformance
```

**Effort:** 3-4 weeks. New `GraphQLSourceAdapter` + updated LLM prompt for GQL test patterns.

---

### 23. gRPC / Protobuf Support ❌ → Backend Engineering Niche

gRPC is standard in microservices. Every company running K8s microservices has gRPC services. No tool does: `.proto` → LLM → typed gRPC tests.

**Pipeline:** `.proto` → `protoc` → descriptor → CHERENKOV → gRPC Playwright tests.

**Effort:** 3 weeks. Requires `protoc` integration + gRPC-specific test templates.

---

### 24. AsyncAPI / WebSocket / Kafka ❌ → Event-Driven APIs

The next frontier. REST is 60% of APIs. Events are the other 40% and completely untested. AsyncAPI spec → CHERENKOV → event-driven conformance tests.

**Examples:**
- Kafka topic schema validation
- WebSocket message conformance
- Server-Sent Events (CHERENKOV already uses SSE internally)

**Effort:** 4-6 weeks. Long-term strategic play.

---

### 25. Postman Collection Import ❌ → Conversion Funnel

Postman has 25M users. Importing a Postman collection as a source adapter means: every Postman user can migrate their manual API tests to CHERENKOV-generated conformance tests.

```python
class PostmanSourceAdapter(SourceAdapter):
    def ingest(self, collection_path: str) -> list[EndpointSlice]:
        """Converts Postman Collection v2.1 → EndpointSlice[]"""
```

**This is a migration path from the competitor's format. Massive conversion funnel.**

**Effort:** 1 week.

---

## Integration Prioritization Matrix

```
                    HIGH IMPACT
                         │
   Xray/Zephyr           │    VS Code Extension ◄── #1
   Jira (complete)       │    GitHub Actions ◄── #2
   Teams                 │    GraphQL Support
   Backstage             │    MCP (complete stubs) ◄── #3
   OTEL                  │    Slack ◄── #4
                         │
LOW EFFORT ──────────────┼──────────────── HIGH EFFORT
                         │
   Allure                │    Desktop Auto-Setup Wizard
   GitHub Issues         │    gRPC / Protobuf
   Grafana Dashboard     │    Backstage Plugin
   PagerDuty             │    AsyncAPI
   Postman Import        │    LangChain Tool
                         │
                    LOW IMPACT
```

---

## The Integration Delivery Plan

### Sprint 1 (Weeks 1-2): Foundation
- [ ] Complete 3 MCP stub tools (`run_k6_perf`, `export_jira_ticket`, `scan_mena_compliance`)
- [ ] GitHub Actions marketplace action (SARIF output included)
- [ ] JUnit XML output format (unblocks Xray/Zephyr/TestRail at zero extra cost)
- [ ] `SlackNotifier` adapter wired to `OpenClawAdapter`
- [ ] Wire `notification_endpoint` for outbound webhooks (generic HTTP POST)

### Sprint 2 (Weeks 3-6): Developer Tools
- [ ] VS Code extension beta (generate + validate commands + gutter icons)
- [ ] Jira API client (complete the stub)
- [ ] Linear integration
- [ ] Allure report emitter
- [ ] Pre-commit hook

### Sprint 3 (Weeks 7-10): Enterprise QA
- [ ] Xray Cloud import
- [ ] Zephyr Scale import
- [ ] TestRail import
- [ ] Teams Adaptive Card integration
- [ ] GitHub Issues auto-create

### Sprint 4 (Weeks 11-14): AI Ecosystem
- [ ] Anthropic/Claude provider in substrate router
- [ ] OpenAI provider (for BYOK enterprise tier)
- [ ] LangChain tool package
- [ ] Publish MCP server to official registry
- [ ] Desktop auto-setup wizard

### Sprint 5 (Weeks 15-20): Observability & Platform
- [ ] OpenTelemetry export
- [ ] ArgoCD ApplicationSet template
- [ ] Backstage plugin
- [ ] Grafana dashboard publish
- [ ] PagerDuty / OpsGenie adapter
- [ ] Postman collection import

### Sprint 6 (Weeks 20-28): Market Expansion
- [ ] GraphQL schema support
- [ ] gRPC / Protobuf support
- [ ] AsyncAPI / WebSocket support
- [ ] Buf schema registry integration

---

## The Compounding Effect

Each integration is not just a feature — it's a distribution channel:

```
VS Code Extension
  → 73M VS Code users discover CHERENKOV
  → They open OpenAPI specs daily
  → They click "Generate Tests" → they see the value
  → They add GitHub Actions action to their CI
  → CI runs → violations appear in Slack
  → Slack alert → Jira ticket auto-created
  → QA lead sees Jira ticket → asks "what tool is this?"
  → Starts enterprise trial
  → Buys K8s operator license
```

Every integration shortens this funnel. The goal is not to support integrations — **the goal is to make CHERENKOV invisible by making it omnipresent.**

When a developer can't tell where their IDE ends and CHERENKOV begins, when a QA lead's Jira tickets are auto-populated, when an on-call engineer gets paged before the customer complains — that's when CHERENKOV has won.

---

## The Desktop App — Honest Answer

**Is it ready?** No. It's a browser wrapper.

**Should it be a priority?** Yes — but for the right reason. The desktop app is not about "having a desktop app." It is about **eliminating the #1 adoption barrier**: requiring users to install Ollama, Docker, Python, and Node before seeing any value.

The desktop app's job is to be a **self-contained onboarding machine**:
1. User downloads `.dmg` / `.exe` / `.AppImage`
2. Opens it — sees a setup wizard
3. Wizard installs Ollama silently
4. Wizard downloads `qwen2.5-coder:7b` (progress bar)
5. User drags in their OpenAPI spec
6. 60 seconds later: sees their first conformance report

**That flow — no terminal, no Docker, no reading docs — is worth more than 6 months of documentation.**

The technical path: unblock `cargo` via `tauri-action` in CI, build the setup wizard as a Tauri native window (not a web view), bundle the Python CLI as a sidecar via PyInstaller.

**This should be Phase 9 after the GitHub Actions action ships.** Order matters: engineers need the CLI to work first, then the desktop app makes it accessible to non-engineers.

---

*Document authored: 2026-06-09*
*Part of: PRODUCT_STRATEGY_ROADMAP.md series*
