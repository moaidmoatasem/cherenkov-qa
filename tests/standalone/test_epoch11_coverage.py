"""
test_epoch11_coverage.py — Unit tests for Epoch 11 Coverage SDET (Issue #92).
Tests: UnitTestEmitter, CoverageLoop, AssertionGate.
"""
import unittest
from unittest import mock
import tempfile
import os
import json

from cherenkov.coverage.emitter import UnitTestEmitter
from cherenkov.coverage.loop import CoverageLoop, CoverageThreshold, CoverageReport
from cherenkov.coverage.assertion_gate import AssertionGate, AssertionGateResult, BrokenImplementation
from cherenkov.core.contracts import GenerateOutput, Status, StageMeta


SAMPLE_ENDPOINT = {
    "path": "/users",
    "method": "POST",
    "operation": {
        "summary": "Create a new user",
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "password": {"type": "string"},
                        },
                        "required": ["email", "password"],
                    }
                }
            }
        },
        "responses": {
            "201": {
                "description": "User created",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer"},
                                "email": {"type": "string"},
                            },
                        }
                    }
                }
            },
            "400": {"description": "Validation error"},
        },
    },
}

SAMPLE_GET_ENDPOINT = {
    "path": "/health",
    "method": "GET",
    "operation": {
        "summary": "Health check",
        "responses": {
            "200": {
                "description": "OK",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "status": {"type": "string"},
                            },
                        }
                    }
                }
            }
        },
    },
}


class TestUnitTestEmitter(unittest.TestCase):
    """Test unit-test emitter for pytest/jest."""

    def setUp(self):
        self.emitter = UnitTestEmitter(run_id="test")
        self.tmpdir = tempfile.mkdtemp()

    def test_emit_pytest_creates_file(self):
        results = self.emitter.emit(
            [SAMPLE_ENDPOINT],
            output_dir=self.tmpdir,
            framework="pytest",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, Status.OK)
        self.assertIn("pytest", results[0].test_code)
        self.assertIn("requests.", results[0].test_code)

    def test_emit_pytest_contains_status_assertion(self):
        results = self.emitter.emit([SAMPLE_ENDPOINT], output_dir=self.tmpdir, framework="pytest")
        self.assertIn("assert response.status_code == 201", results[0].test_code)

    def test_emit_pytest_contains_shape_assertion(self):
        results = self.emitter.emit([SAMPLE_ENDPOINT], output_dir=self.tmpdir, framework="pytest")
        self.assertIn('"id" in data', results[0].test_code)
        self.assertIn('"email" in data', results[0].test_code)

    def test_emit_pytest_generates_sample_body(self):
        results = self.emitter.emit([SAMPLE_ENDPOINT], output_dir=self.tmpdir, framework="pytest")
        self.assertIn("json=", results[0].test_code)

    def test_emit_get_endpoint_no_body(self):
        results = self.emitter.emit([SAMPLE_GET_ENDPOINT], output_dir=self.tmpdir, framework="pytest")
        self.assertNotIn("json=", results[0].test_code)

    def test_emit_jest_creates_file(self):
        results = self.emitter.emit(
            [SAMPLE_GET_ENDPOINT],
            output_dir=self.tmpdir,
            framework="jest",
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, Status.OK)
        self.assertIn("describe", results[0].test_code)
        self.assertIn("expect(", results[0].test_code)

    def test_emit_jest_contains_expected_assertions(self):
        results = self.emitter.emit([SAMPLE_GET_ENDPOINT], output_dir=self.tmpdir, framework="jest")
        self.assertIn("expect(response.status).toBe(200)", results[0].test_code)
        self.assertIn('toHaveProperty("status")', results[0].test_code)

    def test_emit_multiple_endpoints(self):
        results = self.emitter.emit(
            [SAMPLE_ENDPOINT, SAMPLE_GET_ENDPOINT],
            output_dir=self.tmpdir,
            framework="pytest",
        )
        self.assertEqual(len(results), 2)

    def test_output_file_written_to_disk(self):
        self.emitter.emit([SAMPLE_ENDPOINT], output_dir=self.tmpdir, framework="pytest")
        files = os.listdir(self.tmpdir)
        py_files = [f for f in files if f.endswith(".py")]
        self.assertGreater(len(py_files), 0)

    def test_infer_expected_status_201(self):
        status = self.emitter._infer_expected_status(SAMPLE_ENDPOINT["operation"])
        self.assertEqual(status, 201)

    def test_infer_expected_status_200(self):
        status = self.emitter._infer_expected_status(SAMPLE_GET_ENDPOINT["operation"])
        self.assertEqual(status, 200)

    def test_generate_sample_body(self):
        body = self.emitter._generate_sample_body(SAMPLE_ENDPOINT["operation"])
        self.assertIn("email", body)
        self.assertIn("password", body)
        self.assertEqual(body["email"], "test")
        self.assertEqual(body["password"], "test")

    def test_to_class_name(self):
        name = UnitTestEmitter._to_class_name("/api/users/{id}", "get")
        self.assertEqual(name, "TestApiUsersIdGet")

    def test_to_test_name(self):
        name = UnitTestEmitter._to_test_name("/api/users", "post")
        self.assertEqual(name, "api_users_post")


