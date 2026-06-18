import unittest
from types import SimpleNamespace
from cherenkov.core.contracts import DivergenceFinding
from cherenkov.execution.emitters.allure import AllureEmitter


class TestAllureEmitter(unittest.TestCase):
    def test_emit_allure_json(self):
        report = SimpleNamespace(
            findings=[
                DivergenceFinding(
                    violation_type="conformance-drift",
                    endpoint="POST /api/users",
                    http_method="POST",
                    expected="201 Created",
                    actual="400 Bad Request",
                    summary="Drift detected",
                    description="Failed",
                    severity="critical",
                    remediation="Fix it",
                )
            ]
        )
        setattr(report, "_total_tests", 2)

        emitter = AllureEmitter()
        results = emitter.emit(report, "openapi.yaml")

        self.assertEqual(len(results), 2)

        # Check passing test
        passing = [r for r in results if r["status"] == "passed"][0]
        self.assertIn("successful_conformance_check", passing["name"])

        # Check failing test
        failing = [r for r in results if r["status"] == "failed"][0]
        self.assertEqual(failing["name"], "POST /api/users")
        self.assertEqual(failing["statusDetails"]["message"], "Drift detected")
        self.assertEqual(failing["statusDetails"]["trace"], "Failed")
        self.assertTrue(
            any(
                label
                for label in failing["labels"]
                if label["name"] == "severity" and label["value"] == "critical"
            )
        )


if __name__ == "__main__":
    unittest.main()
