# Vision 15: Second Brain (Knowledge Mesh)

**Date:** 2026-06-08  
**Status:** Active  
**Related EPIC:** #280 (Phase 1)

---

## Overview

The Second Brain is CHERENKOV's knowledge mesh — a unified query interface over multiple data stores (verdicts, idioms, incidents, HITL decisions, feedback, agent memory). It enables:

- **Unified search**: `query("auth timeout")` searches across all stores
- **GraphRAG**: Multi-domain retrieval with semantic search
- **Event bridges**: HITL → Reflector, Feedback → RAG, agent_memory → RAG
- **CLI/API access**: `cherenkov knowledge query` and `/api/v1/knowledge/query`

---

## Architecture

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

---

## Stores Indexed

| Store | Current Format | Indexed By |
|-------|---------------|------------|
| `verdicts.db` | SQLite | Reflector |
| `hitl.db` | SQLite | HITL queue |
| `feedback.json` | JSON file | FeedbackStore (→ SQLite) |
| `agent_memory/` | Markdown files | Wiki indexer |
| `incidents/` | JSON files | RAG index |
| `idioms/` | SQLite (in verdicts.db) | Reflector |

---

## Domain Models

```python
# cherenkov/knowledge/domain/models.py
from dataclasses import dataclass, field
from typing import Any, Literal
from datetime import datetime

@dataclass
class KnowledgeQuery:
    query: str
    source: str | None = None  # "verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"
    limit: int = 10
    filter: dict[str, Any] = field(default_factory=dict)

@dataclass
class KnowledgeResult:
    data: Any
    source: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

@dataclass
class KnowledgeItem:
    item_id: str
    source: str
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
```

---

## Port Interface

```python
# cherenkov/knowledge/ports/repository.py
from typing import Protocol
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult, KnowledgeItem

class KnowledgeRepository(Protocol):
    def query(self, query: KnowledgeQuery) -> KnowledgeResult: ...
    def store(self, item: KnowledgeItem) -> str: ...
    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeResult]: ...
    def get_by_id(self, item_id: str) -> KnowledgeResult | None: ...
```

---

## SQLite Adapter

```python
# cherenkov/knowledge/adapters/sqlite_repository.py
import sqlite3
import json
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult, KnowledgeItem

class SQLiteKnowledgeRepository:
    def __init__(self, db_path: str = "data/knowledge.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                item_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON knowledge_items(source)")
        conn.commit()
        conn.close()
    
    def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        conn = sqlite3.connect(self.db_path)
        
        sql = "SELECT item_id, source, data, metadata FROM knowledge_items"
        params = []
        
        if query.source:
            sql += " WHERE source = ?"
            params.append(query.source)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(query.limit)
        
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append(KnowledgeResult(
                data=json.loads(row[2]),
                source=row[1],
                confidence=1.0,
                metadata=json.loads(row[3]) if row[3] else {}
            ))
        
        return KnowledgeResult(
            data=results,
            source=query.source or "all",
            confidence=1.0,
            metadata={"count": len(results)}
        )
    
    def store(self, item: KnowledgeItem) -> str:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO knowledge_items (item_id, source, data, metadata) VALUES (?, ?, ?, ?)",
            (item.item_id, item.source, json.dumps(item.data), json.dumps(item.metadata))
        )
        conn.commit()
        conn.close()
        return item.item_id
    
    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeResult]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT item_id, source, data, metadata FROM knowledge_items WHERE data LIKE ? LIMIT ?",
            (f"%{pattern}%", limit)
        )
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append(KnowledgeResult(
                data=json.loads(row[2]),
                source=row[1],
                confidence=1.0,
                metadata=json.loads(row[3]) if row[3] else {}
            ))
        return results
    
    def get_by_id(self, item_id: str) -> KnowledgeResult | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT item_id, source, data, metadata FROM knowledge_items WHERE item_id = ?",
            (item_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return KnowledgeResult(
            data=json.loads(row[2]),
            source=row[1],
            confidence=1.0,
            metadata=json.loads(row[3]) if row[3] else {}
        )
```

---

## Redis Adapter

