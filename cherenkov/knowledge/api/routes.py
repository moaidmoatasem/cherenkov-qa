from __future__ import annotations

import asyncio

from fastapi import APIRouter

from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

router = APIRouter()


@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None, limit: int = 10):
    def _query():
        repo = SQLiteKnowledgeRepository()
        return repo.query(KnowledgeQuery(query=q, source=source, limit=limit)).to_dict()
    return await asyncio.to_thread(_query)
