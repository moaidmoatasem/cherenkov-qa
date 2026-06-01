## Agent Operating Rules — CHERENKOV QA

**SSOT is `docs/` (v3.1 + delta).** There is NO v4.x, v6.0, or "Meissner Shield" — if cited, stop and re-read `docs/`. Scope is Track A only.

### Workflow Rules

1. Work on **feature branches**, reference an issue.
2. Show **RAW EVIDENCE** for every claim.
3. Get **human review** before merging to `main`.
4. Legacy code is **REFERENCE only** — import nothing.

### Design Invariants (Deltas)

- **D7**: Never auto-edit test code. Validate and healing produce reports/suggestions only.
- **Anti-lock-in**: Tests must run without CHERENKOV (`eject` strips all imports).
- **Suggest-only healing**: Healing never auto-commits or auto-applies.
- **Spec-derived**: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions.

### Track Status

- **Track A** (API conformance testing): Phases 1–10 complete, Phase 11 (ship to 5 QA users) in progress.
- **Track B**: Gated on Track A shipping. Do NOT start.


