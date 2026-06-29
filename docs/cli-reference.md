# CHERENKOV CLI Reference

This document provides a reference for the new Click-based CHERENKOV CLI.

## Global Options
- `--json`: Output pure JSON for machine readability (CC-6).
- `--quiet, -q`: Suppress non-error standard output (CC-6).

## Core Commands

### `validate`
Validate E2E test suite against a real server.
**Usage**: `cherenkov validate --target <URL> --spec <FILE>`
- Use `--spec -` to read from stdin.
- Add `--fail-on-drift` to exit with code `1` (or `2` for validation errors) if conformance fails.

### `generate`
Generate Playwright E2E tests from a spec without running them.

### `dashboard`
Launch the interactive web UI and MCP network conductor.

### `teleport`
Manage cross-device session teleportation (CC-5).
- `cherenkov teleport push <session_id>`
- `cherenkov teleport pull <token>`

### `routine`
Manage autonomous background routines (CC-4).
- `cherenkov routine list`

### `examples`
Show a gallery of common CHERENKOV one-liners.

> Note: All CLI interactions support shell completions. Install them using `eval "$(_CHERENKOV_COMPLETE=bash_source cherenkov)"`.
