import json
import os
import glob
from cherenkov.core.errors import get_logger


def get_latest_run_dir() -> str:
    runs_dir = os.path.abspath(".cherenkov/runs")
    if not os.path.exists(runs_dir):
        return ""
    all_runs = glob.glob(os.path.join(runs_dir, "*"))
    if not all_runs:
        return ""
    return max(all_runs, key=os.path.getctime)


def run_report(output: str, diff: str = None, run_id: str | None = None) -> int:
    get_logger("REPORT")
    if run_id:
        run_dir = os.path.abspath(os.path.join(".cherenkov/runs", run_id))
        if not os.path.isdir(run_dir):
            print(f"Error: Run directory not found: {run_dir}")
            return 1
    else:
        run_dir = get_latest_run_dir()
        if not run_dir:
            print("Error: No runs found in .cherenkov/runs/")
            return 1

    events_file = os.path.join(run_dir, "events.jsonl")
    if not os.path.exists(events_file):
        print(f"Error: {events_file} not found")
        return 1

    report_data = {
        "run_id": os.path.basename(run_dir),
        "skipped_endpoints": [],
        "scenarios": [],
        "success_rate": 0.0,
        "total_scenarios": 0,
        "passed_scenarios": 0,
    }

    with open(events_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get(
                "stage"
            ) == "INGEST" and "skipping low richness endpoint" in event.get("msg", ""):
                report_data["skipped_endpoints"].append(
                    {
                        "path": event.get("path"),
                        "method": event.get("method"),
                        "richness": event.get("richness"),
                    }
                )
            elif event.get("stage") == "REVIEW" and event.get("msg") == "stage success":
                passed = event.get("verdict") in (
                    "AUTO_APPROVE",
                    "HITL",
                )  # basic heuristic
                report_data["scenarios"].append(
                    {
                        "scenario_id": event.get("scenario_id", "unknown"),
                        "quality_score": event.get("quality_score"),
                        "verdict": event.get("verdict"),
                        "passed": passed,
                    }
                )

    report_data["total_scenarios"] = len(report_data["scenarios"])
    report_data["passed_scenarios"] = sum(
        1 for s in report_data["scenarios"] if s["passed"]
    )
    if report_data["total_scenarios"] > 0:
        report_data["success_rate"] = (
            report_data["passed_scenarios"] / report_data["total_scenarios"]
        )

    if output:
        with open(output, "w") as f:
            json.dump(report_data, f, indent=2)
        print(f"Report saved to {output}")

    if diff:
        if not os.path.exists(diff):
            print(f"Error: Diff file {diff} not found.")
            return 1
        with open(diff, "r") as f:
            diff_data = json.load(f)

        print(f"\n--- DIFF REPORT vs {diff} ---")
        print(f"Previous Success Rate: {diff_data.get('success_rate', 0):.2%}")
        print(f"Current Success Rate: {report_data['success_rate']:.2%}")

        prev_scens = {s["scenario_id"]: s for s in diff_data.get("scenarios", [])}
        curr_scens = {s["scenario_id"]: s for s in report_data["scenarios"]}

        added = set(curr_scens) - set(prev_scens)
        removed = set(prev_scens) - set(curr_scens)

        if added:
            print(f"Added scenarios: {len(added)}")
        if removed:
            print(f"Removed scenarios: {len(removed)}")

    # Print basic report
    print("\n=== CHERENKOV REPORT ===")
    print(f"Run ID: {report_data['run_id']}")
    print(
        f"Scenarios: {report_data['passed_scenarios']}/{report_data['total_scenarios']} passed"
    )
    print(f"Skipped low-richness endpoints: {len(report_data['skipped_endpoints'])}")
    for sk in report_data["skipped_endpoints"]:
        print(f"  - {sk['method']} {sk['path']} (richness: {sk['richness']})")
    print("========================\n")
    return 0
