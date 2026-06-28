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
    """A single unit of accumulated agent memory."""

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
        """Return a copy of this entry marked as promoted."""
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
    """

    min_session_count: int = 3
    """Number of distinct sessions a pattern must appear in before promotion."""

    min_recurrence_count: int = 1
    """Minimum raw recurrence count (per session) — filters noise."""

    def should_promote(self, pattern: MemoryPattern) -> bool:
        """Return True if the pattern meets promotion criteria."""
        return (
            pattern.session_count >= self.min_session_count
            and not pattern.is_auto_loaded
        )


@dataclass
class MemoryQuery:
    """Parameters for a memory search query."""

    query: str = ""
    task_type: str | None = None
    kind: EntryKind | None = None
    promoted_only: bool = False
    limit: int = 20
