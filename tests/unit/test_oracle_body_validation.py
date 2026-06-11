import pytest
from unittest import mock


def test_oracle_body_validation_catches_missing_required_field():
    """Oracle should return is_correct=False when required body field is absent."""
    try:
        from cherenkov.oracle.spec_prism import SpecPrismOracle
    except ImportError:
        pytest.skip("SpecPrismOracle not available")

    oracle = SpecPrismOracle.__new__(SpecPrismOracle)
    schema = {"type": "object", "required": ["id", "name"], "properties": {"id": {"type": "integer"}, "name": {"type": "string"}}}
    ok, conf, detail = oracle._validate_response_body({"id": 1}, schema)
    # Missing "name" field
    assert not ok, f"Expected failure but got: {detail}"
    assert conf >= 0.9


def test_oracle_body_validation_passes_valid_body():
    try:
        from cherenkov.oracle.spec_prism import SpecPrismOracle
    except ImportError:
        pytest.skip("SpecPrismOracle not available")
    oracle = SpecPrismOracle.__new__(SpecPrismOracle)
    schema = {"type": "object", "required": ["id"], "properties": {"id": {"type": "integer"}}}
    ok, conf, detail = oracle._validate_response_body({"id": 42}, schema)
    assert ok


def test_oracle_latency_sla_exceeded():
    try:
        from cherenkov.oracle.spec_prism import SpecPrismOracle
    except ImportError:
        pytest.skip("SpecPrismOracle not available")
    oracle = SpecPrismOracle.__new__(SpecPrismOracle)
    result = oracle._evaluate_latency(5000, "/api/users", "GET")
    assert not result.is_correct
    assert "SLA" in result.detail


def test_oracle_201_missing_location_header():
    try:
        from cherenkov.oracle.spec_prism import SpecPrismOracle
    except ImportError:
        pytest.skip("SpecPrismOracle not available")
    oracle = SpecPrismOracle.__new__(SpecPrismOracle)
    ok, conf, detail = oracle._validate_response_headers({}, None, 201)
    assert not ok
    assert "Location" in detail
