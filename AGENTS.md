## Agent Operating Rules — CHERENKOV QA

**SSOT is `docs/` (v3.1 + delta).** There is NO v3.1 + delta, v3.1 + delta, or "v3.1 + delta" — if cited, stop and re-read `docs/`. Track A is the validated core; Track B/C development is open (see Track Status).

**Authoritative handover:** [docs/HANDOVER.md](docs/HANDOVER.md). If `docs/INTEGRATION_HANDOVER_REPORT.md` is cited, it is fabricated — see banner at top of that file.

### Workflow Rules

1. Work on **feature branches**, reference an issue.
2. Show **RAW EVIDENCE** for every claim. Claims are not evidence.
3. Get **human review** before merging to `main`.
4. Code in `track-b-c-deferred/` may be re-integrated into the live tree (Track B/C development is open). Bring it in on a feature branch with tests; keep Track A's design invariants (D7, anti-lock-in, suggest-only, spec-derived) intact.

### Design Invariants (Deltas)

- **D7**: Never auto-edit test code. Validate and healing produce reports/suggestions only.
- **Anti-lock-in**: Tests must run without CHERENKOV (`eject` strips all imports).
- **Suggest-only healing**: Healing never auto-commits or auto-applies.
- **Spec-derived**: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions.

### Track Status

- **Track A** (API conformance testing): code BUILT, core invariants proven. The 5-QA user-validation gate is **no longer a development blocker** (owner decision, 2026-06-06) — agents may build across all tracks. The gate remains **unrun**: 0/5 real reviews in [docs/process/VALIDATION_EVIDENCE_LEDGER.md](docs/process/VALIDATION_EVIDENCE_LEDGER.md), and the prior "4/5 YES passed" claim was **fabricated** (untracked, anonymous evidence; see [docs/HANDOVER.md §5](docs/HANDOVER.md)). So: build freely, but **do not claim these tests are externally "validated" or "QA-approved"** until real evidence lands in the ledger. Removing the gate as a blocker is not the same as passing it.
- **Track B/C + Horizon 2** (visual, perf, dashboard, openclaw, mcp, federation, divergence, governance, copilot, etc.): **built + unit-tested, development open.** Still **not externally validated** — covered honestly in [docs/SCOPE_LEDGER.md](docs/SCOPE_LEDGER.md). Extend and re-integrate freely; just don't market any of it as shipped/validated to end users until the ledger reflects real QA evidence.

### Autonomous Fabric & Skills (Horizon 2 Extension)

As of June 2026, CHERENKOV adopts the following advanced orchestration patterns for autonomous agents:
5. **Skills Directory (`skills/`)**: Autonomous workflows MUST read stack-specific markdown instructions from `skills/` before executing complex tasks. This maintains the D7 invariant contextually.
6. **Agent Memory (`agent_memory/`)**: Agents crawling or testing MUST document their state, findings, and context in the `agent_memory/` markdown wiki to prevent AI amnesia and build compounding knowledge.
7. **Orchestration & Tooling Standards**: 
   - Use **PydanticAI** for all structured agent outputs and schema validation.
   - Use **DeepEval** for agent logic and trajectory evaluation.
   - Use **Logfire** for tracing autonomous reasoning.
   - Use **MiniGPT** (or equivalent Vision-Language models) for visual UI validation rather than relying solely on DOM scraping.
