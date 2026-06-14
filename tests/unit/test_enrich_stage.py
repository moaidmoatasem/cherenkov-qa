"""Unit tests for cherenkov/stages/enrich.py — RESTGPT-style spec enrichment."""
from __future__ import annotations

import pytest

from cherenkov.stages.enrich import (
    SpecEnrichStage,
    SpecRules,
    _collect_examples,
    _collect_schema_hints,
    _extract_constraint_sentences,
)


# ── helper builders ───────────────────────────────────────────────────────────


def _make_operation(
    description: str = "",
    parameters: list | None = None,
    request_body_properties: dict | None = None,
) -> dict:
    op: dict = {}
    if description:
        op["description"] = description
    if parameters is not None:
        op["parameters"] = parameters
    if request_body_properties is not None:
        op["requestBody"] = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": request_body_properties,
                    }
                }
            }
        }
    return op


# ── _extract_constraint_sentences ─────────────────────────────────────────────


def test_extracts_must_be_sentence():
    text = "The value must be a positive integer. Optional field."
    results = _extract_constraint_sentences(text)
    assert len(results) == 1
    assert "must be" in results[0]


def test_extracts_for_example_sentence():
    text = "Provide a date, for example 2024-01-15."
    results = _extract_constraint_sentences(text)
    assert results  # at least one sentence extracted


def test_ignores_plain_description():
    text = "This field stores the user name."
    results = _extract_constraint_sentences(text)
    assert results == []


def test_multiple_constraint_sentences():
    text = (
        "The email must be a valid RFC 5322 address. "
        "The password must contain at least 8 characters. "
        "An optional alias."
    )
    results = _extract_constraint_sentences(text)
    assert len(results) == 2


# ── _collect_examples ─────────────────────────────────────────────────────────


def test_collects_example_field():
    schema = {"type": "string", "example": "hello@example.com"}
    assert _collect_examples(schema) == ["hello@example.com"]


def test_collects_default_field():
    schema = {"type": "integer", "default": 42}
    assert 42 in _collect_examples(schema)


def test_collects_enum_values():
    schema = {"type": "string", "enum": ["admin", "user", "guest"]}
    result = _collect_examples(schema)
    assert "admin" in result


def test_collects_examples_object():
    schema = {
        "examples": {
            "ex1": {"value": "first"},
            "ex2": {"value": "second"},
        }
    }
    result = _collect_examples(schema)
    assert "first" in result


# ── _collect_schema_hints ─────────────────────────────────────────────────────


def test_hint_pattern():
    schema = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    hints = _collect_schema_hints(schema)
    assert any("regex" in h for h in hints)


def test_hint_format():
    schema = {"type": "string", "format": "email"}
    hints = _collect_schema_hints(schema)
    assert any("email" in h for h in hints)


def test_hint_min_max_length():
    schema = {"type": "string", "minLength": 3, "maxLength": 50}
    hints = _collect_schema_hints(schema)
    texts = " ".join(hints)
    assert "3" in texts and "50" in texts


def test_hint_min_max_value():
    schema = {"type": "integer", "minimum": 1, "maximum": 100}
    hints = _collect_schema_hints(schema)
    texts = " ".join(hints)
    assert "1" in texts and "100" in texts


def test_no_hints_for_bare_schema():
    schema = {"type": "string"}
    hints = _collect_schema_hints(schema)
    assert hints == []


# ── SpecRules ─────────────────────────────────────────────────────────────────


def test_spec_rules_render_empty():
    rules = SpecRules()
    assert rules.is_empty()
    assert rules.render_prompt_block() == ""


def test_spec_rules_render_nonempty():
    rules = SpecRules()
    rules.rules = ["Value must be a valid ISO 8601 date."]
    rules.body_examples = {"email": "test@example.com"}
    block = rules.render_prompt_block()
    assert "SPEC RULES" in block
    assert "ISO 8601" in block
    assert "test@example.com" in block


def test_spec_rules_caps_rules_at_8():
    rules = SpecRules()
    rules.rules = [f"Rule {i}" for i in range(20)]
    block = rules.render_prompt_block()
    # Only 8 rules rendered
    assert block.count("Rule") == 8


# ── SpecEnrichStage ───────────────────────────────────────────────────────────


def test_enrich_with_description_constraint():
    stage = SpecEnrichStage()
    op = _make_operation(description="The name must be unique across all tenants.")
    result = stage.enrich("/items", "post", op, {})
    assert any("must be" in r for r in result.rules)


def test_enrich_with_parameter_example():
    stage = SpecEnrichStage()
    op = _make_operation(
        parameters=[
            {
                "name": "limit",
                "in": "query",
                "schema": {"type": "integer", "example": 25},
            }
        ]
    )
    result = stage.enrich("/items", "get", op, {})
    assert result.param_examples.get("limit") == 25


def test_enrich_with_body_property_example():
    stage = SpecEnrichStage()
    op = _make_operation(
        request_body_properties={
            "email": {"type": "string", "example": "user@example.com"},
        }
    )
    result = stage.enrich("/users", "post", op, {})
    assert result.body_examples.get("email") == "user@example.com"


def test_enrich_with_body_property_hints():
    stage = SpecEnrichStage()
    op = _make_operation(
        request_body_properties={
            "age": {"type": "integer", "minimum": 18, "maximum": 120},
        }
    )
    result = stage.enrich("/users", "post", op, {})
    hints = result.body_hints.get("age", [])
    assert any("18" in h for h in hints)


def test_enrich_deduplicates_rules():
    stage = SpecEnrichStage()
    op = _make_operation(
        description="The name must be unique. The name must be unique.",
    )
    result = stage.enrich("/x", "post", op, {})
    # Even though description contains the sentence twice, dedup removes duplicate
    assert result.rules.count(result.rules[0]) == 1


def test_enrich_empty_operation_is_empty():
    stage = SpecEnrichStage()
    result = stage.enrich("/health", "get", {}, {})
    assert result.is_empty()


def test_enrich_resolves_body_ref():
    """SpecEnrich should dereference $ref in body schema using the schemas dict."""
    stage = SpecEnrichStage()
    op = {
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/CreateUser"}
                }
            }
        }
    }
    schemas = {
        "CreateUser": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "example": "ref@example.com"},
            },
        }
    }
    result = stage.enrich("/users", "post", op, schemas)
    assert result.body_examples.get("email") == "ref@example.com"
