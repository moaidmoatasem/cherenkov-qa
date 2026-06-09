from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from cherenkov.chat.domain.models import Session, Message, Role
from cherenkov.chat.ports.memory import ConversationMemory


class SQLiteConversationMemory:
    def __init__(self, db_path: str = "data/chat.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)")
        conn.commit()
        conn.close()

    def create_session(self, session_id: str, persona_id: str = "qa_assistant") -> Session:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, persona_id, created_at, metadata, is_active) "
            "VALUES (?, ?, ?, ?, 1)",
            (session_id, persona_id, datetime.now().isoformat(), "{}"),
        )
        conn.commit()
        conn.close()
        return Session(session_id=session_id, persona_id=persona_id)

    def get_session(self, session_id: str) -> Session | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT session_id, persona_id, created_at, metadata FROM sessions WHERE session_id = ? AND is_active = 1",
            (session_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return Session(
            session_id=row["session_id"],
            persona_id=row["persona_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def add_message(self, session_id: str, message: Message) -> None:
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

    def get_messages(self, session_id: str, limit: int = 50) -> list[Message]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT role, content, timestamp, tool_calls FROM messages WHERE session_id = ? ORDER BY id LIMIT ?",
            (session_id, limit),
        )
        rows = cursor.fetchall()
        conn.close()
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
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def list_sessions(self, limit: int = 20) -> list[Session]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT session_id, persona_id, created_at, metadata FROM sessions WHERE is_active = 1 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            Session(
                session_id=row["session_id"],
                persona_id=row["persona_id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            for row in rows
        ]
