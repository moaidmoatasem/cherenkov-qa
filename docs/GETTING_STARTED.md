# CHERENKOV Getting Started Guide

Welcome to CHERENKOV! This usage-first guide will walk you from initial installation to running your first passing test suite and ejecting standalone Playwright tests in under 5 minutes.

---

## 🛠️ Prerequisites & Installation

Ensure you have the following installed in your environment:
- Node.js (v18 or higher)
- Python (v3.10 or higher)

### 1. Setup WSL/Local Environment
Clone this repository and run standard package installations inside the workspace:

```bash
# Set up Python Virtual Environment and install packages
python3 -m venv .venv
source .venv/bin/activate
pip install -r target/requirements.txt

# Set up Node/Playwright in the stub folder
cd stub
npm install
npx playwright install
cd ..
```

---

## 🚀 CLI Commands & Usage

CHERENKOV exposes all operations natively through a unified CLI tool: `./bin/cherenkov`.

### Display CLI Command Help
To view all supported commands and options:
```bash
./bin/cherenkov --help
```

---

### Command 1: `validate`
Executes your Playwright test suite against a real server, programmatically parses trace files, compares request vs response payloads, and suggests value assertions.

#### Command Help:
```bash
./bin/cherenkov validate --help
```

#### Standard Usage:
1. Ensure your Target API is healthy and online:
   ```bash
   cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000
   ```
2. Execute validation:
   ```bash
   ./bin/cherenkov validate --target http://localhost:8000
   ```

---

### Command 2: `eject`
Copies all your generated specs and TypeScript compilation files, emits a clean `client.ts` completely stripped of trace interception metadata, and generates standard Playwright and package settings.

#### Command Help:
```bash
./bin/cherenkov eject --help
```

#### Standard Usage:
Eject the suite to a standalone folder with ZERO tool dependencies:
```bash
./bin/cherenkov eject --output ejected_suite
```
The ejected folder `ejected_suite/` is 100% clean and can be executed natively with vanilla Playwright commands:
```bash
cd ejected_suite
npm install
npx playwright test
```

---

### Command 3: `visual` (optional Track B capability layer)
Runs visual-regression checks against a rendered URL. Auto-initializes a baseline on first run; compares against it on subsequent runs. Reuses Track A contracts (`VisualSlice`, `VisualReport`) and the Track A `PlaywrightRunner` — never replaces API conformance.

#### Command Help:
```bash
./bin/cherenkov visual --help
```

#### Standard Usage:
```bash
./bin/cherenkov visual --target http://localhost:3000/checkout
```

Override the baseline-directory label:
```bash
./bin/cherenkov visual --target http://localhost:3000/checkout --baseline-dir stub/visual_baselines
```

---

### Command 4: `init` (E5-1 — zero-config project setup)
Auto-detects OpenAPI specs and generates a sensible `cherenkov.toml` with defaults that are offline, free, and deterministic.

#### Command Help:
```bash
./bin/cherenkov init --help
```

#### Standard Usage:
```bash
./bin/cherenkov init
```

Override profile and force overwrite existing config:
```bash
./bin/cherenkov init --profile ci --force
```

---

### Command 5: `doctor` (E5-3 — system health check)
Reports effective configuration, device health (GPU vs CPU), model availability, egress policy consistency, and environmental dependencies (Node, Playwright, Docker/Prism).

#### Command Help:
```bash
./bin/cherenkov doctor --help
```

#### Standard Usage:
```bash
./bin/cherenkov doctor
```

---

### Command 6: `dashboard` (E5-4 — Truth Model + divergences view)
Displays the Truth Model claim graph and any open divergences. Uses mock data when no Truth Model has been built.

#### Command Help:
```bash
./bin/cherenkov dashboard --help
```

#### Standard Usage:
```bash
./bin/cherenkov dashboard
```

---

