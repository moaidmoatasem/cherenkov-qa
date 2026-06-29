---
title: CLI Reference
description: Complete reference for all CHERENKOV-QA CLI commands, flags, and options.
---

# CLI Reference

The CHERENKOV CLI is the primary interface for the platform.

## Global Options

These flags apply to every command:

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | | Output pure JSON for machine-readable use (CC-6) |
| `--quiet` | `-q` | Suppress non-error standard output |
| `--help` | `-h` | Show help for any command |
| `--version` | | Show CHERENKOV version |

---

## `validate`

Run conformance tests against a live server.

```bash
cherenkov validate --spec <file> --target <url>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | Path to OpenAPI `.yaml` or `.json` spec. Use `-` to read from stdin. |
| `--target URL` | Yes | Base URL of the server under test |
| `--fail-on-drift` | No | Exit with code `1` (or `2` for validation errors) if drift is detected |
| `--output DIR` | No | Write JUnit XML + SARIF to this directory |
| `--json` | No | Output results as JSON to stdout |

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | All tests pass, no drift |
| `1` | Drift detected (spec violation found) |
| `2` | Validation error (config, spec parse failure) |

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

---

## `generate`

Generate Playwright tests from a spec without executing them.

```bash
cherenkov generate --spec <file>
```

**Flags:**

| Flag | Required | Description |
|------|----------|-------------|
| `--spec FILE` | Yes | Path to OpenAPI spec |
| `--output DIR` | No | Output directory (default: `./tests`) |

**Example:**

```bash
cherenkov generate --spec api.yaml --output ./generated-tests
```

---

## `eject`

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

**Example:**

```bash
cherenkov eject --output ./my-tests
cd my-tests
npm install
npx playwright test
```

---

## `dashboard`

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

---

## `hitl`

Manage the Human-in-the-Loop review queue.

```bash
# List pending items
cherenkov hitl list

# Approve a verdict
cherenkov hitl approve <item-id>

# Reject a verdict with reason
cherenkov hitl reject <item-id> --reason "False positive"
```

---

## `knowledge`

Query the GraphRAG second brain.

```bash
# Query knowledge mesh
cherenkov knowledge query "What endpoints drift most often?"

# List stored idioms
cherenkov knowledge list --type idioms

# Add a custom idiom
cherenkov knowledge add --type idiom --content "Always check 404 on /pets/{petId}"
```

---

## `teleport`

Cross-device session management (Phase CC-5).

```bash
# Push current session to another device
cherenkov teleport push <session-id>

# Join a session from another device via token
cherenkov teleport pull <token>
```

---

## `routine`

Manage autonomous background routines (Phase CC-4).

```bash
# List active routines
cherenkov routine list

# Start a scheduled routine
cherenkov routine start drift-check --schedule "0 */6 * * *"

# Stop a routine
cherenkov routine stop <routine-id>
```

---

## `doctor`

Diagnose environment issues.

```bash
cherenkov doctor
```

Checks: Python version, Node, Playwright, Ollama, Docker, models pulled, config validity.

---

## `examples`

Show a gallery of common one-liners.

```bash
cherenkov examples
```

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
