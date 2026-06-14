from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime

from cherenkov.chat.domain.models import Session, Message


class SQLiteConversationMemory:
    def __init__(self, db_path: str = "data/chat.db"):
        import os

        # Resolve relative path against the project root so it works regardless of cwd
        if not os.path.isabs(db_path):
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            db_path = os.path.join(root, db_path)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
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
        con = sqlite3.connect(self.db_path, timeout=30.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys = ON")
        self._local.con = con
        return con

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "session_id TEXT PRIMARY KEY,"
            "persona_id TEXT NOT NULL DEFAULT 'qa_assistant',"
            "created_at TEXT NOT NULL,"
            "metadata TEXT DEFAULT '{}',"
            "is_active INTEGER DEFAULT 1"
            ")"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS messages ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "session_id TEXT NOT NULL,"
            "role TEXT NOT NULL,"
            "content TEXT NOT NULL,"
            "timestamp TEXT NOT NULL,"
            "tool_calls TEXT,"
            "FOREIGN KEY (session_id) REFERENCES sessions(session_id)"
            ")"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)"
        )
        conn.commit()

    def create_session(
        self, session_id: str, persona_id: str = "qa_assistant"
    ) -> Session:
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, persona_id, created_at, metadata, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            (session_id, persona_id, datetime.now().isoformat(), "{}"),
        )
        conn.commit()
        return Session(session_id=session_id, persona_id=persona_id)

    def get_session(self, session_id: str) -> Session | None:
        conn = self._connect()
        cursor = conn.execute(
            "SELECT session_id, persona_id, created_at, metadata FROM sessions WHERE session_id = ? AND is_active = 1",
            (session_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Session(
            session_id=row["session_id"],
            persona_id=row["persona_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def add_message(self, session_id: str, message: Message) -> None:
        conn = self._connect()
        conn.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, tool_calls) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                message.role,
                message.content,
                message.timestamp.isoformat(),
                json.dumps(message.tool_calls) if message.tool_calls else None,
            ),
        )
        conn.commit()

    def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        conn = self._connect()
        cursor = conn.execute(
            "SELECT role, content, timestamp, tool_calls FROM messages WHERE session_id = ? ORDER BY id LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        return [
            Message(
                role=row["role"],
                content=row["content"],
                session_id=session_id,
                timestamp=datetime.fromisoformat(row["timestamp"]),
                tool_calls=json.loads(row["tool_calls"]) if row["tool_calls"] else None,
            )
            for row in rows
        ]

    def close_session(self, session_id: str) -> None:
        conn = self._connect()
        conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,)
        )
        conn.commit()

    def list_sessions(self, limit: int = 20) -> list[Session]:
        conn = self._connect()
        cursor = conn.execute(
            "SELECT session_id, persona_id, created_at, metadata FROM sessions WHERE is_active = 1 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            Session(
                session_id=row["session_id"],
                persona_id=row["persona_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            for row in rows
        ]

    def close(self) -> None:
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None