### Command 7: `perf` (optional Track B capability layer)
Runs performance baseline checks against an API endpoint using k.  Records latency per run in a local SQLite store (`.cherenkov/perf_metrics.db`) and flags standard-deviation outlier regressions once >= 3 runs exist. If `k6` is not installed, the stage degrades to a simulated baseline tick (HITL verdict) so it still runs in any env.

#### Command Help:
```bash
./bin/cherenkov perf --help
```

#### Standard Usage:
```bash
./bin/cherenkov perf --target http://localhost:8000 --endpoint /health --method GET
```

Tune load profile:
```bash
./bin/cherenkov perf --target http://localhost:8000 --endpoint /users --method POST --vus 10 --duration 10
```

---

### Command 8: `map` (E11 — claims mapping)
Generates the static truth graph map connecting specifications with code and active traces.

#### Command Help:
```bash
./bin/cherenkov map --help
```

#### Standard Usage:
```bash
./bin/cherenkov map
```

---

### Command 9: `daemon` (background observability daemon)
Starts the background websocket server monitoring traffic and coordination logic.

#### Command Help:
```bash
./bin/cherenkov daemon --help
```

#### Standard Usage:
```bash
./bin/cherenkov daemon --port 8080
```

---

### Command 10: `explore` (autonomous exploration crawler)
Crawls targets to inspect anomalies, console/network exceptions, and visual baselines.

#### Command Help:
```bash
./bin/cherenkov explore --help
```

#### Standard Usage:
```bash
./bin/cherenkov explore --target http://localhost:3000
```

---

### Command 11: `author` (intent-driven test generator)
Enables NL-to-Playwright E2E interactive testing loops.

#### Supported Actions
The intent parser recognises these action types and renders them as Playwright code:
- `navigate` — navigate to a URL
- `click` — click a button/link by role/label
- `fill` — fill an input field
- `expect` — assert visible text or URL match
- `request` — direct HTTP request (GET/POST/PUT/DELETE/PATCH)

Any other action emits a warning in the CLI output and is skipped as a comment
in the generated test.

#### Command Help:
```bash
./bin/cherenkov author --help
```

#### Standard Usage:
```bash
./bin/cherenkov author --intent "Register new test user"
```

---

### Command 12: `hitl` (Human-In-The-Loop review queue)

When a `REVIEW` stage yields `Verdict.HITL`, the finding is persisted in a durable
SQLite queue (`.cherenkov/hitl.db`). The `hitl` command lets any reviewer inspect,
approve, or reject pending items entirely from the terminal — no dashboard required.

All subcommands accept a `--json` flag that emits a versioned **`hitl/v1` envelope**:

```json
{
  "schema_version": "hitl/v1",
  "ok": true,
  "command": "hitl.approve",
  "payload": { ... },
  "error": null
}
```

#### Command Help:
```bash
./bin/cherenkov hitl --help
./bin/cherenkov hitl list --help
./bin/cherenkov hitl approve --help
```

---

#### Subcommand: `hitl list`
List items in the queue (defaults to `pending` only).

```bash
# Show pending items (default)
./bin/cherenkov hitl list

# Show all statuses
./bin/cherenkov hitl list --all

# Filter by a specific status
./bin/cherenkov hitl list --status approved

# Machine-readable hitl/v1 JSON output
./bin/cherenkov hitl list --json
./bin/cherenkov hitl list --all --json
```

**Human output example:**
```
HITL queue — pending (1 item(s))
  id                                    status      info
  ------------------------------------  ----------  ----
  ck_abc123-...                         pending     conf=0.72  gate=gate_3_ast  POST /orders
```

**JSON envelope example (`--json`):**
```json
{
  "schema_version": "hitl/v1",
  "ok": true,
  "command": "hitl.list",
  "payload": {
    "status_filter": "pending",
    "count": 1,
    "items": [
      {
        "id": "ck_abc123-...",
        "status": "pending",
        "endpoint": "/orders",
        "method": "POST",
        "confidence": 0.72,
        "review_gate_failed": "gate_3_ast",
        "created_at": "2026-06-04T08:00:00+00:00"
      }
    ]
  },
  "error": null
}
```

