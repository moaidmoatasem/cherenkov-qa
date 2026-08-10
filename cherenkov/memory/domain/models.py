"""Auto-Memory Engine — domain models.

Pure business logic; no I/O, no external deps (ADR-004).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EntryKind(str, Enum):
    """Classification of a memory entry."""

    FINDING = "finding"
    DECISION = "decision"
    PITFALL = "pitfall"
    CONTEXT = "context"
    PATTERN = "pattern"  # promoted / auto-extracted cross-session pattern


@dataclass
class MemoryEntry:
    """A single unit of accumulated agent memory.

    Attributes:
        id (str): Unique identifier for the memory entry.
        session_id (str): ID of the session in which this memory was created.
        task_type (str): Category of task being executed when recorded.
        kind (EntryKind): Classification of the entry (finding, decision, etc.).
        content (str): Textual body of the memory item.
        created_at (datetime): UTC timestamp when recorded. Defaults to current UTC time.
        tags (list[str]): Optional list of associated tags. Defaults to empty list.
        recurrence_count (int): Frequency count of how often this memory has recurred. Defaults to 0.
        is_promoted (bool): Whether this entry has been promoted to a pattern. Defaults to False.
        promoted_at (datetime | None): UTC timestamp when promoted, if applicable. Defaults to None.
    """

    id: str
    session_id: str
    task_type: str
    kind: EntryKind
    content: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    tags: list[str] = field(default_factory=list)

    # Promotion tracking
    recurrence_count: int = 0
    is_promoted: bool = False
    promoted_at: datetime | None = None

    def promote(self) -> MemoryEntry:
        """Return a new MemoryEntry marked as a promoted cross-session pattern.

        Returns:
            MemoryEntry: A copy of this entry with kind set to EntryKind.PATTERN,
                is_promoted set to True, and promoted_at set to current UTC time.
        """
        return MemoryEntry(
            id=self.id,
            session_id=self.session_id,
            task_type=self.task_type,
            kind=EntryKind.PATTERN,
            content=self.content,
            created_at=self.created_at,
            tags=self.tags,
            recurrence_count=self.recurrence_count,
            is_promoted=True,
            promoted_at=datetime.now(tz=timezone.utc),
        )


@dataclass
class MemoryPattern:
    """A cross-session pattern automatically extracted from findings.

    Promoted patterns are injected into every future ``before`` context load
    without requiring a search query — they are "always relevant."

    Attributes:
        fingerprint (str): Normalized text hash used for deduplication.
        content (str): Human-readable pattern description.
        first_seen_session (str): Session ID where pattern was first recorded.
        last_seen_session (str): Session ID where pattern was most recently recorded.
        session_count (int): Number of distinct sessions this pattern appeared in.
        task_types (list[str]): Task types under which this pattern appeared.
        is_auto_loaded (bool): True once promoted past threshold for auto-injection.
    """

    fingerprint: str          # Normalized text hash used for deduplication
    content: str              # Human-readable pattern description
    first_seen_session: str
    last_seen_session: str
    session_count: int        # Number of distinct sessions this appeared in
    task_types: list[str]     # Task types this pattern appeared under
    is_auto_loaded: bool = False   # True once promoted past threshold


@dataclass
class PromotionRule:
    """Policy governing when a MemoryPattern is promoted to auto-load.

    Configurable via ``cherenkov.toml [memory] auto_promote_threshold``.

    Attributes:
        min_session_count (int): Number of distinct sessions a pattern must appear in.
        min_recurrence_count (int): Minimum raw recurrence count per session.
    """

    min_session_count: int = 3
    """Number of distinct sessions a pattern must appear in before promotion."""

    min_recurrence_count: int = 1
    """Minimum raw recurrence count (per session) — filters noise."""

    def should_promote(self, pattern: MemoryPattern) -> bool:
        """Determine whether the specified pattern meets promotion criteria.

        Args:
            pattern (MemoryPattern): The memory pattern candidate to evaluate.

        Returns:
            bool: True if pattern session count meets or exceeds min_session_count
                and is not already auto-loaded; False otherwise.
        """
        return (
            pattern.session_count >= self.min_session_count
            and not pattern.is_auto_loaded
        )


@dataclass
class MemoryQuery:
    """Parameters and filter options for querying stored memory entries.

    Attributes:
        query (str): The search query string for text matching. Defaults to "".
        task_type (str | None): Optional filter for specific task type. Defaults to None.
        kind (EntryKind | None): Optional filter by entry classification. Defaults to None.
        promoted_only (bool): Whether to limit results to promoted patterns. Defaults to False.
        limit (int): Maximum number of memory entries to return. Defaults to 20.
    """

    query: str = ""
    task_type: str | None = None
    kind: EntryKind | None = None
    promoted_only: bool = False
    limit: int = 20

