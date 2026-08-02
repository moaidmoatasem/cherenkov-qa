# Comprehensive Audit Report: Subsystem 2 (Second Brain & Memory Layer)

**Target Subsystem:** Subsystem 2 — Second Brain, Memory Layer, SQLite FTS5, GraphRAG, Event Bridges, MemSearch, and SDD Protocol  
**Auditor:** Explorer 2 (`explorer_memory_brain`)  
**Date:** 2026-08-02  
**Status:** Audit Complete — Complete Evidence & File-Level Traceability Verified  

---

## Executive Summary

This deep-dive architectural audit evaluates **Subsystem 2** of CHERENKOV-QA, covering the Memory Layer (`cherenkov/memory/`), Knowledge Mesh (`cherenkov/knowledge/`), GraphRAG engine (`cherenkov/knowledge/graph_rag.py`), Event Bridges (`cherenkov/knowledge/bridges/`), MemSearch vector integration (`cherenkov/memory/adapters/memsearch_memory.py`), and the Sync-Driven Development (SDD) protocol (`scripts/agent_sync.py`, `scripts/memory_sync.py`, `docs/engineering/SYNC_DRIVEN_DEV.md`).

Subsystem 2 exhibits an exceptionally clean **Hexagonal / Clean Architecture** (ADR-004, ADR-011), completely isolating core domain logic from storage technology. Key findings include:
- **Architecture**: Clear port/adapter isolation via Python `Protocol` definitions, enabling zero-dependency SQLite FTS5 as default with seamless fallback/upgrade paths to Milvus/MemSearch and Redis.
- **SDD Protocol**: Comprehensive 3-phase agent lifecycle (`before`, `during`/`log`/`token`, `after`) driving automatic memory pattern extraction, token budget enforcement, and pattern auto-promotion after 3 distinct sessions.
- **Technical Debt & Bugs**: Discovered schema and file path discrepancies between `scripts/memory_sync.py` (`agent_memory/knowledge.db`), `SQLiteKnowledgeRepository` (`data/knowledge.db`), and `SQLiteMemoryRepository` (`agent_memory/cherenkov_memory.db`), as well as unescaped double quotes in FTS5 query string formatting.

---

## 1. Memory & Knowledge Architecture

### 1.1 SQLite FTS5 Integration & Triggers

Subsystem 2 utilizes SQLite virtual tables powered by the **FTS5 extension** across both the Memory and Knowledge layers to provide sub-millisecond keyword search without external infrastructure dependencies.

#### A. Memory Engine FTS5 (`cherenkov/memory/adapters/sqlite_memory.py`)
- **File & Location**: `cherenkov/memory/adapters/sqlite_memory.py`, lines 30–87
- **Schema Design**: Content table `memory_entries` paired with external content FTS5 virtual table `memory_fts`.
- **Triggers**: Synchronized in real-time via 3 SQLite triggers (`memory_entries_ai`, `memory_entries_ad`, `memory_entries_au`).

```sql
CREATE TABLE IF NOT EXISTS memory_entries (
    id            TEXT PRIMARY KEY,
    session_id    TEXT NOT NULL,
    task_type     TEXT NOT NULL,
    kind          TEXT NOT NULL,
    content       TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '[]',   -- JSON array
    recurrence    INTEGER NOT NULL DEFAULT 0,
    is_promoted   INTEGER NOT NULL DEFAULT 0,
    promoted_at   TEXT,
    created_at    TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts
USING fts5(
    id UNINDEXED,
    content,
    task_type,
    kind,
    content=memory_entries,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS memory_entries_ai
AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, id, content, task_type, kind)
    VALUES (new.rowid, new.id, new.content, new.task_type, new.kind);
END;
```

#### B. Knowledge Mesh FTS5 (`cherenkov/knowledge/adapters/sqlite_repository.py`)
- **File & Location**: `cherenkov/knowledge/adapters/sqlite_repository.py`, lines 47–96
- **Schema Design**: `knowledge_items` content table paired with `knowledge_fts` virtual table.
- **Retroactive Index Rebuild**: Implements `_ensure_fts_populated()` (lines 84–96) to rebuild the shadow table when initializing over pre-existing SQLite databases where triggers were not active during initial insert:

