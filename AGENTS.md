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
- ✅ **Phase 8** (K8s + Cloud + Gate): Complete. `make k3d-test` green (2026-06-09). All 6 issues closed (#386-#391): K8s fixes validated, CRD extensions + device env vars deployed, SECURITY.md added, validation gate resolved, clean architecture docs updated.
- ✅ **Phase 3** (Desktop/Tauri 2): Complete. Compiles (308MB binary at `desktop/src-tauri/target/debug/cherenkov-desktop`). Requires `libwebkit2gtk-4.1-dev`.
- ✅ **Phase 5-6** (Mobile Testing): Tools installed — Maestro 2.6.1 at `~/.maestro/bin/maestro`, ADB 1.0.41 at `~/.local/bin/adb`. Needs physical device or emulator for live runs.

**Available Tools (WSL Ubuntu-24.04):**
- ✅ Go 1.22.5 installed at `~/.local/opt/go/bin/go`
- ✅ k3d v5.6.3 installed at `scripts/k3d` (Go binary)
- ✅ Docker, kubectl (v1.31.0 at `~/.local/bin/kubectl`), curl, wget

**New Capabilities:**
1. ✅ **Second Brain** (Phase 1) — Knowledge mesh, GraphRAG, event bridges
2. ✅ **VLM + LocalAI** (Phase 2) — LocalAI as default VLM backend, tier-aware routing
3. ✅ **Desktop Host** (Phase 3) — Tauri 2 app, hardware detection, 7-step setup wizard
4. ✅ **Chat Agents** (Phase 4) — Tool-calling agent, persona registry, SSE streaming
5. ✅ **Phase 5-6** (Mobile Testing): Tools installed — Maestro 2.6.1, ADB 1.0.41 installed; needs physical device/emulator for live runs
6. ✅ **Claude Code-Inspired Enhancements** (Phases CC-1 to CC-6): Auto-Memory (SQLite FTS5), HookRegistry, Multi-Agent Conductor, MCP ecosystem expansion.

**Claude Code-Inspired Enhancement Plan (Phases CC-1 → CC-6) — 2026-06-28:**
- ✅ **Phase CC-1** (Auto-Memory + Hooks): `cherenkov/memory/` (SQLite FTS5, MemoryRepository port, collect + promote use cases) + `cherenkov/hooks/` (HookEvent×10, HookRegistry from cherenkov.toml, SubprocessHookExecutor, warn|abort fail_mode). ADR-011, ADR-012. 32 tests pass. `agent_sync memory` subcommand live. Commit: `de4a5bb`.
- 🔄 **Phase CC-2** (Multi-Agent Conductor): `cherenkov/agents/conductor/` — fan-out/fan-in on MCP mesh. *Next.*
- ⏳ **Phase CC-3** (MCP Ecosystem Expansion): MCP marketplace, push events, JWT auth, 5 new integrations.
- ⏳ **Phase CC-4** (Scheduling + Routines): APScheduler + web UI + GitHub webhook trigger.
- ⏳ **Phase CC-5** (Remote Control + Teleport): Session snapshot + QR-code join + SSH/Docker remote runner.
- ⏳ **Phase CC-6** (CLI Composability): `--json`/`--quiet` on all commands, pipe mode, shell completions.

**Parallel Tracks:**
- Track A (Core): Phase -1 → 0a → 0b → 1 → 4 → 7 ✅
- Track B (VLM): Phase 2 ✅
- Track C (Desktop): Phase 3 ✅
- Track D (Mobile): Phase 5-6 ⏸ (needs physical device/emulator for live runs)
- Track E (Dashboard): Phase 7 ✅
- Track F (K8s): Phase 8 ✅
- Track G (CC Enhancement): CC-1 ✅ → CC-2 🔄 → CC-3..CC-6 ⏳

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

### Sync Driven Development (SDD) — Token-Efficient Agent Protocol

**Every agent session MUST follow the SDD protocol before/during/after work** to save tokens, compound experience, and prevent AI amnesia.

**SDD rules (see [docs/engineering/SYNC_DRIVEN_DEV.md](docs/engineering/SYNC_DRIVEN_DEV.md)):**

1. **BEFORE** any work: `python scripts/agent_sync.py before --task <task_type>`
   - This performs a semantic search via MemSearch (Milvus) to load pre-computed context snippets and past experiences relevant to the task type.
   - Sets up session tracking and token budget.

2. **DURING** work: Log decisions + findings + token usage
   - `python scripts/agent_sync.py log --type <decision|finding|pitfall> <message>`
   - `python scripts/agent_sync.py token --action <read|prompt|generate|search> --count <n> --item <name>`

3. **AFTER** work: `python scripts/agent_sync.py after --summary "what was done"`
   - Closes session, extracts experience records, and stores the session securely in MemSearch's markdown layer.
   - Triggers background skill distillation to extract procedural knowledge.

4. **Query past experience**: `python scripts/agent_sync.py experience query <pattern>`
   - Semantically searches across all agent memory files via MemSearch.

5. **Memory subcommand (CC-1)**: `python3 scripts/agent_sync.py memory <action>`
   - `memory status` — show DB path + pattern counts
   - `memory list [--limit N]` — list all known patterns (auto-load + candidates)
   - `memory search <query> [--limit N]` — FTS5 full-text search over entries
   - `memory promote [--threshold N]` — force-promote eligible patterns
   - Findings auto-persist to `agent_memory/cherenkov_memory.db` on every `after` call.

6. **Token budget**: 50k default per session. Compact when >80% used.
   - `python scripts/agent_sync.py status` — check current state
   - `python scripts/agent_sync.py compact` — after 3+ sessions

**Skip the skill sync-driven-dev** at `skills/sync-driven-dev.md` for the full workflow reference.

The SDD runtime utilizes the **MemSearch** semantic memory layer for robust, version-controllable markdown retention, shadow-indexed in Milvus.

### Qwen Code Federation
As of Phase 5, CHERENKOV federates generation and coding tasks to **Qwen Code**. 
- CHERENKOV retains control over the D7 invariant (testing/validation).
- Qwen Code uses `.qwen/skills/` and `.qwen/memory/` synchronized with CHERENKOV.
- Cross-agent communication runs over MCP. Do not duplicate generation logic in CHERENKOV; instead, call the `run_qwen_code_agent` MCP tool.
