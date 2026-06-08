from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class KnowledgeKind(str, Enum):
    IDIOM = "idiom"
    FEEDBACK = "feedback"
    VERDICT = "verdict"
    INSIGHT = "insight"
    MUTATION = "mutation"
    SPEC_FACT = "spec_fact"


class KnowledgeResult(BaseModel):
    id: str
    kind: KnowledgeKind
    key: str
    value: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    source: str = ""
    confidence: float = 0.0
    created_at: str = ""
    tags: list[str] = Field(default_factory=list)
    ttl_seconds: int = 0
    schema_version: int = 1

    def __init__(self, **data):
        super().__init__(**data)
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_event_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "key": self.key,
            "summary": self.summary[:200],
            "source": self.source,
            "confidence": self.confidence,
            "tags": self.tags,
        }
