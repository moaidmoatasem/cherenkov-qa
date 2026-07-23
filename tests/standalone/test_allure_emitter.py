import unittest
from types import SimpleNamespace

from cherenkov.core.contracts import DivergenceFinding
from cherenkov.execution.emitters.allure import AllureEmitter


class TestAllureEmitter(unittest.TestCase):
    def test_emit_allure_json(self):
        report = SimpleNamespace(findings=[
            DivergenceFinding(
                violation_type="conformance-drift",
                endpoint="POST /api/users",
                http_method="POST",
                expected="201 Created",
                actual="400 Bad Request",
                summary="Drift detected",
                description="Failed",
                severity="critical",
                remediation="Fix it"
            )
        ])
        report._total_tests = 2

        emitter = AllureEmitter()
        results = emitter.emit(report, "openapi.yaml")

        self.assertEqual(len(results), 2)

        # Check passing test
        passing = next(r for r in results if r["status"] == "passed")
        self.assertIn("successful_conformance_check", passing["name"])

        # Check failing test
        failing = next(r for r in results if r["status"] == "failed")
        self.assertEqual(failing["name"], "POST /api/users")
        self.assertEqual(failing["statusDetails"]["message"], "Drift detected")
        self.assertEqual(failing["statusDetails"]["trace"], "Failed")
        self.assertTrue(any(lbl for lbl in failing["labels"] if lbl["name"] == "severity" and lbl["value"] == "critical"))

if __name__ == "__main__":
    unittest.main()