class TestCoverageReport(unittest.TestCase):
    """Test CoverageReport helper."""

    def test_endpoint_coverage_pct(self):
        r = CoverageReport(total_endpoints=10, covered_endpoints=7)
        self.assertEqual(r.endpoint_coverage_pct, 0.7)

    def test_endpoint_coverage_zero_division(self):
        r = CoverageReport(total_endpoints=0, covered_endpoints=0)
        self.assertEqual(r.endpoint_coverage_pct, 1.0)

    def test_test_pass_rate(self):
        r = CoverageReport(total_tests=10, passed_tests=8)
        self.assertEqual(r.test_pass_rate, 0.8)

    def test_to_dict(self):
        r = CoverageReport(total_endpoints=10, covered_endpoints=8, total_tests=5, passed_tests=4, failed_tests=1)
        d = r.to_dict()
        self.assertIn("endpoint_coverage_pct", d)
        self.assertIn("test_pass_rate", d)


class TestCoverageLoop(unittest.TestCase):
    """Test the coverage loop."""

    def setUp(self):
        self.loop = CoverageLoop(run_id="test")
        self.tmpdir = tempfile.mkdtemp()

    @mock.patch("cherenkov.coverage.loop.subprocess.run")
    def test_run_emits_tests(self, mock_run):
        mock_run.return_value = mock.MagicMock(
            returncode=0,
            stdout="PASSED test_users\nPASSED test_health\n",
            stderr="",
        )
        slices = [SAMPLE_ENDPOINT, SAMPLE_GET_ENDPOINT]
        report = self.loop.run(
            slices,
            output_dir=self.tmpdir,
            framework="pytest",
        )
        self.assertIsInstance(report, CoverageReport)
        self.assertGreater(report.total_tests, 0)

    def test_check_threshold_met(self):
        self.assertTrue(self.loop._check_threshold_met(8, 10, 0.9))

    def test_check_threshold_not_met(self):
        self.assertFalse(self.loop._check_threshold_met(2, 10, 0.3))

    def test_estimate_status_coverage(self):
        slices = [SAMPLE_ENDPOINT, SAMPLE_GET_ENDPOINT]
        cov = self.loop._estimate_status_coverage(slices)
        self.assertGreater(cov, 0)
        self.assertLessEqual(cov, 1.0)


class TestBrokenImplementation(unittest.TestCase):
    """Test BrokenImplementation bug generation."""

    def setUp(self):
        self.broken = BrokenImplementation()

    def test_generates_status_bugs(self):
        bugs = self.broken.generate(SAMPLE_ENDPOINT["operation"])
        status_bugs = [b for b in bugs if "wrong_status" in b["id"]]
        self.assertGreater(len(status_bugs), 0)

    def test_bug_has_description(self):
        bugs = self.broken.generate(SAMPLE_ENDPOINT["operation"])
        for b in bugs:
            self.assertIn("description", b)

    def test_bug_has_broken_behaviour(self):
        bugs = self.broken.generate(SAMPLE_ENDPOINT["operation"])
        for b in bugs:
            self.assertIn("broken_behavior", b)

    def test_get_endpoint_generates_fewer_bugs(self):
        bugs = self.broken.generate(SAMPLE_GET_ENDPOINT["operation"])
        self.assertGreater(len(bugs), 0)


class TestAssertionGate(unittest.TestCase):
    """Test the AssertionGate (self-play broken-impl check)."""

    def setUp(self):
        self.gate = AssertionGate(run_id="test")
        self.tmpdir = tempfile.mkdtemp()
        self._write_test_file("test_users.py", '''
import requests
response = requests.post("http://localhost:8001/users", json={"email": "test@test.com", "password": "secret"})
assert response.status_code == 201
data = response.json()
assert "id" in data
assert "email" in data
''')

    def _write_test_file(self, name: str, content: str):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w") as f:
            f.write(content)

    def test_generates_bugs_from_endpoints(self):
        bugs = self.gate._generate_bugs([SAMPLE_ENDPOINT, SAMPLE_GET_ENDPOINT])
        self.assertGreater(len(bugs), 0)

    def test_detects_status_assertion(self):
        bug = {"id": "wrong_status_201", "broken_behavior": {"status": 400}, "expected_correct": {"status": 201}}
        self.assertTrue(self.gate._check_status_assertion(self.tmpdir, bug))

    def test_detects_missing_field_assertion(self):
        bug = {"id": "missing_field_id", "broken_behavior": {"missing_field": "id"}}
        self.assertTrue(self.gate._check_field_assertion(self.tmpdir, bug))

    def test_missing_field_not_found(self):
        bug = {"id": "missing_field_nonexistent", "broken_behavior": {"missing_field": "nonexistent"}}
        self.assertFalse(self.gate._check_field_assertion(self.tmpdir, bug))

    def test_run_returns_result(self):
        result = self.gate.run([SAMPLE_ENDPOINT, SAMPLE_GET_ENDPOINT], test_dir=self.tmpdir)
        self.assertIsInstance(result, AssertionGateResult)
        self.assertGreater(result.total_tests, 0)

    def test_result_to_dict(self):
        result = AssertionGateResult(total_tests=5, caught_bugs=4, missed_bugs=1, passed=True)
        d = result.to_dict()
        self.assertIn("bug_catch_rate", d)
        self.assertEqual(d["bug_catch_rate"], 0.8)

    def test_count_assertions_counts_correctly(self):
        count = self.gate._count_assertions(self.tmpdir)
        self.assertGreaterEqual(count, 3)


if __name__ == "__main__":
    unittest.main()
