from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeQueryResult
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository


class SearchKnowledgeUseCase:
    """Full-text search across stored knowledge items."""

    def __init__(self, repository: KnowledgeMeshRepository):
        self._repository = repository

    def execute(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]:
        return self._repository.search(pattern, limit=limit)
