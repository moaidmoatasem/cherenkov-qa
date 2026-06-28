# CHERENKOV: Claude Code-Inspired Enhancement Plan

**Date:** 2026-06-28
**Horizon:** 3–6 months (6 phases)
**Inspiration:** https://code.claude.com/docs/en/overview
**Status:** Draft — pending owner review

---

## Executive Summary

Claude Code's multi-surface architecture, auto-memory, hooks, sub-agents, MCP ecosystem,
scheduling, and CLI composability offer a mature reference for CHERENKOV's next evolution.
This plan adapts those concepts into 6 phases that extend CHERENKOV's existing SDD,
MCP, agent, and event infrastructure.

| Area | Claude Code Feature | CHERENKOV Gap | Phase |
|------|-------------------|----------------|-------|
| Memory | CLAUDE.md + Auto-memory | SDD context is manual + file-based; no auto-compounding | **1** |
| Automation | Hooks (pre/post action) | No pre/post action hooks for edit/test/lint chains | **1** |
| Parallelism | Sub-agents | PilotAgent exists but no multi-agent orchestration | **2** |
| Ecosystem | MCP integrations | 21 MCP tools exist; no marketplace, no push, no auth | **3** |
| Recurrence | Routines + Scheduling | `daemon trigger_loop` exists but no cron UI, no web triggers | **4** |
| Continuity | Remote Control + Teleport | No cross-device session persistence | **5** |
| Composability | Unix pipe, CI scripting | `cherenkov.py` argparse CLI exists but no pipe-friendly mode | **6** |

---

## Phase 1 — Auto-Memory + Hooks (Weeks 1–4)

**Goal:** Extend SDD with persistent, auto-compounding memory and pre/post action hooks.

### 1.1 Auto-Memory Engine

Extend `scripts/agent_sync.py` with a background memory layer that automatically
captures and surfaces learnings across sessions — inspired by Claude Code's auto-memory.

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Auto-memory collector | Hook into `agent_sync after` to auto-extract patterns from findings | 2d |
| Context promotion | When same pattern appears in 3+ sessions, promote to auto-load in `context.json` | 1d |
| Memory persistence | Replace JSON file store with SQLite FTS5 (reuse `cherenkov/ai/rag_index.py`) | 3d |
| Semantic context retrieval | Integrate MemSearch (Milvus) for vector search — already stubbed in agent_sync.py | 2d |
| Auto-memory CLI | `cherenkov memory list/promote/archive/search` | 2d |
| Memory dashboard widget | Web UI: show recent auto-memories, session history, token savings | 3d |

**Total:** ~13 days

### 1.2 Hook System

Pre/post action hooks that run shell commands before/after key CHERENKOV actions.

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Hook registry | `cherenkov/hooks/` — `registry.py`, `models.py`, `executor.py` | 2d |
| Hook events | Define hook points: `pre_edit`, `post_edit`, `pre_test`, `post_test`, `pre_commit` | 1d |
| Hook execution | Sync/async shell command runner with timeout, env injection, failure policy | 2d |
| Config in cherenkov.toml | `[hooks.pre_test]`, `[hooks.post_edit]` — commands, timeout, fail_mode | 1d |
| Hook CLI | `cherenkov hooks list/run/test/log` | 2d |
| MCP hook integration | Expose hooks as MCP resources for external agents | 1d |

**Total:** ~9 days

**Phase 1 total:** ~22 days (4 weeks)

---

## Phase 2 — Multi-Agent Orchestration (Weeks 5–8)

**Goal:** Enable parallel agent teams coordinated by a lead agent — Claude Code's sub-agents.

### 2.1 Agent Conductor

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Conductor port | `cherenkov/ports/agent_conductor.py` — Protocol for orchestrating sub-agents | 1d |
| Conductor impl | `cherenkov/agents/conductor.py` — Lead agent: decompose task, assign, merge | 4d |
| Sub-agent protocol | `cherenkov/agents/sub_agent.py` — `SubAgent` protocol with `run(fn, ctx) -> Result` | 2d |
| Task decomposition | Strategy: parallel-by-file, sequential-by-step, fan-out-fan-in | 2d |
| Result aggregation | Merge strategies: union (tests), consensus (reviews), weighted (confidence) | 2d |
| Session isolation | Each sub-agent gets its own SDD session with shared context | 1d |

