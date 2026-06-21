"""Tests for cherenkov/stages/schema_check.py"""

import pytest
import yaml
from pathlib import Path

from cherenkov.stages.schema_check import (
    check_response,
    SchemaCheckStage,
    SchemaCheckResult,
    SchemaViolation,
    _resolve_ref,
    _deref,
    _extract_response_schema,
)

PETSTORE_PATH = Path(__file__).parent.parent.parent / "bench" / "fixtures" / "petstore.yaml"


@pytest.fixture(scope="module")
def petstore():
    return yaml.safe_load(PETSTORE_PATH.read_text(encoding="utf-8"))


# ── _resolve_ref ──────────────────────────────────────────────────────────────

class TestResolveRef:
    def test_resolves_component_schema(self, petstore):
        result = _resolve_ref("#/components/schemas/Pet", petstore)
        assert result is not None
        assert result["type"] == "object"
        assert "id" in result["properties"]

    def test_returns_none_for_missing(self, petstore):
        assert _resolve_ref("#/components/schemas/NonExistent", petstore) is None

    def test_returns_none_for_external_ref(self, petstore):
        assert _resolve_ref("https://example.com/schema", petstore) is None

    def test_handles_tilde_encoding(self):
        spec = {"paths": {"a~b/c": {"type": "string"}}}
        result = _resolve_ref("#/paths/a~0b~1c", spec)
        assert result == {"type": "string"}


# ── _deref ────────────────────────────────────────────────────────────────────

class TestDeref:
    def test_inlines_ref(self, petstore):
        schema = {"$ref": "#/components/schemas/Pet"}
        derefed = _deref(schema, petstore)
        assert "properties" in derefed
        assert "id" in derefed["properties"]

    def test_passthrough_on_no_ref(self, petstore):
        schema = {"type": "string"}
        assert _deref(schema, petstore) == {"type": "string"}

    def test_nested_ref_inlined(self, petstore):
        schema = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/Pet"},
        }
        derefed = _deref(schema, petstore)
        assert derefed["items"]["type"] == "object"


# ── _extract_response_schema ─────────────────────────────────────────────────

class TestExtractResponseSchema:
    def test_extracts_get_pets_200(self, petstore):
        schema = _extract_response_schema(petstore, "/pets", "GET", 200)
        assert schema is not None
        assert schema["type"] == "array"

    def test_extracts_post_pets_201(self, petstore):
        schema = _extract_response_schema(petstore, "/pets", "POST", 201)
        assert schema is not None
        assert schema["type"] == "object"

    def test_returns_none_for_unknown_path(self, petstore):
        assert _extract_response_schema(petstore, "/nonexistent", "GET", 200) is None

    def test_returns_none_for_unknown_method(self, petstore):
        assert _extract_response_schema(petstore, "/pets", "DELETE", 200) is None

    def test_path_template_matching(self, petstore):
        # /pets/{petId} should match /pets/123
        schema = _extract_response_schema(petstore, "/pets/123", "GET", 200)
        assert schema is not None

    def test_returns_none_for_missing_status(self, petstore):
        # petstore doesn't declare a 404 for GET /pets
        result = _extract_response_schema(petstore, "/pets", "GET", 404)
        assert result is None


# ── check_response ────────────────────────────────────────────────────────────

