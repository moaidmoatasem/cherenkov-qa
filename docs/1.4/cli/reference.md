---
title: CLI Reference
description: Complete reference for all CHERENKOV-QA CLI commands, flags, and options.
---

# CLI Reference

The CHERENKOV CLI is the primary interface for the platform. It provides **42 commands** organized into **7 command groups** (46 total registered names, measured from the Click tree).

## Global Options

These flags apply to every command:

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | | Output pure JSON for machine-readable use |
| `--quiet` | `-q` | Suppress non-error standard output |
| `--help` | `-h` | Show help for any command |
| `--version` | | Show CHERENKOV version |

---

## Command Groups

The CLI organizes its 40 top-level commands into 7 logical command groups for
discoverability. Every command remains available at the top level for backwards
compatibility, so `cherenkov validate` and `cherenkov pipeline validate` both
work.

| Group | Member commands |
|-------|-----------------|
| `pipeline` | `validate`, `verify`, `audit`, `check-suite`, `check-stale`, `synthetic`, `generate`, `bench`, `eval`, `drift` |
| `review` | `hitl`, `review`, `ocr` |
| `model` | `visual`, `perf`, `mcp`, `examples` |
| `operate` | `daemon`, `dashboard`, `explore`, `map`, `author`, `record`, `tokens`, `governance`, `profile`, `teleport` |
| `admin` | `init`, `doctor`, `self-test`, `eject`, `completion`, `report`, `diff`, `demo` |
| `enterprise` | `enterprise`, `certify`, `playbook`, `guardian` |
| `routine` | `routine` |

```bash
# List the commands inside a group
cherenkov pipeline --help
```

---

## Core Conformance

### `validate`

Run conformance tests against a live server.

```bash
cherenkov validate --spec <file> --target <url>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | No | Path to OpenAPI `.yaml` or `.json` spec. Use `-` to read from stdin. |
| `--target URL` | Yes | Base URL of the server under test |
| `--fail-on-drift` | No | Exit with code `1` if drift is detected |
| `--output DIR` | No | Write JUnit XML + SARIF to this directory |
| `--json` | No | Output results as JSON to stdout |
| `--source` | No | Spec source type (openapi, graphql, grpc) |
| `--format` | No | Output format (terminal, junit, sarif) |
| `--workers` | No | Parallel workers (default 1) |
| `--no-html` | No | Skip HTML report generation |
| `--no-cache` | No | Bypass result cache |
| `--json-summary` | No | Output summary as JSON only |
| `--quiet` | No | Suppress all non-error output |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All tests pass, no drift |
| `1` | Drift detected (spec violation found) |
| `2` | Validation error (config, spec parse failure) |
| `3` | Configuration error |
| `4` | Network error |

**Examples:**

```bash
# Basic validation
cherenkov validate --spec petstore.yaml --target http://localhost:4010

# CI mode — fail hard on drift, output reports
cherenkov validate \
  --spec petstore.yaml \
  --target http://localhost:4010 \
  --fail-on-drift \
  --output ./reports

# Read spec from stdin (for piping)
cat petstore.yaml | cherenkov validate --spec - --target http://localhost:4010

# Machine-readable JSON output
cherenkov validate --spec api.yaml --target http://api.example.com --json
```

### `verify`

Run spec-derived probe planning and integrity verification against a live server.

```bash
cherenkov verify --url <url> --spec <file>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--url URL` | Yes | Base URL of the server under test |
| `--spec FILE` | Yes | Path to OpenAPI spec |
| `--health-score` | No | Print an A-F health grade for the API |
| `--coverage-report` | No | Generate an endpoint coverage report |
| `--max-probes N` | No | Maximum number of probes to run (default: unlimited) |
| `--fail-on-divergence` | No | Exit with code `1` if any divergences are found |
| `--output FILE` / `-o` | No | Write the divergence report to this file |
| `--format [json\|text]` | No | Report format for `--output` (default: `json`) |
| `--json` | No | Emit the report on **stdout**; progress text moves to stderr |

`--output` writes a file; `--json` writes the same document to stdout, so an
agent or script needs no temp file. Both come from one builder, so they cannot
drift. `--json` composes with `--fail-on-divergence`: the document is emitted
before the non-zero exit, so a failing CI gate still tells you why.

**Examples:**

```bash
# Basic verify with health score
cherenkov verify --url http://localhost:8000 --spec api.yaml --health-score

