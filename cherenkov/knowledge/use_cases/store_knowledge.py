from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeItem
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository


class StoreKnowledgeUseCase:
    """Store a new knowledge item in the mesh."""

    def __init__(self, repository: KnowledgeMeshRepository):
        self._repository = repository

    def execute(self, item: KnowledgeItem) -> str:
        return self._repository.store(item)
