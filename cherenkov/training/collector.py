from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cherenkov.ports.storage import StoragePort, StorageQuery, StorageConfig
from cherenkov.adapters.storage.sqlite import SQLiteStorageAdapter

TELEMETRY_DB_PATH = Path.home() / ".cherenkov" / "training" / "telemetry.db"


class DataCollector:
    def __init__(self, storage: StoragePort | None = None):
        if storage is None:
            config = StorageConfig(db_path=TELEMETRY_DB_PATH, namespace="telemetry")
            storage = SQLiteStorageAdapter(config)
        self._storage = storage

    def record(self, spec_slice: str, test_code: str, verdict: str, endpoint: str = "", duration_ms: float = 0.0) -> str:
        data = {
            "spec_slice": spec_slice,
            "test_code": test_code,
            "verdict": verdict,
            "endpoint": endpoint,
            "duration_ms": duration_ms,
        }
        return self._storage.insert("entries", data)

    def query(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        q = StorageQuery(limit=limit, offset=offset)
        rows = self._storage.query("entries", q)
        
        # Flatten for backwards compatibility with the old tuple-like returns
        # or dict returns, wait, old code returned dicts.
        return [
            {
                "id": r["id"],
                "spec_slice": r.get("spec_slice"),
                "test_code": r.get("test_code"),
                "verdict": r.get("verdict"),
                "endpoint": r.get("endpoint", ""),
                "duration_ms": r.get("duration_ms", 0.0),
                "created_at": r.get("created_at"),
            }
            for r in rows
        ]

    def count(self) -> int:
        q = StorageQuery()
        return self._storage.count("entries", q)

    def export_json(self, path: str) -> None:
        q = StorageQuery(limit=999999)
        rows = self._storage.query("entries", q)
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                record = {
                    "spec_slice": r.get("spec_slice"),
                    "test_code": r.get("test_code"),
                    "verdict": r.get("verdict"),
                    "endpoint": r.get("endpoint", ""),
                    "duration_ms": r.get("duration_ms", 0.0),
                    "created_at": r.get("created_at"),
                }
                f.write(json.dumps(record) + "\n")

    def clear(self) -> None:
        # StoragePort does not have truncate, but we can hard-delete all
        q = StorageQuery()
        self._storage.delete("entries", q)
