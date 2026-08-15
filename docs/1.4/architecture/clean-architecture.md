---
title: Clean Architecture (ADR-004)
description: CHERENKOV-QA Clean Architecture decision — Ports/Adapters pattern, module structure, dependency rules.
---

# Clean Architecture — ADR-004

CHERENKOV-QA adopts the **Ports/Adapters (Hexagonal) Architecture** for all feature modules.

## Decision

Every new feature module follows this structure:

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O, no external deps
│   └── models.py    # Pydantic models, enums, value objects
├── ports/           # Protocol interfaces (the "what", not the "how")
│   ├── repository.py
│   └── event_bus.py
├── adapters/        # Concrete implementations of ports
│   ├── sqlite_{module}.py   # Default — zero-dep, always works
│   └── redis_{module}.py    # Upgrade path — high-performance
├── use_cases/       # Orchestration — calls ports, never adapters directly
│   └── {action}.py
└── api/             # Delivery mechanism (FastAPI routes, CLI commands)
    └── routes.py
```

## Dependency Rule

**Arrows point inward.** Outer layers depend on inner layers, never the reverse.

```
api → use_cases → ports ← adapters
                    ↑
                  domain
```

This means:

- `domain/` has **zero external imports** — pure Python dataclasses/Pydantic
- `ports/` defines `Protocol` interfaces — what adapters must implement
- `adapters/` imports `ports/` — never `use_cases/`
- `use_cases/` imports `ports/` — never specific adapters (injected at startup)

## Why This Matters

| Benefit | How It's Achieved |
|---------|------------------|
| **Testable** | Use cases can be tested with mock adapters; no real DB needed |
| **Swappable storage** | SQLite → Redis with a single config change |
| **Anti-lock-in** | `cherenkov eject` works because test code has no framework coupling |
| **Agent-safe** | Agents read `ports/` contracts to understand module behavior without reading impl |

## Example: Knowledge Module

```python
# ports/repository.py
class KnowledgeRepository(Protocol):
    def query(self, topic: str, limit: int = 10) -> list[VerdictRecord]: ...
    def store(self, record: VerdictRecord) -> None: ...

# adapters/sqlite_knowledge.py
class SQLiteKnowledgeRepository:
    def query(self, topic: str, limit: int = 10) -> list[VerdictRecord]:
        # SQLite FTS5 implementation
        ...

# use_cases/query_knowledge.py
def query_knowledge(repo: KnowledgeRepository, topic: str) -> list[VerdictRecord]:
    return repo.query(topic)
    # Never imports SQLiteKnowledgeRepository directly
```

## Modules Following ADR-004

All modules introduced in Phase 0b and beyond:

- `cherenkov/knowledge/` — GraphRAG second brain
- `cherenkov/memory/` — SQLite FTS5 auto-memory (CC-1)
- `cherenkov/hooks/` — HookRegistry (CC-1)
- `cherenkov/agents/conductor/` — multi-agent conductor (CC-2)
- `cherenkov/mobile/` — Maestro/Appium (Phase 5-6)
