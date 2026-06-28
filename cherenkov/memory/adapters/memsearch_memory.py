"""MemSearchMemoryRepository — Semantic vector search memory adapter (Phase 9).

This adapter wraps the SQLiteMemoryRepository to provide semantic search
over memory entries using Milvus/MemSearch, while delegating structured
pattern storage to SQLite.
"""
from __future__ import annotations

from pathlib import Path

from cherenkov.memory.adapters.sqlite_memory import SQLiteMemoryRepository
from cherenkov.memory.domain.models import (
    MemoryEntry,
    MemoryPattern,
    MemoryQuery,
)
from cherenkov.memory.ports.repository import MemoryRepository

try:
    import memsearch
except ImportError:
    memsearch = None


class MemSearchMemoryRepository(MemoryRepository):
    """Semantic MemoryRepository adapter backed by MemSearch/Milvus."""

    def __init__(self, db_path: Path, workspace_dir: Path) -> None:
        self._sqlite = SQLiteMemoryRepository(db_path)
        self._workspace_dir = workspace_dir
        if memsearch:
            self._ms = memsearch.MemSearch(workspace_dir=str(workspace_dir))
        else:
            self._ms = None

    def save_entry(self, entry: MemoryEntry) -> None:
        """Persist a single MemoryEntry to SQLite (MemSearch auto-indexes markdown)."""
        self._sqlite.save_entry(entry)

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Semantic search over memory entries using MemSearch.
        
        Falls back to SQLite FTS if MemSearch is unavailable.
        """
        if not self._ms:
            return self._sqlite.search(query)

        # Use MemSearch for semantic retrieval
        q_str = query.term or " ".join(query.tags)
        try:
            results = self._ms.search(q_str, limit=query.limit)

            # MemSearch returns raw chunks, we wrap them in MemoryEntry format
            # In a real hybrid setup, we'd cross-reference with SQLite IDs,
            # but for Phase 9 we wrap the semantic chunks.
            entries = []
            for r in results:
                # Some MemSearch objects have 'id' and 'content', others use dicts
                content = getattr(r, "content", "") if hasattr(r, "content") else r.get("content", "")
                r_id = getattr(r, "id", "") if hasattr(r, "id") else r.get("id", "")

                entries.append(
                    MemoryEntry(
                        session_id=r_id or "memsearch",
                        task_type=query.term or "search",
                        content=content,
                        tags=query.tags,
                    )
                )

            if entries:
                return entries
            # Fallback to SQLite if MemSearch returns empty
            return self._sqlite.search(query)
        except Exception:
            # Fallback to SQLite FTS on any vector search error
            return self._sqlite.search(query)

    def get_promoted(self) -> list[MemoryPattern]:
        return self._sqlite.get_promoted()

    def upsert_pattern(self, pattern: MemoryPattern) -> None:
        self._sqlite.upsert_pattern(pattern)

    def promote_pattern(self, fingerprint: str) -> None:
        self._sqlite.promote_pattern(fingerprint)

    def get_pattern(self, fingerprint: str) -> MemoryPattern | None:
        return self._sqlite.get_pattern(fingerprint)

    def list_patterns(self, limit: int = 50) -> list[MemoryPattern]:
        return self._sqlite.list_patterns(limit)
