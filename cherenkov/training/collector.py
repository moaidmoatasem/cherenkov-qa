import json
import sqlite3
from pathlib import Path


TELEMETRY_DB_PATH = Path.home() / ".cherenkov" / "training" / "telemetry.db"
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_slice TEXT NOT NULL,
    test_code TEXT NOT NULL,
    verdict TEXT NOT NULL,
    endpoint TEXT NOT NULL DEFAULT '',
    duration_ms REAL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
)
"""


class DataCollector:
    def __init__(self, db_path=None):
        self.db_path = Path(db_path or TELEMETRY_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute(CREATE_TABLE_SQL)
        self._conn.commit()

    def record(self, spec_slice, test_code, verdict, endpoint="", duration_ms=0.0):
        self._conn.execute(
            "INSERT INTO telemetry (spec_slice, test_code, verdict, endpoint, duration_ms) VALUES (?, ?, ?, ?, ?)",
            (spec_slice, test_code, verdict, endpoint, duration_ms),
        )
        self._conn.commit()

    def query(self, limit=100, offset=0):
        cursor = self._conn.execute(
            "SELECT id, spec_slice, test_code, verdict, endpoint, duration_ms, created_at "
            "FROM telemetry ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "spec_slice": r[1],
                "test_code": r[2],
                "verdict": r[3],
                "endpoint": r[4],
                "duration_ms": r[5],
                "created_at": r[6],
            }
            for r in rows
        ]

    def count(self):
        cursor = self._conn.execute("SELECT COUNT(*) FROM telemetry")
        return cursor.fetchone()[0]

    def export_json(self, path):
        rows = self._conn.execute(
            "SELECT spec_slice, test_code, verdict, endpoint, duration_ms, created_at "
            "FROM telemetry ORDER BY id"
        ).fetchall()
        with open(path, "w") as f:
            for r in rows:
                record = {
                    "spec_slice": r[0],
                    "test_code": r[1],
                    "verdict": r[2],
                    "endpoint": r[3],
                    "duration_ms": r[4],
                    "created_at": r[5],
                }
                f.write(json.dumps(record) + "\n")

    def clear(self):
        self._conn.execute("DELETE FROM telemetry")
        self._conn.commit()

    def close(self):
        self._conn.close()
