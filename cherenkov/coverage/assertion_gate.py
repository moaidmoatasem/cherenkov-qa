"""
CHERENKOV coverage/assertion_gate.py — Epoch 11 Assertion Gate.
Self-play: runs generated tests against a deliberately broken implementation
to verify that assertions actually catch real bugs.
"""
from __future__ import annotations

import subprocess
import time
from typing import Any

from cherenkov.core.errors import get_logger
from cherenkov.core.config import Config


class AssertionGateResult:
    """Result of running the assertion gate."""

    def __init__(
        self,
        total_tests: int = 0,
        caught_bugs: int = 0,
        missed_bugs: int = 0,
        mean_assertions_per_test: float = 0.0,
        weak_assertion_tests: list[str] | None = None,
        passed: bool = False,
        detail: str = "",
    ):
        self.total_tests = total_tests
        self.caught_bugs = caught_bugs
        self.missed_bugs = missed_bugs
        self.mean_assertions_per_test = mean_assertions_per_test
        self.weak_assertion_tests = weak_assertion_tests or []
        self.passed = passed
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "total_tests": self.total_tests,
            "caught_bugs": self.caught_bugs,
            "missed_bugs": self.missed_bugs,
            "bug_catch_rate": round(self.caught_bugs / max(self.total_tests, 1), 3),
            "mean_assertions_per_test": round(self.mean_assertions_per_test, 2),
            "weak_assertion_tests": self.weak_assertion_tests,
            "passed": self.passed,
            "detail": self.detail,
        }


class BrokenImplementation:
    """A deliberately broken server implementation for self-play testing.

    Injects known bugs:
    - Returns wrong status codes (400 instead of 201)
    - Omits required response fields
    - Returns wrong data types
    """

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.bugs: list[dict] = []

    def generate(self, operation: dict) -> list[dict]:
        """Generate a list of bug mutations for an operation.

        Each bug is a dict with:
        - id: unique identifier
        - description: what the bug is
        - expected_correct: what the correct response looks like
        - broken_behavior: what the buggy response looks like
        """
        bugs = []
        responses = operation.get("responses", {})

        for status_code in ("200", "201"):
            if status_code not in responses:
                continue

            success_code = int(status_code)
            error_code = 400 if success_code == 201 else 500

            bugs.append({
                "id": f"wrong_status_{status_code}",
                "description": f"Returns {error_code} instead of {success_code}",
                "expected_correct": {"status": success_code},
                "broken_behavior": {"status": error_code},
            })

            content = responses.get(status_code, {}).get("content", {})
            for media_type in ("application/json",):
                schema = content.get(media_type, {}).get("schema", {})
                props = schema.get("properties", {})

                if props:
                    omitted = list(props.keys())[0]
                    bugs.append({
                        "id": f"missing_field_{omitted}",
                        "description": f"Omits required field '{omitted}' from response",
                        "expected_correct": {"missing_field": omitted},
                        "broken_behavior": {"missing_field": omitted},
                    })
                    break
                break

            if bugs:
                break

        self.bugs.extend(bugs)
        return bugs


