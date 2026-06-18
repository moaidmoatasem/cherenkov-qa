import json
import os
import glob
import xml.etree.ElementTree as ET
from cherenkov.core.errors import get_logger

def write_junit(output_path: str, data: dict):
    testsuites = ET.Element("testsuites")
    testsuite = ET.SubElement(testsuites, "testsuite", 
                              name="cherenkov", 
                              tests=str(data["total_scenarios"]), 
                              failures=str(data["total_scenarios"] - data["passed_scenarios"]))
    for scenario in data["scenarios"]:
        testcase = ET.SubElement(testsuite, "testcase", name=scenario["scenario_id"], classname="cherenkov.review")
        if not scenario["passed"]:
            failure = ET.SubElement(testcase, "failure", message="Conformance or quality check failed")
            failure.text = f"Verdict: {scenario.get('verdict')}\nScore: {scenario.get('quality_score')}"
    
    tree = ET.ElementTree(testsuites)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

def write_sarif(output_path: str, data: dict):
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CHERENKOV-QA",
                        "informationUri": "https://github.com/moaidmoatasem/cherenkov-qa",
                        "rules": [
                            {
                                "id": "API-DRIFT-01",
                                "name": "ApiConformanceDrift",
                                "shortDescription": {"text": "API Drift Detected"}
                            }
                        ]
                    }
                },
                "results": []
            }
        ]
    }
    for scenario in data["scenarios"]:
        if not scenario["passed"]:
            sarif["runs"][0]["results"].append({
                "ruleId": "API-DRIFT-01",
                "message": {
                    "text": f"Scenario {scenario['scenario_id']} failed conformance review. Verdict: {scenario.get('verdict')}."
                },
                "level": "error"
            })
            
    with open(output_path, "w") as f:
        json.dump(sarif, f, indent=2)


def get_latest_run_dir() -> str:
    runs_dir = os.path.abspath(".cherenkov/runs")
    if not os.path.exists(runs_dir):
        return ""
    all_runs = glob.glob(os.path.join(runs_dir, "*"))
    if not all_runs:
        return ""
    return max(all_runs, key=os.path.getctime)


def run_report(output: str, diff: str = None, format: str = "json") -> int:
    get_logger("REPORT")
    latest_run = get_latest_run_dir()
    if not latest_run:
        print("Error: No runs found in .cherenkov/runs/")
        return 1

    events_file = os.path.join(latest_run, "events.jsonl")
    if not os.path.exists(events_file):
        print(f"Error: {events_file} not found")
        return 1

    report_data = {
        "run_id": os.path.basename(latest_run),
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
                report_data["skipped_endpoints"].append(  # type: ignore
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
                report_data["scenarios"].append(  # type: ignore
                    {
                        "scenario_id": event.get("scenario_id", "unknown"),
                        "quality_score": event.get("quality_score"),
                        "verdict": event.get("verdict"),
                        "passed": passed,
                    }
                )

    report_data["total_scenarios"] = len(report_data["scenarios"])  # type: ignore
    report_data["passed_scenarios"] = sum(
        1  # type: ignore
        for s in report_data["scenarios"]  # type: ignore
        if s["passed"]  # type: ignore
    )
    if report_data["total_scenarios"] > 0:  # type: ignore
        report_data["success_rate"] = (
            report_data["passed_scenarios"] / report_data["total_scenarios"]  # type: ignore
        )

    if output:
        if format == "junit":
            write_junit(output, report_data)
        elif format == "sarif":
            write_sarif(output, report_data)
        else:
            with open(output, "w") as f:
                json.dump(report_data, f, indent=2)
        print(f"Report saved to {output} in {format} format")

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
        curr_scens = {s["scenario_id"]: s for s in report_data["scenarios"]}  # type: ignore

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
    print(f"Skipped low-richness endpoints: {len(report_data['skipped_endpoints'])}")  # type: ignore
    for sk in report_data["skipped_endpoints"]:  # type: ignore
        print(f"  - {sk['method']} {sk['path']} (richness: {sk['richness']})")
    print("========================\n")
    return 0
