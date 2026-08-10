"""MemSearchMemoryRepository — Semantic vector search memory adapter (Phase 9).

This adapter wraps the SQLiteMemoryRepository to provide semantic search
over memory entries using Milvus/MemSearch, while delegating structured
pattern storage to SQLite.
"""
from __future__ import annotations

from pathlib import Path

from cherenkov.memory.adapters.sqlite_memory import SQLiteMemoryRepository
from cherenkov.memory.domain.models import (
    EntryKind,
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
    """Semantic MemoryRepository adapter backed by MemSearch/Milvus.

    Attributes:
        _sqlite (SQLiteMemoryRepository): Fallback SQLite repository instance.
        _workspace_dir (Path): Workspace root path for MemSearch index scope.
        _ms (memsearch.MemSearch | None): MemSearch client instance if available.
    """

    def __init__(self, db_path: Path, workspace_dir: Path) -> None:
        """Initialize MemSearchMemoryRepository with SQLite fallback.

        Args:
            db_path (Path): Path to SQLite database file.
            workspace_dir (Path): Path to workspace directory for vector index.

        Returns:
            None
        """
        self._sqlite = SQLiteMemoryRepository(db_path)
        self._workspace_dir = workspace_dir
        if memsearch:
            try:
                self._ms = memsearch.MemSearch(paths=[str(workspace_dir)])
            except Exception:
                # MemSearch eagerly builds its embedding client and raises if
                # credentials/config are missing — honor this adapter's
                # documented SQLite fallback instead of crashing at init.
                self._ms = None
        else:
            self._ms = None

    def save_entry(self, entry: MemoryEntry) -> None:
        """Persist a single MemoryEntry to SQLite (MemSearch auto-indexes markdown).

        Args:
            entry (MemoryEntry): Memory entry object to persist.

        Returns:
            None
        """
        self._sqlite.save_entry(entry)

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Semantic search over memory entries using MemSearch.

        Falls back to SQLite FTS if MemSearch is unavailable or returns no results.

        Args:
            query (MemoryQuery): Search parameters and filtering options.

        Returns:
            list[MemoryEntry]: Retrieved memory entries matching query criteria.
        """
        if not self._ms:
            return self._sqlite.search(query)

        # Use MemSearch for semantic retrieval
        q_str = query.query
        try:
            results = self._ms.search(q_str, top_k=query.limit)

            # MemSearch returns raw chunks, we wrap them in MemoryEntry format
            # In a real hybrid setup, we'd cross-reference with SQLite IDs,
            # but for Phase 9 we wrap the semantic chunks.
            entries = []
            for i, r in enumerate(results):
                # Some MemSearch objects have 'id' and 'content', others use dicts
                content = getattr(r, "content", "") if hasattr(r, "content") else r.get("content", "")
                r_id = getattr(r, "id", "") if hasattr(r, "id") else r.get("id", "")

                entries.append(
                    MemoryEntry(
                        id=r_id or f"memsearch-{i}",
                        session_id="memsearch",
                        task_type=query.task_type or "search",
                        kind=query.kind or EntryKind.CONTEXT,
                        content=content,
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
        """Return all auto-promoted patterns.

        Returns:
            list[MemoryPattern]: List of promoted memory patterns.
        """
        return self._sqlite.get_promoted()

    def upsert_pattern(self, pattern: MemoryPattern) -> None:
        """Insert or update a MemoryPattern.

        Args:
            pattern (MemoryPattern): Memory pattern to upsert.

        Returns:
            None
        """
        self._sqlite.upsert_pattern(pattern)

    def promote_pattern(self, fingerprint: str) -> None:
        """Mark a pattern as auto-loaded.

        Args:
            fingerprint (str): Unique fingerprint of pattern to promote.

        Returns:
            None
        """
        self._sqlite.promote_pattern(fingerprint)

    def get_pattern(self, fingerprint: str) -> MemoryPattern | None:
        """Fetch a pattern by fingerprint.

        Args:
            fingerprint (str): Unique fingerprint hash of the pattern.

        Returns:
            MemoryPattern | None: Pattern if found, else None.
        """
        return self._sqlite.get_pattern(fingerprint)

    def list_patterns(self, limit: int = 50) -> list[MemoryPattern]:
        """List all patterns ordered by session count.

        Args:
            limit (int): Maximum number of patterns to return. Defaults to 50.

        Returns:
            list[MemoryPattern]: List of memory patterns.
        """
        return self._sqlite.list_patterns(limit)

    def apply_promotion_rules(self, rule: PromotionRule) -> list[str]:
        """Apply promotion rules and promote eligible patterns.

        Args:
            rule (PromotionRule): Rule defining promotion criteria.

        Returns:
            list[str]: List of fingerprints promoted during this call.
        """
        return self._sqlite.apply_promotion_rules(rule)

