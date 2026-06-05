"""
CHERENKOV execution/validate.py — validation and value assertion tightening report engine.
Authority: v3.1 + delta. Track A surface only.
"""
from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List

from cherenkov.core.errors import get_logger
from cherenkov.execution.playwright_invoke import PlaywrightRunner
from cherenkov.execution.trace_reader import TraceReader


class TighteningAnalyzer:
    """Compares sent request bodies vs received response bodies to suggest stronger value assertions."""

    @staticmethod
    def analyze(request_body_raw: str, response_body_raw: str) -> List[str]:
        suggestions = []
        if not request_body_raw or not response_body_raw:
            return suggestions

        try:
            req_json = json.loads(request_body_raw)
            resp_json = json.loads(response_body_raw)
        except Exception:
            return suggestions

        if not isinstance(req_json, dict) or not isinstance(resp_json, dict):
            return suggestions

        for rk, rv in req_json.items():
            for pk, pv in resp_json.items():
                if rv == pv and rv is not None:
                    suggestions.append(
                        f"expect(data.{pk}).toBe('{pv}')" if isinstance(pv, str) else f"expect(data.{pk}).toBe({pv})"
                    )
                    if rk == pk:
                        suggestions.append(f"expect(data.{pk}).toBe(body.{rk})")
        return suggestions


class ValidationEngine:
    """Runs the Playwright test suite against a real server and produces value tightening reports."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "validate"
        self.log = get_logger("VALIDATE", self.run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")

    def validate_suite(self, target_url: str) -> Dict[str, Any]:
        """Runs all spec tests in generated_tests against target_url and parses trace files for tightening suggestions."""
        self.log.info("starting suite validation", target_url=target_url)

        if not os.path.exists(self.tests_dir):
            self.log.warning("no generated tests directory found")
            return {"status": "empty", "message": "No generated tests found.", "reports": []}

        test_files = [f for f in os.listdir(self.tests_dir) if f.endswith(".spec.ts")]
        if not test_files:
            return {"status": "empty", "message": "No spec files found.", "reports": []}

        reports = []
        runner = PlaywrightRunner(run_id=self.run_id)
        reader = TraceReader(run_id=self.run_id)

        for t_file in test_files:
            scenario_id = t_file.replace(".spec.ts", "")
            test_path = os.path.join(self.tests_dir, t_file)

            with open(test_path, "r", encoding="utf-8") as f:
                code = f.read()

            self.log.info("validating scenario", scenario_id=scenario_id)

            result = runner.execute_test(
                scenario_id=scenario_id,
                api_url=target_url,
                test_code=None
            )

            trace_path = result.get("trace_path", "")
            passed = result.get("passed", False)
            suggestions = []
            req_body_str = ""
            resp_body_str = ""

            if passed and trace_path:
                method_match = re.search(r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code)
                if method_match:
                    target_method = method_match.group(1)
                    target_url_path = method_match.group(2)

                    response_info = reader.extract_http_response(trace_path, target_url_path, target_method)
                    if response_info:
                        req_body_str = response_info.get("request_body_raw", "")
                        resp_body_str = response_info.get("body_raw", "")
                        suggestions = TighteningAnalyzer.analyze(req_body_str, resp_body_str)

            reports.append({
                "scenario_id": scenario_id,
                "passed": passed,
                "request_body": req_body_str,
                "response_body": resp_body_str,
                "suggestions": suggestions,
                "error": result.get("failure_message", "") if not passed else "",
            })

        return {
            "status": "success",
            "target_url": target_url,
            "reports": reports,
        }
