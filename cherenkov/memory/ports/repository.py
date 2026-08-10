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
    """Port interface for reading and writing accumulated agent memory."""

    def save_entry(self, entry: MemoryEntry) -> None:
        """Persist a single MemoryEntry.

        Args:
            entry (MemoryEntry): The memory entry instance to save.

        Returns:
            None
        """
        ...

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Full-text search over memory entries.

        Args:
            query (MemoryQuery): Search query parameters and filtering criteria.

        Returns:
            list[MemoryEntry]: Memory entries matching criteria, ranked by relevance.
        """
        ...

    def get_promoted(self) -> list[MemoryPattern]:
        """Return all auto-promoted patterns.

        Returns:
            list[MemoryPattern]: Patterns marked as auto-loaded.
        """
        ...

    def upsert_pattern(self, pattern: MemoryPattern) -> None:
        """Insert or update a MemoryPattern.

        Args:
            pattern (MemoryPattern): Memory pattern to create or update.

        Returns:
            None
        """
        ...

    def promote_pattern(self, fingerprint: str) -> None:
        """Mark a pattern as auto-loaded (is_auto_loaded = True).

        Args:
            fingerprint (str): Unique fingerprint hash of the pattern to promote.

        Returns:
            None
        """
        ...

    def get_pattern(self, fingerprint: str) -> MemoryPattern | None:
        """Fetch a single pattern by fingerprint.

        Args:
            fingerprint (str): Unique fingerprint hash of the pattern.

        Returns:
            MemoryPattern | None: The matching MemoryPattern if found, else None.
        """
        ...

    def list_patterns(self, limit: int = 50) -> list[MemoryPattern]:
        """List all patterns ordered by session_count desc.

        Args:
            limit (int): Maximum number of patterns to return. Defaults to 50.

        Returns:
            list[MemoryPattern]: List of retrieved memory patterns.
        """
        ...

    def apply_promotion_rules(self, rule: PromotionRule) -> list[str]:
        """Check all patterns against rule and promote eligible ones.

        Args:
            rule (PromotionRule): Promotion criteria rule to apply.

        Returns:
            list[str]: Fingerprints of patterns that were promoted during this operation.
        """
        ...

