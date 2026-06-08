# ADR-006: Knowledge Mesh (Unified Query, Separate Stores)

**Date:** 2026-06-08  
**Status:** Accepted  
**Deciders:** Project Owner + AI Agents  
**Related EPIC:** #277 (Phase -1), #280 (Phase 1)

---

## Context

CHERENKOV-QA has multiple data stores:
- `verdicts.db` (Reflector verdicts)
- `hitl.db` (HITL queue)
- `feedback.json` (human feedback)
- `agent_memory/` (markdown wiki)
- `incidents/` (JSON files)
- `idioms/` (SQLite in verdicts.db)

Each store is useful independently, but querying across them requires manual joins. Options considered:
1. **Unified database** (single PostgreSQL/SQLite database)
2. **Knowledge mesh** (separate stores, unified query interface)
3. **Data warehouse** (ETL to central warehouse)

## Decision

**Knowledge mesh**: Each store keeps its schema, `KnowledgeRepository` provides a unified query interface. All queries return `KnowledgeResult` envelope.

### Rationale

1. **Anti-lock-in**: Each store is independently useful (can eject any one)
2. **Unified query**: `query("auth timeout")` searches verdicts + idioms + incidents + HITL + feedback + agent_memory
3. **Standard envelope**: `KnowledgeResult(data, source, confidence, metadata)` for all CLI and API output
4. **Incremental adoption**: Start with SQLite adapter, upgrade to Redis for vector search
5. **Respects existing data**: No migration required (stores keep their schemas)

### Architecture

```
┌─────────────────────────────────────┐
│  KnowledgeRepository (Protocol)     │
│  - query(KnowledgeQuery)            │
│  - store(KnowledgeItem)             │
│  - search(pattern, limit)           │
│  - get_by_id(item_id)               │
└──────────────┬──────────────────────┘
               │
               ├─→ SQLiteKnowledgeRepository (default)
               │   - Joins across .db files
               │   - Full-text search (FTS5)
               │   - No vector search
               │
               └─→ RedisKnowledgeRepository (upgrade)
                   - Vector search (HNSWLIB)
                   - Semantic search (embeddings)
                   - Real-time updates (pub/sub)
```

### Stores Indexed

| Store | Current Format | Indexed By |
|-------|---------------|------------|
| `verdicts.db` | SQLite | Reflector |
| `hitl.db` | SQLite | HITL queue |
| `feedback.json` | JSON file | FeedbackStore (→ SQLite) |
| `agent_memory/` | Markdown files | Wiki indexer |
| `incidents/` | JSON files | RAG index |
| `idioms/` | SQLite (in verdicts.db) | Reflector |

### Query Interface

```python
# cherenkov/knowledge/domain/models.py
@dataclass
class KnowledgeQuery:
    query: str
    source: str | None = None  # "verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"
    limit: int = 10
    filter: dict[str, Any] = field(default_factory=dict)

@dataclass
class KnowledgeResult:
    data: Any
    source: str  # "verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"
    confidence: float
    metadata: dict[str, Any]
```

### Usage

**CLI:**
```bash
cherenkov knowledge query "auth timeout" --format json
```

**API:**
```python
GET /api/v1/knowledge/query?q=auth+timeout
```

**Python:**
```python
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery

repo = SQLiteKnowledgeRepository()
query = KnowledgeQuery(query="auth timeout", limit=10)
result = repo.query(query)

print(result.data)  # List of matching items
print(result.source)  # "all" (searched all sources)
print(result.confidence)  # 1.0
```

### GraphRAG (Multi-Domain Retrieval)

```python
# cherenkov/knowledge/graph_rag.py
class GraphRAG:
    def query(self, query: str, sources: list[str] | None = None, limit: int = 10) -> list[KnowledgeResult]:
        """Query across multiple knowledge domains."""
        if sources is None:
            sources = ["verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"]
        
        results = []
        for source in sources:
            knowledge_query = KnowledgeQuery(query=query, source=source, limit=limit // len(sources))
            result = self.repository.query(knowledge_query)
            if result.data:
                results.append(result)
        
        # Sort by confidence
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]
```

### Consequences

**Positive:**
- Anti-lock-in (each store independently useful)
- Unified query (search across all stores)
- Standard envelope (consistent output format)
- Incremental adoption (start with SQLite, upgrade to Redis)
- Respects existing data (no migration required)

**Negative:**
- No ACID transactions across stores (each store has its own transaction)
- No referential integrity (can't enforce foreign keys across stores)
- Query performance (joins across multiple .db files)
- Consistency (stores may be out of sync)

**Mitigations:**
- Event-driven synchronization (emit events on store updates)
- Caching (cache query results in Redis)
- Denormalization (duplicate data across stores for performance)
- Clear documentation of consistency guarantees

## Alternatives Considered

### Alternative 1: Unified Database
Migrate all stores to a single PostgreSQL/SQLite database.

**Rejected because:**
- Requires migration (breaking change)
- Lock-in (can't eject individual stores)
- Complex schema (many tables, many foreign keys)
- Over-engineering (current stores work fine independently)

### Alternative 2: Data Warehouse
ETL all stores to a central data warehouse (Snowflake, BigQuery).

**Rejected because:**
- Adds complexity (ETL pipelines, data warehouse)
- Solo dev overhead (maintaining ETL pipelines)
- Overkill for current scope (6 stores, <1GB data)
- Not localhost-first (requires cloud data warehouse)

### Alternative 3: Federated Query
Use federated query engine (Presto, Trino) to query across stores.

**Rejected because:**
- Adds complexity (federated query engine)
- Solo dev overhead (maintaining query engine)
- Overkill for current scope (6 stores, simple queries)
- Performance overhead (federated queries are slow)

## Implementation Plan

### Phase 0b: Foundations (1 week)
- Add KnowledgeResult envelope (ticket #318)
- Define KnowledgeRepository Protocol
- Create KnowledgeQuery and KnowledgeResult models

### Phase 1: Second Brain (3 weeks)
- Create knowledge/domain/models.py (ticket #328)
- Create knowledge/ports/repository.py (ticket #329)
- Create knowledge/adapters/sqlite_repository.py (ticket #330)
- Create knowledge/adapters/redis_repository.py (ticket #331)
- Create knowledge/graph_rag.py (ticket #332)
- Bridge HITL → Reflector via events (ticket #333)
- Bridge Feedback → RAG (ticket #334)
- Bridge agent_memory → RAG (ticket #335)
- Create knowledge query CLI (ticket #336)
- Truth Model persistence (ticket #337)

## References

- EPIC #280 (Phase 1: Second Brain)
- `cherenkov/ai/rag_index.py` (existing RAG index)
- `cherenkov/reflector/store.py` (existing verdict store)
- `cherenkov/hitl/store.py` (existing HITL queue)

## Notes

This ADR establishes the knowledge mesh architecture. All Phase 1 tickets must follow the unified query, separate stores pattern.

If a future requirement cannot be implemented via knowledge mesh, a new ADR must be created to justify the exception.
