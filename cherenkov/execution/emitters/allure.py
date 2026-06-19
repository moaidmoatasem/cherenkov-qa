import time
import uuid
from typing import Any, Dict, List

class AllureEmitter:
    """Emits DivergenceReports into Allure-compatible JSON result files."""

    def emit(self, report, spec_path: str) -> List[Dict[str, Any]]:
        """Convert findings into Allure JSON format test cases."""
        results = []
        findings = getattr(report, "findings", [])

        # Add successful tests if available
        tests_passed = getattr(report, "_total_tests", len(findings))
        success_count = max(0, tests_passed - len(findings))

        start_time = int(time.time() * 1000)
        stop_time = start_time + 100

        for i in range(success_count):
            test_id = str(uuid.uuid4())
            results.append({
                "uuid": test_id,
                "historyId": test_id,
                "name": f"successful_conformance_check_{i}",
                "fullName": f"cherenkov.conformance.successful_conformance_check_{i}",
                "status": "passed",
                "stage": "finished",
                "start": start_time,
                "stop": stop_time,
                "labels": [
                    {"name": "framework", "value": "cherenkov"},
                    {"name": "language", "value": "python"}
                ]
            })

        for finding in findings:
            test_id = str(uuid.uuid4())
            results.append({
                "uuid": test_id,
                "historyId": test_id,
                "name": getattr(finding, "endpoint", "unknown_endpoint"),
                "fullName": f"cherenkov.conformance.{getattr(finding, 'endpoint', 'unknown')}",
                "status": "failed",
                "statusDetails": {
                    "message": getattr(finding, "summary", "Drift detected"),
                    "trace": getattr(finding, "description", "")
                },
                "stage": "finished",
                "start": start_time,
                "stop": stop_time,
                "labels": [
                    {"name": "framework", "value": "cherenkov"},
                    {"name": "severity", "value": getattr(finding, "severity", "normal")},
                    {"name": "language", "value": "python"}
                ]
            })

        return results
