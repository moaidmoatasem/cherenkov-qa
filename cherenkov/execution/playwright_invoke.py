"""
CHERENKOV execution/playwright_invoke.py — native Playwright test execution runner.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import json
import os
import subprocess
from cherenkov.core.errors import get_logger

class PlaywrightRunner:
    """Invokes pure Playwright test command line in the stub workspace and parses native JSON results."""

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("PLAYWRIGHT", run_id)
        # Root is cherenkov-qa, stub is inside it
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")

    def execute_test(self, scenario_id: str, test_code: str, api_url: str, update_snapshots: bool = False) -> dict:
        """Writes the generated TypeScript test code, executes Playwright natively, and parses the JSON results."""
        os.makedirs(self.tests_dir, exist_ok=True)
        test_file_path = os.path.join(self.tests_dir, f"{scenario_id}.spec.ts")
        
        # 1. Write pure Playwright TS test code
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(test_code)
            
        self.log.info("wrote generated test file", path=test_file_path)

        # 2. Run npx playwright test (pure runner) with json reporter and trace enabled on failure
        # We override baseURL via API_URL env variable which playwright config picks up
        env = os.environ.copy()
        env["API_URL"] = api_url

        cmd = [
            "npx", "playwright", "test",
            f"generated_tests/{scenario_id}.spec.ts",
            "--reporter=json"
        ]
        
        # If the execution fails, Playwright will automatically save trace if we run with --trace on
        # But we only want trace on failure -> config has "on-first-retry". However, we can enforce --trace on
        # to ensure we capture trace.zip on any failure for analysis (pure Playwright D3).
        cmd.append("--trace=on")
        if update_snapshots:
            cmd.append("--update-snapshots")

        self.log.info("invoking playwright runner", command=" ".join(cmd), api_url=api_url)
        
        process = subprocess.run(
            cmd,
            cwd=self.stub_dir,
            env=env,
            capture_output=True,
            text=True
        )
        
        stdout = process.stdout.strip()
        stderr = process.stderr.strip()
        exit_code = process.returncode

        # 3. Parse JSON output of the reporter
        passed = (exit_code == 0)
        failure_msg = ""
        trace_path = ""

        try:
            # Playwright might print warnings/logs before the JSON payload
            # We locate the start of the JSON object
            json_start = stdout.find("{")
            if json_start != -1:
                results = json.loads(stdout[json_start:])
                suites = results.get("suites", [])
                for suite in suites:
                    for spec in suite.get("specs", []):
                        for test in spec.get("tests", []):
                            for result in test.get("results", []):
                                # --trace=on saves traces for ALL tests (pass & fail).
                                # Always collect the trace path so TighteningAnalyzer
                                # can run on passing tests to suggest stronger assertions.
                                attachments = result.get("attachments", [])
                                for att in attachments:
                                    if att.get("name") == "trace":
                                        trace_path = att.get("path", "")
                                if result.get("status") != "expected":
                                    # Collect error details for failing tests
                                    errors = result.get("errors", [])
                                    if errors:
                                        failure_msg += "\n".join([err.get("message", "") for err in errors])
            else:
                if not passed:
                    failure_msg = stderr or stdout or "Unknown execution failure."
        except Exception as e:
            self.log.warning("could not parse playwright json output", error=str(e))
            if not passed:
                failure_msg = stderr or stdout or str(e)

        self.log.info(
            "playwright execution finished",
            passed=passed,
            exit_code=exit_code,
            trace_path=trace_path
        )
        
        return {
            "passed": passed,
            "exit_code": exit_code,
            "failure_message": failure_msg,
            "trace_path": trace_path,
            "test_file": test_file_path
        }
