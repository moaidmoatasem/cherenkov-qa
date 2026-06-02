"""
CHERENKOV stages/perf/perf_stage.py - Phase B2 Perf Baseline stage.
Authority: v3.1 + delta.

Optional capability layer on top of Track A. Never replaces API conformance.
Records run latencies in local SQLite (.cherenkov/perf_metrics.db) and flags
statistical-outlier regressions vs historical mean+stddev (>= 3 runs).

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
import time
from cherenkov.core.contracts import (
    StageMeta, StageError, Status, Verdict,
    PerfSlice, PerfGateResult, PerfReport,
)
from cherenkov.core.errors import get_logger


class _BaselineDB:
    def __init__(self, db_path):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS perf_metrics ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "endpoint TEXT NOT NULL,"
            "method TEXT NOT NULL,"
            "latency_ms REAL NOT NULL,"
            "timestamp INTEGER NOT NULL)"
        )
        conn.commit()
        conn.close()

    def record(self, endpoint, method, latency_ms):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO perf_metrics (endpoint, method, latency_ms, timestamp) VALUES (?,?,?,?)",
            (endpoint, method, latency_ms, int(time.time())),
        )
        conn.commit()
        conn.close()

    def stats(self, endpoint, method):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT latency_ms FROM perf_metrics WHERE endpoint=? AND method=?",
            (endpoint, method),
        ).fetchall()
        conn.close()
        latencies = [r[0] for r in rows]
        count = len(latencies)
        if count == 0:
            return {"count": 0, "mean": 0.0, "stddev": 0.0}
        mean = sum(latencies) / count
        variance = sum((x - mean) ** 2 for x in latencies) / count if count > 1 else 0.0
        return {"count": count, "mean": round(mean, 2), "stddev": round(math.sqrt(variance), 2)}


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
    return (K6_SCRIPT_TEMPLATE
            .replace("__VUS__", str(sl.vus))
            .replace("__DUR__", str(sl.duration_sec))
            .replace("__URL__", sl.target_url)
            .replace("__METHOD__", sl.method.upper())
            .replace("__ENDPOINT__", sl.endpoint))


class PerfStage:
    def __init__(self, run_id=None, db_path=None):
        self.run_id = run_id
        self.log = get_logger("PERF", run_id)
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        self.stub_dir = os.path.join(repo_root, "stub")
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")
        self.k6_script_path = os.path.join(self.tests_dir, "k6_perf.js")
        self.db_path = db_path or os.path.join(repo_root, ".cherenkov", "perf_metrics.db")
        self.db = _BaselineDB(self.db_path)

    def _write_script(self, sl):
        os.makedirs(self.tests_dir, exist_ok=True)
        code = _render_script(sl)
        with open(self.k6_script_path, "w", encoding="utf-8") as f:
            f.write(code)
        return code

    def _analyze(self, endpoint, method, current_ms, threshold=2.0):
        stats = self.db.stats(endpoint, method)
        count, mean, stddev = stats["count"], stats["mean"], stats["stddev"]
        if count < 3:
            return {"count": count, "mean": mean, "stddev": stddev,
                    "threshold_limit": 0.0, "anomaly_detected": False, "initializing": True}
        limit = mean + (threshold * stddev)
        return {"count": count, "mean": mean, "stddev": stddev,
                "threshold_limit": round(limit, 2),
                "anomaly_detected": current_ms > limit, "initializing": False}

    def run(self, sl):
        t0 = time.time()
        scenario_id = "perf_" + sl.name
        self._write_script(sl)

        k6_bin = shutil.which("k6")
        k6_available = bool(k6_bin)
        errors = []

        if not k6_available:
            self.log.warning("k6 binary not on PATH; using simulated baseline tick")
            latency_ms = 45.0
        else:
            self.log.info("invoking k6", bin=k6_bin, script=self.k6_script_path)
            env = os.environ.copy()
            env["API_URL"] = sl.target_url
            proc = subprocess.run([k6_bin, "run", self.k6_script_path],
                                  env=env, capture_output=True, text=True)
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

        self.db.record(sl.endpoint, sl.method.upper(), latency_ms)
        analysis = self._analyze(sl.endpoint, sl.method.upper(), latency_ms)

        passed = (not analysis["anomaly_detected"]) and (not errors)
        gate = PerfGateResult(
            gate="latency_baseline", passed=passed, latency_ms=latency_ms,
            baseline_count=analysis["count"], baseline_mean_ms=analysis["mean"],
            baseline_stddev_ms=analysis["stddev"],
            threshold_limit_ms=analysis["threshold_limit"],
            anomaly_detected=analysis["anomaly_detected"], k6_available=k6_available,
        )

        if not k6_available or analysis["initializing"]:
            verdict, status = Verdict.HITL, Status.OK
        elif analysis["anomaly_detected"]:
            verdict, status = Verdict.REGENERATE, Status.FAILED
            errors.append(StageError(code="PERF_ANOMALY",
                detail="latency " + str(latency_ms) + "ms > limit " + str(analysis["threshold_limit"]) + "ms",
                where=sl.name))
        else:
            verdict, status = Verdict.AUTO_APPROVE, Status.OK

        return PerfReport(scenario_id=scenario_id, gates=[gate], verdict=verdict,
                          status=status, errors=errors,
                          metadata=StageMeta(stage="perf", duration_ms=int((time.time() - t0) * 1000)))
