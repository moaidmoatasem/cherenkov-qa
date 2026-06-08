from __future__ import annotations

from fastapi import APIRouter

from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

router = APIRouter()


@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None, limit: int = 10):
    repo = SQLiteKnowledgeRepository()
    query = KnowledgeQuery(query=q, source=source, limit=limit)
    result = repo.query(query)
    return result.to_dict()
