from cherenkov.knowledge.domain.models import KnowledgeItem, KnowledgeQuery, KnowledgeQueryResult
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository

_repository: KnowledgeMeshRepository | None = None


def get_repository() -> KnowledgeMeshRepository:
    global _repository
    if _repository is None:
        from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

        _repository = SQLiteKnowledgeRepository()
    return _repository


def set_repository(repo: KnowledgeMeshRepository) -> None:
    global _repository
    _repository = repo


__all__ = [
    "KnowledgeItem",
    "KnowledgeMeshRepository",
    "KnowledgeQuery",
    "KnowledgeQueryResult",
    "get_repository",
    "set_repository",
]
