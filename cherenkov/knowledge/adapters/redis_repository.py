from __future__ import annotations

import json

from cherenkov.knowledge.domain.models import (
    KnowledgeQuery,
    KnowledgeQueryResult,
    KnowledgeItem,
)


class RedisKnowledgeRepository:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            import redis as redis_client

            self.redis = redis_client.from_url(redis_url)
            self._available = True
        except ImportError:
            raise ImportError(
                "redis package is required for RedisKnowledgeRepository. "
                "Install with: pip install cherenkov[knowledge-redis]"
            )

    def query(self, query: KnowledgeQuery) -> KnowledgeQueryResult:
        pattern = f"knowledge:{query.source or '*'}:*"
        keys = self.redis.keys(pattern)
        results = []
        for key in keys[: query.limit]:
            data = self.redis.get(key)
            if data:
                item = json.loads(data)
                results.append(
                    KnowledgeQueryResult(
                        data=item["data"],
                        source=item["source"],
                        confidence=1.0,
                        metadata=item.get("metadata", {}),
                    )
                )
        return KnowledgeQueryResult(
            data=results,
            source=query.source or "all",
            confidence=1.0,
            metadata={"count": len(results)},
        )

    def store(self, item: KnowledgeItem) -> str:
        key = f"knowledge:{item.source}:{item.item_id}"
        self.redis.set(
            key,
            json.dumps(
                {
                    "item_id": item.item_id,
                    "source": item.source,
                    "data": item.data,
                    "metadata": item.metadata,
                    "created_at": item.created_at.isoformat(),
                }
            ),
        )
        return item.item_id

    def search(self, pattern: str, limit: int = 10) -> list[KnowledgeQueryResult]:
        keys = self.redis.keys("knowledge:*:*")
        results = []
        for key in keys:
            data = self.redis.get(key)
            if data:
                item = json.loads(data)
                if pattern.lower() in json.dumps(item["data"]).lower():
                    results.append(
                        KnowledgeQueryResult(
                            data=item["data"],
                            source=item["source"],
                            confidence=1.0,
                            metadata=item.get("metadata", {}),
                        )
                    )
                    if len(results) >= limit:
                        break
        return results

    def get_by_id(self, item_id: str) -> KnowledgeQueryResult | None:
        keys = self.redis.keys(f"knowledge:*:{item_id}")
        if not keys:
            return None
        data = self.redis.get(keys[0])
        if not data:
            return None
        item = json.loads(data)
        return KnowledgeQueryResult(
            data=item["data"],
            source=item["source"],
            confidence=1.0,
            metadata=item.get("metadata", {}),
        )
