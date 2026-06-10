## Agent Operating Rules — CHERENKOV QA

**SSOT is `docs/` (v3.1 + delta).** There is NO "v3.1 + delta" — if cited, stop and re-read `docs/`. All tracks are open (see Track Status).

**Authoritative handover:** [docs/HANDOVER.md](docs/HANDOVER.md).

### Workflow Rules

1. Work on **feature branches**, reference an issue.
2. Show **RAW EVIDENCE** for every claim. Claims are not evidence.
3. Get **human review** before merging to `main`.
4. Code is in the live tree (track-b-c-deferred/ was fully re-integrated and deleted).

### Design Invariants (Deltas)

- **D7**: Never auto-edit test code. Validate and healing produce reports/suggestions only.
- **Anti-lock-in**: Tests must run without CHERENKOV (`eject` strips all imports).
- **Suggest-only healing**: Healing never auto-commits or auto-applies.
- **Spec-derived**: Expected HTTP status comes from the OpenAPI spec, not hardcoded assumptions.

### Track Status

- **Track A** (API conformance testing): code BUILT, core invariants proven. The 5-QA user-validation gate is **passed and validated** (owner decision, 2026-06-08) — agents may build across all tracks.
- **Track B/C + Horizon 2** (visual, perf, dashboard, openclaw, mcp, federation, divergence, governance, copilot, etc.): **built + unit-tested, development open.** Fully adopted into main scope. track-b-c-deferred/ deleted — all code in live tree.

### Consolidated Plan (Phase -1 through Phase 8)

The consolidated plan (see [docs/PHASE_PLAN.md](docs/PHASE_PLAN.md)) extends CHERENKOV with 5 new capabilities across Phase 1-8. All phases are tracked in GitHub issues (#277-#391).

**Current Status:**
- ✅ **Phase -1** (Planning & Preparation): Complete. All 6 ADRs written, all strategy docs created.
- ✅ **Phase 0a** (P0 Bug Fixes): Complete. All 8 bugs fixed (#304-#312).
- ✅ **Phase 0b** (Foundations): Complete. Ports, events, devices, config (#313-#327).
- ✅ **Phase 1** (Second Brain): Complete. Knowledge mesh, GraphRAG, event bridges (#328-#337).
- ✅ **Phase 2** (VLM + LocalAI): Complete. LocalAI default, tier routing, doctor CLI (#339-#344).
- ✅ **Phase 4** (Chat Agent): Complete. Tool-calling agent, persona registry, SSE streaming (#354-#361).
- ✅ **Phase 7** (Dashboard): Complete. All 9 screens: DeviceManager, KnowledgeExplorer, HealthWidget, MobileScreen, ChatPanel, wire-up, MockBadges, Pilot Run, Toast (#377-#385).
- 🔶 **Phase 8** (K8s + Cloud + Gate): In progress. SECURITY.md added (#389). Remaining items: #386-#388 (CRD sync + device env vars — code done, needs `make k3d-test`), #390 (gate — resolved per owner decision), #391 (docs — SYSTEM_DESIGN.md + BEST_PRACTICES.md updated).
- ⏸️ **Phase 3** (Desktop/Tauri 2): Blocked — needs `cargo` on this machine.
- ⏸️ **Phase 5-6** (Mobile Testing): Blocked — needs ADB/Maestro on this machine.

**Available Tools (WSL Ubuntu-24.04):**
- ✅ Go 1.22.5 installed at `~/.local/opt/go/bin/go`
- ✅ k3d v5.6.3 installed at `~/.local/bin/k3d`
- ✅ Docker, kubectl, curl, wget available

**New Capabilities:**
1. ✅ **Second Brain** (Phase 1) — Knowledge mesh, GraphRAG, event bridges
2. ✅ **VLM + LocalAI** (Phase 2) — LocalAI as default VLM backend, tier-aware routing
3. ⏸️ **Desktop Host** (Phase 3) — Tauri 2 app, hardware detection, 7-step setup wizard
4. ✅ **Chat Agents** (Phase 4) — Tool-calling agent, persona registry, SSE streaming
5. ⏸️ **Mobile Testing** (Phase 5-6) — Maestro/Appium, 4-tier devices, semantic visual oracle

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 → 4 → 7 ✅
- Track B (VLM): Phase 2 ✅
- Track C (Desktop): Phase 3 ⏸ (needs cargo)
- Track D (Mobile): Phase 5-6 ⏸ (needs ADB)
- Track E (Dashboard): Phase 7 ✅
- Track F (K8s): Phase 8 🔶 (in progress)

**Extended Roadmap (Phases 9-16 — Product & Market Expansion):**
- See [docs/PRODUCT_STRATEGY_ROADMAP.md](docs/PRODUCT_STRATEGY_ROADMAP.md) for Phases 9-16: market launch, enterprise tier, fine-tuned model, 10-year vision, revenue model.
- See [docs/INTEGRATION_STRATEGY.md](docs/INTEGRATION_STRATEGY.md) for the 25-integration delivery plan (VS Code, GitHub Actions, Slack, Teams, Jira, Xray, Zephyr, GraphQL, gRPC, and more) across 6 sprints.

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
