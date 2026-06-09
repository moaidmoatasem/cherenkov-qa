"""Lightweight metrics collector — stores to SQLite, optionally emits Prometheus-format text."""
from __future__ import annotations
import sqlite3
import time
import os
from dataclasses import dataclass, field
from typing import Optional

try:
    import structlog
    log = structlog.get_logger("cherenkov.observability")
except ImportError:
    import logging as _logging
    log = _logging.getLogger("cherenkov.observability")

_DEFAULT_DB = os.path.join(".cherenkov", "metrics.db")
_BUSY_TIMEOUT_S = 10


@dataclass
class StageMetric:
    run_id: str
    stage: str
    latency_ms: float
    success: bool
    error_type: Optional[str] = None
    model_name: str = ""
    provider_name: str = ""
    cache_hit: bool = False
    timestamp: int = field(default_factory=lambda: int(time.time()))


class MetricsCollector:
    """Collects and persists pipeline metrics to SQLite."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or _DEFAULT_DB
        # For :memory: databases, keep a persistent connection so the schema is retained
        if self.db_path == ":memory:":
            self._mem_conn: sqlite3.Connection | None = sqlite3.connect(":memory:", check_same_thread=False)
        else:
            self._mem_conn = None
            os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        return sqlite3.connect(self.db_path, timeout=_BUSY_TIMEOUT_S)

    def _init_db(self) -> None:
        conn = self._connect()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stage_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                success INTEGER NOT NULL,
                error_type TEXT,
                model_name TEXT DEFAULT '',
                provider_name TEXT DEFAULT '',
                cache_hit INTEGER DEFAULT 0,
                timestamp INTEGER NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON stage_metrics(run_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON stage_metrics(timestamp)")
        conn.commit()
        if self._mem_conn is None:
            conn.close()

    def record(self, metric: StageMetric) -> None:
        try:
            conn = self._connect()
            conn.execute(
                "INSERT INTO stage_metrics (run_id, stage, latency_ms, success, error_type, "
                "model_name, provider_name, cache_hit, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
                (metric.run_id, metric.stage, metric.latency_ms, int(metric.success),
                 metric.error_type, metric.model_name, metric.provider_name,
                 int(metric.cache_hit), metric.timestamp)
            )
            conn.commit()
        except Exception as e:
            log.error("metrics_write_failed: %s (stage=%s)", str(e), metric.stage)
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_summary(self, last_n_runs: int = 10) -> list[dict]:
        """Return per-stage summary for the last N run_ids."""
        try:
            conn = self._connect()
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT run_id, stage,
                       AVG(latency_ms) as avg_latency_ms,
                       MAX(latency_ms) as max_latency_ms,
                       SUM(success) * 1.0 / COUNT(*) as success_rate,
                       SUM(cache_hit) * 1.0 / COUNT(*) as cache_hit_rate,
                       COUNT(*) as call_count
                FROM stage_metrics
                WHERE run_id IN (
                    SELECT run_id FROM (
                        SELECT run_id, MAX(timestamp) AS last_ts
                        FROM stage_metrics
                        GROUP BY run_id
                        ORDER BY last_ts DESC
                        LIMIT ?
                    )
                )
                GROUP BY run_id, stage
                ORDER BY MIN(timestamp) DESC
            """, (last_n_runs,)).fetchall()
            result = [dict(r) for r in rows]
            if self._mem_conn is None:
                conn.close()
            return result
        except Exception as e:
            log.error("metrics_read_failed: %s", str(e))
            return []

    def to_prometheus(self) -> str:
        """Emit current metrics in Prometheus text format."""
        summary = self.get_summary(last_n_runs=1)
        lines = ["# HELP cherenkov_stage_latency_ms Average stage latency in milliseconds",
                 "# TYPE cherenkov_stage_latency_ms gauge"]
        for row in summary:
            label = f'stage="{row["stage"]}",run_id="{row["run_id"]}"'
            lines.append(f'cherenkov_stage_latency_ms{{{label}}} {row["avg_latency_ms"]:.2f}')
        lines += ["# HELP cherenkov_stage_success_rate Stage success rate (0-1)",
                  "# TYPE cherenkov_stage_success_rate gauge"]
        for row in summary:
            label = f'stage="{row["stage"]}",run_id="{row["run_id"]}"'
            lines.append(f'cherenkov_stage_success_rate{{{label}}} {row["success_rate"]:.4f}')
        return "\n".join(lines) + "\n"
