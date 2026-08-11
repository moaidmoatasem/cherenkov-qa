from __future__ import annotations

from typing import Protocol

from cherenkov.core.knowledge_result import KnowledgeResult


class KnowledgeRepository(Protocol):
    def store(self, result: KnowledgeResult) -> None: ...

    def get(self, key: str) -> KnowledgeResult | None: ...

    def search(self, query: str, limit: int = 10) -> list[KnowledgeResult]: ...

    def delete(self, key: str) -> bool: ...

    def list_by_kind(self, kind: str, limit: int = 50) -> list[KnowledgeResult]: ...
