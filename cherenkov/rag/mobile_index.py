"""
cherenkov/rag/mobile_index.py — Issue #366: Mobile RAG Index.
Per-app knowledge retrieval using SQLite.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from typing import Any


class MobileRAGIndex:
    def __init__(self, index_path: str = "data/mobile_rag.db"):
        self.index_path = index_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)
        con = sqlite3.connect(self.index_path, timeout=5.0)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mobile_apps (
                    app_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    description TEXT,
                    screens TEXT DEFAULT '[]',
                    flows TEXT DEFAULT '[]'
                )
            """)
            conn.commit()

    def index_app(
        self,
        app_id: str,
        name: str,
        platform: str,
        description: str,
        screens: list[dict[str, Any]] | None = None,
        flows: list[dict[str, Any]] | None = None,
    ) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO mobile_apps
                   (app_id, name, platform, description, screens, flows)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    app_id,
                    name,
                    platform,
                    description,
                    json.dumps(screens or []),
                    json.dumps(flows or []),
                ),
            )
            conn.commit()

    def query(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                """SELECT * FROM mobile_apps
                   WHERE description LIKE ?
                   LIMIT ?""",
                (f"%{query}%", limit),
            )
            results = []
            for row in cursor.fetchall():
                item = dict(row)
                item["screens"] = json.loads(item.get("screens", "[]"))
                item["flows"] = json.loads(item.get("flows", "[]"))
                results.append(item)
            return results
