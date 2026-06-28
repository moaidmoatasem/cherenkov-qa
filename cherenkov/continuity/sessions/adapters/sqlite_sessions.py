"""SQLite implementation of SessionStore (CC-5)."""
from __future__ import annotations

import datetime
import json
import os
import sqlite3

from cherenkov.continuity.sessions.domain.models import SessionSnapshot, TeleportToken
from cherenkov.continuity.sessions.ports.store import SessionStore


class SQLiteSessionStore(SessionStore):
    def __init__(self, db_path: str = ""):
        self.db_path = db_path or os.path.join(
            os.path.expanduser("~"), ".cherenkov", "cherenkov_sessions.db"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    token TEXT,
                    token_expires_at TEXT,
                    state_data TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
                '''
            )
            conn.commit()

    def save(self, snapshot: SessionSnapshot) -> None:
        with sqlite3.connect(self.db_path) as conn:
            token_str = snapshot.token.token if snapshot.token else None
            token_expires_at = snapshot.token.expires_at.isoformat() if snapshot.token else None
            conn.execute(
                '''
                INSERT OR REPLACE INTO sessions (id, token, token_expires_at, state_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    snapshot.id,
                    token_str,
                    token_expires_at,
                    json.dumps(snapshot.state_data),
                    snapshot.created_at.isoformat(),
                    snapshot.updated_at.isoformat(),
                )
            )
            conn.commit()

    def _row_to_snapshot(self, row: sqlite3.Row) -> SessionSnapshot:
        token = None
        if row["token"] and row["token_expires_at"]:
            token = TeleportToken(
                token=row["token"],
                expires_at=datetime.datetime.fromisoformat(row["token_expires_at"])
            )
        return SessionSnapshot(
            id=row["id"],
            token=token,
            state_data=json.loads(row["state_data"]),
            created_at=datetime.datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.datetime.fromisoformat(row["updated_at"])
        )

    def load(self, session_id: str) -> SessionSnapshot | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_snapshot(row)
        return None

    def list_sessions(self) -> list[SessionSnapshot]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC")
            return [self._row_to_snapshot(row) for row in cursor.fetchall()]

    def find_by_token(self, token_str: str) -> SessionSnapshot | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE token = ?", (token_str,))
            row = cursor.fetchone()
            if row:
                snapshot = self._row_to_snapshot(row)
                if snapshot.token and snapshot.token.expires_at > datetime.datetime.now(datetime.UTC):
                    return snapshot
        return None
