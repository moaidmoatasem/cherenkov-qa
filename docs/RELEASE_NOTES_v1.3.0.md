# Release Notes: CHERENKOV-QA v1.3.0

**Date:** 2026-08-02
**Tag:** `v1.3.0`

## What's New Since v1.2.0

### Features

- **Spec Guardian CLI** (Phase 14): `cherenkov guardian start --spec <spec> --base-url <url>`
  polls every endpoint declared in the OpenAPI spec and persists drift events to the
  drift store until interrupted (SIGINT/SIGTERM). Override with repeatable
  `--endpoint METHOD:PATH`, tune with `--interval` and `--db`. The `SpecGuardianDaemon`
  previously had zero callers; this gives it its first real entry point (#811, #823).
- **Enterprise CLI wiring** (Phase 13): `cherenkov enterprise` commands now wire the real
  `cherenkov/enterprise/` modules — SAML 2.0/SSO configuration, RBAC role assignment,
  org management, audit-log export, and SOC2 compliance reports — instead of the
  `"""Placeholder"""` stubs (#810, #824).
- **MCP agent tools**: check-suite, verify, and generate are exposed as agent-invokable
  MCP tools for IDEs/autonomous agents (#812, #821).
- **MCP registry manifest**: `manifest.json` + publish instructions ready for submission
  to the official MCP registry (#792).
- **5-Workspace UI/UX revamp**: Overview, Author & Generate, Triage, Coverage &
  Certification, and Knowledge hubs; FastAPI backend wiring; Playwright E2E suite
  (2e66658). Cold-run onboarding now survives end-to-end.
- **Scope filters**: `validate` accepts a `--tests` filter and OpenAPI 3.0.x patch
  versions (#829).

### Fixed

- **FTS5 query refactor** (#832): query construction in
  `cherenkov/knowledge/adapters/sqlite_repository.py` and
  `cherenkov/memory/adapters/sqlite_memory.py` now joins on the FTS shadow-table
  `rowid` (avoiding a full-table scan) and escapes embedded quotes via a shared helper.
- **Generate persistence**: one distinct file per scenario (#828).
- **SDD runtime**: `agent_sync` MemSearch `workspace_dir` API mismatch repaired.
- **OpenAPI version accept**: validate accepts Swagger 2.0 and OpenAPI 3.0.x patch
  versions (#829).

### Certification

- **Main certified green**: 2064 passed / 2 failed. The 2 failures
  (`test_verify_cmd.py`, mock drift) are pre-existing and tracked as **#819** (D7 —
  agents do not modify tests). UI build verified: `vite` output matches committed dist.
- The malformed `v1.1.1` tag was corrected to `v1.1.1`. Future releases are cut through
  release-please to avoid repeat tag-name breakage.
