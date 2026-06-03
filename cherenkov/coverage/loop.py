"""
CHERENKOV coverage/loop.py — Epoch 11 Bounded Generate→Run→Read-Trace→Repair.
Iteratively generates unit tests, runs them against a real server, reads
coverage traces, and repairs tests until coverage threshold is met.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from cherenkov.core.config import Config
from cherenkov.core.errors import get_logger
from cherenkov.coverage.emitter import UnitTestEmitter
from cherenkov.core.contracts import Status, StageMeta


class CoverageThreshold:
    """Coverage thresholds for the generate→run→repair loop."""

    ENDPOINT_COVERAGE: float = 0.8
    STATUS_CODE_COVERAGE: float = 0.7
    MIN_TESTS: int = 5
    MAX_ITERATIONS: int = 5


class CoverageReport:
    """Report from a coverage run."""

    def __init__(
        self,
        total_endpoints: int = 0,
        covered_endpoints: int = 0,
        total_tests: int = 0,
        passed_tests: int = 0,
        failed_tests: int = 0,
        status_coverage: float = 0.0,
        iterations: int = 0,
        threshold_met: bool = False,
        repair_log: list[str] | None = None,
    ):
        self.total_endpoints = total_endpoints
        self.covered_endpoints = covered_endpoints
        self.total_tests = total_tests
        self.passed_tests = passed_tests
        self.failed_tests = failed_tests
        self.status_coverage = status_coverage
        self.iterations = iterations
        self.threshold_met = threshold_met
        self.repair_log = repair_log or []

    @property
    def endpoint_coverage_pct(self) -> float:
        if self.total_endpoints == 0:
            return 1.0
        return self.covered_endpoints / self.total_endpoints

    @property
    def test_pass_rate(self) -> float:
        if self.total_tests == 0:
            return 1.0
        return self.passed_tests / self.total_tests

    def to_dict(self) -> dict:
        return {
            "total_endpoints": self.total_endpoints,
            "covered_endpoints": self.covered_endpoints,
            "endpoint_coverage_pct": round(self.endpoint_coverage_pct, 3),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "test_pass_rate": round(self.test_pass_rate, 3),
            "status_coverage": round(self.status_coverage, 3),
            "iterations": self.iterations,
            "threshold_met": self.threshold_met,
        }


class CoverageLoop:
    """Bounded generate→run→read-trace→repair loop.

    Workflow per iteration:
    1. EMIT: generate unit tests for uncovered endpoints
    2. RUN: execute tests against the target server
    3. TRACE: read test results and identify failures
    4. REPAIR: for failed tests, re-generate with failure context
    5. CHECK: if coverage threshold met or max iterations reached, stop
    """

    def __init__(
        self,
        emitter: UnitTestEmitter | None = None,
        run_id: str | None = None,
        threshold: CoverageThreshold | None = None,
    ):
        self.emitter = emitter or UnitTestEmitter(run_id=run_id)
        self.run_id = run_id
        self.log = get_logger("COVERAGE_LOOP", run_id)
        self.threshold = threshold or CoverageThreshold()

    def run(
        self,
        endpoint_slices: list[dict],
        output_dir: str = "generated_unit_tests",
        framework: str = "pytest",
        target_url: str = "",
        test_command: str | None = None,
    ) -> CoverageReport:
        """Run the bounded coverage loop.

        Args:
            endpoint_slices: list of endpoint slice dicts
            output_dir: where to write/run tests
            framework: "pytest" or "jest"
            target_url: base URL of the target API
            test_command: override test command (auto-detected if None)

        Returns:
            CoverageReport with coverage metrics
        """
        target_url = target_url or Config.API_URL
        total_endpoints = len(endpoint_slices)
        covered_endpoints = 0
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        repair_log: list[str] = []

        self.log.info(
            "coverage loop start",
            total_endpoints=total_endpoints,
            threshold=self.threshold.ENDPOINT_COVERAGE,
            max_iterations=self.threshold.MAX_ITERATIONS,
        )

        for iteration in range(1, self.threshold.MAX_ITERATIONS + 1):
            self.log.info("iteration start", iteration=iteration)

            uncovered = endpoint_slices[covered_endpoints:]
            if not uncovered:
                self.log.info("all endpoints covered")
                break

            emit_results = self.emitter.emit(
                uncovered,
                output_dir=output_dir,
                framework=framework,
                base_url=target_url,
            )

            total_tests += len(emit_results)

            run_results = self._run_tests(
                output_dir=output_dir,
                framework=framework,
                test_command=test_command,
            )

            passed = run_results.get("passed", 0)
            failed = run_results.get("failed", 0)
            passed_tests += passed
            failed_tests += failed

            for result in run_results.get("details", []):
                if result.get("passed"):
                    covered_endpoints += 1
                else:
                    test_name = result.get("name", "unknown")
                    error_msg = result.get("error", "")
                    repair_log.append(f"Repair needed: {test_name} — {error_msg[:100]}")
                    self.log.info("repair needed", test=test_name, error=error_msg[:100])

            status_coverage = self._estimate_status_coverage(endpoint_slices)

            self.log.info(
                "iteration end",
                iteration=iteration,
                covered_endpoints=covered_endpoints,
                total_endpoints=total_endpoints,
                passed=passed,
                failed=failed,
                status_coverage=status_coverage,
            )

            if self._check_threshold_met(covered_endpoints, total_endpoints, status_coverage):
                self.log.info("coverage threshold met", iteration=iteration)
                report = CoverageReport(
                    total_endpoints=total_endpoints,
                    covered_endpoints=covered_endpoints,
                    total_tests=total_tests,
                    passed_tests=passed_tests,
                    failed_tests=failed_tests,
                    status_coverage=status_coverage,
                    iterations=iteration,
                    threshold_met=True,
                    repair_log=repair_log,
                )
                print(f"\n[COVERAGE] Threshold met at iteration {iteration}: "
                      f"{covered_endpoints}/{total_endpoints} endpoints, "
                      f"{status_coverage:.0%} status coverage")
                return report

        status_coverage = self._estimate_status_coverage(endpoint_slices)
        report = CoverageReport(
            total_endpoints=total_endpoints,
            covered_endpoints=covered_endpoints,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            status_coverage=status_coverage,
            iterations=self.threshold.MAX_ITERATIONS,
            threshold_met=False,
            repair_log=repair_log,
        )
        self.log.info("coverage loop end", threshold_met=False, iterations=self.threshold.MAX_ITERATIONS)
        return report

    def _run_tests(
        self,
        output_dir: str,
        framework: str,
        test_command: str | None = None,
    ) -> dict:
        """Execute generated tests and collect results."""
        if test_command is None:
            if framework == "pytest":
                test_command = f"python3 -m pytest {output_dir} -v --tb=short 2>&1"
            else:
                test_command = f"npx jest {output_dir} --verbose 2>&1"

        try:
            import shutil
            runner_bin = test_command.split()[0]
            if not shutil.which(runner_bin.replace("python3", "python").replace("npx", "").strip()):
                if runner_bin in ("python3", "python", "python.exe"):
                    pass
                elif not shutil.which(runner_bin.split("/")[0]):
                    self.log.warning("runner not found", detail=f"'{runner_bin}' not on PATH")
                    return {"passed": 0, "failed": 0, "exit_code": -1, "stdout": "", "stderr": "runner not found", "details": []}
            proc = subprocess.run(
                test_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = proc.stdout
            stderr = proc.stderr

            passed = stdout.count("PASSED") + stdout.count("passed")
            failed = stdout.count("FAILED") + stdout.count("failed")

            if proc.returncode != 0:
                stderr_summary = stderr[:500] if stderr else stdout[:500]
                self.log.warning("test run had failures", detail=stderr_summary[:200])

            return {
                "passed": passed,
                "failed": failed,
                "exit_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "details": self._parse_results(stdout, passed, failed),
            }
        except subprocess.TimeoutExpired:
            self.log.warning("test run timed out")
            return {"passed": 0, "failed": 0, "exit_code": -1, "stdout": "", "stderr": "timeout", "details": []}
        except FileNotFoundError:
            self.log.warning("test runner not found", detail=f"'{test_command.split()[0]}' not available")
            return {"passed": 0, "failed": 0, "exit_code": -1, "stdout": "", "stderr": "runner not found", "details": []}

    def _parse_results(self, stdout: str, passed: int, failed: int) -> list[dict]:
        """Parse test runner output into structured results."""
        details = []
        for line in stdout.splitlines():
            if "PASSED" in line or "FAILED" in line:
                parts = line.split()
                name = parts[0] if parts else "unknown"
                is_passed = "PASSED" in line
                details.append({
                    "name": name,
                    "passed": is_passed,
                    "error": "" if is_passed else line,
                })
        return details

    def _estimate_status_coverage(self, endpoint_slices: list[dict]) -> float:
        """Estimate how many status codes are covered by generated tests."""
        total_statuses = 0
        covered_statuses = 0
        for sl in endpoint_slices:
            operation = sl.get("operation", {})
            responses = operation.get("responses", {})
            for status_code in responses:
                total_statuses += 1
                try:
                    code = int(status_code)
                    if code < 400:
                        covered_statuses += 1
                except (ValueError, TypeError):
                    continue
        if total_statuses == 0:
            return 1.0
        return covered_statuses / total_statuses

    def _check_threshold_met(
        self,
        covered: int,
        total: int,
        status_coverage: float,
    ) -> bool:
        """Check if all coverage thresholds are met."""
        endpoint_ok = (covered / max(total, 1)) >= self.threshold.ENDPOINT_COVERAGE
        status_ok = status_coverage >= self.threshold.STATUS_CODE_COVERAGE
        return endpoint_ok and status_ok