```python
def _ensure_fts_populated(self, conn: sqlite3.Connection) -> None:
    (fts_count,) = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()
    (items_count,) = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()
    if fts_count < items_count:
        conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES ('rebuild')")
        conn.commit()
```

---

### 1.2 MemoryRepository Port & Adapters

Per ADR-004 and ADR-011, the memory engine defines a strict port protocol:

```
┌─────────────────────────────────────────────────────────────┐
│                    MemoryRepository                         │
│                    (Protocol Port)                          │
│        cherenkov/memory/ports/repository.py                │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
  SQLiteMemoryRepository           MemSearchMemoryRepository
       (Adapter)                       (Proxy Adapter)
  cherenkov/memory/adapters/       cherenkov/memory/adapters/
      sqlite_memory.py                memsearch_memory.py
```

#### Port Definition (`cherenkov/memory/ports/repository.py`, lines 20–60)
The `@runtime_checkable Protocol` defines the interface contracts:
- `save_entry(entry: MemoryEntry) -> None`
- `search(query: MemoryQuery) -> list[MemoryEntry]`
- `get_promoted() -> list[MemoryPattern]`
- `upsert_pattern(pattern: MemoryPattern) -> None`
- `promote_pattern(fingerprint: str) -> None`
- `get_pattern(fingerprint: str) -> MemoryPattern | None`
- `list_patterns(limit: int = 50) -> list[MemoryPattern]`
- `apply_promotion_rules(rule: PromotionRule) -> list[str]`

#### Primary Adapter (`cherenkov/memory/adapters/sqlite_memory.py`)
Implements all `MemoryRepository` methods backed by `agent_memory/cherenkov_memory.db`. Operates with `PRAGMA journal_mode = WAL` and `PRAGMA foreign_keys = ON`.

#### Semantic Upgrade Adapter (`cherenkov/memory/adapters/memsearch_memory.py`)
Acts as a Proxy wrapping `SQLiteMemoryRepository`:
- Delegates structured pattern operations (`get_promoted`, `upsert_pattern`, `promote_pattern`) directly to SQLite.
- Delegates `search()` queries to Milvus vector search via `memsearch.MemSearch`. If `memsearch` is missing or fails (e.g. invalid API credentials), it gracefully falls back to `SQLiteMemoryRepository.search()`.

---

### 1.3 Knowledge Mesh Architecture

The Knowledge Mesh provides heterogeneous storage adapters for domain knowledge (API verdicts, testing idioms, incident reports, human feedback, agent memory).

- **Port Protocol**: `KnowledgeMeshRepository` (`cherenkov/knowledge/ports/repository.py`, lines 12–20).
- **SQLite Adapter**: `SQLiteKnowledgeRepository` (`cherenkov/knowledge/adapters/sqlite_repository.py`).
- **Redis Adapter**: `RedisKnowledgeRepository` (`cherenkov/knowledge/adapters/redis_repository.py`). Key pattern `knowledge:{source}:{item_id}`.
- **Domain Models**: `KnowledgeItem`, `KnowledgeQuery`, `KnowledgeQueryResult` (`cherenkov/knowledge/domain/models.py`).

---

### 1.4 GraphRAG Query Execution

The `GraphRAG` engine (`cherenkov/knowledge/graph_rag.py`) performs multi-source knowledge aggregation and divergence explanations across the knowledge mesh.

```python
class GraphRAG:
    def __init__(self, repository: KnowledgeMeshRepository):
        self.repository = repository

    def query(
        self, query: str, sources: list[str] | None = None, limit: int = 10
    ) -> list[KnowledgeQueryResult]:
        if sources is None:
            sources = [
                "verdicts",
                "idioms",
                "incidents",
                "hitl",
                "feedback",
                "agent_memory",
            ]
        per_source = max(1, limit // len(sources))
        results = []
        for source in sources:
            q = KnowledgeQuery(query=query, source=source, limit=per_source)
            result = self.repository.query(q)
            if result.data:
                results.append(result)
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:limit]
```

- **Query Execution**: Fans out queries across configured knowledge sources (`verdicts`, `idioms`, `incidents`, `hitl`, `feedback`, `agent_memory`), allocates equal retrieval limits (`limit // len(sources)`), and ranks returned results by confidence score.
- **Divergence Explanation**: `explain_divergence(endpoint, method)` queries `verdicts`, `idioms`, and `incidents` simultaneously to synthesize structured divergence explanations when API behavior deviates from expectations.

