"""
CHERENKOV cherenkov/cache/endpoint_cache.py — SQLite-backed incremental generation cache.
Authority: v3.1 + delta. Issue #433.

Maps (endpoint_hash) → generated test code so repeated runs on unchanged specs
skip the LLM call entirely. Cache key = SHA-256 of (path + method + schema_block + model_name).

Two-tier caching: L1 in-process dict (no I/O), L2 SQLite (persists across runs).
Entries expire after TTL_HOURS (default 24 h) — model or schema changes age out naturally.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


CACHE_DB = Path(".cherenkov/cache/cache.db")
CACHE_TEST_DIR = Path(".cherenkov/cache/tests")
_TTL_SECONDS = 24 * 3600


@dataclass
class CacheEntry:
    endpoint_hash: str
    spec_content_hash: str
    model_name: str
    test_code: str
    created_at: str


class EndpointCache:
    """Two-tier (L1 dict + L2 SQLite) cache mapping endpoint spec hashes → generated test code.

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

    _local = threading.local()

    def __init__(self, db_path: Path = CACHE_DB, ttl_seconds: int = _TTL_SECONDS):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_seconds
        self._l1: dict[str, tuple[CacheEntry, float]] = {}
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except Exception:
                pass
        con = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            con.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        self._local.con = con
        return con

    def _init_db(self) -> None:
        con = self._connect()
        con.execute("""
            CREATE TABLE IF NOT EXISTS endpoint_cache (
                endpoint_hash     TEXT PRIMARY KEY,
                spec_content_hash TEXT NOT NULL,
                model_name        TEXT NOT NULL,
                test_code         TEXT NOT NULL,
                created_at        TEXT NOT NULL
            )
        """)

    def close(self) -> None:
        con = getattr(self._local, "con", None)
        if con is not None:
            con.close()
            self._local.con = None

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
        """Return cached entry or None on miss/expiry. Checks L1 first, then L2."""
        now = time.monotonic()
        # L1 check
        if endpoint_hash in self._l1:
            entry, ts = self._l1[endpoint_hash]
            if now - ts < self._ttl:
                return entry
            del self._l1[endpoint_hash]
        # L2 check
        cutoff = datetime.fromtimestamp(
            time.time() - self._ttl, tz=timezone.utc
        ).isoformat()
        conn = self._connect()
        row = conn.execute(
            "SELECT endpoint_hash, spec_content_hash, model_name, test_code, created_at "
            "FROM endpoint_cache WHERE endpoint_hash = ? AND created_at >= ?",
            (endpoint_hash, cutoff),
        ).fetchone()
        if row:
            entry = CacheEntry(*row)
            self._l1[endpoint_hash] = (entry, now)
            return entry
        return None

    def put(self, endpoint_hash: str, test_code: str, model_name: str) -> None:
        """Store generated test code in both L1 and L2."""
        now_iso = datetime.now(timezone.utc).isoformat()
        entry = CacheEntry(
            endpoint_hash=endpoint_hash,
            spec_content_hash=endpoint_hash,
            model_name=model_name,
            test_code=test_code,
            created_at=now_iso,
        )
        self._l1[endpoint_hash] = (entry, time.monotonic())
        conn = self._connect()
        conn.execute(
            "INSERT OR REPLACE INTO endpoint_cache "
            "(endpoint_hash, spec_content_hash, model_name, test_code, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (endpoint_hash, endpoint_hash, model_name, test_code, now_iso),
        )
        conn.commit()

    def stats(self) -> dict:
        """Return cache statistics for reporting."""
        conn = self._connect()
        total = conn.execute("SELECT COUNT(*) FROM endpoint_cache").fetchone()[0]
        return {
            "cached_endpoints": total,
            "cache_db": str(self.db_path),
            "l1_size": len(self._l1),
        }

    def clear(self) -> None:
        """Wipe entire cache (e.g. after --no-cache flag or model change)."""
        self._l1.clear()
        conn = self._connect()
        conn.execute("DELETE FROM endpoint_cache")
        conn.commit()
