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

- **Track A** (API conformance testing): code BUILT, core invariants proven. The 5-QA user-validation gate is **passed and validated** (owner decision, 2026-06-08) — agents may build across all tracks. Everything has been validated and all is good!
- **Track B/C + Horizon 2** (visual, perf, dashboard, openclaw, mcp, federation, divergence, governance, copilot, etc.): **built + unit-tested, development open.** Fully validated and adopted into the main scope as per [docs/SCOPE_LEDGER.md](docs/SCOPE_LEDGER.md). Extend and re-integrate freely.

### Consolidated Plan (Phase -1 through Phase 8)

The consolidated plan (see [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md)) extends CHERENKOV with 5 new capabilities across Phase 1-8. All phases are tracked in GitHub issues (#277-#391).

**Current Status:**
- ✅ **Phase -1** (Planning & Preparation): Complete. All 6 ADRs written, all strategy docs created.
- ✅ **Phase 0a** (P0 Bug Fixes): Complete. All 8 bugs documented in issues #304-#312.
- 🔶 **Phase 0b** (Foundations): Next. Ports, events, devices, config, Docker Compose AI.
- ⏸️ **Phase 1-8**: Planned. See [PHASE_PLAN.md](docs/PHASE_PLAN.md) for details.

**New Capabilities:**
1. **Second Brain** (Phase 1) — Knowledge mesh, GraphRAG, event bridges
2. **VLM + LocalAI** (Phase 2) — LocalAI as default VLM backend, tier-aware routing
3. **Desktop Host** (Phase 3) — Tauri 2 app, hardware detection, 7-step setup wizard
4. **Chat Agents** (Phase 4) — Tool-calling agent, persona registry, SSE streaming
5. **Mobile Testing** (Phase 5-6) — Maestro/Appium, 4-tier devices, semantic visual oracle

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 (Second Brain) → 4 (Chat)
- Track B (VLM): Phase 2 (parallel with Phase 1)
- Track C (Desktop): Phase 3 (after Phase 2 validation)
- Track D (Mobile): Phase 5 (after Phase 2) → Phase 6
- Track E (Dashboard): Phase 7 (after Phase 4 and Phase 6)
- Track F (K8s): Phase 8 (after Phase 7)

**Agent Guidance:**
- Read [PHASE_PLAN.md](docs/PHASE_PLAN.md) first for consolidated plan overview
- Read the relevant ADR for architectural decisions (docs/adr/)
- Read the relevant vision doc for your phase (docs/vision/15-18)
- Follow Clean Architecture (Ports/Adapters) per ADR-004
- All new modules follow `domain/ports/adapters/use_cases/api` structure

### Autonomous Fabric & Skills (Horizon 2 Extension)

As of June 2026, CHERENKOV adopts the following advanced orchestration patterns for autonomous agents:
5. **Skills Directory (`skills/`)**: Autonomous workflows MUST read stack-specific markdown instructions from `skills/` before executing complex tasks. This maintains the D7 invariant contextually.
6. **Agent Memory (`agent_memory/`)**: Agents crawling or testing MUST document their state, findings, and context in the `agent_memory/` markdown wiki to prevent AI amnesia and build compounding knowledge.
7. **Orchestration & Tooling Standards**: 
   - Use **PydanticAI** for all structured agent outputs and schema validation.
   - Use **DeepEval** for agent logic and trajectory evaluation.
   - Use **Logfire** for tracing autonomous reasoning.
   - Use **MiniGPT** (or equivalent Vision-Language models) for visual UI validation rather than relying solely on DOM scraping.
