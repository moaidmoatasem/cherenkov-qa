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

- **Track A** (API conformance testing): code BUILT, core invariants proven. **User-validation gate (5 QA demos) NOT PASSED** — this is the real blocker.
- **Track B/C** (visual, perf, RAG, compliance, jira, dashboard): code present in `track-b-c-deferred/` but **NOT shipped, NOT validated**. Built prematurely before the Track A validation gate. Do not extend until Track A validates. Roadmap order in [docs/HANDOVER.md §6.3](docs/HANDOVER.md).
