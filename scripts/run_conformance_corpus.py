"""
scripts/run_conformance_corpus.py — Phase M0 E0.5d Conformance Corpus Benchmark Runner.

Executes probe planning and unprobed endpoint analysis across all specs in specs/corpus/.
Validates the zero-silent-drop invariant: Total Endpoints == Probes Planned + Dropped Endpoints.
Outputs detailed statistics and reason breakdowns per spec.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any
import yaml

from cherenkov.divergence.coverage import _extract_endpoints
from cherenkov.divergence.probe_planner import plan_probes, unprobed_endpoints

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def load_spec(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(f)
        try:
            return json.load(f)
        except Exception:
            f.seek(0)
            return yaml.safe_load(f)


def analyze_spec(spec_path: Path, max_probes: int = 100000) -> dict[str, Any]:
    spec_name = spec_path.stem
    spec_dict = load_spec(spec_path)

    # 1. Extract total endpoints from spec across all HTTP operations
    raw_endpoints = _extract_endpoints(spec_dict)
    total_endpoints = len(raw_endpoints)

    engine_status = "PASS"
    crash_trace = ""

    try:
        # 2. Plan probes
        planned = plan_probes(
            spec_dict,
            max_probes=max_probes,
            include_bare=False,
            known_identifiers=None,
            allow_mutations=False,
        )

        # 3. Get unprobed (dropped) endpoints with explicit reasons
        unprobed = unprobed_endpoints(
            spec_dict,
            max_probes=max_probes,
            include_bare=False,
            known_identifiers=None,
            allow_mutations=False,
        )
    except Exception as exc:
        engine_status = f"CAUGHT CRASH: {type(exc).__name__}: {exc}"
        crash_trace = traceback.format_exc()
        planned = []
        unprobed = []

    probes_planned_count = len(planned)
    dropped_count = len(unprobed)

    # 4. Zero silent drop check
    silent_drops = total_endpoints - (probes_planned_count + dropped_count)

    # Categorize drop reasons
    reason_counter = Counter()
    for ep in unprobed:
        # Simplify reason string to taxonomy categories
        r = ep.reason
        if "path parameters could not be sampled" in r:
            category = "Unfillable Path Parameters (Missing Schema/Samples)"
        elif "no probe for" in r and "mutation probes need a required" in r:
            category = "Non-GET Method Without Required Body/Enum (Mutation Safeguard)"
        elif "happy-path probe is skipped on templated paths" in r:
            category = "Templated Path Without Known Identifier (404 Avoidance)"
        elif "query parameters are required" in r:
            category = "Required Query Parameters Without Safe Defaults"
        elif "no mechanical hypothesis was derivable" in r:
            category = "No Derivable Mechanical Hypothesis (Complex/Opaque Schema)"
        elif "dropped by the max_probes cap" in r:
            category = "Max Probes Cap Exceeded"
        else:
            category = f"Other: {r[:60]}"
        reason_counter[category] += 1

    return {
        "spec": spec_name,
        "filename": spec_path.name,
        "file": str(spec_path),
        "title": spec_dict.get("info", {}).get("title", spec_name),
        "version": spec_dict.get("openapi") or spec_dict.get("swagger") or "3.0.0",
        "total_endpoints": total_endpoints,
        "probes_planned": probes_planned_count,
        "dropped_endpoints": dropped_count,
        "silent_drops": silent_drops,
        "zero_silent_drop_passed": (silent_drops == 0),
        "engine_status": engine_status,
        "crash_trace": crash_trace,
        "drop_reasons": dict(reason_counter),
        "unprobed_details": [
            {"method": ep.method, "path": ep.path, "reason": ep.reason}
            for ep in unprobed
        ],
    }


def main():
    corpus_dir = Path("specs/corpus")
    if not corpus_dir.exists():
        print(f"[ERROR] Directory {corpus_dir} does not exist. Run fetch_corpus_specs.py first.")
        sys.exit(1)

    spec_files = sorted(
        [p for p in corpus_dir.iterdir() if p.suffix.lower() in (".json", ".yaml", ".yml")]
    )
    if not spec_files:
        print(f"[ERROR] No specs found in {corpus_dir}.")
        sys.exit(1)

    print(f"=== Running CHERENKOV Conformance Corpus Benchmark on {len(spec_files)} Specs ===")

    results = []
    grand_total_endpoints = 0
    grand_total_probes = 0
    grand_total_dropped = 0
    grand_total_silent = 0
    taxonomy_total = Counter()

    for sf in spec_files:
        res = analyze_spec(sf)
        results.append(res)

        grand_total_endpoints += res["total_endpoints"]
        grand_total_probes += res["probes_planned"]
        grand_total_dropped += res["dropped_endpoints"]
        grand_total_silent += res["silent_drops"]

        for cat, cnt in res["drop_reasons"].items():
            taxonomy_total[cat] += cnt

        status_flag = "PASS" if res["zero_silent_drop_passed"] else "FAIL (SILENT DROPS)"
        print(f"\nSpec: {res['filename'].upper()} ({res['title']})")
        print(f"  Version        : {res['version']}")
        print(f"  Total Endpoints: {res['total_endpoints']}")
        print(f"  Probes Planned : {res['probes_planned']}")
        print(f"  Dropped        : {res['dropped_endpoints']}")
        print(f"  Silent Drops   : {res['silent_drops']} [{'OK' if res['silent_drops']==0 else 'FAIL'}]")
        print(f"  Engine Status  : {res['engine_status']}")
        print("  Drop Reasons Breakdown:")
        for r, c in res["drop_reasons"].items():
            print(f"    - {r}: {c}")

        # Assert zero silent drop invariant
        assert res["silent_drops"] == 0, f"Silent drop violation in {sf.name}: {res['silent_drops']} silent drops detected!"

    print("\n" + "=" * 70)
    print("=== HIGH-LEVEL CONFORMANCE CORPUS DASHBOARD ===")
    print(f"  Total Specs Tested     : {len(results)}")
    print(f"  Total Spec Endpoints   : {grand_total_endpoints:,}")
    print(f"  Total Probes Planned   : {grand_total_probes:,}")
    print(f"  Total Dropped Endpoints: {grand_total_dropped:,}")
    print(f"  Total Silent Drops     : {grand_total_silent} (Zero-Silent-Drop Invariant: {'100% PROVEN' if grand_total_silent == 0 else 'VIOLATED'})")
    print("=" * 70)

    print("\n--- GLOBAL DROP REASON TAXONOMY ---")
    for cat, count in taxonomy_total.most_common():
        pct = (count / grand_total_dropped * 100.0) if grand_total_dropped > 0 else 0
        print(f"  {count:5d} ({pct:5.1f}%) | {cat}")

    # Write output JSON for report generator
    report_data = {
        "summary": {
            "total_specs": len(results),
            "grand_total_endpoints": grand_total_endpoints,
            "grand_total_probes": grand_total_probes,
            "grand_total_dropped": grand_total_dropped,
            "grand_total_silent_drops": grand_total_silent,
            "zero_silent_drop_proven": (grand_total_silent == 0),
        },
        "taxonomy": dict(taxonomy_total),
        "spec_results": results,
    }

    out_file = Path("specs/corpus_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nSaved benchmark results to {out_file}")


if __name__ == "__main__":
    main()
