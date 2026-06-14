from cherenkov.core.settings import get_settings
# TODO: convert to pytest — complex file (>150 lines, setUp/tearDown)
"""
Tests for Issue #194 — Lightweight DAST Mutation Profile.

Validates:
- DAST_PAYLOADS constant is defined and contains expected entries
- Security mutations are emitted for string properties when CHERENKOV_DAST_ENABLED=1
- Security mutations are NOT emitted when DAST is disabled (default)
- Mutation.case_type is "security" with correct expected_status
- The value field is set to the hostile payload string
"""

import os
import unittest
from unittest.mock import patch
import cherenkov.core.config

from cherenkov.stages.ingest import DAST_PAYLOADS


class TestDASTPayloads(unittest.TestCase):
    """Tests for DAST payload definition."""

    def test_dast_payloads_defined(self):
        self.assertTrue(len(DAST_PAYLOADS) > 0)
        names = [p[0] for p in DAST_PAYLOADS]
        self.assertIn("sqli_tautology", names)
        self.assertIn("xss_reflected", names)
        self.assertIn("path_traversal", names)
        self.assertIn("template_injection", names)

    def test_dast_payloads_includes_expected_entries(self):
        payload_map = dict(DAST_PAYLOADS)
        self.assertIn("' OR '1'='1", payload_map["sqli_tautology"])
        self.assertIn("<script>alert(1)</script>", payload_map["xss_reflected"])
        self.assertIn("../../../../etc/passwd", payload_map["path_traversal"])


class TestDASTMutationIngest(unittest.TestCase):
    """Tests that DAST mutations are emitted in the ingest pipeline."""

    def setUp(self):
        self.spec = {
            "openapi": "3.1.0",
            "info": {"title": "Test", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create User",
                        "operationId": "create_user",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/UserCreate"
                                    }
                                }
                            },
                            "required": True,
                        },
                        "responses": {
                            "201": {"description": "Created"},
                            "422": {"description": "Validation Error"},
                        },
                    }
                }
            },
            "components": {
                "schemas": {
                    "UserCreate": {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {
                                "type": "string",
                                "maxLength": 50,
                                "description": "User email",
                            },
                            "password": {
                                "type": "string",
                                "minLength": 8,
                                "description": "User password",
                            },
                        },
                    }
                }
            },
        }
        self.os_environ_patch = patch.dict(os.environ, {"CHERENKOV_DAST_ENABLED": "1"})
        self.os_environ_patch.start()

    def tearDown(self):
        self.os_environ_patch.stop()

    def test_security_mutations_emitted_when_enabled(self):
        with patch.object(get_settings(), "DAST_ENABLED", True):
            from cherenkov.stages.ingest import IngestStage as IngSt

            stage = IngSt("test_dast")
            spec_path = self._write_temp_spec()
            try:
                output = stage.run(spec_path)
                self.assertEqual(len(output.endpoints), 1)
                ep = output.endpoints[0]
                security_muts = [m for m in ep.mutations if m.case_type == "security"]
                self.assertTrue(
                    len(security_muts) > 0,
                    f"Expected security mutations, got case_types: {[m.case_type for m in ep.mutations]}",
                )
                for mut in security_muts:
                    self.assertEqual(
                        mut.expected_status,
                        422,
                        f"Security mutation {mut.id} should have spec-derived validation_status",
                    )
                    self.assertIsNotNone(
                        mut.value,
                        f"Security mutation {mut.id} should have a payload value",
                    )
                    self.assertIn("hostile", mut.instruction.lower())
                    self.assertIn("4xx", mut.instruction)
                    self.assertIn("NOT 5xx", mut.instruction)
            finally:
                self._cleanup_temp(spec_path)

    def test_security_mutations_not_emitted_when_disabled(self):
        with patch.object(get_settings(), "DAST_ENABLED", False):
            from cherenkov.stages.ingest import IngestStage as IngSt

            stage = IngSt("test_dast_disabled")
            spec_path = self._write_temp_spec()
            try:
                output = stage.run(spec_path)
                ep = output.endpoints[0]
                security_muts = [m for m in ep.mutations if m.case_type == "security"]
                self.assertEqual(
                    len(security_muts),
                    0,
                    f"Expected no security mutations when disabled, got {len(security_muts)}",
                )
            finally:
                self._cleanup_temp(spec_path)

    def test_security_mutations_per_string_field(self):
        with patch.object(get_settings(), "DAST_ENABLED", True):
            from cherenkov.stages.ingest import IngestStage as IngSt

            stage = IngSt("test_dast_count")
            spec_path = self._write_temp_spec()
            try:
                output = stage.run(spec_path)
                ep = output.endpoints[0]
                security_muts = [m for m in ep.mutations if m.case_type == "security"]
                expected_per_field = len(DAST_PAYLOADS)
                self.assertEqual(
                    len(security_muts),
                    2 * expected_per_field,
                    f"Expected {2 * expected_per_field} security mutations "
                    f"(2 string fields x {expected_per_field} payloads), got {len(security_muts)}",
                )
            finally:
                self._cleanup_temp(spec_path)

    # ── helpers ──────────────────────────────────────────────────────────

    def _write_temp_spec(self):
        import tempfile
        import json

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(self.spec, tmp)
        tmp.close()
        return tmp.name

    def _cleanup_temp(self, path):
        import os as _os

        if _os.path.exists(path):
            _os.unlink(path)


if __name__ == "__main__":
    unittest.main()
