"""tests/unit/test_phase15_personas.py — Phase 15 multi-persona suite generation.

Covers: personas, SpecContext extraction, per-persona generators, merge, enricher,
and the SuiteEngine end-to-end. No live API or LLM calls.
"""

from __future__ import annotations

import pytest

from cherenkov.synthetic.personas import (
    build_spec_contexts,
    DEFAULT_PERSONAS,
    PERSONA_BY_NAME,
    HAPPY_PATH,
    ERROR_PATH,
    SECURITY_PROBER,
    SCHEMA_PEDANT,
    BOUNDARY_SEEKER,
)
from cherenkov.synthetic.persona_generator import generate_for_persona
from cherenkov.synthetic.merge import merge_suites
from cherenkov.synthetic.enricher import enrich_suite
from cherenkov.synthetic.suite_engine import SuiteEngine


# ── fixtures ───────────────────────────────────────────────────────────────────

_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "PetStore", "version": "1.0"},
    "security": [{"bearerAuth": []}],
    "components": {
        "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
        "schemas": {
            "Pet": {
                "type": "object",
                "required": ["id", "name"],
                "properties": {
                    "id":   {"type": "integer"},
                    "name": {"type": "string"},
                    "tag":  {"type": "string"},
                },
            },
        },
    },
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Pet"},
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "tag":  {"type": "string"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {"description": "created"},
                    "400": {"description": "bad request"},
                    "422": {"description": "validation error"},
                },
            },
        },
        "/pets/{id}": {
            "get": {
                "operationId": "getPet",
                "summary": "Get a pet by ID",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"}
                            }
                        },
                    },
                    "404": {"description": "not found"},
                },
            },
        },
    },
}


# ── SpecContext tests ──────────────────────────────────────────────────────────

def test_spec_context_extracts_all_operations():
    ctx = build_spec_contexts(_SPEC)
    assert set(ctx.keys()) == {"listPets", "createPet", "getPet"}


def test_spec_context_success_codes():
    ctx = build_spec_contexts(_SPEC)
    assert 200 in ctx["listPets"].success_codes
    assert 201 in ctx["createPet"].success_codes


def test_spec_context_error_codes():
    ctx = build_spec_contexts(_SPEC)
    assert 400 in ctx["createPet"].error_codes
    assert 422 in ctx["createPet"].error_codes
    assert 404 in ctx["getPet"].error_codes


def test_spec_context_path_params():
    ctx = build_spec_contexts(_SPEC)
    assert ctx["getPet"].path_params == ["id"]
    assert ctx["listPets"].path_params == []


def test_spec_context_required_body_fields():
    ctx = build_spec_contexts(_SPEC)
    assert "name" in ctx["createPet"].required_body_fields
    assert ctx["listPets"].required_body_fields == []


def test_spec_context_auth_required():
    ctx = build_spec_contexts(_SPEC)
    # Global security applies to all ops
    assert ctx["listPets"].auth_required is True
    assert ctx["getPet"].auth_required is True


def test_spec_context_response_fields():
    ctx = build_spec_contexts(_SPEC)
    # getPet returns Pet schema → id, name, tag
    fields = ctx["getPet"].response_fields
    assert "id" in fields or "name" in fields  # $ref resolved


# ── HappyPath persona tests ────────────────────────────────────────────────────

def test_happy_path_generates_status_assertion():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(HAPPY_PATH, ctx, _SPEC)
    test = suite["listPets"][0]
    assertion_types = [a["type"] for a in test["assertions"]]
    assert "status" in assertion_types


def test_happy_path_generates_content_type_assertion():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(HAPPY_PATH, ctx, _SPEC)
    test = suite["listPets"][0]
    header_assertions = [a for a in test["assertions"] if a.get("type") == "header"]
    assert any("Content-Type" in a.get("name", "") for a in header_assertions)


def test_happy_path_covers_all_ops():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(HAPPY_PATH, ctx, _SPEC)
    assert set(suite.keys()) == {"listPets", "createPet", "getPet"}


# ── ErrorPath persona tests ────────────────────────────────────────────────────

