from __future__ import annotations

import asyncio
import dataclasses
from functools import lru_cache

from fastapi import APIRouter, Depends

from cherenkov.knowledge import get_repository
from cherenkov.knowledge.domain.models import KnowledgeQuery
from cherenkov.knowledge.ports.repository import KnowledgeMeshRepository
from cherenkov.web.sdd_auth import verify_api_key

router = APIRouter()


@lru_cache(maxsize=1)
def _get_repo() -> KnowledgeMeshRepository:
    return get_repository()


@router.get("/api/v1/knowledge/query")
async def get_knowledge(q: str, source: str | None = None, limit: int = 10, _auth=Depends(verify_api_key)):
    repo = _get_repo()
    result = await asyncio.to_thread(repo.query, KnowledgeQuery(query=q, source=source, limit=limit))
    d = result.to_dict()
    if isinstance(d.get("data"), list):
        d["data"] = [
            dataclasses.asdict(item) if dataclasses.is_dataclass(item) else item
            for item in d["data"]
        ]
    return d
