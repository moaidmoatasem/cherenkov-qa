from __future__ import annotations

import asyncio
from functools import lru_cache

from fastapi import APIRouter

from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

router = APIRouter()


@lru_cache(maxsize=1)
def _get_repo() -> SQLiteKnowledgeRepository:
    return SQLiteKnowledgeRepository()


@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None, limit: int = 10):
    repo = _get_repo()
    result = await asyncio.to_thread(repo.query, KnowledgeQuery(query=q, source=source, limit=limit))
    return result.to_dict()
