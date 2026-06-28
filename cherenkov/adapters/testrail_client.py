import os
import json
import base64
import urllib.request
from typing import Any, Dict

CHERENKOV_TO_TESTRAIL = {
    "PASS": 1,   # Passed
    "FAIL": 5,   # Failed
    "DRIFT": 5,  # Failed
    "SKIP": 4,   # Retest
    "ERROR": 2   # Blocked
}

class TestRailClient:
    """Import test execution results into TestRail."""

    def __init__(self):
        self.base_url = os.environ.get("CHERENKOV_TESTRAIL_URL", "").rstrip("/")
        self.user = os.environ.get("CHERENKOV_TESTRAIL_USER", "")
        self.token = os.environ.get("CHERENKOV_TESTRAIL_TOKEN", "")

    def _headers(self) -> Dict[str, str]:
        auth_str = f"{self.user}:{self.token}"
        auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        return {
            "Authorization": f"Basic {auth_bytes}",
            "Content-Type": "application/json",
        }

    def import_execution(self, report: Dict[str, Any], run_id: str) -> Dict[str, Any]:
        """Convert a CHERENKOV report dict and POST results to TestRail."""
        if not self.base_url or not self.token:
            return {"error": "TestRail configuration missing"}

        results = []
        for item in report.get("items", report.get("divergences", [])):
            verdict = str(item.get("verdict", item.get("status", "SKIP"))).upper()
            status_id = CHERENKOV_TO_TESTRAIL.get(verdict, 4)
            test_case_id = item.get("test_case_id") or item.get("test_key")

            # Extract numbers only (e.g. C1234 -> 1234)
            if test_case_id and isinstance(test_case_id, str):
                test_case_id = test_case_id.lstrip("C")

            if not test_case_id:
                continue

            endpoint = item.get("endpoint", item.get("path", ""))
            method = item.get("method", "GET")
            summary = item.get("summary", item.get("message", ""))

            results.append({
                "case_id": test_case_id,
                "status_id": status_id,
                "comment": f"{method} {endpoint} — {summary}",
                "elapsed": f"{max(1, item.get('duration_ms', 1000) // 1000)}s"
            })

        if not results:
            return {"status": "no_results_with_case_ids"}

        url = f"{self.base_url}/index.php?/api/v2/add_results_for_cases/{run_id}"
        req = urllib.request.Request(
            url,
            data=json.dumps({"results": results}).encode("utf-8"),
            headers=self._headers(),
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def import_junit_xml(self, junit_xml_path: str, project_id: str) -> Dict[str, Any]:
        """Not natively supported by TestRail REST API without a middleware script, stubbed."""
        return {"status": "unsupported_by_native_api_use_cli"}
