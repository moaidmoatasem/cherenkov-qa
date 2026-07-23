"""
Coverage gap report: compare spec endpoints against executed test scenarios.

Reads the OpenAPI spec via IngestStage and compares the full endpoint+method
set against the .spec.ts files present in stub/generated_tests/.  Writes a
machine-readable JSON file and prints a human summary.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _load_spec_endpoints(spec_path: str | None) -> list[dict[str, Any]]:
    """Return [{path, method, response_codes}] for every operation in the spec."""
    from cherenkov.core.contracts import Status
    from cherenkov.stages.ingest import IngestStage

    if not spec_path:
        # Try auto-discovery
        from cherenkov.core.config_loader import LayeredConfig
        found = LayeredConfig().autodetect_spec()
        if not found:
            return []
        spec_path = found[0]

    stage = IngestStage(run_id="coverage")
    result = stage.run(spec_path)

    endpoints = []
    if result.status == Status.FAILED:
        return []

    for ep in result.endpoints:
        response_codes = sorted(
            str(k) for k in ep.operation.get("responses", {})
            if str(k).isdigit()
        )
        endpoints.append({
            "path": ep.path,
            "method": ep.method,
            "response_codes": response_codes,
            "richness": round(ep.richness, 2),
        })

    return endpoints


def _get_tested_scenarios(tests_dir: str) -> set[str]:
    """Return the set of scenario base-names (file stems) present in tests_dir."""
    if not os.path.isdir(tests_dir):
        return set()
    return {
        f.replace(".spec.ts", "")
        for f in os.listdir(tests_dir)
        if f.endswith(".spec.ts")
    }


def generate_coverage_report(
    spec_path: str | None,
    tests_dir: str,
    executed_scenario_ids: list[str] | None = None,
    out_path: str = ".cherenkov/coverage_report.json",
) -> dict[str, Any]:
    """
    Build a coverage report dict, print a human summary, and write out_path.

    executed_scenario_ids: scenario_ids from validate_suite() results, used
    to distinguish "test file exists" from "test was actually executed".
    Falls back to the set of .spec.ts files if None.
    """
    all_endpoints = _load_spec_endpoints(spec_path)
    tested_scenarios = _get_tested_scenarios(tests_dir)
    executed = set(executed_scenario_ids) if executed_scenario_ids is not None else tested_scenarios

    covered_paths: set[str] = set()
    uncovered: list[dict] = []

    for ep in all_endpoints:
        key = f"{ep['method'].lower()}_{ep['path'].strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        # Fuzzy match: any executed scenario whose name starts with the key or contains the path
        matched = any(
            key in sid or ep["path"].strip("/").replace("/", "_") in sid
            for sid in executed
        )
        if matched:
            covered_paths.add(ep["path"])
        else:
            uncovered.append(ep)

    total_endpoints = len(all_endpoints)
    covered_count = len(covered_paths)
    test_count = len(tested_scenarios)

    # Collect all response codes in the spec vs what was tested
    all_codes: set[str] = set()
    for ep in all_endpoints:
        all_codes.update(ep["response_codes"])

    # Codes covered = response codes from spec endpoints that have matching tests
    covered_codes: set[str] = set()
    for ep in all_endpoints:
        if ep["path"] in covered_paths:
            covered_codes.update(ep["response_codes"])

    report = {
        "spec_endpoints": total_endpoints,
        "tests_generated": test_count,
        "covered_endpoints": covered_count,
        "coverage_pct": round(covered_count / total_endpoints * 100, 1) if total_endpoints else 0.0,
        "uncovered": [f"{e['method']} {e['path']}" for e in uncovered],
        "response_codes": {
            "in_spec": sorted(all_codes),
            "covered": sorted(covered_codes),
            "missing": sorted(all_codes - covered_codes),
        },
    }

    # Write JSON file
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Print human summary
    width = 43
    pct = report["coverage_pct"]
    print("\nCoverage Report")
    print("─" * width)
    print(f"Endpoints in spec:  {total_endpoints:>6}")
    print(f"Tests generated:    {test_count:>6}  ({pct:.0f}%)")
    print(f"Covered endpoints:  {covered_count:>6}  ({pct:.0f}%)")
    if uncovered:
        print(f"Skipped (no test):  {len(uncovered):>6}")
        for ep in uncovered[:10]:
            print(f"  {ep['method']} {ep['path']}  — no test generated")
        if len(uncovered) > 10:
            print(f"  … and {len(uncovered) - 10} more")
    print()
    if all_codes:
        covered_str = "  ".join(
            ("✓" if c in covered_codes else "✗") + " " + c
            for c in sorted(all_codes)
        )
        print(f"Response codes:  {covered_str}")
    print("─" * width)
    print(f"Coverage report written to {out_path}\n")

    return report
