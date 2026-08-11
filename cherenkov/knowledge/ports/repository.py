from __future__ import annotations

from typing import Protocol

from cherenkov.knowledge.domain.models import (
    KnowledgeItem,
    KnowledgeQuery,
    KnowledgeQueryResult,
)


class KnowledgeMeshRepository(Protocol):
    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult: ...

    def store(self, item: KnowledgeItem) -> str: ...

    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]: ...

    def get_by_id(self, item_id: str) -> KnowledgeQueryResult | None: ...