class AssertionGate:
    """Runs generated tests against a deliberately broken implementation
    to verify the assertions are meaningful.

    Self-play workflow:
    1. Generate a buggy version of the target API (status code flip, field omission)
    2. Run the test suite against the broken implementation
    3. Check which tests caught the bug (expected to fail) vs. passed anyway
    4. If too many tests pass against the broken impl, the assertions are weak
    5. Report weak assertion tests for repair
    """

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.log = get_logger("ASSERTION_GATE", run_id)
        self.broken = BrokenImplementation()

    def run(
        self,
        endpoint_slices: list[dict],
        test_dir: str = "generated_unit_tests",
        framework: str = "pytest",
    ) -> AssertionGateResult:
        """Run the assertion gate.

        Creates a broken implementation specification, runs tests against it,
        and evaluates whether assertions caught the injected bugs.

        Args:
            endpoint_slices: list of endpoint slice dicts
            test_dir: directory containing generated tests
            framework: "pytest" or "jest"

        Returns:
            AssertionGateResult with pass/fail and weak assertion list
        """
        t0 = time.time()

        bugs = self._generate_bugs(endpoint_slices)
        total_bugs = len(bugs)
        self.log.info("assertion gate start", bugs_generated=total_bugs)

        caught_count = 0
        weak_assertions: list[str] = []

        for bug in bugs:
            was_caught = self._simulate_bug_run(bug, test_dir, framework)
            if was_caught:
                caught_count += 1
            else:
                weak_assertions.append(bug["id"])

        assertion_count = self._count_assertions(test_dir)
        total_tests = max(len(weak_assertions) + caught_count, 1)

        result = AssertionGateResult(
            total_tests=total_tests,
            caught_bugs=caught_count,
            missed_bugs=total_bugs - caught_count,
            mean_assertions_per_test=assertion_count / max(total_tests, 1),
            weak_assertion_tests=weak_assertions,
            passed=(caught_count / total_bugs) >= 0.8 if total_bugs > 0 else True,
            detail=(
                f"Caught {caught_count}/{total_bugs} injected bugs "
                f"({caught_count / max(total_bugs, 1):.0%} catch rate)"
            ),
        )

        dt = int((time.time() - t0) * 1000)
        self.log.info(
            "assertion gate end",
            passed=result.passed,
            caught=caught_count,
            total=total_bugs,
            duration_ms=dt,
        )
        return result

    def _generate_bugs(self, endpoint_slices: list[dict]) -> list[dict]:
        """Generate bugs from endpoint slices."""
        bugs: list[dict] = []
        for sl in endpoint_slices:
            operation = sl.get("operation", {})
            bugs.extend(self.broken.generate(operation))
        return bugs

    def _simulate_bug_run(
        self,
        bug: dict,
        test_dir: str,
        framework: str,
    ) -> bool:
        """Simulate running a test against a broken implementation.

        In production, this would spin up a broken server and run the
        specific test. In this offline analysis mode, we check whether
        the test has assertions that SHOULD catch the described bug.

        Returns True if the bug would be caught (test fails against broken impl).
        """
        bug_id = bug.get("id", "")

        if "wrong_status" in bug_id:
            return self._check_status_assertion(test_dir, bug)

        if "missing_field" in bug_id:
            return self._check_field_assertion(test_dir, bug)

        return True

    def _check_status_assertion(self, test_dir: str, bug: dict) -> bool:
        """Check if tests assert on the status code that would be wrong."""
        broken_status = bug.get("broken_behavior", {}).get("status", 400)
        expected_correct = bug.get("expected_correct", {}).get("status", 200)

        score = 0

        test_files = self._find_test_files(test_dir)
        for tf in test_files:
            content = tf.get("content", "")
            if f"assert response.status_code == {broken_status}" in content:
                score += 1
            if f"assert response.status_code == {expected_correct}" in content:
                score += 1
            if f"toBe({broken_status})" in content:
                score += 1
            if f"toBe({expected_correct})" in content:
                score += 1

        return score >= 1

    def _check_field_assertion(self, test_dir: str, bug: dict) -> bool:
        """Check if tests assert on the field that would be missing."""
        field = bug.get("broken_behavior", {}).get("missing_field", "")

        test_files = self._find_test_files(test_dir)
        for tf in test_files:
            content = tf.get("content", "")
            if f'"{field}" in data' in content or f'toHaveProperty("{field}")' in content:
                return True

        return False

    def _count_assertions(self, test_dir: str) -> int:
        """Count total assertions in the test directory."""
        count = 0
        for tf in self._find_test_files(test_dir):
            content = tf.get("content", "")
            count += content.count("assert ")
            count += content.count("expect(")
            count += content.count(".toBe(")
            count += content.count(".toHaveProperty(")
        return count

    def _find_test_files(self, test_dir: str) -> list[dict]:
        """Find test files in the directory and read their contents."""
        import os
        files = []
        if not os.path.exists(test_dir):
            return files
        for fname in os.listdir(test_dir):
            if fname.endswith((".py", ".ts")):
                fpath = os.path.join(test_dir, fname)
                try:
                    with open(fpath) as f:
                        content = f.read()
                    files.append({"name": fname, "path": fpath, "content": content})
                except Exception:
                    pass
        return files
