"""Report-printing functions extracted from legacy_cli.py during CLI unification."""

def print_visual_report(target_url: str, reports):
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


def print_perf_report(target_url, reports):
    print(chr(10) + "=" * 80)
    print("CHERENKOV PERFORMANCE BASELINE REPORT (B2 - optional Track B layer)")
    print("=" * 80)
    print("Target URL:", target_url)
    print("Slices Verified:", len(reports))
    print("=" * 80)
    for r in reports:
        status_str = "OK" if r.status == "ok" else "FAILED"
        verdict_str = (
            r.verdict.upper() if hasattr(r.verdict, "upper") else str(r.verdict).upper()
        )
        print(
            chr(10) + "Slice:",
            r.scenario_id,
            "[" + status_str + "]  Verdict:",
            verdict_str,
        )
        print("-" * 80)
        if r.errors:
            for err in r.errors:
                print("  Error [" + err.code + "]:", err.detail)
        if not r.gates:
            print("  (no gates evaluated)")
            continue
        for g in r.gates:
            pass_str = "PASS" if g.passed else "FAIL"
            print("  Gate " + g.gate + ": [" + pass_str + "]")
            print(
                "    latency_ms="
                + str(g.latency_ms)
                + "  k6_available="
                + str(g.k6_available)
            )
            print(
                "    baseline: count="
                + str(g.baseline_count)
                + " mean="
                + str(g.baseline_mean_ms)
                + "ms stddev="
                + str(g.baseline_stddev_ms)
                + "ms"
            )
            if g.threshold_limit_ms:
                print(
                    "    threshold_limit_ms="
                    + str(g.threshold_limit_ms)
                    + "  anomaly_detected="
                    + str(g.anomaly_detected)
                )
    print(chr(10) + "=" * 80 + chr(10))