def test_error_path_generates_test_for_body_ops():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(ERROR_PATH, ctx, _SPEC)
    assert "createPet" in suite
    test = next(t for t in suite["createPet"] if "missing_body" in t["name"])
    statuses = test["assertions"][0]["expected"]
    assert any(c >= 400 for c in statuses)


def test_error_path_generates_not_found_for_get_with_path_params():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(ERROR_PATH, ctx, _SPEC)
    assert "getPet" in suite
    test = next(t for t in suite["getPet"] if "not_found" in t["name"])
    statuses = test["assertions"][0]["expected"]
    assert 404 in statuses


def test_error_path_empty_body_request():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(ERROR_PATH, ctx, _SPEC)
    test = next(t for t in suite["createPet"] if "missing_body" in t["name"])
    assert test["request"]["body"] == {}


# ── SecurityProber persona tests ───────────────────────────────────────────────

def test_security_prober_generates_test_for_every_op():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(SECURITY_PROBER, ctx, _SPEC)
    assert set(suite.keys()) == {"listPets", "createPet", "getPet"}


def test_security_prober_expects_401_or_403():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(SECURITY_PROBER, ctx, _SPEC)
    test = suite["listPets"][0]
    statuses = test["assertions"][0]["expected"]
    assert any(c in (401, 403) for c in statuses)


def test_security_prober_sends_invalid_auth_header():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(SECURITY_PROBER, ctx, _SPEC)
    test = suite["listPets"][0]
    headers = test["request"].get("headers", {})
    assert "Authorization" in headers


# ── SchemaPedant persona tests ─────────────────────────────────────────────────

def test_schema_pedant_generates_two_tests_per_op():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(SCHEMA_PEDANT, ctx, _SPEC)
    assert len(suite["listPets"]) == 2


def test_schema_pedant_asserts_response_fields():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(SCHEMA_PEDANT, ctx, _SPEC)
    pedant_tests = suite["getPet"]
    field_test = next(t for t in pedant_tests if "fields" in t["name"])
    json_key_assertions = [a for a in field_test["assertions"] if a.get("type") == "json_key"]
    # Pet schema has id, name, tag
    assert len(json_key_assertions) >= 2


# ── BoundarySeeker persona tests ───────────────────────────────────────────────

def test_boundary_seeker_sends_empty_required_fields():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(BOUNDARY_SEEKER, ctx, _SPEC)
    test = next(t for t in suite["createPet"] if "empty_fields" in t["name"])
    body = test["request"]["body"]
    assert body == {"name": ""}  # only required field


def test_boundary_seeker_tests_zero_path_param():
    ctx = build_spec_contexts(_SPEC)
    suite = generate_for_persona(BOUNDARY_SEEKER, ctx, _SPEC)
    test = next(t for t in suite["getPet"] if "zero_id" in t["name"])
    assert test["request"]["path_params"]["id"] == "0"


# ── merge tests ────────────────────────────────────────────────────────────────

def test_merge_combines_all_ops():
    ctx = build_spec_contexts(_SPEC)
    suites = [generate_for_persona(p, ctx, _SPEC) for p in DEFAULT_PERSONAS]
    merged = merge_suites(suites)
    assert set(merged.keys()) == {"listPets", "createPet", "getPet"}


def test_merge_deduplicates_by_name():
    suite_a = {"listPets": [{"name": "test_list", "assertions": []}]}
    suite_b = {"listPets": [{"name": "test_list", "assertions": []}]}
    merged = merge_suites([suite_a, suite_b])
    assert len(merged["listPets"]) == 1


def test_merge_total_test_count_reasonable():
    ctx = build_spec_contexts(_SPEC)
    suites = [generate_for_persona(p, ctx, _SPEC) for p in DEFAULT_PERSONAS]
    merged = merge_suites(suites)
    total = sum(len(v) for v in merged.values())
    # 5 personas × 3 ops, many generate 1-2 tests each → expect ≥ 10
    assert total >= 10


# ── enricher tests ─────────────────────────────────────────────────────────────

