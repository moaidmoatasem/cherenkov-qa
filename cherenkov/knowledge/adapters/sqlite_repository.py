from __future__ import annotations

import json
import sqlite3
from typing import Any

from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeQueryResult, KnowledgeItem


class SQLiteKnowledgeRepository:
    def __init__(self, db_path: str = "data/knowledge.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult:
        conn = sqlite3.connect(self.db_path)
        sql = "SELECT item_id, source, data, metadata FROM knowledge_items"
        params: list[Any] = []
        if query.source:
            sql += " WHERE source = ?"
            params.append(query.source)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(query.limit)
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
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
        return KnowledgeQueryResult(
            data=results,
            source=query.source or "all",
            confidence=1.0,
            metadata={"count": len(results)},
        )

    def store(self, item: KnowledgeItem) -> str:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_items (item_id, source, data, metadata) VALUES (?, ?, ?, ?)",
            (item.item_id, item.source, json.dumps(item.data), json.dumps(item.metadata)),
        )
        conn.commit()
        conn.close()
        return item.item_id

    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]:
        conn = sqlite3.connect(self.db_path)
        # FTS5 match (indexed) — falls back to LIKE scan if FTS table is missing
        try:
            cursor = conn.execute(
                "SELECT k.item_id, k.source, k.data, k.metadata "
                "FROM knowledge_items k "
                "JOIN knowledge_fts f ON k.item_id = f.item_id "
                "WHERE knowledge_fts MATCH ? LIMIT ?",
                (f'"{pattern}"', limit),
            )
        except sqlite3.OperationalError:
            cursor = conn.execute(
                "SELECT item_id, source, data, metadata FROM knowledge_items WHERE data LIKE ? LIMIT ?",
                (f"%{pattern}%", limit),
            )
        rows = cursor.fetchall()
        conn.close()
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT item_id, source, data, metadata FROM knowledge_items WHERE item_id = ?",
            (item_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return KnowledgeQueryResult(
            data=json.loads(row[2]),
            source=row[1],
            confidence=1.0,
            metadata=json.loads(row[3]) if row[3] else {},
        )
