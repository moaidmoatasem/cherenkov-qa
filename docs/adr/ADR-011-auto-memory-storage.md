# ADR-011: Auto-Memory Storage Backend

**Status:** Accepted
**Date:** 2026-06-28
**Deciders:** Owner (via Claude Code-Inspired Enhancement Plan approval)
**Supersedes:** None
**Related:** ADR-004 (Clean Architecture), ADR-006 (Knowledge Mesh)

---

## Context

The SDD protocol (`scripts/agent_sync.py`) accumulates agent learnings — findings,
decisions, pitfalls — across sessions using JSON flat-files
(`agent_memory/sync/context.json`, `experience.json`). This works at the
smallest scale but has three problems:

1. **No semantic retrieval**: `context.json` is loaded in full on every `before`
   call; there is no way to surface only the relevant past learnings for a new task.
2. **No auto-promotion**: Patterns that recur across sessions are not automatically
   elevated to "always load" status — a human must edit `context.json` manually.
3. **No query surface**: Agents cannot search accumulated memory without reading
   every JSON file — expensive and brittle.

The Phase 9 goal (PHASE_PLAN.md §"Phase 9") is to integrate MemSearch for
semantic memory. The CC-1 goal is to build the storage backbone that Phase 9
MemSearch will index on top of.

Claude Code's "auto-memory" — where the tool accumulates learnings like build
commands and debugging insights across sessions without the user writing anything
— is the inspiration.

## Decision

### Storage: SQLite with FTS5

Use an embedded SQLite database (`agent_memory/cherenkov_memory.db`) as the
primary memory store with an **FTS5 virtual table** for full-text search.

- **Reuses pattern from `cherenkov/ai/rag_index.py`** — no new technology.
- **Zero infra**: works offline, no Docker, no Redis, no Milvus required at L0.
- **FTS5** provides sub-millisecond keyword search over all accumulated entries.
- **Milvus/MemSearch** remains the optional Phase 9 upgrade path; the SQLite store
  implements the `MemoryRepository` port so the upgrade is a single adapter swap.

### Auto-Promotion Rule

A `MemoryPattern` is automatically promoted to "auto-load" (returned on every
`before` call without a query) when it has appeared in **≥3 distinct sessions**.
Threshold is configurable via `cherenkov.toml [memory] auto_promote_threshold = 3`.

### Module Layout (Clean Architecture, ADR-004)

```
cherenkov/memory/
├── domain/models.py          # MemoryEntry, MemoryPattern, PromotionRule
├── ports/repository.py       # MemoryRepository Protocol
├── adapters/sqlite_memory.py # FTS5-backed adapter (default)
├── use_cases/collect.py      # Auto-extract patterns from agent_sync findings
├── use_cases/promote.py      # Promote patterns after N sessions
└── api/routes.py             # /api/v1/memory/* REST + web widget data
```

### agent_sync.py Integration

The `after` command is extended to call `collect.py` synchronously, writing
any newly extracted patterns to the SQLite store. The `before` command adds
a second retrieval path: promoted patterns are prepended to context snippets.

## Alternatives Considered

**Redis as primary store**: rejected — adds mandatory infra dependency; SQLite
is the established CHERENKOV default (same as KnowledgeRepository, spec_guardian/store.py).

**Milvus/MemSearch as primary store**: rejected for CC-1 — MemSearch import is
already wrapped in `try/except` in agent_sync.py; Phase 9 is the right time to
make it primary. CC-1 builds the port so Phase 9 is a clean adapter swap.

**Extend context.json with indexes**: rejected — JSON files have no efficient
query path; FTS5 gives full-text search with the same zero-dependency footprint.

## Consequences

- `agent_memory/cherenkov_memory.db` is a new file (add to `.gitignore`).
- `cherenkov/memory/` follows ADR-004 Clean Architecture — domain never imports adapters.
- `MemoryRepository` port makes the Phase 9 MemSearch upgrade a 1-file change.
- `[memory]` section is added to the `cherenkov.toml` schema (validated in config_loader.py).
- D7 invariant unaffected: memory is for agent learnings, not test code.
