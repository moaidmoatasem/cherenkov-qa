# Architecture Decision Records

Formal log of design choices. `AGENTS.md` asks agents to read the relevant ADR before
architectural work; this index is the entry point `docs/INDEX.md` links to.

| ADR | Decision |
|---|---|
| [ADR-001](ADR-001-seam-widening.md) | Seam-Widening Architecture |
| [ADR-002](ADR-002-tauri2-sidecar.md) | Tauri 2 + PyInstaller Sidecar Desktop |
| [ADR-003](ADR-003-localai-default.md) | LocalAI as Default LLM Backend |
| [ADR-004](ADR-004-clean-architecture.md) | Clean Architecture (Ports/Adapters) |
| [ADR-005](ADR-005-event-driven.md) | Event-Driven Architecture (asyncio.Queue → Redis Streams) |
| [ADR-006](ADR-006-knowledge-mesh.md) | Knowledge Mesh (Unified Query, Separate Stores) |
| [ADR-007](ADR-007-qa-reasoning-engine.md) | QA Reasoning Engine — artifact-adaptive QA workflows |
| [ADR-008](ADR-008-multi-agent-mcp-mesh.md) | Multi-Agent MCP Mesh |
| [ADR-009](ADR-009-spec-guardian-daemon.md) | Spec Guardian Daemon |
| [ADR-010](ADR-010-bench-eval-quality-gate.md) | Benchmark command and eval quality gate |
| [ADR-011](ADR-011-auto-memory-storage.md) | Auto-Memory Storage Backend |
| [ADR-012](ADR-012-hook-execution-model.md) | Hook Execution Model |
| [ADR-013](ADR-013-agent-conductor-protocol.md) | Agent Conductor Protocol |
| [ADR-014](ADR-014-spec-derived-probe-planner.md) | Spec-Derived Probe Planner (offline hypothesis synthesis) |
| [ADR-015](ADR-015-per-process-limiter.md) | Per-Process Concurrency Limiter |
