from __future__ import annotations

import json
import unittest

from cherenkov.langchain.tool import CherenkovValidateTool


class TestCherenkovValidateTool(unittest.TestCase):
    def setUp(self):
        self.tool = CherenkovValidateTool()

    def test_validate_target_returns_summary(self):
        """Smoke-test the validate_target operation against the local ValidationEngine."""
        query = json.dumps(
            {
                "operation": "validate_target",
                "target_url": "http://localhost:8000",
                "workers": 1,
            }
        )
        result = self.tool._run(query)
        # Validation may fail because no server is running, but the tool should
        # return a string response, not raise.
        self.assertIsInstance(result, str)
        self.assertIn("Validation", result)

    def test_generate_tests_returns_guidance(self):
        query = json.dumps(
            {
                "operation": "generate_tests",
                "spec_path": "stub/openapi.yaml",
                "target_url": "http://localhost:8000",
            }
        )
        result = self.tool._run(query)
        self.assertIn("stub/openapi.yaml", result)
        self.assertIn("validate_target", result)

    def test_explain_violation_unknown_id(self):
        query = json.dumps(
            {"operation": "explain_violation", "violation_id": "not-real"}
        )
        result = self.tool._run(query)
        self.assertIn("not found", result)

    def test_invalid_json(self):
        result = self.tool._run("not-json")
        self.assertIn("Invalid JSON", result)

    def test_unknown_operation(self):
        query = json.dumps({"operation": "fly_to_moon"})
        result = self.tool._run(query)
        self.assertIn("Unknown operation", result)


if __name__ == "__main__":
    unittest.main()
