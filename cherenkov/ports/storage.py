"""
Unified Storage Port (ADR-013) — Single source of truth for all persistent storage.

Replaces 5 duplicate SQLite stores:
  1. cherenkov/memory/adapters/sqlite_memory.py        (agent_memory/cherenkov_memory.db)
  2. cherenkov/chat/adapters/sqlite_memory.py          (data/chat.db)
  3. cherenkov/core/feedback_store.py                  (.cherenkov/feedback.json → SQLite)
  4. cherenkov/reflector/store.py                      (.cherenkov/verdicts.db + reflector.db)
  5. cherenkov/knowledge/adapters/sqlite_repository.py (data/knowledge.db)

All modules now inject StoragePort and use namespaced tables.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlite3


# ─── Namespaces ──────────────────────────────────────────────────────────────
# Each domain gets its own table prefix to avoid collisions in a single DB.
NAMESPACE_MEMORY = "memory"          # agent_sync entries, patterns
NAMESPACE_CHAT = "chat"              # sessions, messages
NAMESPACE_FEEDBACK = "feedback"      # HITL feedback entries
NAMESPACE_REFLECTOR = "reflector"    # verdicts, idioms, rejected_fingerprints
NAMESPACE_KNOWLEDGE = "knowledge"    # knowledge_items, knowledge_fts


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class StorageConfig:
    """Configuration for a namespaced storage adapter."""
    db_path: Path
    namespace: str
    enable_fts: bool = False
    fts_columns: tuple[str, ...] = ()  # columns to include in FTS index
    wal_mode: bool = True
    busy_timeout_s: float = 30.0


@dataclass
class QueryFilter:
    """Generic filter for storage queries."""
    column: str
    operator: str  # =, !=, >, <, >=, <=, LIKE, MATCH
    value: Any


@dataclass
class StorageQuery:
    """Generic storage query."""
    filters: list[QueryFilter] = None
    order_by: str = "created_at"
    order_desc: bool = True
    limit: int = 100
    offset: int = 0

    def __post_init__(self):
        if self.filters is None:
            self.filters = []


# ─── Storage Port ────────────────────────────────────────────────────────────

class StoragePort(ABC):
    """Unified storage protocol — all adapters implement this."""

    @property
    @abstractmethod
    def namespace(self) -> str:
        """Return the namespace this adapter owns."""

    @abstractmethod
    def init_schema(self) -> None:
        """Create tables/indexes for this namespace."""

    @abstractmethod
    def insert(self, table: str, data: dict[str, Any]) -> str:
        """Insert row, return rowid/primary key."""

    @abstractmethod
    def upsert(self, table: str, data: dict[str, Any], conflict_key: str) -> str:
        """Insert or replace on conflict_key."""

    @abstractmethod
    def query(
        self,
        table: str,
        query: StorageQuery,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Query with filters, ordering, pagination."""

    @abstractmethod
    def query_one(
        self,
        table: str,
        query: StorageQuery,
        columns: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Query single row."""

    @abstractmethod
    def delete(self, table: str, query: StorageQuery) -> int:
        """Delete rows matching query, return count."""

    @abstractmethod
    def execute(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """Execute raw SQL (for FTS, complex joins, migrations)."""

    @abstractmethod
    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Execute write SQL, return affected row count."""

    @abstractmethod
    def close(self) -> None:
        """Close connections."""

    @contextmanager
    @abstractmethod
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for atomic transactions."""

    # Convenience methods for common patterns

    @abstractmethod
    def insert_one(
        self, table: str, data: dict[str, Any], id_column: str = "id"
    ) -> str:
        """Insert single row, return id."""

    @abstractmethod
    def query_by_id(
        self, table: str, row_id: str, columns: list[str] | None = None
    ) -> dict[str, Any] | None:
        """Query by primary key."""

    @abstractmethod
    def soft_delete(
        self, table: str, row_id: str, id_column: str = "id"
    ) -> int:
        """Soft delete row (sets deleted_at timestamp)."""

    @abstractmethod
    def exists(self, table: str, query: StorageQuery) -> bool:
        """Check if row exists matching query."""

    @abstractmethod
    def count(self, table: str, query: StorageQuery) -> int:
        """Count rows matching query."""


# ─── Helper: Build WHERE clause ──────────────────────────────────────────────

def build_where(filters: list[QueryFilter]) -> tuple[str, list[Any]]:
    """Build WHERE clause and params from filters."""
    if not filters:
        return "", []
    clauses = []
    params = []
    for f in filters:
        if f.operator == "MATCH":
            clauses.append(f"{f.column} MATCH ?")
        else:
            clauses.append(f"{f.column} {f.operator} ?")
        params.append(f.value)
    return " WHERE " + " AND ".join(clauses), params


def build_order_by(order_by: str, desc: bool) -> str:
    return f" ORDER BY {order_by} {'DESC' if desc else 'ASC'}"


def build_limit(limit: int, offset: int) -> tuple[str, list[int]]:
    return " LIMIT ? OFFSET ?", [limit, offset]