"""
CHERENKOV execution/validate.py — validation and value assertion tightening report engine.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import re
import json
import subprocess
from typing import Any, Dict, List

from cherenkov.core.errors import get_logger
from cherenkov.execution.playwright_invoke import PlaywrightRunner
from cherenkov.execution.trace_reader import TraceReader
from cherenkov.stages.diagnostics_stage import DiagnosticsStage
from cherenkov.validate.jira_exporter import JiraExporter

class TighteningAnalyzer:
    """Compares sent request bodies vs received response bodies to suggest stronger value assertions."""

    @staticmethod
    def analyze(request_body_raw: str, response_body_raw: str) -> List[str]:
        """Compares values in request vs response and returns suggested assertion strings."""
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

        # Find matching values between sent request body and returned response body
        for rk, rv in req_json.items():
            for pk, pv in resp_json.items():
                if rv == pv and rv is not None:
                    # Suggest asserting value matches
                    suggestions.append(
                        f"expect(data.{pk}).toBe('{pv}')" if isinstance(pv, str) else f"expect(data.{pk}).toBe({pv})"
                    )
                    # Suggest asserting value equals what was sent in the request body
                    if rk == pk:
                        suggestions.append(
                            f"expect(data.{pk}).toBe(body.{rk})"
                        )
        return suggestions


class ValidationEngine:
    """Runs the Playwright test suite against a real server and produces value tightening reports."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "validate"
        self.log = get_logger("VALIDATE", self.run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")

    def validate_suite(self, target_url: str, run_visual: bool = False, run_perf: bool = False) -> Dict[str, Any]:
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
            
            # Execute Playwright against the real server target URL
            result = runner.execute_test(
                scenario_id=scenario_id,
                test_code=code,
                api_url=target_url
            )

            # Locate trace
            trace_path = result.get("trace_path", "")
            passed = result.get("passed", False)
            suggestions = []
            req_body_str = ""
            resp_body_str = ""

            if passed and trace_path:
                # Find HTTP method and path to search the trace
                method_match = re.search(r"client\.(GET|POST|PUT|DELETE|PATCH)\('([^']+)'", code)
                if method_match:
                    target_method = method_match.group(1)
                    target_url_path = method_match.group(2)
                    
                    # Parse trace network details
                    response_info = reader.extract_http_response(trace_path, target_url_path, target_method)
                    if response_info:
                        req_body_str = response_info.get("request_body_raw", "")
                        resp_body_str = response_info.get("body_raw", "")
                        
                        # Generate tightening suggestions
                        suggestions = TighteningAnalyzer.analyze(req_body_str, resp_body_str)

            ticket_path = ""
            if not passed:
                failure_message = result.get("failure_message", "")
                
                # Guess failure class
                failure_class = "CONTRACT_DRIFT"
                if "401" in failure_message or "Unauthorized" in failure_message:
                    failure_class = "AUTH_EXPIRY"
                elif "404" in failure_message or "Not Found" in failure_message:
                    failure_class = "STATE_SEQUENCE"

                # Parse expected status from code or message
                expected_status = None
                received_status = None
                expected_match = re.search(r"expect\(response\.status\)\.toBe\((\d+)\)", code)
                if expected_match:
                    expected_status = int(expected_match.group(1))
                else:
                    expected_match = re.search(r"Expected: (\d+)", failure_message)
                    if expected_match:
                        expected_status = int(expected_match.group(1))

                received_match = re.search(r"Received: (\d+)", failure_message)
                if received_match:
                    received_status = int(received_match.group(1))

                # 1. Run local AI Diagnostics synthesis
                self.log.info("running local AI diagnostics for failed scenario", scenario_id=scenario_id)
                diag_stage = DiagnosticsStage(self.run_id)
                try:
                    diag_output = diag_stage.run(
                        scenario_id=scenario_id,
                        failure_class=failure_class,
                        error_message=failure_message
                    )
                    hypothesis = diag_output.hypothesis
                    res_steps = diag_output.resolution_steps
                    similar_cases = diag_output.similar_cases_found
                except Exception as e:
                    self.log.warning("failed to run AI diagnostics", error=str(e))
                    hypothesis = f"Failed scenario: suspected {failure_class}."
                    res_steps = ["Review test execution logs."]
                    similar_cases = 0

                # 2. Get compliance score from report if exists
                compliance_score = None
                report_path = os.path.abspath(os.path.join(self.stub_dir, "../.cherenkov/mena_compliance_report.json"))
                if os.path.exists(report_path):
                    try:
                        with open(report_path, "r", encoding="utf-8") as rf:
                            rep = json.load(rf)
                            compliance_score = rep.get("overall_compliance_score")
                    except Exception:
                        pass

                # 3. Export suggest-only Jira ticket
                exporter = JiraExporter(self.run_id)
                try:
                    ticket_path = exporter.export_ticket(
                        scenario_id=scenario_id,
                        failure_class=failure_class,
                        error_message=failure_message,
                        expected_status=expected_status,
                        received_status=received_status,
                        hypothesis=hypothesis,
                        resolution_steps=res_steps,
                        similar_cases_count=similar_cases,
                        compliance_score=compliance_score
                    )
                    self.log.info("exported Jira ticket for scenario failure", scenario_id=scenario_id, path=ticket_path)
                except Exception as e:
                    self.log.error("failed to export Jira ticket", error=str(e))

            reports.append({
                "scenario_id": scenario_id,
                "passed": passed,
                "request_body": req_body_str,
                "response_body": resp_body_str,
                "suggestions": suggestions,
                "error": result.get("failure_message", "") if not passed else "",
                "jira_ticket_path": ticket_path
            })

        visual_report = None
        if run_visual:
            self.log.info("triggering optional visual validation checks")
            from cherenkov.execution.visual_diff import VisualDiffEngine
            v_engine = VisualDiffEngine(self.run_id)
            try:
                visual_report = v_engine.run_visual_validation(target_url)
            except Exception as e:
                self.log.error("visual validation check crashed", error=str(e))
                visual_report = {"passed": False, "message": f"Visual validation check encountered error: {e}"}

        perf_report = None
        if run_perf:
            self.log.info("triggering optional performance validation checks")
            from cherenkov.execution.k6_runner import K6Runner
            p_runner = K6Runner(self.run_id)
            try:
                perf_report = p_runner.run_k6_validation(target_url)
            except Exception as e:
                self.log.error("performance validation check crashed", error=str(e))
                perf_report = {"status": "failed", "message": f"Performance validation check encountered error: {e}"}

        return {
            "status": "success",
            "target_url": target_url,
            "reports": reports,
            "visual_report": visual_report,
            "perf_report": perf_report
        }

