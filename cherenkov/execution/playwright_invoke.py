"""
CHERENKOV execution/playwright_invoke.py — native Playwright test execution runner.
"""

from __future__ import annotations

import json
import os
import shlex
import sys
import subprocess
from cherenkov.core.errors import get_logger
from cherenkov.core.compat import npx as _npx


_WSL_PREFIX = "\\\\wsl.localhost\\"


def _wsl_path(windows_path: str) -> str:
    """Convert a \\\\wsl.localhost\\<distro>\\ path to a WSL Linux path."""
    if not windows_path.startswith(_WSL_PREFIX):
        return windows_path
    # \\wsl.localhost\Ubuntu-24.04\home\moaid\... -> /home/moaid/...
    parts = windows_path.split("\\")
    # parts[0]='' (UNC), parts[1]='' (empty), parts[2]='wsl.localhost', parts[3]='Ubuntu-24.04', ...
    distro = parts[3]
    linux_parts = parts[4:]  # home, moaid, ...
    return "/" + "/".join(linux_parts).replace("\\", "/")


def _is_unc_path(path: str) -> bool:
    return path.startswith("\\\\") or path.startswith("//")


class PlaywrightRunner:
    """Invokes pure Playwright test command line in the stub workspace and parses native JSON results."""

    def __init__(self, run_id: str | None = None):
        self.log = get_logger("PLAYWRIGHT", run_id)
        # Root is cherenkov-qa, stub is inside it
        self.stub_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../stub")
        )
        self.tests_dir = os.path.join(self.stub_dir, "generated_tests")
        # Detect Windows UNC path — cmd.exe cannot use UNC as cwd
        self._use_wsl = sys.platform == "win32" and _is_unc_path(self.stub_dir)

    def execute_test(
        self,
        scenario_id: str,
        api_url: str,
        test_code: str | None = None,
        update_snapshots: bool = False,
    ) -> dict:
        """Writes the generated TypeScript test code, executes Playwright natively, and parses the JSON results."""
        os.makedirs(self.tests_dir, exist_ok=True)
        test_file_path = os.path.join(self.tests_dir, f"{scenario_id}.spec.ts")

        # 1. Write pure Playwright TS test code if provided
        if test_code is not None:
            with open(test_file_path, "w", encoding="utf-8") as f:
                f.write(test_code)
            self.log.info("wrote generated test file", path=test_file_path)

        # 2. Run npx playwright test (pure runner) with json reporter and trace enabled on failure
        # We override baseURL via API_URL env variable which playwright config picks up

        if self._use_wsl:
            exit_code, failure_msg, trace_path = self._exec_via_wsl(
                scenario_id, api_url, update_snapshots
            )
        else:
            exit_code, failure_msg, trace_path = self._exec_native(
                scenario_id, api_url, update_snapshots
            )

        self.log.info(
            "playwright execution finished",
            passed=(exit_code == 0),
            exit_code=exit_code,
            trace_path=trace_path,
        )

        return {
            "passed": (exit_code == 0),
            "exit_code": exit_code,
            "failure_message": failure_msg,
            "trace_path": trace_path,
            "test_file": test_file_path,
        }

    def _exec_native(
        self, scenario_id: str, api_url: str, update_snapshots: bool
    ) -> tuple:
        env = os.environ.copy()
        env["API_URL"] = api_url
        playwright_out = os.environ.get("PLAYWRIGHT_OUTPUT_DIR") or os.path.join(
            os.environ.get("TEMP", "/tmp"), "pw_test_results"
        )
        env["PLAYWRIGHT_OUTPUT_DIR"] = playwright_out

        cmd = [
            _npx(),
            "playwright",
            "test",
            f"generated_tests/{scenario_id}.spec.ts",
            "--reporter=json",
        ]
        cmd.append("--trace=on")
        if update_snapshots:
            cmd.append("--update-snapshots")

        self.log.info(
            "invoking playwright runner (native)",
            command=" ".join(cmd),
            api_url=api_url,
        )

        process = subprocess.run(
            cmd, cwd=self.stub_dir, env=env, capture_output=True, text=True
        )
        return self._parse_result(process.stdout, process.stderr, process.returncode)

    def _exec_via_wsl(
        self, scenario_id: str, api_url: str, update_snapshots: bool
    ) -> tuple:
        linux_stub = _wsl_path(self.stub_dir)
        test_rel = f"generated_tests/{scenario_id}.spec.ts"
        cmd_parts = [
            "npx",
            "playwright",
            "test",
            test_rel,
            "--reporter=json",
            "--trace=on",
        ]
        if update_snapshots:
            cmd_parts.append("--update-snapshots")

        # API_URL must be exported inside the WSL bash session
        shell_cmd = (
            f"export API_URL={shlex.quote(api_url)}; "
            f"cd {shlex.quote(linux_stub)} && " + " ".join(cmd_parts)
        )
        wsl_cmd = ["wsl.exe", "-e", "bash", "-c", shell_cmd]

        self.log.info(
            "invoking playwright runner (wsl)",
            command=" ".join(wsl_cmd),
            api_url=api_url,
        )

        process = subprocess.run(wsl_cmd, capture_output=True, text=True)
        return self._parse_result(process.stdout, process.stderr, process.returncode)

    @staticmethod
    def _parse_result(stdout: str, stderr: str, exit_code: int) -> tuple:
        stdout = stdout.strip()
        stderr = stderr.strip()
        failure_msg = ""
        trace_path = ""

        try:
            json_start = stdout.find("{")
            if json_start != -1:
                results = json.loads(stdout[json_start:])
                suites = results.get("suites", [])
                for suite in suites:
                    for spec in suite.get("specs", []):
                        for test in spec.get("tests", []):
                            for result in test.get("results", []):
                                attachments = result.get("attachments", [])
                                for att in attachments:
                                    if att.get("name") == "trace":
                                        trace_path = att.get("path", "")
                                if result.get("status") != "expected":
                                    errors = result.get("errors", [])
                                    if errors:
                                        failure_msg += "\n".join(
                                            [err.get("message", "") for err in errors]
                                        )
            else:
                if exit_code != 0:
                    failure_msg = stderr or stdout or "Unknown execution failure."
        except Exception as e:
            if exit_code != 0:
                failure_msg = stderr or stdout or str(e)

        return exit_code, failure_msg, trace_path
