#!/usr/bin/env python3
"""
smoke_test_perf_anomaly.py — proves the E8 robust latency anomaly detector:
catches spikes AND gradual drift, resists baseline contamination, and abstains
on thin data. Dependency-free.

Run:  PYTHONPATH=. python3 smoke_test_perf_anomaly.py
"""

from __future__ import annotations

import statistics
import sys

from cherenkov.stages.perf.anomaly import LatencyAnomalyDetector


def main() -> int:
    d = LatencyAnomalyDetector()
    stable = [50, 52, 49, 51, 50, 48, 53, 50, 51, 49]  # ~50ms baseline

    checks = {}

    # 1) normal point -> no anomaly
    checks["normal point is clean"] = d.evaluate(stable, 52).kind == "none"

    # 2) clear spike -> flagged
    checks["spike flagged"] = d.evaluate(stable, 500).kind == "spike"

    # 3) gradual drift: no single point spikes, but recent median creeps up.
    drift_hist = [50, 51, 52, 60, 70, 80, 90, 95, 100, 105]
    v = d.evaluate(drift_hist, 110)
    checks["drift flagged (before a hard spike)"] = v.kind == "drift"

    # 4) robustness: one contaminated warm-up sample must NOT inflate the band
    #    and swallow a real spike (mean+stddev would).
    contaminated = [50, 51, 49, 9000, 50, 52, 48, 51, 50, 49]  # one 9s outlier
    robust = d.evaluate(contaminated, 300).kind == "spike"
    # show the naive method would have been fooled:
    mean = statistics.mean(contaminated)
    sd = statistics.pstdev(contaminated)
    naive_upper = mean + 3.5 * sd
    naive_fooled = 300 < naive_upper
    checks["robust detector still catches spike"] = robust
    checks["(naive mean+stddev would miss it)"] = naive_fooled

    # 5) thin data -> abstain
    checks["abstains on thin data"] = (
        d.evaluate([50, 51], 999).kind == "insufficient_data"
    )

    for k, ok in checks.items():
        print(f"  [{'ok' if ok else 'XX'}] {k}")
    print(
        f"\n  naive upper bound with 9s outlier = {naive_upper:.0f}ms "
        f"(so a real 300ms spike hides under it)"
    )

    passed = all(checks.values())
    print(
        "\n[PASS] robust anomaly detector: spike + drift + contamination-resistant"
        if passed
        else "\n[FAIL] see above"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
