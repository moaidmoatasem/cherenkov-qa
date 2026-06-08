from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Role = Literal["user", "assistant", "system", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: list[dict] | None = None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": self.tool_calls,
        }


@dataclass
class Session:
    session_id: str
    persona_id: str = "qa_assistant"
    created_at: datetime = field(default_factory=datetime.now)
    messages: list[Message] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "persona_id": self.persona_id,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages),
            "metadata": self.metadata,
        }