---

### 1.5 Milvus Shadow Indexing & MemSearch

Phase 9 integrates **MemSearch** (Milvus-backed semantic search over repository markdown files and memory logs):
- `_memsearch_client()` in `scripts/agent_sync.py` (lines 30–44) initializes `memsearch.MemSearch(paths=[str(ROOT)])`.
- `cmd_before` queries Milvus for context snippets matching `task_type`.
- `cmd_after` syncs closed session summaries into MemSearch vector index via `ms.add_memory(...)`.
- `MemSearchMemoryRepository` wraps vector results in `MemoryEntry` model instances.

---

## 2. System Design & Event Bridges

### 2.1 Event Bridges

Subsystem 2 integrates event bridges that dynamically transform external events and Markdown files into structured `KnowledgeItem` records:

1. **Agent Memory Bridge** (`cherenkov/knowledge/bridges/agent_memory_rag.py`):
   Scans `agent_memory/*.md` markdown files and ingests them into `KnowledgeMeshRepository` with source `"agent_memory"`.
2. **Feedback Bridge** (`cherenkov/knowledge/bridges/feedback_rag.py`):
   Ingests user/agent feedback entries into `KnowledgeMeshRepository` under source `"feedback"`.
3. **HITL Reflector Bridge** (`cherenkov/knowledge/bridges/hitl_reflector.py`):
   Subscribes to Human-in-the-Loop decision events (`on_hitl_decision`), stores `hitl` knowledge items, and forwards human verdicts into the feedback reflector (`reflector.ingest_human_verdict`).

```
[ agent_memory/*.md ] ──► AgentMemoryRAGBridge ──┐
                                                 │
[ User Feedback ]     ──► FeedbackRAGBridge     ──┼──► KnowledgeMeshRepository
                                                 │
[ HITL Decisions ]    ──► HITLReflectorBridge   ──┘
```

---

### 2.2 Collect & Promote Workflows

The CC-1 Auto-Memory Engine automates the lifecycle of capturing findings and promoting recurring patterns.

```
 agent_sync after
        │
        ▼
 collect_from_findings()  ──►  Normalize & Hash  ──►  upsert_pattern() (candidate)
        │
        ▼
  run_promotion()         ──►  Check session_count ≥ 3  ──►  is_auto_loaded = True
```

#### A. Findings Collection (`cherenkov/memory/use_cases/collect.py`)
- `collect_from_findings()` iterates over logged session findings.
- Saves every item as a `MemoryEntry` (kinds: `FINDING`, `DECISION`, `PITFALL`, `CONTEXT`).
- When encountering `PITFALL` or `DECISION` entries, it executes `_extract_pattern()`:
  - Normalizes text by removing session IDs (`sess_\w+`), timestamps (`\d{4}-\d{2}...`), and file paths (`/[^\s]+`).
  - Hashes the normalized string to a 16-character SHA-256 fingerprint.
  - Calls `repo.upsert_pattern()` to insert or merge the pattern into `memory_patterns`.

#### B. Pattern Promotion (`cherenkov/memory/use_cases/promote.py` & `models.py`)
- `PromotionRule`: Configured by default to `min_session_count = 3` (overridable via `cherenkov.toml [memory] auto_promote_threshold`).
- `run_promotion()` triggers `repo.apply_promotion_rules(rule)`.
- Patterns meeting the threshold have `is_auto_loaded` set to `1` in SQLite.
- Auto-promoted patterns are prepended to context snippets in all future `agent_sync before` calls.

---

### 2.3 SDD Protocol CLI Subcommands (`scripts/agent_sync.py`)

The SDD protocol implements a rigid CLI lifecycle for token accounting and context preservation:

