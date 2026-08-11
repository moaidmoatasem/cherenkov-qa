# CHERENKOV Getting Started Guide

Welcome to CHERENKOV! This usage-first guide will walk you from initial
installation to running your first passing test suite and ejecting standalone
Playwright tests in under 5 minutes.

> **New here?** This doc is one of three entry points. Pick the one that fits:
>
> - **[../README.md](../README.md)** — 2-minute overview.
> - **[CLI_DEMO.md](CLI_DEMO.md)** — terminal walk-through of the full flow.
> - This file — the full install + first run guide.
>
> **Need the project status?** → [STATUS.md](STATUS.md).
> **Lost in the docs?** → [INDEX.md](INDEX.md).

**In this guide:**

1. [Prerequisites & Installation](#-prerequisites--installation)
2. [CLI Commands & Usage](#-cli-commands--usage)
   - [Command Groups](#command-groups)
   - [Track A Core](#track-a-core)
   - [Track B/C & Horizon 2](#track-bc-and-horizon-2-built-re-integrated)
3. [Next steps](#next-steps)

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

### 2. Docker Setup (Recommended)
You can run CHERENKOV in a fully containerized environment using Docker Compose. This packages the Python engine, the pre-built React dashboard, the target API, and the Ollama model server automatically.

```bash
# Run the complete environment (requires GPU)
make full

# Or run the offline Demo mode (no GPU, no model download)
make demo
```
When running `make demo`, you can view the mock findings in the dashboard at `http://localhost:8000`.

---

## 🚀 CLI Commands & Usage

CHERENKOV exposes all operations natively through a unified CLI tool: `./bin/cherenkov`.

### Display CLI Command Help
To view all supported commands and options:
```bash
./bin/cherenkov --help
```

---

### Command Groups

The CLI organizes its 40 top-level commands into 7 logical command groups for
discoverability. Every command remains available at the top level for backwards
compatibility, so `cherenkov validate` and `cherenkov pipeline` both
work. See [CLI_GROUPS.md](CLI_GROUPS.md) for the full group reference.

```bash
# List the commands inside a group
./bin/cherenkov pipeline --help
```

#### `pipeline`
Core API conformance pipeline: `validate`, `verify`, `audit`, `check-suite`,
`check-stale`, `synthetic`, `generate`, `bench`, `eval`, `drift`.

#### `review`
Human-in-the-loop review workflows: `hitl`, `review`, `ocr`.

#### `model`
Model / VLM substrate commands: `visual`, `perf`, `mcp`, `examples`.

#### `operate`
Long-running operations and observability: `daemon`, `dashboard`, `explore`,
`map`, `author`, `record`, `tokens`, `governance`, `profile`, `teleport`.

#### `admin`
Setup, maintenance, and self-service: `init`, `doctor`, `self-test`, `eject`,
`completion`, `report`, `diff`, `demo`.

#### `enterprise`
Enterprise integrations and certification: `enterprise`, `certify`, `playbook`,
`guardian`.

#### `routine`
Scheduled routines: `routine`.

---

### Track A Core

Core API conformance testing and pipeline operations. These commands are fully
built, validated, and governed by the CHERENKOV design invariants (D7, anti-lock-in,
suggest-only, spec-derived).

---

#### `validate`
Executes your Playwright test suite against a real server, programmatically parses trace files, compares request vs response payloads, and suggests value assertions.

```bash
# Command help
./bin/cherenkov validate --help

# Standard usage
cd target && uvicorn target_api:app --host 127.0.0.1 --port 8000
./bin/cherenkov validate --target http://localhost:8000
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target`, `-t` | *(required)* | The real server target base URL |

---

#### `verify`
Zero-config entry point that finds spec↔implementation divergences on a live API. Runs in offline mode by default (no LLM, no Ollama required). Use `--llm` to engage the full Skeptic agent for richer hypothesis generation.

```bash
# Zero-config demo against the public Petstore
cherenkov verify --url https://petstore3.swagger.io/api/v3

# Point at your own API with a local spec
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml

# CI gate: fail the build if any divergences are found
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml --fail-on-divergence

# Write a JSON report and show spec coverage gap
cherenkov verify --url http://localhost:8080 --spec ./openapi.yaml \
  --output report.json --coverage-report
```

| Flag | Default | Description |
|------|---------|-------------|
| `--url` / `-u` | *(required)* | Base URL of the live server to probe |
| `--spec` / `-s` | *(built-in Petstore)* | Path or URL to the OpenAPI spec |
| `--llm` | off | Use the LLM Skeptic (requires Ollama) |
| `--output` / `-o` | *(stdout)* | Write divergence report to file |
| `--format` | `json` | Report format: `json` or `text` |
| `--fail-on-divergence` | off | Exit 1 if divergences found (CI gate) |
| `--coverage-report` | off | Print endpoint coverage gap analysis |
| `--simple` | off | Use legacy single-probe summary |
| `--no-mutation-oracle` | off | Skip mutation oracle (faster) |
| `--fixture-dir` | `.cherenkov/fixtures` | Directory for golden fixtures |

---

#### `demo`
60-second offline demo — no Ollama, no API key, no running server required. Demonstrates the core CHERENKOV value proposition: catching an AI-generated test suite that was silently weakened.

```bash
cherenkov demo
```

---

#### `generate`
Generate Playwright E2E test files from an OpenAPI specification using the LLM-backed generate→review→repair loop.

```bash
# Generate tests for a local spec (uses Ollama by default)
cherenkov generate --spec ./openapi.yaml

# Write to a custom output directory, skip repair loop
cherenkov generate --spec ./openapi.yaml --output-dir ./tests --no-repair
```

| Flag | Default | Description |
|------|---------|-------------|
| `--spec` | *(required)* | Path to the OpenAPI spec (JSON/YAML) |
| `--output-dir` | `stub/generated_tests` | Directory to write `.spec.ts` files |
| `--no-repair` | off | Write first generation directly, skip repair |
| `--max-attempts` | `3` | Maximum repair attempts per scenario |

---

#### `admin`
Admin utilities: manage service accounts, rotate keys, and run admin-only maintenance tasks.

```bash
./bin/cherenkov admin --help
./bin/cherenkov admin rotate-keys
```

---

#### `model`
Model management: download, list, and pin models used by CHERENKOV (Ollama/LocalAI integration).

```bash
./bin/cherenkov model --help
./bin/cherenkov model list
./bin/cherenkov model pin <model-name>
```

---

#### `operate`
Operational commands for runbook actions and long-running tasks (start/stop/health of agents).

```bash
./bin/cherenkov operate --help
./bin/cherenkov operate skeptic
```

---

#### `pipeline`
Pipeline helpers: orchestrate CI/CD fragments, validate landing zones, and run canary checks.

```bash
./bin/cherenkov pipeline --help
./bin/cherenkov pipeline
```

---

#### `self-test`
Run a deterministic dry-run of the pipeline (mocking Ollama and the server).

```bash
./bin/cherenkov self-test --help
./bin/cherenkov self-test
```

---

#### `report`
Generate test coverage and diff reports from run logs.

```bash
# Generate a report from the latest run
./bin/cherenkov report --output report.json

# Diff two reports to detect regressions
./bin/cherenkov report --diff previous_report.json --output report.json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | *(none)* | JSON output file path (e.g. report.json) |
| `--diff`, `-d` | *(none)* | Path to previous report.json for diff comparison |

---

#### `eject`
Copies all your generated specs and TypeScript compilation files, emits a clean `client.ts` completely stripped of trace interception metadata, and generates standard Playwright and package settings.

```bash
# Eject the suite to a standalone folder
./bin/cherenkov eject --output ejected_suite

# If you generated with a custom --output-dir, tell eject where to find it —
# otherwise it only ever reads stub/generated_tests and won't see your tests:
./bin/cherenkov eject --output ejected_suite --tests-dir ./tests

# The ejected folder runs with vanilla Playwright
cd ejected_suite
npm install
npx playwright test
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output`, `-o` | *(required)* | Target output directory for the standalone suite |
| `--tests-dir`, `-t` | `stub/generated_tests` | Directory containing the `.spec.ts` files to eject — must match `generate`'s `--output-dir` if you used a custom one |

---

#### `init` (E5-1 — zero-config project setup)
Auto-detects OpenAPI specs and generates a sensible `cherenkov.toml` with defaults that are offline, free, and deterministic.

```bash
# Auto-detect and generate config
./bin/cherenkov init

# Override profile and force overwrite
./bin/cherenkov init --profile ci --force
```

| Flag | Default | Description |
|------|---------|-------------|
| `--profile`, `-p` | `autodetect` | Configuration profile: `laptop`, `ci`, `enterprise-vpc`, `frontier-cloud` |
| `--force`, `-f` | `false` | Overwrite existing cherenkov.toml |

---

#### `doctor` (E5-3 — system health check)
Reports effective configuration, device health (GPU vs CPU), model availability, egress policy consistency, and environmental dependencies (Node, Playwright, Docker/Prism).

```bash
./bin/cherenkov doctor --help
./bin/cherenkov doctor
```

---

#### `dashboard` (E5-4 — Truth Model + divergences view)
Displays the Truth Model claim graph and any open divergences. Uses mock data when no Truth Model has been built.

```bash
./bin/cherenkov dashboard --help
./bin/cherenkov dashboard
```

---

#### `hitl` (Human-In-The-Loop review queue)

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

```bash
./bin/cherenkov hitl --help
```

##### `hitl list`
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

##### `hitl show <id>`
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

##### `hitl approve <id>`
Approve a **pending** item. Atomic: only one approver can win on a race; the loser
receives a truthful `conflict` error.

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

##### `hitl reject <id>`
Reject a **pending** item with a mandatory reason string.

```bash
# Reject with reason (required)
./bin/cherenkov hitl reject ck_abc123-... --reason "incorrect_spec"

# Reject with explicit actor
./bin/cherenkov hitl reject ck_abc123-... --reason "flaky_endpoint" --actor @bob

# Reject and emit JSON envelope
./bin/cherenkov hitl reject ck_abc123-... --reason "flaky_endpoint" --actor @bob --json

# Reject with a short reason plus a longer free-text elaboration — kept as
# separate fields in FeedbackStore (cherenkov/core/feedback_store.py) so the
# learning loop can distinguish category from detail
./bin/cherenkov hitl reject ck_abc123-... --reason too_noisy --note "flaky under load"
```

##### `hitl classify <id>` (Tier-2)
Classify a HITL item as `regression`, `intended`, or `ignore`.

```bash
./bin/cherenkov hitl classify ck_abc123-... --classification regression --actor @alice
./bin/cherenkov hitl classify ck_abc123-... --classification intended --detail "Known flaky endpoint" --json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--classification`, `-c` | *(required)* | One of: `regression`, `intended`, `ignore` |
| `--actor` | `$USER` | Reviewer identity |
| `--detail`, `-d` | `""` | Free-text detail |
| `--json` | `false` | Emit hitl/v1 JSON envelope |

##### `hitl explain <id>` (Tier-3)
Get an AI explanation for why the HITL item was flagged.

```bash
./bin/cherenkov hitl explain ck_abc123-...
./bin/cherenkov hitl explain ck_abc123-... --json
```

##### `hitl/v1` Error Codes

| Code | Meaning |
|------|---------|
| `conflict` | Item was already resolved by another actor |
| `not_found` | Item ID does not exist in the queue |
| `forbidden` | Actor is not authorized to act on this item |
| `invalid_input` | Malformed arguments |
| `db_locked` | SQLite busy-timeout exceeded |
| `llm_unavailable` | LLM backend unavailable (voice path only) |

---

### Track B/C and Horizon 2 (built, re-integrated)

These commands extend CHERENKOV beyond core API conformance into visual testing,
performance benchmarking, truth model management, autonomous exploration, intent-
driven authoring, governance, certification, autonomy profiling, IDE integration
(MCP), and the review web UI. They are built, unit-tested, and re-integrated
into the live tree. Runtime requirements (k6 for `perf`, `adb` for some
mobile paths, `cargo` for the desktop host) are noted per command below.

> Earlier docs described a separate `track-b-c-deferred/` directory. That
> directory was fully re-integrated into the live tree and **deleted** — see
> [AGENTS.md](../AGENTS.md). If you see a `track-b-c-deferred/` reference
> elsewhere, treat it as stale and link to [docs/STATUS.md](STATUS.md).

---

#### `visual` (Track B — visual regression)
Runs visual-regression checks against a rendered URL. Auto-initializes a baseline
on first run; compares against it on subsequent runs.

```bash
./bin/cherenkov visual --target http://localhost:3000/checkout
./bin/cherenkov visual --target http://localhost:3000/checkout --baseline-dir stub/visual_baselines
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target`, `-t` | *(required)* | Absolute URL of the page to snapshot |
| `--baseline-dir` | `stub/visual_baselines` | Baseline directory label |

---

#### `perf` (Track B — performance baseline)
Runs performance baseline checks against an API endpoint using k6. Records latency
in a local SQLite store (`.cherenkov/perf_metrics.db`) and flags standard-deviation
outlier regressions once >= 3 runs exist. Degrades gracefully without k6.

```bash
./bin/cherenkov perf --target http://localhost:8000 --endpoint /health --method GET
./bin/cherenkov perf --target http://localhost:8000 --endpoint /users --method POST --vus 10 --duration 10
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target`, `-t` | *(required)* | Base URL of the API to load test |
| `--endpoint` | `/` | Endpoint path |
| `--method` | `GET` | HTTP method |
| `--vus` | `5` | Virtual users |
| `--duration` | `5` | Test duration in seconds |

---

#### `mobile` (Track B — mobile flow integrity)
Plans Maestro flows from a recorded mobile source, gates them for assertion
strength, and executes them on a connected device or emulator via Maestro (or
Appium with `--runner appium`).

`SOURCE` is a `.hil` interaction trace or an `.apk`. A `.har` is rejected with a
pointer to `cherenkov verify`: it records network traffic, not screen
interactions, so no flow can be planned from it.

Two integrity rules apply. A flow whose assertion matches any screen (`.*`,
`.+`, `*`, empty) fails the gate and never reaches the device — that is a
weakened assertion, and it can never fail. A flow that never executed is
reported `not_executed`, never as passing.

```bash
./bin/cherenkov mobile flows.hil --app-id com.acme.shop
./bin/cherenkov mobile app.apk --no-execute
./bin/cherenkov mobile flows.hil --json --fail-on-finding
./bin/cherenkov mobile --demo
```

| Flag | Default | Description |
|------|---------|-------------|
| `--app-id` | *(from source)* | Application package id to target |
| `--out` | `stub/generated_tests/mobile` | Directory for generated flows |
| `--runner` | `maestro` | Execution backend (`maestro` or `appium`) |
| `--execute/--no-execute` | `--execute` | Run flows on a device |
| `--strict/--no-strict` | `--strict` | Fail a flow carrying no assertion |
| `--demo` | off | Use built-in scenarios; never executed on a device |
| `--json` | off | Machine-readable output |
| `--fail-on-finding` | off | Exit non-zero on gate or execution failure |

---

#### `map` (E2-6 — Truth Model builder)
Build and inspect the Truth Model from configured sources (OpenAPI specs, traffic
logs, etc.). Produces a claim graph connecting specifications with code and traces.

```bash
./bin/cherenkov map
./bin/cherenkov map --detailed
```

| Flag | Default | Description |
|------|---------|-------------|
| `--detailed`, `-d` | `false` | Show full claim details |

---

#### `daemon` (E4-4 — continuous watcher)
Continuously watches configured sources and rebuilds the Truth Model on change.

```bash
# Poll every 60 seconds indefinitely
./bin/cherenkov daemon

# Poll every 30 seconds, max 10 iterations
./bin/cherenkov daemon --interval 30 --max-loops 10
```

| Flag | Default | Description |
|------|---------|-------------|
| `--interval`, `-i` | `60` | Poll interval in seconds |
| `--max-loops`, `-n` | `0` | Max rebuild iterations (`0` = infinite) |

---

#### `explore` (E10 — autonomous risk crawl)
Crawl a live surface and print a "second pair of eyes" risk digest. Probes
endpoints for anomalies, console/network exceptions, and security headers.

```bash
# Crawl a target with default settings
./bin/cherenkov explore --target http://localhost:3000

# Probe multiple routes with a custom HTTP method
./bin/cherenkov explore --target http://localhost:3000 --path /api/users --path /api/orders --method POST
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target`, `-t` | *(required)* | Base URL of the app/API to crawl |
| `--path`, `-p` | `["/"]` | Route to probe (repeatable) |
| `--method`, `-m` | `GET` | HTTP method to probe with |

---

#### `author` (E10 — intent-driven test generator)
Turn plain-language intent into an ejectable Playwright test. The intent parser
recognises these action types: `navigate`, `click`, `fill`, `expect`, `request`.
Any unrecognised action emits a warning and is skipped as a comment in the output.

```bash
# Generate a Playwright test from plain-language intent
./bin/cherenkov author "Register new test user" --output generated_tests

# Specify a target base URL
./bin/cherenkov author "Check guest checkout with a discount" --output generated_tests --target http://localhost:8000
```

| Flag | Default | Description |
|------|---------|-------------|
| `intent` | *(positional, required)* | Plain-language test intent |
| `--output`, `-o` | *(required)* | Directory to write the `.spec.ts` test into |
| `--target`, `-t` | `""` | Base URL the flow runs against |

---

#### `audit` (E0.5h — Baseline-Free Oracle suite audit)
Evaluates whether an existing test suite actually catches regressions by recording
baseline traffic against a live target, generating spec-derived mutants (status,
value, missing, enum), and replaying the suite against those mutants.

```bash
# Audit a Playwright suite against a live API (baseline-free oracle)
./bin/cherenkov audit --target http://localhost:8000 \
  --spec openapi.yaml \
  --test-cmd "npx playwright test tests/"
```

| Flag | Default | Description |
|------|---------|-------------|
| `--target`, `-t` | *(required)* | Base URL of the live server to record the baseline from |
| `--spec`, `-s` | *(required)* | Path or URL to the OpenAPI spec JSON/YAML |
| `--test-cmd`, `-c` | *(required)* | Command to run the test suite (receives `API_URL` in the environment) |
| `--proxy-port` | `9100` | Port for the recording proxy |
| `--mock-port` | `9101` | Port for the mutant mock server |

---

#### `governance` (E12 — Governance KPI panel)
Surfaces escape-rate, false-positive, coverage, and maintenance KPIs over the
verdict/audit history.

```bash
# Show the governance KPI panel
./bin/cherenkov governance

# Machine-readable report
./bin/cherenkov governance --json

# Trend for a single metric
./bin/cherenkov governance --trend escape_rate
```

| Flag | Default | Description |
|------|---------|-------------|
| `--json` | `false` | Emit machine-readable JSON report |
| `--trend`, `-t` | *(none)* | Metric to trend (`health_score`, `escape_rate`, `coverage`, etc.) |

---

#### `certify` (E12 — Gold-Set + RAG-Triad certification)
Certifies a capability tier against the gold set using RAG-Triad metrics.

```bash
# Certify the default (small) tier
./bin/cherenkov certify

# Certify a specific tier with per-item RAG-Triad detail
./bin/cherenkov certify --llm deep --rag-report
```

| Flag | Default | Description |
|------|---------|-------------|
| `--tier`, `-T` | `small` | Capability tier: `small`, `deep`, `vision` |
| `--rag-report`, `-r` | `false` | Show per-item RAG-Triad metrics |

---

#### `profile` (E13 — Autonomy-ladder profile)
Shows or sets the autonomy level the pipeline operates at.

```bash
# Show the current autonomy profile
./bin/cherenkov profile

# Set the autonomy level
./bin/cherenkov profile --level augmented
```

| Flag | Default | Description |
|------|---------|-------------|
| `action` | `show` | Sub-action: `show` or `set` |
| `--level`, `-l` | *(none)* | Autonomy level: `assisted`, `augmented`, `agentic`, `predictive` |

---

#### `record` (CC-5 — teleport session ingestion)
Ingests live agentic-exploration scenario results into the HITL review queue from a
result file, optionally tagging the enqueued items with a run id.

```bash
# Ingest exploration results into the HITL queue
./bin/cherenkov record .cherenkov/explore_results.json

# Tag enqueued items with a run id
./bin/cherenkov record .cherenkov/explore_results.json --run-id 20260801-120000
```

| Flag | Default | Description |
|------|---------|-------------|
| `RESULT_PATH` | *(positional, required)* | Path to the scenario results file |
| `--run-id` | *(none)* | Tag enqueued HITL items with this run id |

---

#### `mcp` (X4 — Model Context Protocol server)
Exposes CHERENKOV over the [Model Context Protocol](https://modelcontextprotocol.io)
(JSON-RPC 2.0 over stdio) so Claude Desktop, Open Interpreter, Cursor, and other MCP
clients can run conformance checks, query drift findings, and manage the HITL queue
without leaving their editor or terminal.

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
| `run_conformance_check` | Trigger `cherenkov validate` against a target URL; returns report summary |
| `get_last_report` | Return last `.cherenkov/report.json` without a new run |
| `list_drift_findings` | Drift findings from the last run, filterable by severity / endpoint |
| `get_tightening_suggestions` | OpenAPI spec tightening suggestions for a specific endpoint |
| `explain_finding` | LLM natural-language explanation of a finding |
| `hitl_list` | List HITL queue items by status |
| `hitl_approve` | Approve a pending item (atomic SQL gatekeeper) |
| `hitl_reject` | Reject a pending item (atomic SQL gatekeeper) |
| `validate_run_gate` | Run the Validation Gate in report-only mode (suggest-only, D7 honored) |
| `chat_explain_divergence` | GraphRAG explanation of an endpoint divergence |
| `chat_run_test` | Plan test scenarios for an endpoint (suggest-only) |

**Claude Desktop** (add to `claude_desktop_config.json → mcpServers`):

```json
{
  "cherenkov": {
    "command": "python3",
    "args": ["-m", "cherenkov", "mcp", "serve"],
    "cwd": "/home/you/cherenkov-qa"
  }
}
```

**Open Interpreter** — one-command setup:

```bash
bash scripts/setup_oi.sh   # writes ~/.openinterpreter/mcp.json
interpreter                # cherenkov tools appear automatically
```

See [docs/guides/OPEN_INTERPRETER_SETUP.md](guides/OPEN_INTERPRETER_SETUP.md) for full walkthrough and example prompts.

**Cursor / VS Code** (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "python3",
      "args": ["-m", "cherenkov", "mcp", "serve"],
      "cwd": "/home/you/cherenkov-qa"
    }
  }
}
```

> **Trust model:** MCP peers are untrusted. All tool arguments are validated with
> Pydantic before reaching the HITL queue. Writes go through the existing atomic SQL
> gatekeeper — the same path as `hitl approve` in the terminal. The server never
> reads secrets or env vars from client input.

---

#### `review` (Horizon V — review dashboard web UI)
Serves the prebuilt web review surface (the HITL/validation review UI) over HTTP
so verdicts can be inspected and actioned from the browser instead of the terminal.

```bash
# Serve the prebuilt web UI on the default port (8000)
./bin/cherenkov review

# Bind a custom port
./bin/cherenkov review --port 8080

# Load demo fixture data on startup
./bin/cherenkov review --demo
```

| Flag | Default | Description |
|------|---------|-------------|
| `--web`, `-w` | `True` | Serve the prebuilt web UI |
| `--port`, `-p` | `8000` | Port to bind |
| `--demo` | `false` | Load demo fixture data into HITL queue on startup |

---

#### `diff`
Compare two OpenAPI specs for breaking changes.

```bash
cherenkov diff --before old-openapi.yaml --after new-openapi.yaml
cherenkov diff --before old-openapi.yaml --after new-openapi.yaml --format json
```

| Flag | Default | Description |
|------|---------|-------------|
| `--before` | *(required)* | Path to the original spec |
| `--after` | *(required)* | Path to the modified spec |
| `--format` | `text` | Output format: `text` or `json` |

---

#### `completion`
Generate shell completion scripts.

```bash
# Bash / Zsh
eval "$(cherenkov completion bash)"
eval "$(cherenkov completion zsh)"

# Fish
cherenkov completion fish | source
```

| Argument | Description |
|----------|-------------|
| `shell` | Shell type: `bash`, `zsh`, or `fish` |

---

#### `tokens`
Token consumption monitor — inspect LLM usage, costs, and recommendations.

```bash
cherenkov tokens
cherenkov tokens --help
```

---

#### `playbook`
Manage and run validation playbooks — named, auto-triggering skill rules that fire against endpoints during daemon check cycles.

```bash
# List all loaded playbooks (built-in + project-local)
cherenkov playbook list
cherenkov playbook list --json

# Inspect a specific playbook
cherenkov playbook show auth-strict

# Fire matching playbooks against a live endpoint
cherenkov playbook run --url http://localhost:8080 --path /health

# Scaffold a new playbook YAML in .cherenkov/playbooks/
cherenkov playbook new my-playbook
```

---

#### `enterprise`
Enterprise-tier commands for org management, SSO, audit logs, and compliance.

```bash
 # Manage organizations and tenants
 cherenkov enterprise org
 
 # Configure SAML 2.0 / SSO
 cherenkov enterprise saml
 
 # Manage Role-Based Access Control
 cherenkov enterprise rbac
 
 # Generate compliance reports
 cherenkov enterprise compliance
 
 # Access audit logs
 cherenkov enterprise audit
 ```
 
 ---
 
#### `guardian`
 Continuous spec-drift monitoring against a live API. `guardian start` polls every endpoint declared in the OpenAPI spec and persists drift events to the drift store until interrupted (SIGINT/SIGTERM).
 
 ```bash
 # Monitor all spec paths (every 60s)
 cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080
 
 # Watch a single endpoint every 10s, store history elsewhere
 cherenkov guardian start --spec openapi.yaml --base-url http://localhost:8080 \
   --endpoint "GET:/health" --interval 10 --db .cherenkov/guardian.db
 ```

---

#### `check-suite`
Detect AI cheating in a test suite — find weakened, deleted, or hallucinated assertions via fast static analysis (no execution required).

```bash
# Check a candidate suite against a baseline for weakened/deleted assertions
cherenkov check-suite --candidate suite.py --baseline baseline.py

# Check against a spec for hallucinated field references
cherenkov check-suite --candidate suite.ts --spec openapi.yaml

# CI gate: exit 1 on any finding, write JSON report
cherenkov check-suite --candidate suite.ts --baseline baseline.ts --fail-on-finding --output findings.json
```

---

#### `check-stale`
Check whether generated tests are stale relative to the spec.

```bash
# Compare manifest hash against current spec
cherenkov check-stale

# CI gate: exit 1 if stale
cherenkov check-stale --fail-on-stale

# Override spec path and output JSON
cherenkov check-stale --spec openapi.yaml --json
```

---

#### `bench`
Benchmark generated test quality against golden fixtures.

```bash
# Run benchmark across the default test directory
cherenkov bench

# Include a custom test directory
cherenkov bench --dir stub/generated_tests

# Set pass thresholds and write a JSON report
cherenkov bench --threshold-compile 0.95 --threshold-quality 0.9 --output bench.json
```

---

#### `examples`
Print usage examples for common CHERENKOV workflows.

```bash
cherenkov examples
```

---

#### `docs`
Show CLI documentation for a topic, as text or JSON. `--json` returns
`{summary, commands, notes}` per topic, so an agent or script can read the docs
without scraping help output.

```bash
# List every topic
cherenkov docs

# One topic, human-readable
cherenkov docs check-suite

# Everything, structured
cherenkov docs --json
```

---

#### `agent`
Make CHERENKOV discoverable to a coding agent working in this repository.
`agent init` installs the public skills (`npx skills add moaidmoatasem/cherenkov-qa`)
and writes a delimited `<!-- CHERENKOV:START -->` block into `AGENTS.md`.

Run it once per repository. It is idempotent — re-running refreshes the block in
place rather than appending — and it never fails on a missing `npx`: the skills
install degrades to a printed instruction, because the AGENTS.md block is the
half that matters for discovery. Both steps are local; nothing is uploaded.

```bash
# The whole thing
cherenkov agent init

# Structured result, for a script or agent
cherenkov agent init --json

# Either half on its own
cherenkov agent init --skip-skills
cherenkov agent init --skip-agents-md
```

---

#### `synthetic`
Generate synthetic test data payloads from an OpenAPI spec.

```bash
# Generate random payloads for up to 10 endpoints
cherenkov synthetic openapi.yaml

# Use LLM strategy and write to file
cherenkov synthetic openapi.yaml --strategy llm --output payloads.json --endpoints 20
```

---

#### `drift`
Track and reconcile spec-suite drift over time using an immutable ledger.

```bash
# Seed a new baseline snapshot
cherenkov drift seed --spec openapi.yaml --suite suite.json

# List recorded snapshots
cherenkov drift list

# Reconcile current spec/suite against baseline (CI gate)
cherenkov drift reconcile --spec openapi.yaml --suite suite.json --fail-on-drift

# Export a baseline snapshot for zero-latency CI
cherenkov drift export -o baseline.json
```

---

#### `eval`
Evaluate and grade test suite quality (STORM-inspired lifecycle).

```bash
# Grade a suite against a spec (no live API needed)
cherenkov eval grade --spec openapi.yaml --suite suite.json

# Run suite against a live API and emit a trace
cherenkov eval run --suite suite.json --target http://localhost:8080

# Grade and fail CI below a threshold
cherenkov eval grade --spec openapi.yaml --suite suite.json --fail-on C
```

---

#### `ocr`
OCR-powered visual review: read and validate text in screenshots.

```bash
# Check OCR provider status
cherenkov ocr status

# Test OCR on a file
cherenkov ocr test

# Review a screenshot
cherenkov ocr review --file screenshot.png
```

---

#### `routine`
Manage recurring scheduled validation routines.

```bash
# List all configured routines
cherenkov routine list

# Create a new routine
cherenkov routine --name health-check --trigger cron --value "0 * * * *" --target cherenkov.scheduling.templates.health:run

# Toggle a routine on/off
cherenkov routine toggle <routine_id> true
```

---

#### `teleport`
Transfer CHERENKOV session state across environments.

```bash
# Push session state
cherenkov teleport push <session_id>

# Pull session state using a token
cherenkov teleport pull <token>

# List active sessions
cherenkov teleport list

# Check session status
cherenkov teleport status <session_id>
```

---

#### `plugins`
Manage and inspect CHERENKOV plugins loaded via entry points.

```bash
# List all loaded plugins
cherenkov plugins list
```

---

#### `template`
Manage and install test templates from the marketplace.

```bash
# Search the marketplace for available templates
cherenkov template search

# List templates installed locally
cherenkov template list

# Install a template by id
cherenkov template install <template_id>
```

---

#### `federation`
Manage federation with remote CHERENKOV instances.

```bash
# Store a remote federation endpoint
cherenkov federation join

# Push a JSON payload to the remote mesh under a topic
cherenkov federation push <topic> <payload>

# Query the remote mesh for a topic and display results
cherenkov federation query <topic>
```

---

#### `mobile`
Generate mobile tests from an OpenAPI spec via the Maestro pipeline.
Runs ingest → plan → generate → review in sequence, and reports pass/fail per scenario.

```bash
# Generate and review mobile scenarios from a spec
cherenkov mobile openapi.yaml

# Tag the run for logging/correlation
cherenkov mobile openapi.yaml --run-id nightly-042
```

Ejects to vanilla Appium or Maestro (`cherenkov/execution/mobile_eject_appium.py`,
`mobile_eject_maestro.py`), so the generated suites carry no CHERENKOV imports —
the same anti-lock-in promise as the Playwright path.

---

#### `train`
Fine-tune a small language model on your own locally collected QA corpus (Phase 15).
Collection is **opt-in and local** — nothing is uploaded, and the pipeline runs entirely on your machine.

```bash
# Export the locally collected corpus to a JSONL dataset
cherenkov train export --out corpus.jsonl --limit 5000

# Validate the whole pipeline without doing any real computation
cherenkov train run --data corpus.jsonl --backend dry_run

# Run a real LoRA fine-tune via the HuggingFace backend
cherenkov train run --data corpus.jsonl --backend huggingface --epochs 3 --batch-size 4

# Inspect the last run (reads training_run.json)
cherenkov train status --json
```

Start with `--backend dry_run`: it exercises the full prepare → train → save → evaluate path
and reports what a real run would do, without requiring GPU or training dependencies.

> **Note:** publishing or serving a trained model is not implemented yet — tracked as #779 (model
> release) and #780 (self-hosted serving). `cherenkov train` produces local artefacts only.

---

#### `testerarmy`
TesterArmy-inspired command group.

```bash
# Retrieve documentation for a topic (JSON if requested)
cherenkov testerarmy docs <topic> --json

# List environments
cherenkov testerarmy environments

# List projects
cherenkov testerarmy projects

# List runs
cherenkov testerarmy runs

# List tests
cherenkov testerarmy tests
```

---

## 🔒 The Anti-Lock-In Promise
CHERENKOV does not lock you into a proprietary framework. Every test generated is a standard, pure Playwright TypeScript file (`.spec.ts`) that imports a pure `openapi-fetch` client.

Running `eject` strips all CHERENKOV-specific trace monkey-patching and hooks cleanly, leaving you with a standard open-source suite.

---

## Next steps

- **Want to see it live?** → [recordings/](recordings/) — 8 step-by-step Loom recording scripts with real test data and live evidence.
- **Want the project state and roadmap?** → [STATUS.md](STATUS.md) and [PHASE_PLAN.md](PHASE_PLAN.md).
- **Want the bigger picture?** → [INDEX.md](INDEX.md) maps the whole docs tree.
- **Lost or hitting an issue?** Search [wiki/FAQ.md](wiki/FAQ.md) or open an issue.
- **Agent or contributor?** Read [HANDOVER.md](../HANDOVER.md) and [AGENTS.md](../AGENTS.md) **before** any work.

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
