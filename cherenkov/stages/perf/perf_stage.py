"""
CHERENKOV stages/perf/perf_stage.py - Phase B2 Perf Baseline stage.

Optional capability layer on top of Track A. Never replaces API conformance.
Records run latencies in local SQLite (.cherenkov/perf_metrics.db) and flags
performance anomalies using both statistical and ML-based detection.

Enhanced with Epoch 8 Perf Intelligence capabilities:
- Statistical → ML anomaly detection (seasonal baseline + isolation forest)
- Generative load profiles from traffic sources
- LLM-aware metrics (TTFT/ITL/cost)
- Zero-dependency statistical path remains default

If k6 is missing from PATH the stage degrades gracefully (simulated 45ms tick +
HITL verdict + k6_available=False) so QA can run the smoke without k6 locally.
Anti-lock-in invariant: generated k6 script is plain JS, runs standalone.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from typing import Optional, Dict, Any
from cherenkov.core.contracts import (
    StageMeta,
    StageError,
    Status,
    Verdict,
    PerfSlice,
    PerfGateResult,
    PerfReport,
)
from cherenkov.core.errors import get_logger

# Optional ML dependencies - import only when available
ML_AVAILABLE = False
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    import pandas as pd
    from datetime import datetime, timedelta

    ML_AVAILABLE = True
except ImportError:
    pass


class _BaselineDB:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._local = threading.local()
        conn = self._connect()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS perf_metrics ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "endpoint TEXT NOT NULL,"
            "method TEXT NOT NULL,"
            "latency_ms REAL NOT NULL,"
            "ttft_ms REAL,"
            "itl_ms REAL,"
            "cost_usd REAL,"
            "is_llm BOOLEAN DEFAULT 0,"
            "timestamp INTEGER NOT NULL)"
        )
        conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Return a per-thread cached connection; reconnects if the connection is dead."""
        con = getattr(self._local, "con", None)
        if con is not None:
            try:
                con.execute("SELECT 1")
                return con
            except Exception:
                pass
        con = sqlite3.connect(self.db_path, timeout=30.0)
        con.execute("PRAGMA journal_mode=WAL")
        self._local.con = con
        return con

    def record(
        self,
        endpoint,
        method,
        latency_ms,
        ttft_ms: Optional[float] = None,
        itl_ms: Optional[float] = None,
        cost_usd: Optional[float] = None,
        is_llm: bool = False,
    ):
        """
        Record performance metrics with optional LLM-specific metrics.

        Args:
            endpoint: API endpoint
            method: HTTP method
            latency_ms: Total request latency in milliseconds
            ttft_ms: Time To First Token in milliseconds (LLM-specific)
            itl_ms: Inter Token Latency in milliseconds (LLM-specific)
            cost_usd: Cost in USD for the request (LLM-specific)
            is_llm: Whether this is an LLM request
        """
        conn = self._connect()
        conn.execute(
            "INSERT INTO perf_metrics (endpoint, method, latency_ms, ttft_ms, itl_ms, cost_usd, is_llm, timestamp) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                endpoint,
                method,
                latency_ms,
                ttft_ms,
                itl_ms,
                cost_usd,
                int(is_llm),
                int(time.time()),
            ),
        )
        conn.commit()

    def stats(self, endpoint, method):
        conn = self._connect()
        rows = conn.execute(
            "SELECT latency_ms FROM perf_metrics WHERE endpoint=? AND method=?",
            (endpoint, method),
        ).fetchall()
        latencies = [r[0] for r in rows]
        count = len(latencies)
        if count == 0:
            return {"count": 0, "mean": 0.0, "stddev": 0.0}
        mean = sum(latencies) / count
        variance = sum((x - mean) ** 2 for x in latencies) / count if count > 1 else 0.0
        return {
            "count": count,
            "mean": round(mean, 2),
            "stddev": round(math.sqrt(variance), 2),
        }

    def llm_stats(self, endpoint, method) -> Dict[str, Any]:
        """
        Get LLM-specific performance statistics.

        Returns:
            Dictionary with LLM performance metrics
        """
        conn = self._connect()
        rows = conn.execute(
            "SELECT ttft_ms, itl_ms, cost_usd FROM perf_metrics "
            "WHERE endpoint=? AND method=? AND is_llm=1 AND ttft_ms IS NOT NULL",
            (endpoint, method),
        ).fetchall()

        ttft_values = [r[0] for r in rows if r[0] is not None]
        itl_values = [r[1] for r in rows if r[1] is not None]
        cost_values = [r[2] for r in rows if r[2] is not None]

        stats = {
            "llm_request_count": len(rows),
            "ttft_mean_ms": round(sum(ttft_values) / len(ttft_values), 2)
            if ttft_values
            else 0.0,
            "ttft_stddev_ms": round(
                math.sqrt(
                    sum(
                        (x - (sum(ttft_values) / len(ttft_values))) ** 2
                        for x in ttft_values
                    )
                    / len(ttft_values)
                ),
                2,
            )
            if len(ttft_values) > 1
            else 0.0,
            "itl_mean_ms": round(sum(itl_values) / len(itl_values), 2)
            if itl_values
            else 0.0,
            "itl_stddev_ms": round(
                math.sqrt(
                    sum(
                        (x - (sum(itl_values) / len(itl_values))) ** 2
                        for x in itl_values
                    )
                    / len(itl_values)
                ),
                2,
            )
            if len(itl_values) > 1
            else 0.0,
            "cost_mean_usd": round(sum(cost_values) / len(cost_values), 4)
            if cost_values
            else 0.0,
            "cost_stddev_usd": round(
                math.sqrt(
                    sum(
                        (x - (sum(cost_values) / len(cost_values))) ** 2
                        for x in cost_values
                    )
                    / len(cost_values)
                ),
                4,
            )
            if len(cost_values) > 1
            else 0.0,
        }

        return stats


