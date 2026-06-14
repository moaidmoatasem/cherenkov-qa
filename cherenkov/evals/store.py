from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from cherenkov.evals.core import EvalReport


EVALS_DB = Path(".cherenkov/evals.db")


class EvalStore:
    _lock = threading.Lock()

    def __init__(self, db_path: Path = EVALS_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                con.execute("PRAGMA journal_mode=WAL")
            except Exception:
                pass
            try:
                with con:
                    con.execute("""
                        CREATE TABLE IF NOT EXISTS eval_reports (
                            id          INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp   TEXT NOT NULL,
                            model       TEXT NOT NULL,
                            pass_rate   REAL NOT NULL,
                            total       INTEGER NOT NULL,
                            passed      INTEGER NOT NULL,
                            failed      INTEGER NOT NULL,
                            metrics     TEXT NOT NULL,
                            details     TEXT NOT NULL
                        )
                    """)
            finally:
                con.close()

    def save(self, report: EvalReport) -> int:
        d = report.to_dict()
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                try:
                    con.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    pass
                cur = con.execute(
                    "INSERT INTO eval_reports (timestamp, model, pass_rate, total, passed, failed, metrics, details) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        d["timestamp"],
                        d["model"],
                        d["pass_rate"],
                        d["total_scenarios"],
                        d["passed"],
                        d["failed"],
                        json.dumps(d["metric_averages"]),
                        json.dumps(d["results"]),
                    ),
                )
                con.commit()
                return cur.lastrowid or 0
            finally:
                con.close()

    def latest(self) -> dict[str, Any] | None:
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                try:
                    con.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    pass
                row = con.execute(
                    "SELECT timestamp, model, pass_rate, total, passed, failed, metrics, details "
                    "FROM eval_reports ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    return {
                        "timestamp": row[0],
                        "model": row[1],
                        "pass_rate": row[2],
                        "total": row[3],
                        "passed": row[4],
                        "failed": row[5],
                        "metrics": json.loads(row[6]),
                        "results": json.loads(row[7]),
                    }
                return None
            finally:
                con.close()

    def history(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._lock:
            con = sqlite3.connect(str(self.db_path), timeout=10.0)
            try:
                try:
                    con.execute("PRAGMA journal_mode=WAL")
                except Exception:
                    pass
                rows = con.execute(
                    "SELECT timestamp, model, pass_rate, total, passed, failed, metrics "
                    "FROM eval_reports ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [
                    {
                        "timestamp": r[0],
                        "model": r[1],
                        "pass_rate": r[2],
                        "total": r[3],
                        "passed": r[4],
                        "failed": r[5],
                        "metrics": json.loads(r[6]),
                    }
                    for r in rows
                ]
            finally:
                con.close()
