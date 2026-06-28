"""SQLiteMemoryRepository — FTS5-backed memory adapter (ADR-011).

Schema
------
  memory_entries      — raw entries written by agent_sync
  memory_fts          — FTS5 virtual table over memory_entries
  memory_patterns     — cross-session patterns (promoted / candidate)

The database lives at: <project_root>/agent_memory/cherenkov_memory.db
Add this file to .gitignore.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from cherenkov.memory.domain.models import (
    EntryKind,
    MemoryEntry,
    MemoryPattern,
    MemoryQuery,
    PromotionRule,
)

_DDL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

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

CREATE TRIGGER IF NOT EXISTS memory_entries_ad
AFTER DELETE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, id, content, task_type, kind)
    VALUES ('delete', old.rowid, old.id, old.content, old.task_type, old.kind);
END;

CREATE TRIGGER IF NOT EXISTS memory_entries_au
AFTER UPDATE ON memory_entries BEGIN
    INSERT INTO memory_fts(memory_fts, rowid, id, content, task_type, kind)
    VALUES ('delete', old.rowid, old.id, old.content, old.task_type, old.kind);
    INSERT INTO memory_fts(rowid, id, content, task_type, kind)
    VALUES (new.rowid, new.id, new.content, new.task_type, new.kind);
END;

CREATE TABLE IF NOT EXISTS memory_patterns (
    fingerprint        TEXT PRIMARY KEY,
    content            TEXT NOT NULL,
    first_seen_session TEXT NOT NULL,
    last_seen_session  TEXT NOT NULL,
    session_count      INTEGER NOT NULL DEFAULT 1,
    task_types         TEXT NOT NULL DEFAULT '[]',  -- JSON array
    is_auto_loaded     INTEGER NOT NULL DEFAULT 0,
    updated_at         TEXT NOT NULL
);
"""


def _fingerprint(text: str) -> str:
    """Normalize + hash text for deduplication."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class SQLiteMemoryRepository:
    """Default MemoryRepository adapter backed by SQLite FTS5 (ADR-011)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_DDL)

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

    # ── MemoryRepository protocol ─────────────────────────────────────

    def save_entry(self, entry: MemoryEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory_entries
                  (id, session_id, task_type, kind, content, tags,
                   recurrence, is_promoted, promoted_at, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry.id,
                    entry.session_id,
                    entry.task_type,
                    entry.kind.value,
                    entry.content,
                    json.dumps(entry.tags),
                    entry.recurrence_count,
                    int(entry.is_promoted),
                    entry.promoted_at.isoformat() if entry.promoted_at else None,
                    entry.created_at.isoformat(),
                ),
            )

    def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        with self._connect() as conn:
            clauses: list[str] = []
            params: list = []

            if query.query:
                # FTS5 match — AND-join terms, fallback to LIKE on empty
                fts_query = " AND ".join(
                    f'"{t}"' for t in query.query.split() if t
                ) or query.query
                clauses.append(
                    "e.rowid IN (SELECT rowid FROM memory_fts WHERE memory_fts MATCH ?)"
                )
                params.append(fts_query)

            if query.task_type:
                clauses.append("e.task_type = ?")
                params.append(query.task_type)

            if query.kind:
                clauses.append("e.kind = ?")
                params.append(query.kind.value)

            if query.promoted_only:
                clauses.append("e.is_promoted = 1")

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            params.append(query.limit)

            rows = conn.execute(
                f"""
                SELECT * FROM memory_entries e
                {where}
                ORDER BY e.created_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [self._row_to_entry(r) for r in rows]

    def get_promoted(self) -> list[MemoryPattern]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_patterns WHERE is_auto_loaded = 1 ORDER BY session_count DESC"
            ).fetchall()
        return [self._row_to_pattern(r) for r in rows]

    def upsert_pattern(self, pattern: MemoryPattern) -> None:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM memory_patterns WHERE fingerprint = ?",
                (pattern.fingerprint,),
            ).fetchone()

            if existing:
                # Merge: update counts, keep first_seen, update last_seen
                merged_task_types = list(
                    set(json.loads(existing["task_types"])) | set(pattern.task_types)
                )
                conn.execute(
                    """
                    UPDATE memory_patterns
                    SET last_seen_session = ?,
                        session_count     = ?,
                        task_types        = ?,
                        updated_at        = ?
                    WHERE fingerprint = ?
                    """,
                    (
                        pattern.last_seen_session,
                        max(existing["session_count"], pattern.session_count),
                        json.dumps(merged_task_types),
                        _now(),
                        pattern.fingerprint,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO memory_patterns
                      (fingerprint, content, first_seen_session, last_seen_session,
                       session_count, task_types, is_auto_loaded, updated_at)
                    VALUES (?,?,?,?,?,?,?,?)
                    """,
                    (
                        pattern.fingerprint,
                        pattern.content,
                        pattern.first_seen_session,
                        pattern.last_seen_session,
                        pattern.session_count,
                        json.dumps(pattern.task_types),
                        int(pattern.is_auto_loaded),
                        _now(),
                    ),
                )

    def promote_pattern(self, fingerprint: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE memory_patterns SET is_auto_loaded = 1, updated_at = ? WHERE fingerprint = ?",
                (_now(), fingerprint),
            )

    def get_pattern(self, fingerprint: str) -> MemoryPattern | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM memory_patterns WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
        return self._row_to_pattern(row) if row else None

    def list_patterns(self, limit: int = 50) -> list[MemoryPattern]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_patterns ORDER BY session_count DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_pattern(r) for r in rows]

    def apply_promotion_rules(self, rule: PromotionRule) -> list[str]:
        """Promote all patterns that meet the PromotionRule threshold."""
        promoted: list[str] = []
        with self._connect() as conn:
            candidates = conn.execute(
                """
                SELECT fingerprint, session_count FROM memory_patterns
                WHERE is_auto_loaded = 0 AND session_count >= ?
                """,
                (rule.min_session_count,),
            ).fetchall()

            for row in candidates:
                conn.execute(
                    "UPDATE memory_patterns SET is_auto_loaded = 1, updated_at = ? WHERE fingerprint = ?",
                    (_now(), row["fingerprint"]),
                )
                promoted.append(row["fingerprint"])

        return promoted

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
        return MemoryEntry(
            id=row["id"],
            session_id=row["session_id"],
            task_type=row["task_type"],
            kind=EntryKind(row["kind"]),
            content=row["content"],
            tags=json.loads(row["tags"]),
            recurrence_count=row["recurrence"],
            is_promoted=bool(row["is_promoted"]),
            promoted_at=(
                datetime.fromisoformat(row["promoted_at"]) if row["promoted_at"] else None
            ),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_pattern(row: sqlite3.Row) -> MemoryPattern:
        return MemoryPattern(
            fingerprint=row["fingerprint"],
            content=row["content"],
            first_seen_session=row["first_seen_session"],
            last_seen_session=row["last_seen_session"],
            session_count=row["session_count"],
            task_types=json.loads(row["task_types"]),
            is_auto_loaded=bool(row["is_auto_loaded"]),
        )


def get_default_repository(project_root: Path) -> SQLiteMemoryRepository:
    """Factory — returns the default SQLite-backed repository."""
    db_path = project_root / "agent_memory" / "cherenkov_memory.db"
    return SQLiteMemoryRepository(db_path)