---

#### Subcommand: `hitl show <id>`
Display full details of a single queue item.

```bash
# Human-readable detail view
./bin/cherenkov hitl show ck_abc123-...

# JSON envelope
./bin/cherenkov hitl show ck_abc123-... --json
```

**Human output example:**
```
HITL item: ck_abc123-...
  id              : ck_abc123-...
  status          : pending
  endpoint        : POST /orders
  mutation_id     : mut_42
  mutation_label  : Omit required field: email
  confidence      : 0.72
  review_gate_failed: gate_3_ast
  run_id          : run_20260604_001
  created_at      : 2026-06-04T08:00:00+00:00
  approved_by     : None
```

---

#### Subcommand: `hitl approve <id>`
Approve a **pending** item. Atomic: only one approver can win on a race; the loser
receives a truthful `conflict` error (see error codes below).

```bash
# Approve (actor defaults to $USER env var)
./bin/cherenkov hitl approve ck_abc123-...

# Approve with explicit actor identity
./bin/cherenkov hitl approve ck_abc123-... --actor @alice

# Approve and emit JSON envelope
./bin/cherenkov hitl approve ck_abc123-... --actor @alice --json
```

**JSON success envelope:**
```json
{
  "schema_version": "hitl/v1",
  "ok": true,
  "command": "hitl.approve",
  "payload": {
    "id": "ck_abc123-...",
    "action": "approve",
    "previous_status": "pending",
    "current_status": "approved",
    "actor": "@alice",
    "actor_at": "2026-06-04T08:05:00Z",
    "rows_affected": 1
  },
  "error": null
}
```

**JSON conflict envelope** (item already resolved):
```json
{
  "schema_version": "hitl/v1",
  "ok": false,
  "command": "hitl.approve",
  "payload": null,
  "error": {
    "code": "conflict",
    "message": "ck_abc123-... no longer pending. Already approved by @alice.",
    "detail": {
      "current_status": "approved",
      "current_actor": "@alice",
      "current_actor_at": "2026-06-04T08:05:00Z"
    }
  }
}
```

---

#### Subcommand: `hitl reject <id>`
Reject a **pending** item with a mandatory reason string.

```bash
# Reject with reason (required)
./bin/cherenkov hitl reject ck_abc123-... --reason "incorrect_spec"

# Reject with explicit actor
./bin/cherenkov hitl reject ck_abc123-... --reason "flaky_endpoint" --actor @bob

# Reject and emit JSON envelope
./bin/cherenkov hitl reject ck_abc123-... --reason "flaky_endpoint" --actor @bob --json
```

---

#### `hitl/v1` Error Codes

| Code | Meaning |
|------|---------|
| `conflict` | Item was already resolved by another actor |
| `not_found` | Item ID does not exist in the queue |
| `forbidden` | Actor is not authorized to act on this item |
| `invalid_input` | Malformed arguments |
| `db_locked` | SQLite busy-timeout exceeded |
| `llm_unavailable` | LLM backend unavailable (voice path only) |

---

### Frontier commands (post-gate surfaces)

> These CLI surfaces are wired but governed by the Validation Gate — full
> behaviour is labelled `blocked:validation-gate` until Track A passes the 5-QA
> gate. They are documented here so the CLI and docs stay drift-free.

#### `governance` — E12 Governance KPI panel

Surfaces escape-rate, false-positive, coverage, and maintenance KPIs over the
verdict/audit history.

```bash
# Show the governance KPI panel
./bin/cherenkov governance

# Machine-readable report
./bin/cherenkov governance --json

# Trend for a single metric (health_score, escape_rate, coverage, ...)
./bin/cherenkov governance --trend escape_rate
```

#### `certify` — E12 Gold-Set + RAG-Triad certification

Certifies a capability tier against the gold set using RAG-Triad metrics.

```bash
# Certify the default (small) tier
./bin/cherenkov certify

# Certify a specific tier with per-item RAG-Triad detail
./bin/cherenkov certify --tier deep --rag-report
```

