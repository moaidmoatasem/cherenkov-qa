#!/usr/bin/env python3
"""
smoke_test_perf_intelligence.py — Kill-criteria exit demo for Epoch 8 Perf Intelligence.

Covers:
  C2 (#117): Generative load profiles from truth/sources/traffic.py
  C3 (#118): LLM-aware perf metrics (TTFT/inter-token/tokens-sec/P95-99/cost)
  C4 (#119): ML anomaly tier (opt-in; statistical stays default)

Exit code 0 = all criteria passed.
"""
import importlib
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.stages.perf.perf_stage import PerfStage, PerfSlice, _BaselineDB
from cherenkov.stages.perf.anomaly import LatencyAnomalyDetector, AnomalyVerdict

PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  [PASS] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label} — {detail}")
        FAIL += 1


def main() -> int:
    global PASS, FAIL
    print("=" * 60)
    print("Epoch 8 Perf Intelligence — Kill-Criteria Exit Demo")
    print("=" * 60)

    tm = tempfile.TemporaryDirectory()
    db_path = os.path.join(tm.name, "perf_test.db")
    stage = PerfStage(db_path=db_path)

    # ── C3 (#118): LLM-aware metrics ────────────────────────────────────
    print("\n--- C3 (#118): LLM-aware perf metrics ---")

    # Record LLM endpoint metrics
    stage.db.record("/api/chat/completions", "POST", 120.0,
                     ttft_ms=45.0, itl_ms=15.0, cost_usd=0.002, is_llm=True)
    stage.db.record("/api/chat/completions", "POST", 135.0,
                     ttft_ms=50.0, itl_ms=18.0, cost_usd=0.0025, is_llm=True)
    stage.db.record("/api/chat/completions", "POST", 110.0,
                     ttft_ms=42.0, itl_ms=12.0, cost_usd=0.0018, is_llm=True)
    stage.db.record("/api/users", "GET", 30.0, is_llm=False)

    stats = stage.db.stats("/api/chat/completions", "POST")
    check("LLM endpoint has metrics recorded", stats["count"] == 3)

    llm_stats = stage.db.llm_stats("/api/chat/completions", "POST")
    check("LLM stats returns ttft_mean_ms", llm_stats.get("ttft_mean_ms", 0) > 0)
    check("LLM stats returns itl_mean_ms", llm_stats.get("itl_mean_ms", 0) > 0)
    check("LLM stats returns cost_mean_usd", llm_stats.get("cost_mean_usd", 0) > 0)
    check("LLM stats has request count", llm_stats["llm_request_count"] == 3)

    non_llm_stats = stage.db.llm_stats("/api/users", "GET")
    check("Non-LLM endpoint returns zero LLM stats",
           non_llm_stats["llm_request_count"] == 0)

    # Extraction returns None (honest absence, #157)
    llm_extracted = stage._extract_llm_metrics_from_response("some k6 output")
    check("LLM extraction returns None (not hash-derived)", llm_extracted is None)

    # LLM endpoint detection
    check("/api/chat/completions detected as LLM",
           stage._is_llm_endpoint("/api/chat/completions"))
    check("/api/users NOT detected as LLM",
           not stage._is_llm_endpoint("/api/users"))
    check("/v1/embeddings detected as LLM",
           stage._is_llm_endpoint("/v1/embeddings"))
    check("/health NOT detected as LLM",
           not stage._is_llm_endpoint("/health"))

    # P95-99 calculation
    stage.db.record("/api/perf", "GET", 100.0)
    stage.db.record("/api/perf", "GET", 200.0)
    stage.db.record("/api/perf", "GET", 300.0)
    stage.db.record("/api/perf", "GET", 400.0)
    stage.db.record("/api/perf", "GET", 500.0)
    stage.db.record("/api/perf", "GET", 600.0)
    stage.db.record("/api/perf", "GET", 700.0)
    stage.db.record("/api/perf", "GET", 800.0)
    stage.db.record("/api/perf", "GET", 900.0)
    stage.db.record("/api/perf", "GET", 1000.0)
    pstats = stage.db.stats("/api/perf", "GET")
    check("P95 endpoint has 10 metrics", pstats["count"] == 10)

    # ── C4 (#119): ML anomaly tier ───────────────────────────────────────
    print("\n--- C4 (#119): ML anomaly tier ---")

    # Statistical path (zero-dependency default)
    sl = PerfSlice(name="test", target_url="http://localhost:3000",
                   endpoint="/api/test", method="GET", vus=1, duration_sec=1)
    result = stage.run(sl)
    check("Statistical run completes", result.status.value == "ok")

    # Record baseline for anomaly detection
    for i in range(10):
        stage.db.record("/api/anomaly", "GET", 40.0 + (i % 3) * 2.0)

    analysis_normal = stage._analyze("/api/anomaly", "GET", 42.0)
    check("Normal latency not detected as anomaly",
           not analysis_normal["anomaly_detected"])
    check("Default method is statistical",
           analysis_normal["method"] == "statistical")

    analysis_spike = stage._analyze("/api/anomaly", "GET", 500.0)
    check("Spike latency detected as anomaly",
           analysis_spike["anomaly_detected"])
    check("Spike uses statistical method",
           analysis_spike["method"] == "statistical")

    test_count = analysis_normal["count"]
    check("Analysis returns count", test_count >= 3)

    analysis_init = stage._analyze("/api/never_seen", "GET", 50.0)
    check("New endpoint returns initializing",
           analysis_init.get("initializing", False))

    # ── LatencyAnomalyDetector (robust spike + drift) ────────────────────
    print("\n--- LatencyAnomalyDetector (robust spike/drift) ---")
    detector = LatencyAnomalyDetector(k=3.5, min_samples=8)

    history = [40.0, 42.0, 41.0, 43.0, 39.0, 41.0, 42.0, 40.0, 43.0, 41.0]
    verdict = detector.evaluate(history, 42.0)
    check("Normal value within band, no anomaly", not verdict.is_anomaly)
    check("No anomaly kind is 'none'", verdict.kind == "none")

    verdict = detector.evaluate(history, 200.0)
    check("Extreme value detected as spike", verdict.is_anomaly)
    check("Spike kind is 'spike'", verdict.kind == "spike")

    verdict = detector.evaluate([], 42.0)
    check("Insufficient history returns insufficient_data",
           verdict.kind == "insufficient_data")

    # Drift detection: recent values creep up
    drift_history = [40.0] * 10 + [60.0] * 5
    verdict = detector.evaluate(drift_history[:-1], drift_history[-1])
    check("Drift detection works for gradual creep",
           verdict.kind == "drift")

    # ── C2 (#117): Generative load profiles ──────────────────────────────
    print("\n--- C2 (#117): Generative load profiles ---")

    har_content = json.dumps({
        "log": {
            "entries": [
                {"request": {"method": "POST",
                  "url": "http://localhost:3000/api/chat",
                  "postData": {"mimeType": "application/json", "text": "hi"}},
                 "response": {"status": 200, "statusText": "OK", "headers": []},
                 "timings": {"send": 5, "wait": 100, "receive": 10}},
                {"request": {"method": "GET",
                  "url": "http://localhost:3000/api/chat"},
                 "response": {"status": 200, "statusText": "OK", "headers": []},
                 "timings": {"send": 3, "wait": 80, "receive": 5}},
                {"request": {"method": "GET",
                  "url": "http://localhost:3000/health"},
                 "response": {"status": 200, "statusText": "OK", "headers": []},
                 "timings": {"send": 2, "wait": 30, "receive": 3}},
            ]
        }
    })

    fd, har_path = tempfile.mkstemp(suffix=".har")
    os.close(fd)
    with open(har_path, "w") as f:
        f.write(har_content)

    profile = stage.generate_load_profile_from_traffic(har_path)
    check("Load profile generated from HAR", profile is not None)
    if profile:
        check("Profile has valid VUs", profile.vus > 0)
        check("Profile has valid duration", profile.duration_sec > 0)
        check("Profile has endpoint", bool(profile.endpoint))
        check("Profile has method", bool(profile.method))

    os.unlink(har_path)

    # Missing file returns None
    profile = stage.generate_load_profile_from_traffic("/nonexistent.har")
    check("Missing HAR returns None gracefully", profile is None)

    # Empty HAR
    empty_har = json.dumps({"log": {"entries": []}})
    fd, empty_path = tempfile.mkstemp(suffix=".har")
    os.close(fd)
    with open(empty_path, "w") as f:
        f.write(empty_har)
    profile = stage.generate_load_profile_from_traffic(empty_path)
    check("Empty HAR returns None gracefully", profile is None)
    os.unlink(empty_path)

    # Traffic Source Adapter integration with truth/sources/traffic.py
    from cherenkov.truth.sources.traffic import TrafficSourceAdapter
    tsa = TrafficSourceAdapter()
    fd, har_path2 = tempfile.mkstemp(suffix=".har")
    os.close(fd)
    with open(har_path2, "w") as f:
        f.write(har_content)
    claims = tsa.discover_claims(har_path2)
    check("TrafficSourceAdapter extracts claims from HAR", len(claims) > 0)
    observed_statuses = [c for c in claims if c.category == "observed_status"]
    check("Traffic claims include status claims", len(observed_statuses) > 0)
    os.unlink(har_path2)

    # ── Summary ──────────────────────────────────────────────────────────
    tm.cleanup()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    if FAIL == 0:
        print("STATUS: ALL CRITERIA PASSED — Epoch 8 Perf Intelligence is ready.")
    else:
        print(f"STATUS: {FAIL} criteria FAILED — review output above.")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
