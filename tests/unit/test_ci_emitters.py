from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from cherenkov.execution.emitters.junit import emit_junit
from cherenkov.execution.emitters.sarif import emit_sarif
from cherenkov.execution.validate import find_spec_line

# Dynamically load the CLI script cherenkov.py as a module to avoid package namespace conflicts
cli_spec = importlib.util.spec_from_file_location("cherenkov_cli", "cherenkov.py")
cherenkov_cli = importlib.util.module_from_spec(cli_spec)
sys.modules["cherenkov_cli"] = cherenkov_cli
cli_spec.loader.exec_module(cherenkov_cli)


class TestCIEmitters(unittest.TestCase):
    """Unit tests for JUnit XML and SARIF 2.1.0 output emitters and spec location resolution (Issue #444)."""

    def setUp(self):
        self.dummy_results = {
            "status": "success",
            "target_url": "http://localhost:8000",
            "reports": [
                {
                    "scenario_id": "happy_path",
                    "passed": True,
                    "request_body": "{}",
                    "response_body": "{}",
                    "suggestions": [],
                    "error": "",
                    "method": "POST",
                    "endpoint": "/users",
                    "test_file": "stub/generated_tests/happy_path.spec.ts"
                },
                {
                    "scenario_id": "missing_email",
                    "passed": False,
                    "request_body": "{}",
                    "response_body": "{}",
                    "suggestions": [],
                    "error": "Expected 422 got 400",
                    "method": "POST",
                    "endpoint": "/users",
                    "test_file": "stub/generated_tests/missing_email.spec.ts",
                    "error_line": 8,
                    "error_column": 5,
                    "error_file": "stub/generated_tests/missing_email.spec.ts"
                },
                {
                    "scenario_id": "unauthorized",
                    "passed": False,
                    "request_body": "",
                    "response_body": "",
                    "suggestions": [],
                    "error": "Expected 401 got 200",
                    "method": "GET",
                    "endpoint": "/health",
                    "test_file": "stub/generated_tests/unauthorized.spec.ts",
                    "error_line": 4,
                    "error_column": 5,
                    "error_file": "stub/generated_tests/unauthorized.spec.ts"
                }
            ]
        }

    def test_find_spec_line_helper(self):
        # Create a temp multi-line spec file to verify line number lookup
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                '{\n'
                '  "paths": {\n'
                '    "/users": {\n'
                '      "post": {\n'
                '        "summary": "Create User"\n'
                '      }\n'
                '    },\n'
                '    "/health": {\n'
                '      "get": {\n'
                '        "summary": "Health Check"\n'
                '      }\n'
                '    }\n'
                '  }\n'
                '}'
            )
            temp_path = f.name

        try:
            # POST /users should map to line 4 (where "post" is inside "/users")
            post_line = find_spec_line(temp_path, "POST", "/users")
            self.assertEqual(post_line, 4)

            # GET /health should map to line 9 (where "get" is inside "/health")
            get_line = find_spec_line(temp_path, "GET", "/health")
            self.assertEqual(get_line, 9)

            # Fallback for non-existent file
            fallback_line = find_spec_line("non_existent_file.json", "GET", "/health")
            self.assertEqual(fallback_line, 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_emit_junit_structure(self):
        xml_str = emit_junit(self.dummy_results)
        self.assertIsNotNone(xml_str)
        self.assertIn("<testsuites", xml_str)

        # Parse XML to verify structure
        root = ET.fromstring(xml_str)
        self.assertEqual(root.attrib["tests"], "3")
        self.assertEqual(root.attrib["failures"], "2")

        suites = root.findall("testsuite")
        # Should group by endpoint method + path: "POST /users" and "GET /health"
        suite_names = [s.attrib["name"] for s in suites]
        self.assertIn("POST /users", suite_names)
        self.assertIn("GET /health", suite_names)

        # check testcases
        post_suite = [s for s in suites if s.attrib["name"] == "POST /users"][0]
        self.assertEqual(post_suite.attrib["tests"], "2")
        self.assertEqual(post_suite.attrib["failures"], "1")

        cases = post_suite.findall("testcase")
        case_names = [c.attrib["name"] for c in cases]
        self.assertIn("happy_path", case_names)
        self.assertIn("missing_email", case_names)

        # check failure details
        failed_case = [c for c in cases if c.attrib["name"] == "missing_email"][0]
        failure = failed_case.find("failure")
        self.assertIsNotNone(failure)
        self.assertEqual(failure.attrib["message"], "Expected 422 got 400")

    def test_emit_sarif_structure(self):
        sarif_str = emit_sarif(self.dummy_results, spec_path="stub/target_spec.json")
        self.assertIsNotNone(sarif_str)
        
        sarif_data = json.loads(sarif_str)
        self.assertEqual(sarif_data["version"], "2.1.0")
        self.assertIn("runs", sarif_data)
        
        run = sarif_data["runs"][0]
        self.assertEqual(run["tool"]["driver"]["name"], "CHERENKOV-QA")
        
        results = run["results"]
        # Only failed tests should be in the results: 2 failures
        self.assertEqual(len(results), 2)
        
        rules = run["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]
        self.assertIn("POST /users", rule_ids)
        self.assertIn("GET /health", rule_ids)
        
        # Check rule mapping on first result
        first_res = results[0]
        self.assertEqual(first_res["ruleId"], "POST /users")
        self.assertEqual(first_res["message"]["text"], "Expected 422 got 400")
        
        location = first_res["locations"][0]["physicalLocation"]
        self.assertEqual(location["artifactLocation"]["uri"], "stub/target_spec.json")

    @patch("cherenkov_cli.ValidationEngine")
    @patch("sys.stdout")
    def test_cli_validate_junit_option(self, mock_stdout, mock_engine_cls):
        # Mock validation results
        mock_engine = MagicMock()
        mock_engine.validate_suite.return_value = self.dummy_results
        mock_engine_cls.return_value = mock_engine

        def exit_side_effect(code=0):
            raise SystemExit(code)

        # Mock sys.exit to prevent test exit
        with patch("sys.exit", side_effect=exit_side_effect) as mock_exit:
            import sys
            test_args = ["cherenkov.py", "validate", "--target", "http://localhost:8000", "--output-format", "junit", "--spec", "stub/target_spec.json"]
            with patch.object(sys, "argv", test_args):
                with self.assertRaises(SystemExit) as cm:
                    cherenkov_cli.main()
                self.assertEqual(cm.exception.code, 1) # Since we had failures, it should exit with 1

    @patch("cherenkov_cli.ValidationEngine")
    @patch("sys.stdout")
    def test_cli_validate_sarif_option(self, mock_stdout, mock_engine_cls):
        mock_engine = MagicMock()
        mock_engine.validate_suite.return_value = self.dummy_results
        mock_engine_cls.return_value = mock_engine

        def exit_side_effect(code=0):
            raise SystemExit(code)

        with patch("sys.exit", side_effect=exit_side_effect) as mock_exit:
            import sys
            test_args = ["cherenkov.py", "validate", "--target", "http://localhost:8000", "--output-format", "sarif", "--spec", "stub/target_spec.json"]
            with patch.object(sys, "argv", test_args):
                with self.assertRaises(SystemExit) as cm:
                    cherenkov_cli.main()
                self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
