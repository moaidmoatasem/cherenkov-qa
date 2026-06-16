"""
CHERENKOV execution/perf_analyzer.py — local performance baseline and anomaly analyzer.
"""

from __future__ import annotations

import math
import os
import sqlite3
import threading
import time

from cherenkov.core.errors import get_logger


class PerformanceAnalyzer:
    """Records round-trip latency data inside local SQLite database and flags latency regressions."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("PERF_ANALYZER", run_id)
        self.db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../.cherenkov/perf_store.db")
        )
        self._local = threading.local()
        self._initialize_db()

    def _connect(self) -> sqlite3.Connection:
        """Return a per-thread cached connection; reconnects if the connection is dead."""
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except Exception:
                pass
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        con = sqlite3.connect(self.db_path, timeout=30.0)
        con.execute("PRAGMA journal_mode=WAL")
        self._local.con = con
        return con

    def _initialize_db(self):
        """Creates the relational SQLite performance table if not already present."""
        conn = self._connect()
        conn.execute(
            """CREATE TABLE IF NOT EXISTS perf_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp INTEGER NOT NULL
            )"""
        )
        conn.commit()

    def record_latency(self, endpoint: str, method: str, latency_ms: float):
        """Inserts a fresh latency round-trip duration record into the SQLite store."""
        self.log.info(
            "recording execution latency",
            endpoint=endpoint,
            method=method,
            latency=latency_ms,
        )
        conn = self._connect()
        conn.execute(
            """INSERT INTO perf_metrics (endpoint, method, latency_ms, timestamp)
            VALUES (?, ?, ?, ?)""",
            (endpoint, method, latency_ms, int(time.time())),
        )
        conn.commit()

    def get_baseline_stats(self, endpoint: str, method: str) -> dict:
        """Retrieves history count, mean, and standard deviation for the given endpoint and method."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT latency_ms FROM perf_metrics WHERE endpoint = ? AND method = ?",
            (endpoint, method),
        ).fetchall()

        latencies = [row[0] for row in rows]
        count = len(latencies)

        if count == 0:
            return {"count": 0, "mean": 0.0, "stddev": 0.0}

        mean = sum(latencies) / count
        variance = sum((x - mean) ** 2 for x in latencies) / count if count > 1 else 0.0
        stddev = math.sqrt(variance)

        return {"count": count, "mean": round(mean, 2), "stddev": round(stddev, 2)}

    def analyze_anomaly(
        self,
        endpoint: str,
        method: str,
        current_latency_ms: float,
        threshold: float = 2.0,
    ) -> dict:
        """Compares current run metrics vs baseline statistics and checks for standard deviation outliers."""
        stats = self.get_baseline_stats(endpoint, method)
        count = stats["count"]
        mean = stats["mean"]
        stddev = stats["stddev"]

        self.log.info(
            "analyzing performance baselines",
            endpoint=endpoint,
            count=count,
            mean=mean,
            stddev=stddev,
        )

        # We need at least 3 historical runs to compute a meaningful statistical baseline
        if count < 3:
            return {
                "status": "initializing",
                "message": f"Establishing performance baseline database metrics (current runs: {count}/3).",
                "count": count,
                "current_latency": current_latency_ms,
                "mean": mean,
                "anomaly_detected": False,
            }

        # Check statistical outlier boundaries
        limit = mean + (threshold * stddev)
        anomaly = current_latency_ms > limit

        report = {
            "status": "anomaly_detected" if anomaly else "passed",
            "count": count,
            "current_latency": current_latency_ms,
            "mean": mean,
            "stddev": stddev,
            "threshold_limit": round(limit, 2),
            "anomaly_detected": anomaly,
        }

        if anomaly:
            self.log.warning(
                "latency regression anomaly detected",
                endpoint=endpoint,
                latency=current_latency_ms,
                limit=limit,
            )
            report["message"] = (
                f"Latency regression detected on {method} {endpoint}! Current response time "
                f"({current_latency_ms}ms) exceeds the statistical baseline threshold limit ({round(limit, 2)}ms)."
            )
        else:
            self.log.info("performance verification checks passed", endpoint=endpoint)
            report["message"] = (
                f"Performance verification passed. Latency ({current_latency_ms}ms) is within baseline range."
            )

        return report