**Total:** ~12 days

### 2.2 Agent Team Templates

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Review team | Lead + 3 sub-agents: style, security, correctness — each reviews independently, merge | 2d |
| Test generation team | Lead splits spec into modules, sub-agents generate in parallel, lead merges | 2d |
| Healing team | Lead assigns divergent routes, sub-agents diagnose in parallel, lead recommends | 2d |
| Audit team | Sub-agents each validate different spec sections, lead aggregates findings | 1d |

**Total:** ~7 days

### 2.3 Agent Dashboard

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Real-time agent view | SSE stream per sub-agent: current action, tokens used, findings | 3d |
| Agent timeline | Gantt-like view of sub-agent execution, dependencies, merge points | 2d |
| Cost breakdown | Per-agent token tracking, latency, value score | 1d |

**Total:** ~6 days

**Phase 2 total:** ~25 days (4 weeks)

---

## Phase 3 — MCP Ecosystem Expansion (Weeks 9–12)

**Goal:** Turn CHERENKOV's MCP layer into a full ecosystem with marketplace, push
notifications, auth, and expanded integrations.

### 3.1 MCP Marketplace

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Tool registry | Discoverable registry of tool packages via `cherenkov mcp discover` | 2d |
| Tool install/remove | `cherenkov mcp install <server>` — download, verify, register | 2d |
| Tool versioning | Semantic version tracking, compatibility checks | 2d |
| Tool sandbox | Docker-based sandbox execution for 3rd-party tools | 3d |

**Total:** ~9 days

### 3.2 MCP Push + Events

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Resource push | Server-initiated resource updates (diff notification, test results) | 2d |
| Event routing | Route `CHERENKOVEvent` to subscribed MCP clients | 2d |
| MCP ↔ Event bus bridge | `cherenkov/events/mcp_bridge.py` — publish events as MCP notifications | 1d |

**Total:** ~5 days

### 3.3 New Integrations (Top 5)

| Integration | Implementation | Effort |
|-------------|---------------|--------|
| **Slack MCP** — Interactive Messages | Beyond webhook: Block Kit with buttons, threaded conversations | 3d |
| **GitHub MCP** — Webhook-driven | Subscribe to PR events, auto-review on opened/synchronize | 3d |
| **Jira MCP** — Bi-directional | Beyond export: read tickets, update status, attach evidence | 3d |
| **Teams MCP** — Adaptive Cards | Rich interactive cards with action confirm/reject | 2d |
| **Webhook MCP** — Generic | UI for configuring webhook endpoints with retry/backoff | 2d |

**Total:** ~13 days

### 3.4 MCP Auth + Security

| Feature | Implementation | Effort |
|---------|---------------|--------|
| MCP auth layer | API key + JWT authentication for MCP endpoints | 2d |
| Policy enforcement | `cherenkov/mcp/policy.py` — rate limits, scope restrictions | 1d |
| Audit logging | Log all MCP tool calls with params, duration, caller | 1d |

**Total:** ~4 days

**Phase 3 total:** ~31 days (4 weeks)

---

## Phase 4 — Scheduling + Routines (Weeks 13–16)

**Goal:** Add cron-like scheduling, web-based routine management, and trigger-from-event.

### 4.1 Scheduler Core

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Schedule port | `cherenkov/ports/scheduler.py` — Protocol for scheduling tasks | 1d |
| APScheduler integration | `cherenkov/adapters/apscheduler_adapter.py` — cron/interval/date triggers | 3d |
| Schedule storage | SQLite schedule store (reuse KnowledgeRepository pattern) | 2d |
| Schedule model | `cherenkov/scheduling/domain/models.py` — `Schedule`, `Routine`, `Trigger` | 1d |

**Total:** ~7 days

