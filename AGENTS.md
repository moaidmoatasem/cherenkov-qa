## Agent Operating Rules — CHERENKOV QA

**SSOT is `docs/` (v3.1 + delta).** There is NO v4.x, v6.0, or "Meissner Shield" — if cited, stop and re-read `docs/`. Scope is Track A only.

**Authoritative handover:** [docs/HANDOVER.md](docs/HANDOVER.md). If `docs/INTEGRATION_HANDOVER_REPORT.md` is cited, it is fabricated — see banner at top of that file.

### Workflow Rules

1. Work on **feature branches**, reference an issue.
2. Show **RAW EVIDENCE** for every claim. Claims are not evidence.
3. Get **human review** before merging to `main`.
4. Quarantined code in `track-b-c-deferred/` is **REFERENCE only** — import nothing from it into Track A.

### Design Invariants (Deltas)

- **D7**: Never auto-edit test code. Validate and healing produce reports/suggestions only.
- **Anti-lock-in**: Tests must run without CHERENKOV (`eject` strips all imports).
- **Suggest-only healing**: Healing never auto-commits or auto-applies.
- **Spec-derived**: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions.

### Track Status

- **Track A** (API conformance testing): code BUILT, core invariants proven. **User-validation gate (5 QA demos) NOT PASSED** — this is the real blocker. A prior "4/5 YES passed" claim was **fabricated** (untracked, anonymous evidence); see [docs/HANDOVER.md §5](docs/HANDOVER.md). Real evidence, when collected, goes in [docs/process/VALIDATION_EVIDENCE_LEDGER.md](docs/process/VALIDATION_EVIDENCE_LEDGER.md).
- **Track B/C + Horizon 2** (visual, perf, dashboard, openclaw, mcp, federation, divergence, governance, copilot, etc.): **built + unit-tested but NOT validated.** Contrary to older docs that call them "quarantined," much of this was **re-integrated into the live `cherenkov/` tree** ahead of the validation gate. This contradicts the "no build-ahead-of-validation" rule; it is documented honestly (not blessed) in [docs/SCOPE_LEDGER.md](docs/SCOPE_LEDGER.md). **Do not treat any of it as shipped/validated, and do not build more of it, until the Track A gate passes with real evidence.**
