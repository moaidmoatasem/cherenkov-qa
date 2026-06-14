# ADR-004: Clean Architecture (Ports/Adapters)

**Date:** 2026-06-08
**Status:** Accepted
**Deciders:** Project Owner + AI Agents
**Related EPIC:** #277 (Phase -1), #279 (Phase 0b)

---

## Context

The consolidated plan adds 5 new capabilities (Second Brain, Chat, Mobile, Desktop, VLM). Each needs storage, event handling, and API access. Without a clear architecture, we risk:
- Duplication (each module has its own patterns)
- Tight coupling (modules depend on each other's internals)
- Hard to test (I/O mixed with business logic)
- Hard to extend (new features require core changes)

Options considered:
1. **Clean Architecture** (Ports/Adapters / Hexagonal Architecture)
2. **Layered Architecture** (Presentation → Business → Data)
3. **Microservices** (separate services for each module)

## Decision

**Clean Architecture (Ports/Adapters / Hexagonal Architecture)**: Every new feature module follows:

```
cherenkov/{module}/
├── domain/          # Pure business logic, no I/O, no external deps
│   └── models.py    # Pydantic models, enums, value objects
├── ports/           # Protocol interfaces (the "what", not the "how")
│   ├── repository.py
│   └── event_bus.py
├── adapters/        # I/O implementations
│   ├── sqlite_{module}.py   # Default adapter
│   └── redis_{module}.py     # Upgrade adapter
├── use_cases/       # Orchestration of domain + ports
│   └── {action}.py
└── api/             # Thin FastAPI routes / CLI commands
    └── routes.py
```

### Rationale

1. **Contribution-readiness**: New contributor can add an adapter in <30 minutes
2. **Testability**: Domain logic tested without I/O (mock ports)
3. **Swap-in replacements**: SQLite → Redis → PostgreSQL without domain changes
4. **Bounded contexts**: knowledge/, chat/, substrate/, mobile/ are separate bounded contexts
5. **Dependency inversion**: Domain depends on abstractions (ports), not implementations (adapters)

### Design Patterns Per Module

| Module | Primary Pattern | Secondary Pattern | Fallback Chain |
|--------|----------------|-------------------|-----------------|
| Second Brain | Repository | Event Observer | SQLite → Redis |
| VLM Substrate | Strategy | Circuit Breaker | LocalAI → Ollama → Demo |
| Chat Agent | Tool-Calling | CQRS-lite | In-memory → Redis |
| Desktop Host | Sidecar IPC | Observer | VLM auto-detect → Manual |
| Mobile Sources | Adapter | Factory | Maestro → Appium → Pixel Diff |
| Event Bus | Observer | Fan-out | asyncio.Queue → Redis Streams |

### Example: Knowledge Repository

**Domain (pure business logic):**
```python
# cherenkov/knowledge/domain/models.py
@dataclass
class KnowledgeQuery:
    query: str
    source: str | None = None
    limit: int = 10

@dataclass
class KnowledgeResult:
    data: Any
    source: str
    confidence: float
    metadata: dict[str, Any]
```

**Ports (Protocol interfaces):**
```python
# cherenkov/knowledge/ports/repository.py
class KnowledgeRepository(Protocol):
    def query(self, query: KnowledgeQuery) -> KnowledgeResult: ...
    def store(self, item: KnowledgeItem) -> str: ...
    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeResult]: ...
```

**Adapters (I/O implementations):**
```python
# cherenkov/knowledge/adapters/sqlite_repository.py
class SQLiteKnowledgeRepository:
    def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        # SQLite implementation
        pass

# cherenkov/knowledge/adapters/redis_repository.py
class RedisKnowledgeRepository:
    def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        # Redis implementation with vector search
        pass
```

**Use Cases (orchestration):**
```python
# cherenkov/knowledge/use_cases/query.py
def query_knowledge(repo: KnowledgeRepository, query: str) -> KnowledgeResult:
    """Query knowledge repository."""
    knowledge_query = KnowledgeQuery(query=query)
    return repo.query(knowledge_query)
```

**API (thin FastAPI routes):**
```python
# cherenkov/knowledge/api/routes.py
@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None):
    repo = get_knowledge_repository()
    result = query_knowledge(repo, q)
    return result.to_dict()
```

### Dependency Rules

```
domain/ ← ports/ ← adapters/ ← use_cases/ ← api/
  ↑         ↑          ↑            ↑          ↑
  │         │          │            │          │
  Pure      Protocol   I/O          Orchest-   FastAPI
  business  interfaces impl         ration     routes
  logic     (the       (the         (combines  (thin
            "what")    "how")       domain +   wrappers)
                                    ports)
```

**Key rule**: Arrows point inward. Outer layers depend on inner layers, never the reverse.

### Consequences

**Positive:**
- Easy to test (mock ports, test domain logic)
- Easy to extend (new adapter = new file, no core changes)
- Easy to understand (clear separation of concerns)
- Easy to contribute (new contributor can add adapter in <30 min)
- Swap-in replacements (SQLite → Redis without domain changes)

**Negative:**
- More files (domain/, ports/, adapters/, use_cases/, api/)
- More abstractions (Protocol interfaces)
- Learning curve (new contributors must understand Clean Architecture)
- Over-engineering risk (simple features don't need all 5 layers)

**Mitigations:**
- Clear documentation (PHASE_PLAN.md, ADRs, code examples)
- Contract tests (verify all adapters implement protocols)
- Code reviews (enforce Clean Architecture in PRs)
- Start simple (only use all 5 layers for complex features)

## Alternatives Considered

### Alternative 1: Layered Architecture
Use traditional layered architecture (Presentation → Business → Data).

**Rejected because:**
- Tight coupling (business layer depends on data layer)
- Hard to test (I/O mixed with business logic)
- Hard to extend (new features require changes to all layers)
- No clear boundaries (layers bleed into each other)

### Alternative 2: Microservices
Use microservices (separate services for each module).

**Rejected because:**
- Over-engineering for current scope (5 modules don't need microservices)
- Adds complexity (service discovery, load balancing, distributed tracing)
- Harder to develop (multiple codebases, multiple deployments)
- Solo dev overhead (one person managing multiple services)

### Alternative 3: Monolith with Modules
Use monolith with modules (current approach, but without Clean Architecture).

**Rejected because:**
- Tight coupling (modules depend on each other's internals)
- Hard to test (I/O mixed with business logic)
- Hard to extend (new features require core changes)
- No clear boundaries (modules bleed into each other)

## Implementation Plan

### Phase 0b: Foundations (1 week)
- Define port interfaces (ticket #313)
- Create domain events (ticket #314)
- Create KnowledgeResult envelope (ticket #318)
- Refactor substrate into unified providers/ structure (ticket #319)

### Phase 1: Second Brain (3 weeks)
- Create knowledge/domain/models.py (ticket #328)
- Create knowledge/ports/repository.py (ticket #329)
- Create knowledge/adapters/sqlite_repository.py (ticket #330)
- Create knowledge/adapters/redis_repository.py (ticket #331)

### Phase 4: Chat Agents (2 weeks)
- Create chat/domain/models.py (ticket #354)
- Create chat/ports/memory.py (ticket #354)
- Create chat/adapters/sqlite_memory.py (ticket #354)
- Create chat/agents/qa_agent.py (ticket #356)

## References

- EPIC #279 (Phase 0b: Foundations)
- `docs/engineering/ARCHITECTURE_PRINCIPLES.md` (existing principles)
- Clean Architecture by Robert C. Martin
- Hexagonal Architecture by Alistair Cockburn

## Notes

This ADR establishes Clean Architecture as the standard for all new modules. All Phase 0b through Phase 8 tickets must follow the domain/ports/adapters/use_cases/api structure.

If a future requirement cannot be implemented via Clean Architecture, a new ADR must be created to justify the exception.