### 4.2 Routine Templates

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Daily health check | Run `cherenkov validate` every morning, notify Slack on failures | 2d |
| Weekly regression | Run full test suite, diff against last week, report drift trends | 2d |
| PR-auto-review | On GitHub webhook: auto-review PR, post findings, approve/request-changes | 3d |
| Dependency audit | Weekly `pip-audit` / `npm audit`, file GH issues for critical | 2d |
| Spec-monitor | Watch OpenAPI spec URL, auto-trigger validation on change | 1d |

**Total:** ~10 days

### 4.3 Routine Dashboard + CLI

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Routine CLI | `cherenkov routine create/list/edit/delete/toggle/logs` | 3d |
| Routine web UI | Calendar view, enable/disable toggle, last-run status | 3d |
| Notification on completion | Hook into notifier registry for routine results | 1d |
| Routine history | Persistent logs of each routine run: status, duration, findings | 2d |

**Total:** ~9 days

### 4.4 Event-Driven Triggers

| Feature | Implementation | Effort |
|---------|---------------|--------|
| GitHub webhook endpoint | `POST /api/v1/webhooks/github` — parse event, trigger routine | 2d |
| GitLab CI bridge | `.gitlab-ci-template.yml` → trigger CHERENKOV routine | 1d |
| Cron expression UI | Friendly cron builder (hourly, daily, weekdays, custom `*/15 * * * *`) | 2d |

**Total:** ~5 days

**Phase 4 total:** ~31 days (4 weeks)

---

## Phase 5 — Remote Control + Teleport (Weeks 17–20)

**Goal:** Cross-device session continuity — start on desktop, continue from phone,
resume in CI.

### 5.1 Session State Serialization

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Session snapshot | Serialize full session state (findings, context, tokens, history) to JSON | 2d |
| Session store | SQLite session store with `session_id` primary key | 2d |
| Session resume | `cherenkov session resume <id>` — restore context, findings, token budget | 3d |
| Session list/search | `cherenkov session list/search/diff` | 1d |

**Total:** ~8 days

### 5.2 Teleport Protocol

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Teleport MCP tools | `teleport_push`, `teleport_pull`, `teleport_list` — session transfer | 3d |
| Teleport CLI | `cherenkov teleport push/pull/list/status` | 2d |
| Teleport web UI | QR code → join session from browser/phone | 3d |
| Session handoff token | Short-lived token (5 min) for secure cross-device handoff | 1d |

**Total:** ~9 days

### 5.3 Remote Agent Runner

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Remote runner port | `cherenkov/ports/remote_runner.py` — Protocol for remote execution | 1d |
| SSH adapter | `cherenkov/adapters/ssh_runner.py` — Run on remote machines | 3d |
| Docker adapter | `cherenkov/adapters/docker_runner.py` — Run in containers | 2d |
| Cloud runner | `cherenkov/adapters/cloud_runner.py` — ephemeral cloud VM (GCP/AWS) | 4d |

**Total:** ~10 days

### 5.4 Cross-Device Dashboard

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Mobile session UI | React-responsive: continue session from phone (Claude iOS-like) | 3d |
| Session timeline | Shared session timeline visible from any device | 2d |
| Push notifications | Slack/Teams push on session completion, failure, or HITL wait | 1d |

**Total:** ~6 days

**Phase 5 total:** ~33 days (4 weeks)

---

## Phase 6 — CLI Composability + Polish (Weeks 21–24)

**Goal:** Make CHERENKOV a first-class Unix citizen — pipe-friendly, CI-native,
scriptable, with a clean DX.

### 6.1 Pipe-Friendly Mode

| Feature | Implementation | Effort |
|---------|---------------|--------|
| `--json` output flag | All CLI commands support `--json` for programmatic consumption | 3d |
| `--quiet` mode | Suppress all non-output text (spinners, progress bars, logos) | 2d |
| Accept stdin pipe | `cat spec.yaml \| cherenkov validate -` — read spec from pipe | 2d |
| Write to file | `--output <path>` for all commands that produce artifacts | 1d |

**Total:** ~8 days