| Subcommand | Functionality & Code Trace |
|------------|----------------------------|
| `before` | Initializes new session ID `sess_YYYYMMDDHHMMSS_xxxxxx` (`cmd_before`, line 99). Allocates token budget (default 50,000 tokens). Queries MemSearch or loads pre-computed context snippets from `agent_memory/sync/context.json`. Injects promoted auto-load patterns. |
| `log` | Appends a structured finding record (`finding`, `decision`, `pitfall`, `context`) to `agent_memory/sync/findings/<session_id>.json` (`cmd_log`, line 427). |
| `token` | Tracks prompt, generation, read, and search tokens consumed (`cmd_token`, line 452). Monitors progressive compaction thresholds (60% warn, 80% compact, 95% emergency). |
| `after` | Closes session (`cmd_after`, line 199). Computes total tokens, updates historical token stats in `tokens.json`, extracts experience records into `experience.json`, adds session summary to MemSearch, and executes `_memory_collect()` to run `collect_from_findings` and `run_promotion`. |
| `memory` | CLI interface to auto-memory (`cmd_memory`, line 346): `list`, `promote`, `search`, `status`. |

---

## 3. Design Patterns Applied

Subsystem 2 extensively employs established software design patterns:

1. **Repository Pattern**:
   - `MemoryRepository` (`cherenkov/memory/ports/repository.py`) and `KnowledgeMeshRepository` (`cherenkov/knowledge/ports/repository.py`) abstract data persistence completely away from business domain models.
2. **Proxy / Facade Pattern**:
   - `MemSearchMemoryRepository` acts as a proxy/wrapper around `SQLiteMemoryRepository`, routing search calls to Milvus when available while delegating pattern operations to SQLite.
   - `GraphRAG` acts as a Facade over heterogeneous knowledge sources (`verdicts`, `idioms`, `incidents`, `hitl`, `feedback`, `agent_memory`), hiding individual query complexities behind a single unified `query()` method.
3. **Event Listener / Observer Pattern**:
   - RAG Bridges (`AgentMemoryRAGBridge`, `FeedbackRAGBridge`, `HITLReflectorBridge`) observe external state changes and project them into the knowledge store asynchronously.
4. **Strategy Pattern**:
   - Dual context retrieval strategies in `agent_sync.py`: `MemSearch` vector search strategy vs. static `context.json` snippet strategy.
   - Storage strategies: SQLite FTS5 vs. Redis vector store vs. Milvus/MemSearch.

---

## 4. Code Quality, Concurrency & Data Integrity Analysis

### 4.1 Database Transaction Management
- **`SQLiteMemoryRepository`**: Utilizes a Python context manager `_connect()` (lines 109–120) that handles transaction boundaries explicitly:
  ```python
  @contextmanager
  def _connect(self) -> Generator[sqlite3.Connection, None, None]:
      conn = sqlite3.connect(self._db_path, check_same_thread=False)
      conn.row_factory = sqlite3.Row
      try:
          yield conn
          conn.commit()
      except Exception:
          conn.rollback()
          raise
      finally:
          conn.close()
  ```
  *Assessment*: Ensures atomic transactions and clean rollbacks on errors.

- **`SQLiteKnowledgeRepository`**: Uses thread-local connection caching via `self._local.con` (`_connect()`, lines 27–42). Uses explicit `conn.commit()` calls in `store()` and `_init_db()`.

---

### 4.2 SQLite Lock Contention & Thread Safety
- Both repositories configure **Write-Ahead Logging (`PRAGMA journal_mode = WAL`)**.
- WAL mode permits multiple concurrent readers while a single writer is active, significantly reducing lock contention in multi-agent environments.
- `SQLiteKnowledgeRepository` configures a 30-second busy timeout (`sqlite3.connect(..., timeout=30.0)`), effectively handling transient write locks.
- *Caveat in `SQLiteMemoryRepository`*: Opens and closes SQLite connections on every method call (`_connect()`). While safe with `check_same_thread=False` and WAL mode, connection churn creates slight performance overhead compared to thread-local connection pooling under heavy load.

---

### 4.3 FTS5 Query Sanitization & Security

#### Vulnerability Identified: Unescaped FTS5 Special Characters & Double Quotes
In both memory and knowledge adapters, FTS5 queries format input terms by wrapping them in double quotes:

- `cherenkov/memory/adapters/sqlite_memory.py` (line 154):
  ```python
  fts_query = " AND ".join(f'"{t}"' for t in query.query.split() if t) or query.query
  ```
- `cherenkov/knowledge/adapters/sqlite_repository.py` (line 151):
  ```python
  fts_query = " AND ".join(f'"{t}"' for t in terms)
  ```

