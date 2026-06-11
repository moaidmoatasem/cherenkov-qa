"""
CHERENKOV execution/emitters/allure.py — Allure 2 JSON result emitter.

Emits one allure-results/{uuid}-result.json file per test scenario.
The caller (cherenkov.py) passes results into emit_allure(); the function
writes to <output_dir> (default: allure-results/) and returns the list of
written file paths.

Allure result format reference:
  https://allurereport.org/docs/how-it-works-result-file-format/
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List


# Status mapping: CHERENKOV passed/failed → Allure status strings
_STATUS_MAP = {True: "passed", False: "failed"}


def emit_allure(
    results: Dict[str, Any],
    output_dir: str = "allure-results",
    spec_path: str | None = None,
) -> List[str]:
    """
    Writes one Allure 2 JSON result file per test scenario.

    Args:
        results:    The dict returned by ValidationEngine (contains "reports" list).
        output_dir: Directory to write allure-results/*.json files into.
        spec_path:  Optional path to the OpenAPI spec file (used as a label).

    Returns:
        List of absolute paths to the written result files.
    """
    reports: List[Dict[str, Any]] = results.get("reports", [])
    run_id: str = results.get("run_id", str(uuid.uuid4()))
    os.makedirs(output_dir, exist_ok=True)

    written: List[str] = []
    now_ms = int(time.time() * 1000)

    for r in reports:
        scenario_id: str = r.get("scenario_id") or str(uuid.uuid4())
        method: str = (r.get("method") or "UNKNOWN").upper()
        endpoint: str = r.get("endpoint") or "unknown"
        passed: bool = r.get("passed", False)
        error: str = r.get("error") or ""

        status = _STATUS_MAP[passed]

        # Build labels
        labels: List[Dict[str, str]] = [
            {"name": "suite", "value": f"{method} {endpoint}"},
            {"name": "tag", "value": "api-conformance"},
            {"name": "tag", "value": "cherenkov"},
        ]
        if spec_path:
            labels.append({"name": "feature", "value": os.path.basename(spec_path)})

        # Build step list (single step representing the validation)
        steps: List[Dict[str, Any]] = [
            {
                "name": f"Validate {method} {endpoint}",
                "status": status,
                "start": now_ms,
                "stop": now_ms + 1,
                "parameters": [],
                "attachments": [],
            }
        ]

        # Status details (only populated for failures)
        status_details: Dict[str, Any] = {}
        if not passed and error:
            status_details = {
                "message": error,
                "trace": error,
                "flaky": False,
                "muted": False,
                "known": False,
            }

        allure_result: Dict[str, Any] = {
            "uuid": str(uuid.uuid4()),
            "historyId": f"{run_id}::{scenario_id}",
            "testCaseId": scenario_id,
            "fullName": f"{method} {endpoint} :: {scenario_id}",
            "name": scenario_id,
            "status": status,
            "statusDetails": status_details,
            "stage": "finished",
            "description": (
                f"CHERENKOV conformance check for `{method} {endpoint}`.\n\n"
                f"Run ID: `{run_id}`"
            ),
            "labels": labels,
            "parameters": [],
            "steps": steps,
            "attachments": [],
            "start": now_ms,
            "stop": now_ms + 1,
        }

        file_name = f"{allure_result['uuid']}-result.json"
        file_path = os.path.join(output_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as fh:
            json.dump(allure_result, fh, indent=2)
        written.append(os.path.abspath(file_path))

    return written