### 6.2 Exit Codes + Error Protocol

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Standard exit codes | 0=pass, 1=fail, 2=no-tests, 3=error, 4=timeout | 1d |
| Structured error JSON | `--json` mode outputs `{"status": "error", "code": 3, "message": "..."}` | 2d |
| Error classification | `errors.py` extensions for all CLI errors (validation, network, auth, rate-limit) | 2d |

**Total:** ~5 days

### 6.3 CI/CD Enhancements

| Feature | Implementation | Effort |
|---------|---------------|--------|
| GitHub Action v2 | Reusable action with all flags exposed, JSON output, artifacts | 3d |
| GitLab CI template v2 | `include` template with parallel jobs, caching | 2d |
| CircleCI orb v2 | Orb with reusable executors, commands, jobs | 2d |
| Makefile integration | `make validate`, `make diff`, `make report` targets | 1d |

**Total:** ~8 days

### 6.4 Developer Experience

| Feature | Implementation | Effort |
|---------|---------------|--------|
| `--progress` modes | auto|bar|dot|none — progress indication styles | 2d |
| Shell completions | bash/zsh/fish completions via `argcomplete` (already exists for legacy CLI) | 1d |
| Color modes | auto|always|never — respect `NO_COLOR` and `CI` env | 1d |
| Man page | `man cherenkov` via help2man from `--help-all` | 1d |
| `--version --verbose` | Detailed version info, build hash, deps | 1d |

**Total:** ~6 days

### 6.5 Documentation Generator

| Feature | Implementation | Effort |
|---------|---------------|--------|
| Auto-generate CLI docs | From Click help text → markdown reference docs | 2d |
| Example library | `cherenkov examples` — gallery of common one-liners | 2d |
| Quickstart overhaul | 5-minute walkthrough: install → one test → CI integration | 2d |

**Total:** ~6 days

**Phase 6 total:** ~33 days (4 weeks)

---

## Resource Summary

| Phase | Focus | Days | Months |
|-------|-------|------|--------|
| **1** | Auto-Memory + Hooks | 22 | 1 |
| **2** | Multi-Agent Orchestration | 25 | 1 |
| **3** | MCP Ecosystem Expansion | 31 | 1 |
| **4** | Scheduling + Routines | 31 | 1 |
| **5** | Remote Control + Teleport | 33 | 1.3 |
| **6** | CLI Composability + Polish | 33 | 1.3 |
| **Total** | | **175** | **~7** |

With 2–3 parallel workers: ~3–4 months wall clock.

---

## Architecture Decisions

### ADR-007: Auto-Memory Storage
- **Choice:** SQLite FTS5 (reuse `cherenkov/ai/rag_index.py`)
- **Rejected:** Redis (adds dep), Milvus-only (too heavy for local), JSON (no querying)
- **Rationale:** Zero infra, FTS5 enables semantic search, same DB as Knowledge Repository
- **Fallback:** MemSearch (Milvus) for cloud deployments, SQLite for local

### ADR-008: Hook Execution Model
- **Choice:** Subprocess with timeout, configured in `cherenkov.toml`
- **Rejected:** Async Python functions (too coupled), Webhook (too heavy)
- **Rationale:** Max flexibility — any language, any tool. Timeout prevents hung hooks.
- **Policy:** `fail_mode = "abort"` (default) or `"warn"` (continue on failure)

### ADR-009: Agent Conductor Protocol
- **Choice:** MCP-based sub-agent communication via `run_qwen_code_agent` tool
- **Rejected:** Direct PydanticAI calls (MCP already proven), Redis pub/sub (overkill)
- **Rationale:** Reuse existing MCP mesh infrastructure. Each sub-agent is a full MCP client.
- **Evidence:** Qwen Code federation already uses this pattern successfully.

### ADR-010: Scheduler Backend
- **Choice:** APScheduler with SQLite job store
- **Rejected:** Cron (no web UI), Celery (too heavy), Custom loop (re-inventing)
- **Rationale:** APScheduler is battle-tested, supports cron/interval/date triggers,
  SQLite store survives restart, no external deps.

