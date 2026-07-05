---
title: CLI Reference
description: Complete reference for all CHERENKOV-QA CLI commands, flags, and options.
---

# CLI Reference

The CHERENKOV CLI is the primary interface for the platform. It provides **37 commands** organized into functional groups.

## Global Options

These flags apply to every command:

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | | Output pure JSON for machine-readable use |
| `--quiet` | `-q` | Suppress non-error standard output |
| `--help` | `-h` | Show help for any command |
| `--version` | | Show CHERENKOV version |

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

Run the 6-gate integrity verification on a test suite.

```bash
cherenkov verify --suite <path>
```

### `check-suite`

Quick integrity check against the REVIEW gate contract.

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
| `--output DIR` | No | Output directory (default: `./tests`) |

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

Run CHERENKOV's own internal self-test suite.

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

Opens at `http://localhost:8000` by default. Contains 9 screens:

- **Overview** — release readiness
- **Divergences** — severity-sorted findings
- **Explore** — endpoint browser
- **Author** — intent-driven test creation
- **Review Queue** — HITL approve/reject
- **Knowledge Explorer** — GraphRAG second brain
- **Device Manager** — connected device status
- **Chat Panel** — conversational QA agent
- **Health** — system health widget

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

### `enterprise`

Enterprise-tier commands (SSO, audit log, RBAC).

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