```python
# cherenkov/knowledge/adapters/redis_repository.py
import redis
import json
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult, KnowledgeItem

class RedisKnowledgeRepository:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(redis_url)
    
    def query(self, query: KnowledgeQuery) -> KnowledgeResult:
        pattern = f"knowledge:{query.source or '*'}:*"
        keys = self.redis.keys(pattern)
        
        results = []
        for key in keys[:query.limit]:
            data = self.redis.get(key)
            if data:
                item = json.loads(data)
                results.append(KnowledgeResult(
                    data=item["data"],
                    source=item["source"],
                    confidence=1.0,
                    metadata=item.get("metadata", {})
                ))
        
        return KnowledgeResult(
            data=results,
            source=query.source or "all",
            confidence=1.0,
            metadata={"count": len(results)}
        )
    
    def store(self, item: KnowledgeItem) -> str:
        key = f"knowledge:{item.source}:{item.item_id}"
        self.redis.set(key, json.dumps({
            "item_id": item.item_id,
            "source": item.source,
            "data": item.data,
            "metadata": item.metadata,
            "created_at": item.created_at.isoformat()
        }))
        return item.item_id
    
    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeResult]:
        keys = self.redis.keys(f"knowledge:*:*")
        
        results = []
        for key in keys:
            data = self.redis.get(key)
            if data:
                item = json.loads(data)
                if pattern.lower() in json.dumps(item["data"]).lower():
                    results.append(KnowledgeResult(
                        data=item["data"],
                        source=item["source"],
                        confidence=1.0,
                        metadata=item.get("metadata", {})
                    ))
                    if len(results) >= limit:
                        break
        
        return results
    
    def get_by_id(self, item_id: str) -> KnowledgeResult | None:
        keys = self.redis.keys(f"knowledge:*:{item_id}")
        if not keys:
            return None
        
        data = self.redis.get(keys[0])
        if not data:
            return None
        
        item = json.loads(data)
        return KnowledgeResult(
            data=item["data"],
            source=item["source"],
            confidence=1.0,
            metadata=item.get("metadata", {})
        )
```

---

## GraphRAG

```python
# cherenkov/knowledge/graph_rag.py
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeResult
from cherenkov.knowledge.ports.repository import KnowledgeRepository

class GraphRAG:
    def __init__(self, repository: KnowledgeRepository):
        self.repository = repository
    
    def query(self, query: str, sources: list[str] | None = None, limit: int = 10) -> list[KnowledgeResult]:
        if sources is None:
            sources = ["verdicts", "idioms", "incidents", "hitl", "feedback", "agent_memory"]
        
        results = []
        for source in sources:
            knowledge_query = KnowledgeQuery(
                query=query,
                source=source,
                limit=limit // len(sources)
            )
            result = self.repository.query(knowledge_query)
            if result.data:
                results.append(result)
        
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]
    
    def explain_divergence(self, endpoint: str, method: str) -> KnowledgeResult:
        verdicts = self.query(f"{endpoint} {method}", sources=["verdicts"], limit=5)
        idioms = self.query(f"{endpoint} {method}", sources=["idioms"], limit=5)
        incidents = self.query(f"{endpoint} {method}", sources=["incidents"], limit=5)
        
        explanation = {
            "endpoint": endpoint,
            "method": method,
            "verdicts": [v.data for v in verdicts],
            "idioms": [i.data for i in idioms],
            "incidents": [inc.data for inc in incidents]
        }
        
        return KnowledgeResult(
            data=explanation,
            source="graph_rag",
            confidence=1.0,
            metadata={
                "verdicts_count": len(verdicts),
                "idioms_count": len(idioms),
                "incidents_count": len(incidents)
            }
        )
```

---

## Event Bridges

### HITL → Reflector

```python
# cherenkov/knowledge/bridges/hitl_reflector.py
from cherenkov.core.events import HITLDecisionMade, EventBus
from cherenkov.reflector.reflector import Reflector

class HITLReflectorBridge:
    def __init__(self, event_bus: EventBus, reflector: Reflector):
        self.event_bus = event_bus
        self.reflector = reflector
        self.event_bus.subscribe("HITLDecisionMade", self._on_hitl_decision)
    
    def _on_hitl_decision(self, event: HITLDecisionMade):
        item = self._get_hitl_item(event.item_id)
        if not item:
            return
        
        self.reflector.ingest_human_verdict(
            item_id=event.item_id,
            verdict=event.action,
            reason=event.reason,
            endpoint=item.endpoint,
            method=item.method
        )
```

### Feedback → RAG

```python
# cherenkov/knowledge/bridges/feedback_rag.py
from cherenkov.core.feedback_store import FeedbackStore
from cherenkov.knowledge.ports.repository import KnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeItem

class FeedbackRAGBridge:
    def __init__(self, feedback_store: FeedbackStore, repository: KnowledgeRepository):
        self.feedback_store = feedback_store
        self.repository = repository
    
    def sync_feedback(self):
        feedback_entries = self.feedback_store.list_all()
        
        for entry in feedback_entries:
            item = KnowledgeItem(
                item_id=f"feedback_{entry.id}",
                source="feedback",
                data={
                    "endpoint": entry.endpoint,
                    "method": entry.method,
                    "reason": entry.reason,
                    "comment": entry.comment
                },
                metadata={
                    "feedback_id": entry.id,
                    "created_at": entry.created_at.isoformat()
                }
            )
            self.repository.store(item)
```

