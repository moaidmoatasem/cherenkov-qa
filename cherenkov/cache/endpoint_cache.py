"""
CHERENKOV cherenkov/cache/endpoint_cache.py — SQLite-backed incremental generation cache.
Authority: v3.1 + delta. Issue #433.

Maps (endpoint_hash) → generated test code so repeated runs on unchanged specs
skip the LLM call entirely. Cache key = SHA-256 of (path + method + schema_block + model_name).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CACHE_DB = Path(".cherenkov/cache/cache.db")
CACHE_TEST_DIR = Path(".cherenkov/cache/tests")


@dataclass
class CacheEntry:
    endpoint_hash: str
    spec_content_hash: str
    model_name: str
    test_code: str
    created_at: str


class EndpointCache:
    """SQLite-backed cache mapping endpoint spec hashes → generated test code.

    Usage::

        cache = EndpointCache()
        h = cache.compute_hash(path, method, schema_block, model_name)
        entry = cache.get(h)
        if entry:
            code = entry.test_code   # cache hit — skip LLM
        else:
            code = llm_generate(...)
            cache.put(h, code, model_name)
    """

    def __init__(self, db_path: Path = CACHE_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS endpoint_cache (
                    endpoint_hash     TEXT PRIMARY KEY,
                    spec_content_hash TEXT NOT NULL,
                    model_name        TEXT NOT NULL,
                    test_code         TEXT NOT NULL,
                    created_at        TEXT NOT NULL
                )
            """)
            conn.commit()

    def compute_hash(
        self,
        path: str,
        method: str,
        schema_block: dict,
        model_name: str,
    ) -> str:
        """SHA-256 of the canonical JSON representation of the endpoint descriptor."""
        payload = json.dumps(
            {
                "path": path,
                "method": method.upper(),
                "schema": schema_block,
                "model": model_name,
            },
            sort_keys=True,
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, endpoint_hash: str) -> CacheEntry | None:
        """Return cached entry or None on cache miss."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT endpoint_hash, spec_content_hash, model_name, test_code, created_at "
                "FROM endpoint_cache WHERE endpoint_hash = ?",
                (endpoint_hash,),
            ).fetchone()
        if row:
            return CacheEntry(*row)
        return None

    def put(self, endpoint_hash: str, test_code: str, model_name: str) -> None:
        """Store generated test code keyed by endpoint hash."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO endpoint_cache
                    (endpoint_hash, spec_content_hash, model_name, test_code, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (endpoint_hash, endpoint_hash, model_name, test_code, now),
            )
            conn.commit()

    def stats(self) -> dict:
        """Return cache statistics for reporting."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM endpoint_cache"
            ).fetchone()[0]
        return {"cached_endpoints": total, "cache_db": str(self.db_path)}

    def clear(self) -> None:
        """Wipe entire cache (e.g. after --no-cache flag or model change)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM endpoint_cache")
            conn.commit()
