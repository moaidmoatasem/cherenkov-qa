from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeItem
from cherenkov.knowledge.ports.repository import KnowledgeRepository


class HITLReflectorBridge:
    def __init__(self, repository: KnowledgeRepository, reflector):
        self.repository = repository
        self.reflector = reflector

    def on_hitl_decision(self, item_id: str, action: str, reason: str, endpoint: str, method: str) -> None:
        item = KnowledgeItem(
            item_id=f"hitl_{item_id}",
            source="hitl",
            data={
                "item_id": item_id,
                "action": action,
                "reason": reason,
                "endpoint": endpoint,
                "method": method,
            },
            metadata={"source": "hitl_reflector_bridge"},
        )
        self.repository.store(item)
        self.reflector.ingest_human_verdict(
            item_id=item_id,
            verdict=action,
            reason=reason,
            endpoint=endpoint,
            method=method,
        )