# Verify with coverage and capped probe count
cherenkov verify --url http://localhost:8000 --spec api.yaml \
  --coverage-report --max-probes 50

# CI-friendly: fail the build on drift and write a JSON report
cherenkov verify --url http://localhost:8000 --spec api.yaml \
  --fail-on-divergence --output report.json --format json
```

### `check-suite`

Run an integrity check against the REVIEW gate contract for a candidate test suite.

```bash
cherenkov check-suite --candidate <path> --spec <file>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--candidate PATH` / `-c` | Yes | Path to the candidate test suite to check |
| `--spec FILE` / `-s` | Yes | Path to the OpenAPI spec the suite was generated from |
| `--baseline PATH` / `-b` | No | Path to a known-honest baseline suite to compare against |
| `--fail-on-finding` | No | Exit with code `1` if any finding is detected |
| `--output FILE` / `-o` | No | Write the JSON findings report to this file |
| `--json` | No | Emit `{candidate, findings, clean}` on stdout instead of the human report |

`--json` owns stdout, so the document is parseable without stripping a banner —
warnings go to stderr. It composes with `--fail-on-finding`: the JSON is still
emitted before the non-zero exit.

### `diff`

Show diff between spec and live server responses.

### `drift`

List spec-drift findings from the last conformance run.

---

## Test Lifecycle

### `generate`

Generate Playwright tests from a spec without executing them.

```bash
cherenkov generate --spec <file>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | Path to OpenAPI spec |
| `--output-dir DIR` | No | Directory to write generated tests (default: `stub/generated_tests`) |
| `--repair` / `--no-repair` | No | Enable or disable the generate→review→repair loop (default: `--repair`) |
| `--max-attempts N` | No | Maximum LLM generation attempts per endpoint (default: 3, range 1-10) |

### `eject`

Strip all CHERENKOV imports and produce standalone Playwright tests.

```bash
cherenkov eject --output <dir>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--output DIR` | Yes | Directory to write ejected tests |

!!! note "Zero lock-in guarantee"
    Ejected tests use `openapi-fetch` and vanilla Playwright only. They will run without CHERENKOV installed, forever.

### `synthetic`

Generate synthetic traffic patterns for load testing.

### `self-test`

Run a deterministic dry-run of the pipeline (mocking Ollama and the server).

### `init`

Initialize CHERENKOV in the current workspace.

### `eval`

Evaluate generated test quality against known benchmarks.

---

## Dashboard & Visual

### `dashboard`

Launch the interactive React dashboard and MCP network conductor.

```bash
cherenkov dashboard
```

Opens at `http://localhost:8000` by default. Contains 5 workspaces:

- **Overview** (DashboardWorkspace) — release readiness, health, and recent runs
- **Author & Generate** (AuthoringWorkspace) — intent-driven test creation and generation
- **Triage** (TriageWorkspace) — severity-sorted findings and HITL review
- **Coverage & Intelligence** (IntelligenceWorkspace) — endpoint coverage, GraphRAG knowledge explorer
- **Settings** (SettingsWorkspace) — configuration, device management, system health

### `map`

Generate an interactive API topology map from the OpenAPI spec.

### `explore`

Interactive endpoint browser for exploring conformance results.

### `author`

Intent-driven test creation wizard.

### `visual`

Run visual regression testing with screenshot comparison.

### `ocr`

Run OCR-based validation on rendered UI screenshots.

---

## Human-in-the-Loop

### `hitl`

Manage the Human-in-the-Loop review queue.

```bash
# List pending items
cherenkov hitl list

# Approve a verdict
cherenkov hitl approve <item-id>

# Reject a verdict with reason
cherenkov hitl reject <item-id> --reason "False positive"
```

### `review`

Batch review interface for processing multiple HITL items.

---

## MCP & Integration

### `mcp`

MCP ecosystem management commands.

```bash
# List registered MCP servers
cherenkov mcp list

# Publish an external MCP server to the mesh
cherenkov mcp publish --name <name> --url <url>
```

### `agent`

Make CHERENKOV discoverable to a coding agent working in this repository.

`agent init` does two things: installs the public skills via
`npx skills add moaidmoatasem/cherenkov-qa`, and writes a delimited
`<!-- CHERENKOV:START -->` block into the repository's `AGENTS.md`. Run it once
per repository — it is idempotent, replacing the block in place rather than
appending, and a missing `npx` degrades to a printed instruction instead of a
failure. Both steps are local; nothing is uploaded.