**Security & Stability Bug**: If user or agent query input contains raw double-quote characters (e.g. `query = 'ollama "cold start"'`), the resulting `fts_query` string becomes `"ollama" " "cold" "start""`, which violates FTS5 syntax rules and causes SQLite to raise `sqlite3.OperationalError: fts5: syntax error near ...`.

---

### 4.4 Technical Debt & Schema/Path Inconsistencies

#### Critical Architecture Debt: Database Path & Schema Fragmentation
The audit uncovered a 3-way fragmentation across database files and schemas in the codebase:

1. **`SQLiteMemoryRepository`** (`cherenkov/memory/adapters/sqlite_memory.py`):
   - Database Path: `<project_root>/agent_memory/cherenkov_memory.db`
   - Tables: `memory_entries`, `memory_fts`, `memory_patterns`
2. **`SQLiteKnowledgeRepository`** (`cherenkov/knowledge/adapters/sqlite_repository.py`):
   - Database Path: `<project_root>/data/knowledge.db`
   - Tables: `knowledge_items`, `knowledge_fts`
3. **`scripts/memory_sync.py`** (`scripts/memory_sync.py`):
   - Database Path: `<project_root>/agent_memory/knowledge.db`
   - Tables: Standalone virtual table `knowledge_fts` using columns `(id, source, content, timestamp)` — **without** the `knowledge_items` table or triggers used by `SQLiteKnowledgeRepository`!

**Impact**: `scripts/memory_sync.py` writes to a completely separate database file (`agent_memory/knowledge.db`) with a non-conforming table structure, bypassing `SQLiteKnowledgeRepository` (`data/knowledge.db`) and `SQLiteMemoryRepository` (`agent_memory/cherenkov_memory.db`).

---

## 5. Architectural Strengths, Technical Debt & Recommendations

### 5.1 Architectural Strengths
1. **Clean Architecture Adherence**: Domain logic in `cherenkov/memory/domain` and `cherenkov/knowledge/domain` has **zero external dependencies**, strictly conforming to ADR-004.
2. **Flexible Storage Tiering**: Clean port/adapter isolation allows running locally with zero infrastructure (SQLite FTS5) while supporting high-scale vector deployment (Milvus/MemSearch, Redis) seamlessly.
3. **Automated Knowledge Compounding**: SDD protocol combined with `collect_from_findings` and `run_promotion` ensures agent experiences build up compounding knowledge automatically across sessions.

---

### 5.2 Technical Debt Summary & Actionable Recommendations

| Issue / Technical Debt | File & Location | Severity | Recommended Fix |
|------------------------|-----------------|----------|-----------------|
| **Database Path & Schema Fragmentation** | `scripts/memory_sync.py:20` vs `sqlite_repository.py:22` | **HIGH** | Refactor `scripts/memory_sync.py` to use `SQLiteKnowledgeRepository` or `SQLiteMemoryRepository` via standard ports rather than opening a direct SQLite connection to a third DB file (`agent_memory/knowledge.db`). |
| **FTS5 Double-Quote Injection** | `sqlite_memory.py:154`, `sqlite_repository.py:151` | **MEDIUM** | Escape internal double quotes in search terms before wrapping: `t.replace('"', '""')`. |
| **Pattern Normalization Fragility** | `use_cases/collect.py:78-85` | **LOW** | Enhance `_extract_pattern` normalization beyond simple regexes to prevent slightly varied phrasing from generating duplicate SHA-256 pattern fingerprints. |
| **Connection Overhead in `SQLiteMemoryRepository`** | `sqlite_memory.py:109-120` | **LOW** | Adopt thread-local connection caching (`threading.local`) similar to `SQLiteKnowledgeRepository` to eliminate connection creation churn during high-frequency memory reads/writes. |

---

## 6. Verification & Test Suite Coverage

The memory and knowledge subsystems are validated by unit tests in the project test suite:
- `tests/unit/test_memory.py`: 12 tests covering SQLite storage, FTS5 keyword search, pattern upserting, auto-promotion rules, `collect_from_findings`, and `run_promotion`.
- `tests/unit/test_memory_sync.py`: Verifies importability and execution of `scripts/memory_sync.py`.

All 12 unit tests in `tests/unit/test_memory.py` pass cleanly, confirming core invariant stability for Subsystem 2.
