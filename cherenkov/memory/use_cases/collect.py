"""Auto-extract memory patterns from agent_sync findings (use case)."""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone

from cherenkov.memory.domain.models import (
    EntryKind,
    MemoryEntry,
    MemoryPattern,
)
from cherenkov.memory.ports.repository import MemoryRepository


def collect_from_findings(
    *,
    session_id: str,
    task_type: str,
    findings: list[dict],
    repo: MemoryRepository,
) -> list[MemoryEntry]:
    """Persist findings from agent_sync as MemoryEntry records.

    Also extracts candidate MemoryPattern records from recurring content
    and upserts them into the pattern store.

    Args:
        session_id: The current SDD session ID.
        task_type: The task type string from ``agent_sync before``.
        findings: Raw list of finding dicts from the session JSON files.
        repo: MemoryRepository instance to write to.

    Returns:
        List of MemoryEntry objects that were saved.
    """
    saved: list[MemoryEntry] = []
    now = datetime.now(tz=timezone.utc)

    for f in findings:
        kind_str = f.get("type", "finding")
        try:
            kind = EntryKind(kind_str)
        except ValueError:
            kind = EntryKind.FINDING

        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            session_id=session_id,
            task_type=task_type,
            kind=kind,
            content=f.get("message", ""),
            created_at=now,
            tags=f.get("tags", []),
        )
        repo.save_entry(entry)
        saved.append(entry)

        # Auto-extract a candidate pattern from significant findings
        if kind in (EntryKind.PITFALL, EntryKind.DECISION) and entry.content:
            pattern = _extract_pattern(entry, session_id, task_type)
            repo.upsert_pattern(pattern)

    return saved


def _extract_pattern(
    entry: MemoryEntry,
    session_id: str,
    task_type: str,
) -> MemoryPattern:
    """Derive a MemoryPattern from a finding entry."""
    # Normalize: strip file paths, session IDs, timestamps
    cleaned = re.sub(r"sess_\w+", "<session>", entry.content)
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.Z+-]+", "<ts>", cleaned)
    cleaned = re.sub(r"/[^\s]+", "<path>", cleaned)
    normalized = " ".join(cleaned.lower().split())

    fingerprint = hashlib.sha256(normalized.encode()).hexdigest()[:16]

    return MemoryPattern(
        fingerprint=fingerprint,
        content=entry.content,  # Keep original for readability
        first_seen_session=session_id,
        last_seen_session=session_id,
        session_count=1,
        task_types=[task_type],
    )
