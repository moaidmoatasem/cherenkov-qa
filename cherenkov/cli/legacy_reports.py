"""
cherenkov/cli/legacy_reports.py — shared human-readable report printers
used by the Click CLI commands in advanced.py.

These were originally inline in cherenkov.py (argparse entry point) and are
extracted here so the Click-based CLI can reuse them without circular imports.
"""

from __future__ import annotations


def print_visual_report(target_url: str, reports) -> None:
    print("\n" + "=" * 80)
    print("CHERENKOV VISUAL REGRESSION REPORT (B1 — optional Track B layer)")
    print("=" * 80)
    print(f"Target URL: {target_url}")
    print(f"Slices Verified: {len(reports)}")
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = (
            r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        )
        print(f"\nSlice: {r.scenario_id} [{status_str}]  Verdict: {verdict_str}")
        print("-" * 80)
        if r.errors:
            for err in r.errors:
                print(f"  Error [{err.code}]: {err.detail}")
        if not r.gates:
            print("  (no gates evaluated)")
            continue
        for g in r.gates:
            pass_str = "PASS" if g.passed else "FAIL"
            print(f"  Gate {g.gate}: [{pass_str}]  diff_pixels={g.diff_pixels}")
            if g.baseline_path:
                print(f"    baseline: {g.baseline_path}")
            if g.actual_path:
                print(f"    actual:   {g.actual_path}")
    print("\n" + "=" * 80 + "\n")


def print_perf_report(target_url: str, reports) -> None:
    print("\n" + "=" * 80)
    print("CHERENKOV PERFORMANCE BASELINE REPORT (B2 - optional Track B layer)")
    print("=" * 80)
    print(f"Target URL: {target_url}")
    print(f"Slices Verified: {len(reports)}")
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = (
            r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        )
        print(f"\nSlice: {r.scenario_id} [{status_str}]  Verdict: {verdict_str}")
        print("-" * 80)
        if r.errors:
            for err in r.errors:
                print(f"  Error [{err.code}]: {err.detail}")
        if not r.gates:
            print("  (no gates evaluated)")
            continue
        for g in r.gates:
            pass_str = "PASS" if g.passed else "FAIL"
            print(f"  Gate {g.gate}: [{pass_str}]")
            print(
                f"    latency_ms={g.latency_ms}"
                f"  k6_available={g.k6_available}"
            )
            print(
                f"    baseline: count={g.baseline_count}"
                f" mean={g.baseline_mean_ms}ms"
                f" stddev={g.baseline_stddev_ms}ms"
            )
            if g.threshold_limit_ms:
                print(
                    f"    threshold_limit_ms={g.threshold_limit_ms}"
                    f"  anomaly_detected={g.anomaly_detected}"
                )
    print("\n" + "=" * 80 + "\n")
