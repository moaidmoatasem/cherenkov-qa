from __future__ import annotations

import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class EventCategory(str, Enum):
    PIPELINE = "pipeline"
    HITL = "hitl"
    HEALING = "healing"
    REFLECTOR = "reflector"
    KNOWLEDGE = "knowledge"
    CHAT = "chat"
    VLM = "vlm"
    MOBILE = "mobile"
    SYSTEM = "system"


class EventSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class CHERENKOVEvent:
    category: EventCategory
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    severity: EventSeverity = EventSeverity.INFO
    event_id: str = ""
    timestamp: float = 0.0
    source: str = ""
    correlation_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())[:12]
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "name": self.name,
            "severity": self.severity.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def pipeline_start(cls, run_id: str, scenarios: int = 0) -> CHERENKOVEvent:
        return cls(
            category=EventCategory.PIPELINE,
            name="pipeline.start",
            payload={"run_id": run_id, "scenarios": scenarios},
            correlation_id=run_id,
        )

    @classmethod
    def pipeline_complete(cls, run_id: str, success: bool, passed: int = 0, total: int = 0) -> CHERENKOVEvent:
        return cls(
            category=EventCategory.PIPELINE,
            name="pipeline.complete",
            payload={"run_id": run_id, "success": success, "passed": passed, "total": total},
            severity=EventSeverity.INFO if success else EventSeverity.WARNING,
            correlation_id=run_id,
        )

    @classmethod
    def hitl_approved(cls, item_id: str, actor: str = "") -> CHERENKOVEvent:
        return cls(
            category=EventCategory.HITL,
            name="hitl.approved",
            payload={"item_id": item_id, "actor": actor},
            severity=EventSeverity.INFO,
            correlation_id=item_id,
        )

    @classmethod
    def hitl_rejected(cls, item_id: str, reason: str = "", actor: str = "") -> CHERENKOVEvent:
        return cls(
            category=EventCategory.HITL,
            name="hitl.rejected",
            payload={"item_id": item_id, "reason": reason, "actor": actor},
            severity=EventSeverity.WARNING,
            correlation_id=item_id,
        )

    @classmethod
    def healing_suggested(cls, scenario_id: str, healer: str) -> CHERENKOVEvent:
        return cls(
            category=EventCategory.HEALING,
            name="healing.suggested",
            payload={"scenario_id": scenario_id, "healer": healer},
            correlation_id=scenario_id,
        )

    @classmethod
    def knowledge_stored(cls, key: str, source: str) -> CHERENKOVEvent:
        return cls(
            category=EventCategory.KNOWLEDGE,
            name="knowledge.stored",
            payload={"key": key, "source": source},
            correlation_id=key,
        )

    @classmethod
    def system_health(cls, status: str, detail: str = "") -> CHERENKOVEvent:
        return cls(
            category=EventCategory.SYSTEM,
            name="system.health",
            payload={"status": status, "detail": detail},
            severity=EventSeverity.WARNING if status != "ok" else EventSeverity.INFO,
        )