Valid tiers: `small`, `deep`, `vision`.

#### `profile` — E13 Autonomy-ladder profile

Shows or sets the autonomy level the pipeline operates at.

```bash
# Show the current autonomy profile
./bin/cherenkov profile

# Set the autonomy level
./bin/cherenkov profile set --level augmented
```

Valid levels: `assisted`, `augmented`, `agentic`, `predictive`.

---

#### `mcp` — X4 MCP server (`mcp serve`, Model Context Protocol)

Exposes CHERENKOV over the [Model Context Protocol](https://modelcontextprotocol.io)
(JSON-RPC 2.0 over stdio) so Claude Desktop, Cursor, and other MCP clients can read
the HITL queue and run the Validation Gate without leaving their IDE.

```bash
# Start the MCP server (blocks until stdin closes)
./bin/cherenkov mcp serve
```

**Resources exposed (read-only):**

| URI | Description |
|-----|-------------|
| `cherenkov://hitl/pending` | Pending HITL items (`hitl/v1` envelope) |
| `cherenkov://hitl/item/{id}` | Single HITL item detail |
| `cherenkov://validate/latest` | Latest `validate/v1` ValidationReport |
| `cherenkov://validate/evidence` | Evidence directory listing |

**Tools exposed:**

| Tool | Description |
|------|-------------|
| `hitl_list` | List HITL queue items by status |
| `hitl_approve` | Approve a pending item (atomic SQL gatekeeper) |
| `hitl_reject` | Reject a pending item (atomic SQL gatekeeper) |
| `validate_run_gate` | Run the Validation Gate in report-only mode (suggest-only, D7 honored) |

**Claude Desktop config** (add to `claude_desktop_config.json → mcpServers`):

```json
{
  "cherenkov": {
    "command": "python3",
    "args": ["/home/you/cherenkov-qa/cherenkov.py", "mcp", "serve"],
    "cwd": "/home/you/cherenkov-qa"
  }
}
```

> **Trust model:** MCP peers are untrusted. All tool arguments are validated with
> Pydantic before reaching the HITL queue. Writes go through the existing atomic SQL
> gatekeeper — the same path as `hitl approve` in the terminal. The server never
> reads secrets or env vars from client input.

---

#### `review` — Horizon V review UI server

Serves the prebuilt web review surface (the HITL/validation review UI) over HTTP
so verdicts can be inspected and actioned from the browser instead of the terminal.

```bash
# Serve the prebuilt web UI on the default port (8000)
./bin/cherenkov review --web

# Bind a custom port
./bin/cherenkov review --port 8080
```

| Flag | Default | Description |
|------|---------|-------------|
| `--web`, `-w` | `True` | Serve the prebuilt web UI |
| `--port`, `-p` | `8000` | Port to bind |

---

## 🔒 The Anti-Lock-In Promise
CHERENKOV does not lock you into a proprietary framework. Every test generated is a standard, pure Playwright TypeScript file (`.spec.ts`) that imports a pure `openapi-fetch` client. 

Running `eject` strips all CHERENKOV-specific trace monkey-patching and hooks cleanly, leaving you with a standard open-source suite.

---

## ✅ Verifying the core claim against a real model

Every automated test mocks the LLM, so the default suite cannot prove "spec in,
compilable Playwright test out" end-to-end. One opt-in smoke does, by driving the
**real** model through the GENERATE stage:

```bash
# Requires a running Ollama with the generation model pulled (qwen2.5-coder:7b).
CHERENKOV_LIVE_LLM=1 PYTHONPATH=. python3 smoke_test_generate_live.py
```

It **skips cleanly** (exit 0) when `CHERENKOV_LIVE_LLM` is unset, and **fails loudly**
if the flag is set but the model produces empty or structurally invalid output —
the exact silent-failure mode that mocked tests miss. In CI it runs only via manual
dispatch on a self-hosted GPU runner (the `live-llm-generate` job in
`.github/workflows/ci.yml`); hosted runners have no GPU and never fake a pass.
