"""
CHERENKOV ai/cache.py — response prefix cache with LRU eviction and TTL.
Authority: v3.1 + delta. E1-5.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict

from cherenkov.core.contracts import CacheStats


class ResponseCache:
    """In-memory LRU cache for inference responses with TTL and hit tracking.

    Keys are (model, system_prompt_hash, user_prompt_hash) so identical prompts
    served to the same model reuse the cached result. Respects TTL so staleness
    is bounded. LRU eviction keeps memory bounded.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _make_key(self, model: str, system_prompt: str, user_prompt: str) -> str:
        return f"{model}::{self._hash(system_prompt)}::{self._hash(user_prompt)}"

    def get(self, model: str, system_prompt: str, user_prompt: str) -> object | None:
        key = self._make_key(model, system_prompt, user_prompt)
        if key in self._cache:
            ts, value = self._cache[key]
            if time.time() - ts < self.ttl_seconds:
                self._hits += 1
                self._cache.move_to_end(key)
                return value
            del self._cache[key]
        self._misses += 1
        return None

    def set(
        self, model: str, system_prompt: str, user_prompt: str, value: object
    ) -> None:
        key = self._make_key(model, system_prompt, user_prompt)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = (time.time(), value)
        while len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> CacheStats:
        total = self._hits + self._misses
        hit_ratio = self._hits / total if total > 0 else 0.0
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            size=len(self._cache),
            max_size=self.max_size,
            hit_ratio=round(hit_ratio, 4),
        )

    def clear(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0
