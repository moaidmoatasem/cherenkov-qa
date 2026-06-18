from __future__ import annotations

import json
import os
import sqlite3
import threading
from typing import Any

from cherenkov.knowledge.domain.models import (
    KnowledgeQuery,
    KnowledgeQueryResult,
    KnowledgeItem,
)

_BUSY_TIMEOUT_S = 30.0


class SQLiteKnowledgeRepository:
    def __init__(self, db_path: str = "data/knowledge.db"):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Return a per-thread cached connection; reconnects if the connection is dead."""
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except Exception:
                pass
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        con = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        con.execute("PRAGMA journal_mode=WAL")
        self._local.con = con
        return con

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS knowledge_items ("
            "item_id TEXT PRIMARY KEY,"
            "source TEXT NOT NULL,"
            "data TEXT NOT NULL,"
            "metadata TEXT,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            ")"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON knowledge_items(source)")
        # FTS5 index for fast full-text search (replaces LIKE '%x%' full-table-scan)
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts "
            "USING fts5(item_id UNINDEXED, data, content='knowledge_items', content_rowid='rowid')"
        )
        # Keep FTS in sync with the content table
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS knowledge_fts_insert
                AFTER INSERT ON knowledge_items BEGIN
                    INSERT INTO knowledge_fts(rowid, item_id, data)
                    VALUES (new.rowid, new.item_id, new.data);
                END;
            CREATE TRIGGER IF NOT EXISTS knowledge_fts_delete
                AFTER DELETE ON knowledge_items BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, item_id, data)
                    VALUES ('delete', old.rowid, old.item_id, old.data);
                END;
            CREATE TRIGGER IF NOT EXISTS knowledge_fts_update
                AFTER UPDATE ON knowledge_items BEGIN
                    INSERT INTO knowledge_fts(knowledge_fts, rowid, item_id, data)
                    VALUES ('delete', old.rowid, old.item_id, old.data);
                    INSERT INTO knowledge_fts(rowid, item_id, data)
                    VALUES (new.rowid, new.item_id, new.data);
                END;
        """)
        conn.commit()
        self._ensure_fts_populated(conn)

    def _ensure_fts_populated(self, conn: sqlite3.Connection) -> None:
        """Retroactively populate the FTS shadow table on existing DBs.

        The triggers only fire on future writes, so a DB created before the FTS
        table was added has an empty shadow table.  `INSERT INTO … rebuild` is a
        safe no-op when the shadow table is already in sync.
        """
        (fts_count,) = conn.execute("SELECT COUNT(*) FROM knowledge_fts").fetchone()
        (items_count,) = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()
        if fts_count < items_count:
            conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES ('rebuild')")
            conn.commit()

    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult:
        conn = self._connect()
        sql = "SELECT item_id, source, data, metadata FROM knowledge_items"
        params: list[Any] = []
        if query.source:
            sql += " WHERE source = ?"
            params.append(query.source)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(query.limit)
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        items = []
        for row in rows:
            items.append(
                KnowledgeItem(
                    item_id=row[0],
                    source=row[1],
                    data=json.loads(row[2]),
                    metadata=json.loads(row[3]) if row[3] else {},
                )
            )
        return KnowledgeQueryResult(
            data=items,
            source=query.source or "all",
            confidence=1.0,
            metadata={"count": len(items)},
        )

    def store(self, item: KnowledgeItem) -> str:
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_items (item_id, source, data, metadata) VALUES (?, ?, ?, ?)",
            (
                item.item_id,
                item.source,
                json.dumps(item.data),
                json.dumps(item.metadata),
            ),
        )
        conn.commit()
        return item.item_id

    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]:
        conn = self._connect()
        # FTS5 match (indexed) — falls back to LIKE scan if FTS table is missing.
        # Tokenize and quote each term individually (AND-joined) rather than wrapping
        # the whole pattern in one phrase query: a literal phrase match only finds
        # exact contiguous substrings and also lets raw FTS5 syntax (NEAR, -, *) leak
        # in from user input. Per-term quoting keeps multi-word queries matchable
        # while still escaping special characters safely.
        terms = [t for t in pattern.split() if t]
        try:
            if not terms:
                raise sqlite3.OperationalError("empty pattern")
            fts_query = " AND ".join(f'"{t}"' for t in terms)
            # Join on rowid (the FTS shadow-table integer key) rather than item_id TEXT
            # to avoid an UNINDEXED join predicate that forces a full-table scan.
            cursor = conn.execute(
                "SELECT k.item_id, k.source, k.data, k.metadata "
                "FROM knowledge_items k "
                "JOIN knowledge_fts f ON k.rowid = f.rowid "
                "WHERE knowledge_fts MATCH ? LIMIT ?",
                (fts_query, limit),
            )
            rows = cursor.fetchall()
            if not rows:
                raise sqlite3.OperationalError("no FTS matches, falling back to LIKE")
        except sqlite3.OperationalError:
            cursor = conn.execute(
                "SELECT item_id, source, data, metadata FROM knowledge_items WHERE data LIKE ? LIMIT ?",
                (f"%{pattern}%", limit),
            )
            rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append(
                KnowledgeQueryResult(
                    data=json.loads(row[2]),
                    source=row[1],
                    confidence=1.0,
                    metadata=json.loads(row[3]) if row[3] else {},
                )
            )
        return results

    def get_by_id(self, item_id: str) -> KnowledgeQueryResult | None:
        conn = self._connect()
        cursor = conn.execute(
            "SELECT item_id, source, data, metadata FROM knowledge_items WHERE item_id = ?",
            (item_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return KnowledgeQueryResult(
            data=json.loads(row[2]),
            source=row[1],
            confidence=1.0,
            metadata=json.loads(row[3]) if row[3] else {},
        )

    def close(self) -> None:
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None