class TestCheckResponse:
    def test_valid_pet_list_passes(self, petstore):
        body = [{"id": 1, "name": "Fido"}, {"id": 2, "name": "Rex"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert result.ok
        assert not result.skipped
        assert result.issues == []

    def test_missing_required_field_fails(self, petstore):
        # Pet requires 'id' and 'name'
        body = [{"name": "Fido"}]  # missing 'id'
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert not result.ok
        assert len(result.issues) >= 1
        assert any("id" in v.message for v in result.issues)

    def test_wrong_type_fails(self, petstore):
        body = [{"id": "not-an-int", "name": "Fido"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert not result.ok
        assert any("integer" in v.message.lower() or "int" in v.message.lower()
                   for v in result.issues)

    def test_extra_fields_pass(self, petstore):
        # OpenAPI schemas are open by default (additionalProperties not set to false)
        body = [{"id": 1, "name": "Fido", "colour": "brown"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert result.ok

    def test_valid_single_pet_passes(self, petstore):
        body = {"id": 42, "name": "Whiskers", "tag": "cat"}
        result = check_response(body, petstore, "/pets/{petId}", "GET", 200)
        assert result.ok

    def test_no_schema_in_spec_is_skipped(self, petstore):
        # GET /pets has no 404 schema in petstore
        result = check_response({"error": "not found"}, petstore, "/pets", "GET", 404)
        assert result.skipped
        assert result.ok  # skipped is not a failure

    def test_unknown_path_is_skipped(self, petstore):
        result = check_response({}, petstore, "/unknown", "GET", 200)
        assert result.skipped

    def test_post_pet_valid_201(self, petstore):
        body = {"id": 99, "name": "NewPet"}
        result = check_response(body, petstore, "/pets", "POST", 201)
        assert result.ok

    def test_post_pet_missing_id_fails(self, petstore):
        body = {"name": "NoPet"}
        result = check_response(body, petstore, "/pets", "POST", 201)
        assert not result.ok

    def test_result_has_endpoint_metadata(self, petstore):
        body = [{"id": 1, "name": "Fido"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert result.endpoint == "/pets"
        assert result.method == "GET"
        assert result.status_code == 200

    def test_violation_has_path_and_message(self, petstore):
        body = [{"name": "Fido"}]  # missing id
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert result.issues
        v = result.issues[0]
        assert v.path
        assert v.message

    def test_summary_pass(self, petstore):
        body = [{"id": 1, "name": "A"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert "PASS" in result.summary

    def test_summary_fail(self, petstore):
        body = [{"name": "missing-id"}]
        result = check_response(body, petstore, "/pets", "GET", 200)
        assert "FAIL" in result.summary

    def test_summary_skip(self, petstore):
        result = check_response({}, petstore, "/unknown", "GET", 200)
        assert "SKIP" in result.summary


# ── SchemaCheckStage ──────────────────────────────────────────────────────────

class TestSchemaCheckStage:
    def test_from_file(self):
        stage = SchemaCheckStage.from_file(str(PETSTORE_PATH))
        assert stage is not None

    def test_check_valid_response(self):
        stage = SchemaCheckStage.from_file(str(PETSTORE_PATH))
        result = stage.check("/pets", "GET", 200, [{"id": 1, "name": "Fido"}])
        assert result.ok

    def test_check_invalid_response(self):
        stage = SchemaCheckStage.from_file(str(PETSTORE_PATH))
        result = stage.check("/pets", "GET", 200, [{"name": "NoPet"}])
        assert not result.ok

    def test_check_many(self):
        stage = SchemaCheckStage.from_file(str(PETSTORE_PATH))
        entries = [
            {"endpoint": "/pets", "method": "GET", "status_code": 200,
             "response_body": [{"id": 1, "name": "A"}]},
            {"endpoint": "/pets", "method": "POST", "status_code": 201,
             "response_body": {"id": 2, "name": "B"}},
            {"endpoint": "/pets/1", "method": "GET", "status_code": 200,
             "response_body": {"id": 1, "name": "C"}},
        ]
        results = stage.check_many(entries)
        assert len(results) == 3
        assert all(r.ok for r in results)

    def test_check_many_partial_failure(self):
        stage = SchemaCheckStage.from_file(str(PETSTORE_PATH))
        entries = [
            {"endpoint": "/pets", "method": "GET", "status_code": 200,
             "response_body": [{"id": 1, "name": "A"}]},
            {"endpoint": "/pets", "method": "GET", "status_code": 200,
             "response_body": [{"name": "missing-id"}]},  # invalid
        ]
        results = stage.check_many(entries)
        assert results[0].ok
        assert not results[1].ok
