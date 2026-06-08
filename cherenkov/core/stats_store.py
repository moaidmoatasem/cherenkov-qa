from __future__ import annotations

import os
import sqlite3
import time
import logging

logger = logging.getLogger(__name__)

_BUSY_TIMEOUT_S = 10.0
_INIT_RETRY_S = 0.1


def _default_db_path() -> str:
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../..")
    )
    return os.path.join(repo_root, ".cherenkov", "stats.db")


class StatsStore:
    """SQLite-backed persistence for pipeline run stats."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _default_db_path()
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        for attempt in range(3):
            try:
                conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
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
                conn.close()
                return
            except sqlite3.OperationalError as e:
                logger.warning("stats db init attempt %d failed: %s", attempt + 1, str(e))
                if attempt < 2:
                    import time as _time
                    _time.sleep(_INIT_RETRY_S * (attempt + 1))
        logger.warning("stats db init failed after 3 attempts — will retry on first write")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)

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
                (run_id, int(time.time()), int(success), scenarios_passed, scenarios_total,
                 total_duration_ms, total_cost, cache_hit_ratio, verdict_count, idiom_count),
            )
            conn.commit()
            conn.close()
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
            conn.close()
        except Exception as e:
            logger.error("failed to record stats snapshot", exc_info=e)

    def get_recent_runs(self, limit: int = 20) -> list[dict]:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM pipeline_runs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []
        finally:
            conn.close()

    def get_run_summary(self) -> dict:
        conn = sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)
        conn.row_factory = sqlite3.Row
        try:
            total = conn.execute("SELECT COUNT(*) as c FROM pipeline_runs").fetchone()["c"]
            passed = conn.execute(
                "SELECT COUNT(*) as c FROM pipeline_runs WHERE success = 1"
            ).fetchone()["c"]
            return {"total_runs": total, "successful_runs": passed}
        except Exception:
            return {"total_runs": 0, "successful_runs": 0}
        finally:
            conn.close()
