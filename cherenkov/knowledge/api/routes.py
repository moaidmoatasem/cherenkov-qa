from __future__ import annotations

import asyncio
import dataclasses
from functools import lru_cache

from fastapi import APIRouter, Depends
from cherenkov.web.sdd_auth import verify_api_key

from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.adapters.sqlite_repository import SQLiteKnowledgeRepository

router = APIRouter()


@lru_cache(maxsize=1)
def _get_repo() -> SQLiteKnowledgeRepository:
    return SQLiteKnowledgeRepository()


@router.get("/api/v1/knowledge/query")
async def get_knowledge(
    q: str, source: str | None = None, limit: int = 10, _auth=Depends(verify_api_key)
):
    repo = _get_repo()
    result = await asyncio.to_thread(
        repo.query, KnowledgeQuery(query=q, source=source, limit=limit)
    )
    d = result.to_dict()
    # data may contain KnowledgeItem dataclass objects — convert to plain dicts
    if isinstance(d.get("data"), list):
        d["data"] = [
            dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item
            for item in d["data"]
        ]
    return d