def test_enricher_adds_content_type_to_under_asserted_test():
    bare_suite = {
        "listPets": [{
            "name": "bare_test",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [{"type": "status", "expected": [200]}],
        }]
    }
    enriched = enrich_suite(bare_suite, _SPEC)
    assertions = enriched["listPets"][0]["assertions"]
    header_types = [a for a in assertions if a.get("type") == "header"]
    assert any("Content-Type" in a.get("name", "") for a in header_types)


def test_enricher_does_not_duplicate_existing_content_type():
    suite = {
        "listPets": [{
            "name": "already_enriched",
            "request": {"method": "GET", "path": "/pets"},
            "assertions": [
                {"type": "status", "expected": [200]},
                {"type": "header", "name": "Content-Type", "contains": "json"},
                {"type": "json_key", "field": "id", "exists": True},
            ],
        }]
    }
    enriched = enrich_suite(suite, _SPEC)
    ct_count = sum(
        1 for a in enriched["listPets"][0]["assertions"]
        if a.get("type") == "header" and "Content-Type" in a.get("name", "")
    )
    assert ct_count == 1


def test_enricher_preserves_4xx_tests_unchanged():
    suite = {
        "createPet": [{
            "name": "error_test",
            "request": {"method": "POST", "path": "/pets", "body": {}},
            "assertions": [{"type": "status", "expected": [400, 422]}],
        }]
    }
    enriched = enrich_suite(suite, _SPEC)
    # 4xx test — enricher should not add Content-Type or json_key
    assertions = enriched["createPet"][0]["assertions"]
    assert not any(a.get("type") == "header" for a in assertions)


# ── SuiteEngine end-to-end tests ───────────────────────────────────────────────

def test_suite_engine_covers_all_spec_ops():
    result = SuiteEngine(_SPEC).run()
    assert result.operations_covered == 3
    assert set(result.suite.keys()) == {"listPets", "createPet", "getPet"}


def test_suite_engine_total_tests_reasonable():
    result = SuiteEngine(_SPEC).run()
    assert result.total_tests >= 10


def test_suite_engine_produces_grade_report():
    result = SuiteEngine(_SPEC).run()
    assert result.grade_report is not None
    assert result.grade_report.grade in ("A", "B", "C", "D", "F")


def test_suite_engine_grade_better_than_single_skeleton():
    from cherenkov.eval.grader import SuiteGrader
    from cherenkov.drift.maker import build_test_skeleton, _find_operation

    # Minimal single-persona skeleton suite
    single_suite = {}
    for op_id in ("listPets", "createPet", "getPet"):
        found = _find_operation(op_id, _SPEC)
        if found:
            path, method, op = found
            single_suite[op_id] = [build_test_skeleton(op_id, op, _SPEC, path, method)]
    single_report = SuiteGrader(_SPEC).grade(single_suite)

    engine_result = SuiteEngine(_SPEC).run()
    assert engine_result.grade_report is not None
    # Engine suite should have higher assertion density than the single skeleton
    assert (
        engine_result.grade_report.overall_assertion_density
        >= single_report.overall_assertion_density
    )


def test_suite_engine_sequential_same_op_coverage_as_parallel():
    parallel   = SuiteEngine(_SPEC, parallel=True).run()
    sequential = SuiteEngine(_SPEC, parallel=False).run()
    assert parallel.operations_covered == sequential.operations_covered


def test_suite_engine_persona_subset():
    result = SuiteEngine(_SPEC, personas=[HAPPY_PATH, SCHEMA_PEDANT]).run()
    assert result.operations_covered == 3
    # Only HappyPath + SchemaPedant tests — no security or error-path tests
    for tests in result.suite.values():
        names = [t["name"] for t in tests]
        assert not any("security_probe" in n for n in names)


def test_suite_engine_result_to_dict():
    result = SuiteEngine(_SPEC).run()
    d = result.to_dict()
    assert "total_tests" in d
    assert "operations_covered" in d
    assert "persona_runs" in d
    assert d["total_tests"] == result.total_tests