### agent_memory → RAG

```python
# cherenkov/knowledge/bridges/agent_memory_rag.py
from pathlib import Path
from cherenkov.knowledge.ports.repository import KnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeItem

class AgentMemoryRAGBridge:
    def __init__(self, repository: KnowledgeRepository, memory_dir: str = "agent_memory"):
        self.repository = repository
        self.memory_dir = Path(memory_dir)
    
    def sync_agent_memory(self):
        if not self.memory_dir.exists():
            return
        
        for md_file in self.memory_dir.glob("*.md"):
            content = md_file.read_text()
            
            item = KnowledgeItem(
                item_id=f"agent_memory_{md_file.stem}",
                source="agent_memory",
                data={
                    "filename": md_file.name,
                    "content": content
                },
                metadata={
                    "path": str(md_file),
                    "size": len(content)
                }
            )
            self.repository.store(item)
```

---

## CLI Command

```python
# cherenkov/knowledge/cli.py
import click
import json
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery

@click.group()
def knowledge():
    """Knowledge management commands."""
    pass

@knowledge.command()
@click.argument("query_text")
@click.option("--source", type=str, help="Filter by source")
@click.option("--limit", type=int, default=10, help="Maximum results")
@click.option("--format", type=click.Choice(["json", "text", "pretty"]), default="pretty", help="Output format")
def query(query_text: str, source: str, limit: int, format: str):
    """Query knowledge repository."""
    repo = SQLiteKnowledgeRepository()
    
    knowledge_query = KnowledgeQuery(
        query=query_text,
        source=source,
        limit=limit
    )
    
    result = repo.query(knowledge_query)
    
    if format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    elif format == "text":
        click.echo(f"Source: {result.source}")
        click.echo(f"Confidence: {result.confidence}")
        click.echo(f"Results: {len(result.data) if isinstance(result.data, list) else 1}")
        click.echo(f"Data: {result.data}")
    else:  # pretty
        click.echo(f"\n📚 Knowledge Query Results")
        click.echo(f"{'='*50}")
        click.echo(f"Source: {result.source}")
        click.echo(f"Confidence: {result.confidence:.2f}")
        click.echo(f"Results: {len(result.data) if isinstance(result.data, list) else 1}")
        click.echo(f"\n{json.dumps(result.data, indent=2)}")
```

---

## API Endpoint

```python
# cherenkov/knowledge/api/routes.py
from fastapi import APIRouter
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery

router = APIRouter()

@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None, limit: int = 10):
    repo = SQLiteKnowledgeRepository()
    query = KnowledgeQuery(query=q, source=source, limit=limit)
    result = repo.query(query)
    return result.to_dict()
```

---

## Testing

```python
# tests/unit/test_knowledge_repository.py
import pytest
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository
from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeItem

def test_query_returns_knowledge_result():
    repo = SQLiteKnowledgeRepository(":memory:")
    query = KnowledgeQuery(query="auth timeout")
    result = repo.query(query)
    
    assert hasattr(result, "data")
    assert hasattr(result, "source")
    assert hasattr(result, "confidence")

def test_store_returns_item_id():
    repo = SQLiteKnowledgeRepository(":memory:")
    item = KnowledgeItem(
        item_id="test_123",
        source="verdicts",
        data={"endpoint": "/users"}
    )
    item_id = repo.store(item)
    
    assert item_id == "test_123"

def test_search_finds_pattern():
    repo = SQLiteKnowledgeRepository(":memory:")
    
    # Store some items
    repo.store(KnowledgeItem(
        item_id="1",
        source="verdicts",
        data={"endpoint": "/users", "status": "auth timeout"}
    ))
    repo.store(KnowledgeItem(
        item_id="2",
        source="verdicts",
        data={"endpoint": "/login", "status": "success"}
    ))
    
    # Search
    results = repo.search("auth timeout")
    
    assert len(results) == 1
    assert results[0].data["endpoint"] == "/users"
```

---

## References

- EPIC #280 (Phase 1: Second Brain)
- ADR-006 (Knowledge mesh)
- `docs/PHASE_PLAN.md` (Phase 1 details)
- `cherenkov/knowledge/` (to be created)