```bash
# The whole thing
cherenkov agent init

# Structured result for a script or agent
cherenkov agent init --json

# Either half on its own
cherenkov agent init --skip-skills
cherenkov agent init --skip-agents-md

# Write into a different repository root
cherenkov agent init --path ../other-repo
```

### `docs`

CLI documentation as data. Prints a topic's summary, commands and notes; with
`--json`, returns `{topic, summary, commands, notes}` so an agent can read the
docs without scraping help text.

```bash
# List every topic
cherenkov docs

# One topic
cherenkov docs check-suite

# Everything, structured
cherenkov docs --json

# One topic, structured
cherenkov docs verify --json
```

An unknown topic exits non-zero and lists the real ones.

### `completion`

Generate shell completion scripts.

### `tokens`

Manage API tokens for MCP authentication.

---

## Performance & Benchmarks

### `perf`

Run performance benchmarks against the target API.

### `bench`

Run comparative benchmarks between spec versions.

### `profile`

Profile test execution time and resource usage.

---

## Governance & Compliance

### `governance`

Governance policy management for API conformance standards.

### `certify`

Generate conformance certification reports.

```bash
cherenkov certify --spec <file> --url <url>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | Path to OpenAPI spec |
| `--url URL` | Yes | Base URL of the live server under test (alias `-u`) |
| `--coverage-report` | No | Include endpoint coverage breakdown in the report |
| `--compliance STANDARD` | No | Print the compliance evidence mapping (e.g. `sama-ccsf`, `cbe-fincsf`) |
| `--verify` | No | Verify an existing certificate file rather than running a new one |
| `--output DIR` | No | Output directory for the certification report |

### `guardian`

Start the Guardian daemon for continuous spec-drift monitoring.

```bash
cherenkov guardian start --spec <spec> --base-url <url>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | Path to OpenAPI spec |
| `--base-url URL` | Yes | Base URL of the server to monitor |
| `--interval SECONDS` | No | Polling interval in seconds (alias `-i`, default: 300) |
| `--endpoint METHOD:PATH` | No | Specific endpoint to monitor (repeatable) |
| `--max-loops N` | No | Stop after N check cycles (alias `-n`, 0 = run until interrupted) |
| `--db PATH` | No | SQLite drift database path (default: `.cherenkov/drift.db`) |

**Examples:**

```bash
# Start guardian with 5-minute polling
cherenkov guardian start --spec api.yaml --base-url http://localhost:8000

# Custom interval (every 60 seconds)
cherenkov guardian start --spec api.yaml --base-url http://localhost:8000 --interval 60
```

### `enterprise`

Organization-management commands (SSO, audit log, RBAC) — free and self-hosted, no paid tier required.

```bash
# View audit log
cherenkov enterprise audit-log

# Manage RBAC roles
cherenkov enterprise roles list
```

---

## Second Brain & Knowledge

### `report`

Generate a human-readable conformance report from the last run.

### `daemon`

Run CHERENKOV as a background daemon for continuous monitoring.

---

## Remote & Scheduling

### `teleport`

Cross-device session management.

```bash
# Push current session to another device
cherenkov teleport push <session-id>

# Join a session from another device via token
cherenkov teleport pull <token>
```

### `routine`

Manage autonomous background routines.

```bash
# List active routines
cherenkov routine list

# Start a scheduled routine
cherenkov routine start drift-check --schedule "0 */6 * * *"

# Stop a routine
cherenkov routine stop <routine-id>
```

### `check-stale`

Check for stale conformance results and trigger re-runs.

---

## Diagnostics

### `doctor`

Diagnose environment issues.

```bash
cherenkov doctor
```

Checks: Python version, Node, Playwright, Ollama, Docker, models pulled, config validity.

### `examples`

Show a gallery of common one-liners.

```bash
cherenkov examples
```

### `demo`

Run a demo conformance check against the built-in Petstore spec.

### `playbook`

Show the CHERENKOV operations playbook.

---

## Shell Completions

Install shell completions for tab-completion of commands and flags:

=== "bash"

    ```bash
    eval "$(_CHERENKOV_COMPLETE=bash_source cherenkov)"
    # Add to ~/.bashrc for persistence
    ```

=== "zsh"

    ```bash
    eval "$(_CHERENKOV_COMPLETE=zsh_source cherenkov)"
    # Add to ~/.zshrc for persistence
    ```

=== "fish"

    ```bash
    eval (env _CHERENKOV_COMPLETE=fish_source cherenkov)
    # Add to ~/.config/fish/config.fish for persistence
    ```