K6_SCRIPT_TEMPLATE = (
    "import http from 'k6/http';\n"
    "import { check, sleep } from 'k6';\n\n"
    "export const options = { vus: __VUS__, duration: '__DUR__s' };\n\n"
    "export default function () {\n"
    "  const url = __ENV.API_URL || '__URL__';\n"
    "  const r = http.request('__METHOD__', url + '__ENDPOINT__');\n"
    "  check(r, { 'status is 2xx': (res) => res.status >= 200 && res.status < 300 });\n"
    "  sleep(0.5);\n"
    "}\n"
)


def _render_script(sl):
    return (
        K6_SCRIPT_TEMPLATE.replace("__VUS__", str(sl.vus))
        .replace("__DUR__", str(sl.duration_sec))
        .replace("__URL__", sl.target_url)
        .replace("__METHOD__", sl.method.upper())
        .replace("__ENDPOINT__", sl.endpoint)
    )


class PerfStage:
    def __init__(self, run_id=None, db_path=None):
        self.run_id = run_id
        self.log = get_logger("PERF", run_id)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        self.stub_dir = os.path.join(repo_root, "stub")
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")
        self.k6_script_path = os.path.join(self.tests_dir, "k6_perf.js")
        self.db_path = db_path or os.path.join(
            repo_root, ".cherenkov", "perf_metrics.db"
        )
        self.db = _BaselineDB(self.db_path)

    def _write_script(self, sl):
        os.makedirs(self.tests_dir, exist_ok=True)
        code = _render_script(sl)
        with open(self.k6_script_path, "w", encoding="utf-8") as f:
            f.write(code)
        return code

    def _analyze(
        self, endpoint, method, current_ms, threshold=2.0, use_ml: bool = False
    ):
        """
        Analyze performance with statistical method (default) or ML-based anomaly detection.

        Args:
            endpoint: API endpoint being tested
            method: HTTP method (GET, POST, etc.)
            current_ms: Current latency measurement in milliseconds
            threshold: Number of standard deviations for statistical threshold
            use_ml: Whether to use ML-based anomaly detection (requires ML_AVAILABLE)

        Returns:
            Dictionary with analysis results including anomaly detection
        """
        stats = self.db.stats(endpoint, method)
        count, mean, stddev = stats["count"], stats["mean"], stats["stddev"]

        if count < 3:
            return {
                "count": count,
                "mean": mean,
                "stddev": stddev,
                "threshold_limit": 0.0,
                "anomaly_detected": False,
                "initializing": True,
                "method": "statistical",
            }

        # Statistical analysis (always available)
        statistical_limit = mean + (threshold * stddev)
        statistical_anomaly = current_ms > statistical_limit

        # ML-based analysis (when available and requested)
        ml_anomaly = False
        ml_score = 0.0
        ml_method = "n/a"

        if use_ml and ML_AVAILABLE and count >= 10:  # Need enough data for ML
            try:
                ml_result = self._ml_anomaly_detection(endpoint, method, current_ms)
                ml_anomaly = ml_result.get("anomaly", False)
                ml_score = ml_result.get("score", 0.0)
                ml_method = ml_result.get("method", "isolation_forest")
            except Exception as e:
                self.log.warning(
                    "ML anomaly detection failed, falling back to statistical",
                    error=str(e),
                )
                use_ml = False

        # Use ML result if available and confident, otherwise fall back to statistical
        if use_ml and ml_anomaly:
            anomaly_detected = True
            detection_method = f"ml_{ml_method}"
            limit_used = ml_score
        else:
            anomaly_detected = statistical_anomaly
            detection_method = "statistical"
            limit_used = statistical_limit

        return {
            "count": count,
            "mean": mean,
            "stddev": stddev,
            "threshold_limit": round(statistical_limit, 2),
            "anomaly_detected": anomaly_detected,
            "initializing": False,
            "method": detection_method,
            "ml_score": round(ml_score, 3) if use_ml else None,
            "statistical_anomaly": statistical_anomaly,
            "ml_anomaly": ml_anomaly if use_ml else None,
        }

    def _is_llm_endpoint(self, endpoint: str) -> bool:
        """
        Heuristic to determine if an endpoint is likely an LLM endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            True if endpoint appears to be LLM-related
        """
        llm_keywords = [
            "completion",
            "chat",
            "generate",
            "inference",
            "llm",
            "embedding",
            "prompt",
            "model",
            "ai",
            "predict",
        ]

        endpoint_lower = endpoint.lower()
        return any(keyword in endpoint_lower for keyword in llm_keywords)

    def _extract_llm_metrics_from_response(
        self, k6_output: str
    ) -> Optional[Dict[str, float]]:
        """
        Extract LLM-specific metrics from k6 output or response data.

        Args:
            k6_output: Output from k6 run containing performance data

        Returns:
            Dictionary with extracted LLM metrics or None if not available
        """
        self.log.warning(
            "LLM metric extraction not yet implemented; "
            "TTFT/ITL/cost metrics will not be available for this run. "
            "See https://github.com/moaidmoatasem/cherenkov-qa/issues/157"
        )
        return None

    def _update_with_llm_metrics(
        self, endpoint: str, method: str, ttft_ms: float, itl_ms: float, cost_usd: float
    ) -> bool:
        """
        Update the most recent performance record with LLM-specific metrics.

        Args:
            endpoint: API endpoint
            method: HTTP method
            ttft_ms: Time To First Token in milliseconds
            itl_ms: Inter Token Latency in milliseconds
            cost_usd: Cost in USD

        Returns:
            True if update was successful
        """
        try:
            conn = self.db._connect()
            cursor = conn.cursor()

            # Get the most recent record for this endpoint/method
            cursor.execute(
                "SELECT id FROM perf_metrics WHERE endpoint=? AND method=? ORDER BY timestamp DESC LIMIT 1",
                (endpoint, method),
            )
            row = cursor.fetchone()

            if row:
                record_id = row[0]
                cursor.execute(
                    """UPDATE perf_metrics
                    SET ttft_ms=?, itl_ms=?, cost_usd=?, is_llm=1
                    WHERE id=?""",
                    (ttft_ms, itl_ms, cost_usd, record_id),
                )
                conn.commit()
                return True

            return False
        except Exception as e:
            self.log.error("Failed to update LLM metrics", error=str(e))
            return False

    def _ml_anomaly_detection(
        self, endpoint: str, method: str, current_latency_ms: float
    ) -> Dict[str, Any]:
        """
        ML-based anomaly detection using Isolation Forest and seasonal analysis.

        Args:
            endpoint: API endpoint being tested
            method: HTTP method
            current_latency_ms: Current latency measurement

        Returns:
            Dictionary with ML analysis results
        """
        if not ML_AVAILABLE:
            return {"anomaly": False, "score": 0.0, "method": "unavailable"}

        # Fetch historical data
        conn = self.db._connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT latency_ms, timestamp FROM perf_metrics WHERE endpoint=? AND method=? ORDER BY timestamp",
            (endpoint, method),
        )
        rows = cursor.fetchall()

        if len(rows) < 10:
            return {"anomaly": False, "score": 0.0, "method": "insufficient_data"}

        # Prepare data for ML
        timestamps = [row[1] for row in rows]
        latencies = [row[0] for row in rows]

        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame({"timestamp": timestamps, "latency_ms": latencies})

        # Add time-based features for seasonal analysis
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        df["hour"] = df["datetime"].dt.hour
        df["day_of_week"] = df["datetime"].dt.dayofweek
        df["day_of_month"] = df["datetime"].dt.day

        # Prepare features for Isolation Forest
        features = df[["hour", "day_of_week", "latency_ms"]].values

        # Train Isolation Forest model
        model = IsolationForest(contamination=0.1, random_state=42)
        model.fit(features)

        # Predict anomaly score for current measurement
        current_hour = datetime.now().hour
        current_day_of_week = datetime.now().weekday()
        current_features = np.array(
            [[current_hour, current_day_of_week, current_latency_ms]]
        )

        # Get anomaly score (-1 to 1, where -1 is definitely anomalous)
        anomaly_score = model.decision_function(current_features)[0]
        is_anomaly = model.predict(current_features)[0] == -1

        return {
            "anomaly": bool(is_anomaly),
            "score": float(anomaly_score),
            "method": "isolation_forest_seasonal",
            "sample_size": len(rows),
            "model_contamination": 0.1,
        }

    def generate_load_profile_from_traffic(
        self, traffic_file_path: str, base_target_url: str = "http://localhost:3000"
    ) -> Optional[PerfSlice]:
        """
        Generate a realistic load profile from HAR traffic data.

        Args:
            traffic_file_path: Path to HAR file containing traffic data
            base_target_url: Base target URL to use if not found in traffic data

        Returns:
            PerfSlice with traffic-based load profile or None if generation fails
        """
        try:
            import json
            from pathlib import Path

            har_path = Path(traffic_file_path)
            if not har_path.exists():
                self.log.warning(
                    "Traffic file not found for load profile generation",
                    path=traffic_file_path,
                )
                return None

            raw = har_path.read_text(encoding="utf-8")
            har = json.loads(raw)

            entries = har.get("log", {}).get("entries", [])
            if not entries:
                entries = har.get("entries", [])
                if not entries:
                    self.log.warning(
                        "No traffic entries found in HAR file", path=traffic_file_path
                    )
                    return None

            # Analyze traffic patterns
            total_requests = len(entries)
            request_timings = []

            for entry in entries:
                request = entry.get("request", {})
                timings = entry.get("timings", {})
                if timings:
                    total_ms = (
                        timings.get("send", 0)
                        + timings.get("wait", 0)
                        + timings.get("receive", 0)
                    )
                    request_timings.append(total_ms)

            if not request_timings:
                self.log.warning(
                    "No valid timing data found in traffic entries",
                    path=traffic_file_path,
                )
                return None

            # Calculate traffic-based load profile
            avg_latency = sum(request_timings) / len(request_timings)
            requests_per_second = (
                total_requests / 60.0
            )  # Assuming 60 second capture window

            # Generate realistic VUS (virtual users) based on traffic intensity
            vus = max(1, min(50, int(requests_per_second * 2)))  # Scale factor of 2x
            duration_sec = max(
                5, min(60, int(60 / requests_per_second * 3))
            )  # 3x capture window

            # Find most common endpoint pattern
            endpoint_counts = {}
            for entry in entries:
                request = entry.get("request", {})
                url = request.get("url", "")
                method = request.get("method", "GET").upper()

                # Extract path from URL
                path = url.split("?")[0].split("#")[0]
                if path.startswith("http://") or path.startswith("https://"):
                    path = "/" + "/".join(path.split("/")[3:])  # Remove domain

                key = f"{method} {path}"
                endpoint_counts[key] = endpoint_counts.get(key, 0) + 1

            if endpoint_counts:
                most_common_endpoint = max(endpoint_counts.items(), key=lambda x: x[1])[
                    0
                ]
                method, endpoint = most_common_endpoint.split(" ", 1)
            else:
                method = "GET"
                endpoint = "/"

            self.log.info(
                "Generated traffic-based load profile",
                vus=vus,
                duration_sec=duration_sec,
                endpoint=endpoint,
                method=method,
                requests_analyzed=total_requests,
            )

            # Get target URL from first entry if not provided, otherwise use base_target_url
            target_url = base_target_url
            if entries:
                first_url = entries[0].get("request", {}).get("url", "")
                if first_url:
                    # Extract base URL from first request
                    from urllib.parse import urlparse

                    parsed = urlparse(first_url)
                    target_url = f"{parsed.scheme}://{parsed.netloc}"

            return PerfSlice(
                name=f"traffic_{har_path.stem}",
                target_url=target_url,
                endpoint=endpoint,
                method=method,
                vus=vus,
                duration_sec=duration_sec,
            )

        except Exception as e:
            self.log.error("Failed to generate load profile from traffic", error=str(e))
            return None

    def run(self, sl, use_ml: bool = False, traffic_file: str = None):
        """
        Run performance test with enhanced Epoch 8 capabilities.

        Args:
            sl: PerfSlice defining the performance test
            use_ml: Whether to use ML-based anomaly detection
            traffic_file: Optional HAR file path for traffic-based load profile

        Returns:
            PerfReport with performance analysis results
        """
        t0 = time.time()
        scenario_id = "perf_" + sl.name

        # Generate traffic-based load profile if provided
        if traffic_file:
            traffic_sl = self.generate_load_profile_from_traffic(traffic_file)
            if traffic_sl:
                sl = traffic_sl
                scenario_id = "perf_traffic_" + sl.name
                self.log.info(
                    "Using traffic-based load profile",
                    endpoint=sl.endpoint,
                    method=sl.method,
                )

        self._write_script(sl)

        k6_bin = shutil.which("k6")
        k6_available = bool(k6_bin)
        errors = []
        proc = None  # Initialize proc variable

        if not k6_available:
            self.log.warning("k6 binary not on PATH; using simulated baseline tick")
            latency_ms = 45.0
        else:
            self.log.info("invoking k6", bin=k6_bin, script=self.k6_script_path)
            env = os.environ.copy()
            env["API_URL"] = sl.target_url
            proc = subprocess.run(
                [k6_bin, "run", self.k6_script_path],
                env=env,
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout)[-400:]
                errors.append(StageError(code="K6_NONZERO", detail=tail, where=sl.name))
            avg_ms = 0.0
            for line in proc.stdout.splitlines():
                if "http_req_duration" in line:
                    m = re.search(r"avg=([\d\.]+)(ms|s)", line)
                    if m:
                        avg_ms = float(m.group(1))
                        if m.group(2) == "s":
                            avg_ms *= 1000.0
                        break
            latency_ms = avg_ms if avg_ms > 0.0 else 0.0

        # Record performance metrics (with optional LLM-specific metrics)
        self.db.record(
            endpoint=sl.endpoint,
            method=sl.method.upper(),
            latency_ms=latency_ms,
            is_llm=self._is_llm_endpoint(sl.endpoint),
        )

        # Check for LLM-specific metrics if this appears to be an LLM endpoint
        llm_metrics = None
        if self._is_llm_endpoint(sl.endpoint):
            k6_output = ""
            if k6_available and proc is not None:
                k6_output = proc.stdout
            llm_metrics = self._extract_llm_metrics_from_response(k6_output)
            if llm_metrics:
                # Update the record with LLM-specific metrics
                self._update_with_llm_metrics(
                    sl.endpoint, sl.method.upper(), **llm_metrics
                )

        analysis = self._analyze(
            sl.endpoint, sl.method.upper(), latency_ms, use_ml=use_ml
        )

        passed = (not analysis["anomaly_detected"]) and (not errors)
        gate = PerfGateResult(
            gate="latency_baseline",
            passed=passed,
            latency_ms=latency_ms,
            baseline_count=analysis["count"],
            baseline_mean_ms=analysis["mean"],
            baseline_stddev_ms=analysis["stddev"],
            threshold_limit_ms=analysis["threshold_limit"],
            anomaly_detected=analysis["anomaly_detected"],
            k6_available=k6_available,
        )

        if not k6_available or analysis["initializing"]:
            verdict, status = Verdict.HITL, Status.OK
        elif analysis["anomaly_detected"]:
            verdict, status = Verdict.REGENERATE, Status.FAILED
            error_detail = (
                f"latency {latency_ms}ms > limit {analysis['threshold_limit']}ms"
            )
            if analysis.get("method", "").startswith("ml_"):
                error_detail += f" (ML detection: {analysis.get('ml_score', 'N/A')})"
            errors.append(
                StageError(code="PERF_ANOMALY", detail=error_detail, where=sl.name)
            )
        else:
            verdict, status = Verdict.AUTO_APPROVE, Status.OK

        # Add ML-specific metadata if used
        metadata = StageMeta(
            stage="perf",
            duration_ms=int((time.time() - t0) * 1000),
            model="ml_anomaly_detection"
            if use_ml and analysis.get("method", "").startswith("ml_")
            else "statistical",
        )

        return PerfReport(
            scenario_id=scenario_id,
            gates=[gate],
            verdict=verdict,
            status=status,
            errors=errors,
            metadata=metadata,
        )
