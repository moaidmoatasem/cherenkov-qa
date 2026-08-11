from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class KnowledgeQuery:
    query: str
    source: str | None = None
    limit: int = 10
    filter: dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeQueryResult:
    data: Any
    source: str
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeItem:
    item_id: str
    source: str
    data: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
