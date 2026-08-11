from __future__ import annotations

from cherenkov.knowledge.domain.models import KnowledgeQuery, KnowledgeQueryResult
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository


class QueryKnowledgeUseCase:
    """Query the knowledge mesh with a free-text query, optionally filtered by source."""

    def __init__(self, repository: KnowledgeMeshRepository):
        self._repository = repository

    def execute(
        self, query: str, source: str | None = None, limit: int = 10
    ) -> KnowledgeQueryResult:
        q = KnowledgeQuery(query=query, source=source, limit=limit)
        return self._repository.query(q)
