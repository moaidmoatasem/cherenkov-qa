"""Performance metrics API — k6 latency baselines & anomaly detection (#882)."""
from __future__ import annotations

from fastapi import APIRouter
from typing import Any, Dict, List, Optional

from cherenkov.execution.k6_runner import K6Runner
from cherenkov.execution.perf_analyzer import PerformanceAnalyzer

router = APIRouter(prefix="/api/v1/perf", tags=["perf"])


@router.get("/metrics", operation_id="get_perf_metrics")
async def get_perf_metrics() -> List[Dict[str, Any]]:
    """Return latest performance metrics from SQLite baseline store."""
    analyzer = PerformanceAnalyzer()
    conn = analyzer._connect()
    
    # Get most recent metric per endpoint/method combination
    rows = conn.execute("""
        SELECT endpoint, method, latency_ms, timestamp
        FROM perf_metrics pm1
        WHERE timestamp = (
            SELECT MAX(timestamp) FROM perf_metrics pm2 
            WHERE pm2.endpoint = pm1.endpoint AND pm2.method = pm1.method
        )
        ORDER BY endpoint, method
    """).fetchall()
    
    metrics = []
    for endpoint, method, latency_ms, ts in rows:
        stats = analyzer.get_baseline_stats(endpoint, method)
        analysis = analyzer.analyze_anomaly(endpoint, method, latency_ms)
        
        metrics.append({
            "endpoint": endpoint,
            "method": method,
            "latency_ms": latency_ms,
            "status": analysis["status"],
            "baseline_mean": stats["mean"] if stats["count"] > 0 else None,
            "baseline_stddev": stats["stddev"] if stats["count"] > 0 else None,
            "threshold_limit": analysis.get("threshold_limit"),
            "message": analysis.get("message"),
        })
    
    return metrics


@router.post("/run", operation_id="run_perf_test")
async def run_perf_test(target_url: Optional[str] = None) -> Dict[str, Any]:
    """Execute a k6 performance test and return metrics."""
    runner = K6Runner()
    result = runner.run_k6_validation(api_url=target_url)
    
    # Convert to frontend-friendly format
    if result["status"] == "degraded":
        # k6 not installed
        return {
            "endpoint": "/users",
            "method": "POST",
            "latency_ms": 0,
            "status": "initializing",
            "message": result["message"],
            "instructions": result.get("instructions"),
        }
    
    # Parse latency from metrics if available
    latency_ms = 0.0
    duration_line = result.get("metrics", {}).get("http_req_duration", "")
    import re
    match = re.search(r"avg=([\d\.]+)(ms|s)", duration_line)
    if match:
        latency_ms = float(match.group(1))
        if match.group(2) == "s":
            latency_ms *= 1000.0
    
    return {
        "endpoint": "/users",
        "method": "POST",
        "latency_ms": latency_ms,
        "status": result["status"],
        "message": result.get("message"),
        "exit_code": result.get("exit_code"),
        "script_path": result.get("script_path"),
    }
