"""
CHERENKOV execution/perf_analyzer.py — local performance baseline and anomaly analyzer.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import sqlite3
import time
import math
from cherenkov.core.errors import get_logger

class PerformanceAnalyzer:
    """Records round-trip latency data inside local SQLite database and flags latency regressions."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("PERF_ANALYZER", run_id)
        self.db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.cherenkov/perf_store.db"))
        self._initialize_db()

    def _initialize_db(self):
        """Creates the relational SQLite performance table if not already present."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS perf_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp INTEGER NOT NULL
            )"""
        )
        conn.commit()
        conn.close()

    def record_latency(self, endpoint: str, method: str, latency_ms: float):
        """Inserts a fresh latency round-trip duration record into the SQLite store."""
        self.log.info("recording execution latency", endpoint=endpoint, method=method, latency=latency_ms)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO perf_metrics (endpoint, method, latency_ms, timestamp)
            VALUES (?, ?, ?, ?)""",
            (endpoint, method, latency_ms, int(time.time()))
        )
        conn.commit()
        conn.close()

    def get_baseline_stats(self, endpoint: str, method: str) -> dict:
        """Retrieves history count, mean, and standard deviation for the given endpoint and method."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT latency_ms FROM perf_metrics WHERE endpoint = ? AND method = ?",
            (endpoint, method)
        )
        rows = cursor.fetchall()
        conn.close()

        latencies = [row[0] for row in rows]
        count = len(latencies)
        
        if count == 0:
            return {"count": 0, "mean": 0.0, "stddev": 0.0}

        mean = sum(latencies) / count
        
        # Calculate standard deviation
        variance = sum((x - mean) ** 2 for x in latencies) / count if count > 1 else 0.0
        stddev = math.sqrt(variance)

        return {
            "count": count,
            "mean": round(mean, 2),
            "stddev": round(stddev, 2)
        }

    def analyze_anomaly(self, endpoint: str, method: str, current_latency_ms: float, threshold: float = 2.0) -> dict:
        """Compares current run metrics vs baseline statistics and checks for standard deviation outliers."""
        stats = self.get_baseline_stats(endpoint, method)
        count = stats["count"]
        mean = stats["mean"]
        stddev = stats["stddev"]

        self.log.info("analyzing performance baselines", endpoint=endpoint, count=count, mean=mean, stddev=stddev)

        # We need at least 3 historical runs to compute a meaningful statistical baseline
        if count < 3:
            return {
                "status": "initializing",
                "message": f"Establishing performance baseline database metrics (current runs: {count}/3).",
                "count": count,
                "current_latency": current_latency_ms,
                "mean": mean,
                "anomaly_detected": False
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
            "anomaly_detected": anomaly
        }

        if anomaly:
            self.log.warning(
                "latency regression anomaly detected",
                endpoint=endpoint,
                latency=current_latency_ms,
                limit=limit
            )
            report["message"] = (
                f"Latency regression detected on {method} {endpoint}! Current response time "
                f"({current_latency_ms}ms) exceeds the statistical baseline threshold limit ({round(limit, 2)}ms)."
            )
        else:
            self.log.info("performance verification checks passed", endpoint=endpoint)
            report["message"] = f"Performance verification passed. Latency ({current_latency_ms}ms) is within baseline range."

        return report
