from __future__ import annotations

import os
import sqlite3
import threading
import time
import logging

logger = logging.getLogger(__name__)

_BUSY_TIMEOUT_S = 10.0


def _default_db_path() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    return os.path.join(repo_root, ".cherenkov", "stats.db")


class StatsStore:
    """SQLite-backed persistence for pipeline run stats."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _default_db_path()
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._local = threading.local()
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        """Return a per-thread cached connection; reconnects if the connection is dead."""
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except Exception:
                pass
        con = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        self._local.con = con
        return con

    def _init_tables(self) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "CREATE TABLE IF NOT EXISTS pipeline_runs ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "run_id TEXT NOT NULL,"
                "timestamp INTEGER NOT NULL,"
                "success INTEGER NOT NULL,"
                "scenarios_passed INTEGER NOT NULL DEFAULT 0,"
                "scenarios_total INTEGER NOT NULL DEFAULT 0,"
                "total_duration_ms INTEGER NOT NULL DEFAULT 0,"
                "total_cost REAL NOT NULL DEFAULT 0.0,"
                "cache_hit_ratio REAL,"
                "verdict_count INTEGER NOT NULL DEFAULT 0,"
                "idiom_count INTEGER NOT NULL DEFAULT 0)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS snapshot_stats ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "snapshot_time INTEGER NOT NULL,"
                "verdict_count INTEGER NOT NULL DEFAULT 0,"
                "idiom_count INTEGER NOT NULL DEFAULT 0,"
                "source TEXT NOT NULL DEFAULT 'cli')"
            )
            conn.commit()
        except sqlite3.OperationalError as e:
            logger.warning("stats db init failed: %s", str(e))

    def record_run(
        self,
        run_id: str,
        success: bool,
        scenarios_passed: int = 0,
        scenarios_total: int = 0,
        total_duration_ms: int = 0,
        total_cost: float = 0.0,
        cache_hit_ratio: float | None = None,
        verdict_count: int = 0,
        idiom_count: int = 0,
    ) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO pipeline_runs "
                "(run_id, timestamp, success, scenarios_passed, scenarios_total, "
                " total_duration_ms, total_cost, cache_hit_ratio, verdict_count, idiom_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    int(time.time()),
                    int(success),
                    scenarios_passed,
                    scenarios_total,
                    total_duration_ms,
                    total_cost,
                    cache_hit_ratio,
                    verdict_count,
                    idiom_count,
                ),
            )
            conn.commit()
        except Exception as e:
            logger.error("failed to record pipeline run stats", exc_info=e)

    def snapshot(
        self,
        verdict_count: int,
        idiom_count: int,
        source: str = "cli",
    ) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO snapshot_stats (snapshot_time, verdict_count, idiom_count, source) "
                "VALUES (?, ?, ?, ?)",
                (int(time.time()), verdict_count, idiom_count, source),
            )
            conn.commit()
        except Exception as e:
            logger.error("failed to record stats snapshot", exc_info=e)

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        try:
            conn = self._connect()
            cursor = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def get_run_summary(self) -> dict:
        try:
            conn = self._connect()
            total = conn.execute("SELECT COUNT(*) as c FROM pipeline_runs").fetchone()[
                "c"
            ]
            passed = conn.execute(
                "SELECT COUNT(*) as c FROM pipeline_runs WHERE success = 1"
            ).fetchone()["c"]
            return {"total_runs": total, "successful_runs": passed}
        except Exception:
            return {"total_runs": 0, "successful_runs": 0}
