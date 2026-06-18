# CHERENKOV Design Invariants — Qwen Code MUST Respect These

## D7 — Never Auto-Edit Test Code
**Rule**: Validation and healing produce reports/suggestions ONLY. Never auto-commit, auto-apply, or auto-edit test files.
**In Qwen Code**: Always use `approvalMode: manual`. Never run `/edit` on files under `tests/`.
**Enforcement**: If a task touches test files, switch to `/review` mode and produce a diff suggestion only.

## Anti-Lock-In
**Rule**: Tests must run without CHERENKOV (`eject` strips all CHERENKOV imports).
**In Qwen Code**: Never add `from cherenkov import ...` in generated test files. Generated tests must be portable.

## Suggest-Only Healing
**Rule**: Healing never auto-commits or auto-applies.
**In Qwen Code**: When suggesting fixes from `get_tightening_suggestions` or `explain_finding`, output a diff block — do NOT `git commit` or apply patches autonomously.

## Spec-Derived Expected Values
**Rule**: Expected HTTP status codes come from the OpenAPI spec, not hardcoded assumptions.
**In Qwen Code**: When generating tests, always call `run_conformance_check` or `get_last_report` first to get spec-derived expected values.

## Clean Architecture Boundaries (ADR-004)
**Rule**: No cross-layer imports. Domain never knows about adapters.
**In Qwen Code**: When writing new modules, place them in the correct layer. If unsure, ask — do not guess.

## MCP Tool Safety
**Rule**: MCP peers are untrusted. All tool arguments validated with Pydantic.
**In Qwen Code**: When wrapping CHERENKOV tools, pass structured arguments. Never interpolate raw user strings into tool calls.

## CI Safety
**Rule**: Qwen Code runs read-only in CI (report-only mode).
**In Qwen Code headless mode in CI**: Only call `get_last_report`, `list_drift_findings`, `validate_run_gate` (report-only). Never `run_conformance_check` in CI without explicit human approval.