### ADR-011: Teleport Protocol
- **Choice:** Session snapshot JSON + short-lived JWT token
- **Rejected:** WebSocket live streaming (over-engineered), Database-only (latency)
- **Rationale:** Snapshot is simple, portable, works offline. JWT provides 5-min window
  for secure handoff. No server needed for local → local.

### ADR-012: CLI Output Protocol
- **Choice:** JSON output on `--json`, stderr for diagnostics, exit codes per spec
- **Rejected:** Single output format (can't parse), Always-verbose (breaks piping)
- **Rationale:** Follows Claude Code's composability philosophy. `--quiet` + `--json`
  enables clean CI integration.

---

## Dependencies & Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| MemSearch/Milvus not available | Medium | Auto-memory degrades to file-based | Phase-1 mitigates: MemSearch is optional, SQLite is default |
| APScheduler version conflicts | Low | Schedule feature blocked | Pin to v3.x, test in CI with Python 3.10–3.12 |
| MCP marketplace adoption | Medium | Few 3rd-party tools | Focus on first-party tools in Phase 3; marketplace is additive |
| Cross-device session fidelity | Low-Medium | State corruption on resume | Version snapshots with migration, unit test every resume path |
| Parallel agent token costs | High | Budget explosion | Per-agent budget limits, lead agent monitors sub-agent spend |
| CLI breaking changes | Medium | Existing scripts break | Deprecation window: old flags warn for 2 releases before removal |

---

## Integration Points

| Phase | Integrates With | Test |
|-------|----------------|------|
| 1 | `scripts/agent_sync.py`, `cherenkov.toml`, `agent_memory/sync/` | `pytest tests/unit/test_agent_sync.py` |
| 1 | `cherenkov/web/api.py` (dashboard widget) | `npx playwright test tests/e2e/` |
| 2 | `cherenkov/mcp/`, `cherenkov/agents/`, `cherenkov/federation/` | `pytest tests/unit/test_agent_conductor.py` |
| 3 | `cherenkov/mcp/`, `.mcp.json`, `cherenkov/events/` | `pytest tests/unit/test_mcp_*.py` |
| 4 | `cherenkov/daemon/`, `cherenkov/web/`, `cherenkov/adapters/notifiers/` | `pytest tests/unit/test_scheduler.py` |
| 5 | `cherenkov/cli/`, `cherenkov/web/`, `cherenkov/mcp/` | `pytest tests/unit/test_teleport.py` |
| 6 | `cherenkov/cli/`, `pyproject.toml` | `pytest tests/unit/test_cli.py` |

---

## Success Criteria

| Phase | Gate |
|-------|------|
| **1** | `agent_sync before --task <type>` auto-loads SQLite memory; `git commit` triggers pre-commit test run |
| **2** | `cherenkov agent review --spec spec.yaml` spawns 3 sub-agents, merges results in <2 min |
| **3** | `cherenkov mcp discover` lists 10+ tools; Slack MCP allows interactive threaded review |
| **4** | `cherenkov routine create --every 6h "validate --target prod"` runs and notifies on failure |
| **5** | `cherenkov teleport push` on laptop → `cherenkov teleport pull` on phone → resume session |
| **6** | `cat spec.yaml | cherenkov validate --json > results.json` works with exit code 0 |

---

## Agent Guidance for Implementation

1. **Follow Clean Architecture** — domain/ports/adapters/use_cases/api per ADR-004
2. **SDD protocol** — `python scripts/agent_sync.py before --task <phase>` before each implementation session
3. **Tests first** — write failing test, then implement (D7 invariant applies to test editing)
4. **Update AGENTS.md** — add new capabilities to Track Status
5. **Update docs/PHASE_PLAN.md** — add new phases to the consolidated plan
6. **Show raw evidence** — terminal output, test results, not summaries
7. **Get human review** before merging to `main`

---

*See [docs/PHASE_PLAN.md](../../docs/PHASE_PLAN.md) for the existing consolidated plan.*
*See [docs/adr/](../../docs/adr/) for ADR-001 through ADR-006 architectural decisions.*
