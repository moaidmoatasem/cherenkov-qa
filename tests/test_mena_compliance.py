# TODO: convert to pytest — complex file (>150 lines, setUp/tearDown with shutil)
"""
Tests for MENA Compliance Scanner (Issue #248).
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from cherenkov.compliance.mena_scanner import MENAComplianceScanner


class TestMENAComplianceScanner(unittest.TestCase):
    """Tests for MENA cybersecurity compliance auditor."""

    def setUp(self):
        self.scanner = MENAComplianceScanner("test_run")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_bearer_auth_detection_in_spec(self):
        """Test that bearer auth is detected in OpenAPI spec."""
        spec = {
            "components": {
                "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
            }
        }
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "http://localhost:8000", spec_path
            )

        self.assertTrue(result["audit_results"]["bearer_auth_defined"])
        self.assertEqual(
            result["framework_mappings"]["SAMA_CCSF"][
                "SAMA CCSF Domain 3.1 (Cyber Security Governance)"
            ]["status"],
            "COMPLIANT",
        )

    def test_no_bearer_auth_in_spec(self):
        """Test that missing bearer auth is flagged."""
        spec = {
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "in": "header", "name": "X-API-Key"}
                }
            }
        }
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "http://localhost:8000", spec_path
            )

        self.assertFalse(result["audit_results"]["bearer_auth_defined"])
        self.assertEqual(
            result["framework_mappings"]["SAMA_CCSF"][
                "SAMA CCSF Domain 3.1 (Cyber Security Governance)"
            ]["status"],
            "NON-COMPLIANT",
        )

    def test_tls_enforced_on_https(self):
        """Test TLS check passes for HTTPS URLs."""
        spec = {"components": {"securitySchemes": {}}}
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "https://api.example.com", spec_path
            )

        self.assertTrue(result["audit_results"]["tls_enforced"])

    def test_tls_enforced_on_localhost(self):
        """Test TLS check passes for localhost."""
        spec = {"components": {"securitySchemes": {}}}
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "http://127.0.0.1:8000", spec_path
            )

        self.assertTrue(result["audit_results"]["tls_enforced"])

    def test_security_headers_checked(self):
        """Test security headers are audited from response."""
        spec = {"components": {"securitySchemes": {}}}
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
        }
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers=headers)
            result = self.scanner.run_compliance_audit(
                "http://localhost:8000", spec_path
            )

        self.assertTrue(result["audit_results"]["hsts_present"])
        self.assertTrue(result["audit_results"]["clickjacking_protection"])
        self.assertTrue(result["audit_results"]["mime_sniffing_protection"])

    def test_report_written_to_disk(self):
        """Test compliance report is written to .cherenkov/mena_compliance_report.json."""
        spec = {"components": {"securitySchemes": {}}}
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "http://localhost:8000", spec_path
            )

        self.assertTrue(os.path.exists(self.scanner.report_path))
        with open(self.scanner.report_path) as f:
            saved = json.load(f)
        self.assertEqual(saved["target_url"], "http://localhost:8000")
        self.assertIn("overall_compliance_score", saved)

    def test_connection_failure_handled_gracefully(self):
        """Test that connection failures fall back to static audit only."""
        spec = {
            "components": {
                "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}
            }
        }
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            json.dump(spec, f)

        with patch("requests.get", side_effect=Exception("Connection refused")):
            result = self.scanner.run_compliance_audit(
                "http://unreachable:8000", spec_path
            )

        self.assertIn("Target connection failed", result["audit_results"]["errors"][0])
        # Static check should still work
        self.assertTrue(result["audit_results"]["bearer_auth_defined"])

    def test_spec_parsing_error_handled(self):
        """Test that invalid spec files are handled gracefully."""
        spec_path = os.path.join(self.tmpdir, "spec.json")
        with open(spec_path, "w") as f:
            f.write("not valid json")

        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(headers={})
            result = self.scanner.run_compliance_audit(
                "http://localhost:8000", spec_path
            )

        self.assertIn("Spec parsing failed", result["audit_results"]["errors"][0])


if __name__ == "__main__":
    unittest.main()
