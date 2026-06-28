from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
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
    _lock = threading.Lock()

    def __init__(self, db_path: Path = CACHE_DB, ttl_seconds: int = _TTL_SECONDS):
        self.db_path = db_path
        self._l1: dict[str, tuple[CacheEntry, float]] = {}
        self._ttl = ttl_seconds
        self._fallback = False
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                con = sqlite3.connect(str(self.db_path), timeout=1.0)
                try:
                    with con:
                        con.execute("""
                            CREATE TABLE IF NOT EXISTS endpoint_cache (
                                endpoint_hash     TEXT PRIMARY KEY,
                                spec_content_hash TEXT NOT NULL,
                                model_name        TEXT NOT NULL,
                                test_code         TEXT NOT NULL,
                                created_at        TEXT NOT NULL
                            )
                        """)
                finally:
                    con.close()
            except sqlite3.OperationalError:
                self.db_path = Path(os.path.join(tempfile.gettempdir(), "cherenkov", "cache.db"))
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    con = sqlite3.connect(str(self.db_path), timeout=1.0)
                    try:
                        with con:
                            con.execute("""
                                CREATE TABLE IF NOT EXISTS endpoint_cache (
                                    endpoint_hash     TEXT PRIMARY KEY,
                                    spec_content_hash TEXT NOT NULL,
                                    model_name        TEXT NOT NULL,
                                    test_code         TEXT NOT NULL,
                                    created_at        TEXT NOT NULL
                                )
                            """)
                    finally:
                        con.close()
                except Exception:
                    self._fallback = True

    def _query(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        if self._fallback:
            return None
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=1.0)
            try:
                return con.execute(sql, params).fetchone()
            finally:
                con.close()

    def _execute(self, sql: str, params: tuple = ()) -> None:
        if self._fallback:
            return
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=1.0)
            try:
                con.execute(sql, params)
                con.commit()
            finally:
                con.close()

    def clear(self) -> None:
        self._l1.clear()
        if not self._fallback:
            self._execute("DELETE FROM endpoint_cache")

    def stats(self) -> dict:
        if self._fallback:
            return {"cached_endpoints": 0, "cache_db": "L1-only", "l1_size": len(self._l1)}
        row = self._query("SELECT COUNT(*) FROM endpoint_cache")
        total = row[0] if row else 0
        return {
            "cached_endpoints": total,
            "cache_db": str(self.db_path),
            "l1_size": len(self._l1),
        }

    def compute_hash(self, path: str, method: str, schema_block: dict, model_name: str) -> str:
        payload = json.dumps(
            {"path": path, "method": method.upper(), "schema": schema_block, "model": model_name},
            sort_keys=True,
            ensure_ascii=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, endpoint_hash: str) -> CacheEntry | None:
        now = time.monotonic()
        if endpoint_hash in self._l1:
            entry, ts = self._l1[endpoint_hash]
            if now - ts < self._ttl:
                return entry
            del self._l1[endpoint_hash]
        cutoff = datetime.fromtimestamp(time.time() - self._ttl, tz=timezone.utc).isoformat()
        row = self._query(
            "SELECT endpoint_hash, spec_content_hash, model_name, test_code, created_at "
            "FROM endpoint_cache WHERE endpoint_hash = ? AND created_at >= ?",
            (endpoint_hash, cutoff),
        )
        if row:
            entry = CacheEntry(*row)
            self._l1[endpoint_hash] = (entry, now)
            return entry
        return None

    def put(self, endpoint_hash: str, test_code: str, model_name: str) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        entry = CacheEntry(
            endpoint_hash=endpoint_hash,
            spec_content_hash=endpoint_hash,
            model_name=model_name,
            test_code=test_code,
            created_at=now_iso,
        )
        self._l1[endpoint_hash] = (entry, time.monotonic())
        self._execute(
            "INSERT OR REPLACE INTO endpoint_cache "
            "(endpoint_hash, spec_content_hash, model_name, test_code, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (endpoint_hash, endpoint_hash, model_name, test_code, now_iso),
        )
