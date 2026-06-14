#!/usr/bin/env python3
"""
test_source_adapter.py — Conformance tests for Claim/Provenance contracts,
SourceAdapter interface, and OpenAPISourceAdapter implementation.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cherenkov.core.contracts import Claim, Provenance, ProvenanceType
from cherenkov.truth.sources.interface import SourceAdapter
from cherenkov.truth.sources.openapi import OpenAPISourceAdapter


class TestSourceAdapterSPI(unittest.TestCase):
    def test_claims_contract_serialization(self):
        """Verify Claim and Provenance model round-trips via Pydantic model_validate_json."""
        prov = Provenance(
            source_type=ProvenanceType.SPEC,
            source_uri="some/spec/path.json",
            details={"version": "1.0.0"},
        )
        claim = Claim(
            id="spec_get_users_exists",
            category="endpoint",
            subject="GET /users",
            value={"richness": 0.8},
            provenance=prov,
        )

        dumped = claim.model_dump_json()
        restored = Claim.model_validate_json(dumped)

        self.assertEqual(restored.id, claim.id)
        self.assertEqual(restored.category, claim.category)
        self.assertEqual(restored.subject, claim.subject)
        self.assertEqual(restored.value, claim.value)
        self.assertEqual(restored.provenance.source_type, claim.provenance.source_type)
        self.assertEqual(restored.provenance.source_uri, claim.provenance.source_uri)
        self.assertEqual(restored.provenance.details, claim.provenance.details)

    def test_interface_cannot_be_instantiated(self):
        """Verify SourceAdapter is an abstract class and cannot be directly instantiated."""
        with self.assertRaises(TypeError):
            SourceAdapter()  # type: ignore

    def test_openapi_adapter_implements_interface(self):
        """Verify OpenAPISourceAdapter is a subclass of SourceAdapter."""
        adapter = OpenAPISourceAdapter()
        self.assertTrue(isinstance(adapter, SourceAdapter))

    def test_openapi_adapter_claims_extraction(self):
        """Verify OpenAPISourceAdapter correctly reads a spec and maps slices/mutations to Claims."""
        # Create a simple valid OpenAPI spec
        spec_content = {
            "openapi": "3.1.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "post": {
                        "summary": "Create user",
                        "operationId": "createUser",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
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
                    "User": {
                        "type": "object",
                        "required": ["email", "name"],
                        "properties": {
                            "email": {"type": "string"},
                            "name": {"type": "string"},
                        },
                    }
                }
            },
        }

        with TemporaryDirectory() as tmpdir:
            spec_path = Path(tmpdir) / "openapi.json"
            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(spec_content, f)

            adapter = OpenAPISourceAdapter()
            claims = adapter.discover_claims(str(spec_path))

            # We expect multiple claims:
            # 1. endpoint existence claim
            # 2. request details claim
            # 3. mutations: happy_path, unauthorized, missing_email
            categories = [c.category for c in claims]
            self.assertIn("endpoint", categories)
            self.assertIn("request", categories)
            self.assertIn("mutation", categories)

            # Check endpoint existence claim
            exist_claim = next(c for c in claims if c.category == "endpoint")
            self.assertEqual(exist_claim.subject, "POST /users")
            self.assertEqual(exist_claim.value["operation_id"], "createUser")
            self.assertEqual(exist_claim.provenance.source_type, ProvenanceType.SPEC)
            self.assertEqual(
                exist_claim.provenance.source_uri, str(spec_path.resolve())
            )

            # Check mutation claim
            mut_claim = next(
                c
                for c in claims
                if c.category == "mutation" and "missing_email" in c.id
            )
            self.assertEqual(
                mut_claim.subject, "POST /users -> mutation -> missing_email"
            )
            self.assertEqual(mut_claim.value["expected_status"], 422)


if __name__ == "__main__":
    unittest.main()
