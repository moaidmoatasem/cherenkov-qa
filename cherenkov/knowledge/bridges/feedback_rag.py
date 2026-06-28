from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeItem
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository


class FeedbackRAGBridge:
    def __init__(self, repository: KnowledgeMeshRepository, feedback_store):
        self.repository = repository
        self.feedback_store = feedback_store

    def sync_feedback(self) -> int:
        entries = self.feedback_store.list_all()
        count = 0
        for entry in entries:
            item = KnowledgeItem(
                item_id=f"feedback_{entry.id}",
                source="feedback",
                data={
                    "endpoint": entry.endpoint,
                    "method": entry.method,
                    "reason": entry.reason,
                    "comment": entry.comment,
                },
                metadata={
                    "feedback_id": entry.id,
                    "created_at": str(entry.created_at),
                },
            )
            self.repository.store(item)
            count += 1
        return count
