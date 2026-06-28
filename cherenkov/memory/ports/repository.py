"""MemoryRepository — port protocol (ADR-004, ADR-011).

Implementations:
  - cherenkov.memory.adapters.sqlite_memory.SQLiteMemoryRepository (default)
  - Future: MemSearchMemoryRepository (Phase 9 upgrade path)
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from cherenkov.memory.domain.models import (
    MemoryEntry,
    MemoryPattern,
    MemoryQuery,
    PromotionRule,
)


@runtime_checkable
class MemoryRepository(Protocol):
    """Port for reading and writing accumulated agent memory."""

    def save_entry(self, entry: MemoryEntry) -> None:
        """Persist a single MemoryEntry."""
        ...

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Full-text search over memory entries.

        Returns entries ranked by relevance, limited to ``query.limit``.
        """
        ...

    def get_promoted(self) -> list[MemoryPattern]:
        """Return all auto-promoted patterns (always loaded in ``before``)."""
        ...

    def upsert_pattern(self, pattern: MemoryPattern) -> None:
        """Insert or update a MemoryPattern (idempotent on fingerprint)."""
        ...

    def promote_pattern(self, fingerprint: str) -> None:
        """Mark a pattern as auto-loaded (is_auto_loaded = True)."""
        ...

    def get_pattern(self, fingerprint: str) -> MemoryPattern | None:
        """Fetch a single pattern by fingerprint, or None if not found."""
        ...

    def list_patterns(self, limit: int = 50) -> list[MemoryPattern]:
        """List all patterns ordered by session_count desc."""
        ...

    def apply_promotion_rules(self, rule: PromotionRule) -> list[str]:
        """Check all patterns against rule and promote eligible ones.

        Returns list of fingerprints that were promoted in this call.
        """
        ...
