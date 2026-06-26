"""cherenkov/drift/fingerprint.py — Fingerprint + similarity().

Domain-adapted from MetaHarness's cosine+categorical+jaccard blend.
Dimensions are API-test specific rather than generic code metrics.

Weights (0.4/0.3/0.3) ship as defaults — tune against LlamaRestTest/AutoRestTest
eval baselines once the harness can replay them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


_NUMERIC_WEIGHT = 0.4
_CATEGORICAL_WEIGHT = 0.3
_SET_WEIGHT = 0.3


@dataclass(frozen=True)
class Fingerprint:
    # numerics (cosine, weight 0.4) — all normalized to [0,1]
    endpoint_coverage: float      # tested ops / spec ops
    assertion_density: float      # assertions / test (normalized to [0,1] cap at 20)
    schema_conformance: float     # assertions whose target schema still exists
    spec_completeness: float      # ops with full schema vs underspecified
    flake_rate: float             # from benchmark_harness stability classification

    # categoricals (exact-match, weight 0.3)
    spec_version: str             # "2.0", "3.0", "3.1"
    auth_scheme: str              # none | apiKey | bearer | oauth2 | ...
    generation_profile: str

    # sets (jaccard, weight 0.3)
    operation_set: frozenset[str]       # operationIds
    tag_set: frozenset[str]
    required_param_set: frozenset[str]  # "op:param" tuples


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors; 1.0 if both zero."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 and mag_b == 0:
        return 1.0
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _categorical_sim(a: Fingerprint, b: Fingerprint) -> float:
    """Fraction of categorical fields that match exactly."""
    fields = ["spec_version", "auth_scheme", "generation_profile"]
    matches = sum(getattr(a, f) == getattr(b, f) for f in fields)
    return matches / len(fields)


def _jaccard(a: frozenset, b: frozenset) -> float:
    """Jaccard similarity; 1.0 if both empty."""
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def _set_sim(a: Fingerprint, b: Fingerprint) -> float:
    """Average Jaccard across the three set dimensions."""
    j_ops = _jaccard(a.operation_set, b.operation_set)
    j_tags = _jaccard(a.tag_set, b.tag_set)
    j_params = _jaccard(a.required_param_set, b.required_param_set)
    return (j_ops + j_tags + j_params) / 3.0


def similarity(a: Fingerprint, b: Fingerprint) -> float:
    """Overall weighted similarity in [0, 1].

    overall = 0.4·cosine(numerics) + 0.3·categorical(enums) + 0.3·jaccard(sets)
    """
    numeric_fields = [
        "endpoint_coverage",
        "assertion_density",
        "schema_conformance",
        "spec_completeness",
        "flake_rate",
    ]
    vec_a = [getattr(a, f) for f in numeric_fields]
    vec_b = [getattr(b, f) for f in numeric_fields]

    cosine_score = _cosine(vec_a, vec_b)
    cat_score = _categorical_sim(a, b)
    set_score = _set_sim(a, b)

    return _NUMERIC_WEIGHT * cosine_score + _CATEGORICAL_WEIGHT * cat_score + _SET_WEIGHT * set_score


def _extract_operations(spec: dict[str, Any]) -> dict[str, dict]:
    """Return {operationId: operation_dict} from an OpenAPI spec dict."""
    ops: dict[str, dict] = {}
    paths = spec.get("paths", {})
    _http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _http_methods:
                continue
            if not isinstance(operation, dict):
                continue
            op_id = operation.get("operationId", f"{method.upper()}:{path}")
            ops[op_id] = operation
    return ops


def _required_param_set(spec: dict[str, Any]) -> frozenset[str]:
    """Return frozenset of "operationId:paramName" for all required parameters."""
    result: set[str] = set()
    for op_id, operation in _extract_operations(spec).items():
        for param in operation.get("parameters", []):
            if isinstance(param, dict) and param.get("required", False):
                result.add(f"{op_id}:{param.get('name', '?')}")
    return frozenset(result)


def _detect_auth_scheme(spec: dict[str, Any]) -> str:
    """Guess the primary auth scheme from securitySchemes."""
    components = spec.get("components", {}) or spec.get("securityDefinitions", {})
    schemes = components.get("securitySchemes", {}) or components
    if not schemes:
        return "none"
    for name, scheme in schemes.items():
        if not isinstance(scheme, dict):
            continue
        kind = scheme.get("type", "").lower()
        bearer_format = scheme.get("bearerFormat", "").lower()
        if kind == "http" and bearer_format in ("jwt", "bearer"):
            return "bearer"
        if kind == "oauth2":
            return "oauth2"
        if kind == "apikey":
            return "apiKey"
        if kind == "http":
            return "http"
    return "none"


def fingerprint_of(
    spec: dict[str, Any],
    suite: dict[str, Any],
    flake_rate: float = 0.0,
) -> Fingerprint:
    """Compute a Fingerprint from a parsed spec + suite manifest.

    suite is expected to be a dict mapping operationId → list[test_dict].
    Each test_dict may have an "assertions" key with a list of assertion dicts.
    """
    spec_ops = _extract_operations(spec)
    suite_ops = set(suite.keys())
    spec_op_ids = frozenset(spec_ops.keys())

    # endpoint_coverage
    endpoint_coverage = (
        len(suite_ops & spec_op_ids) / len(spec_op_ids) if spec_op_ids else 1.0
    )

    # assertion_density (normalize: cap at 20 assertions/test → 1.0)
    total_tests = sum(len(v) for v in suite.values()) if suite else 0
    total_assertions = sum(
        len(t.get("assertions", [])) for tests in suite.values() for t in tests
    )
    raw_density = (total_assertions / total_tests) if total_tests > 0 else 0.0
    assertion_density = min(raw_density / 20.0, 1.0)

    # schema_conformance: assertions whose target schema operationId still in spec
    total_assertion_count = total_assertions
    valid_assertion_count = 0
    for op_id, tests in suite.items():
        if op_id in spec_op_ids:
            for t in tests:
                valid_assertion_count += len(t.get("assertions", []))
    schema_conformance = (
        valid_assertion_count / total_assertion_count
        if total_assertion_count > 0
        else 1.0
    )

    # spec_completeness: ops that have at least one response schema defined
    ops_with_schema = sum(
        1
        for op in spec_ops.values()
        if op.get("responses") and any(
            isinstance(r, dict) and (
                r.get("content") or r.get("schema")
            )
            for r in op["responses"].values()
        )
    )
    spec_completeness = ops_with_schema / len(spec_ops) if spec_ops else 1.0

    # categoricals
    spec_version = str(spec.get("openapi", spec.get("swagger", "3.0")))[:3]
    auth_scheme = _detect_auth_scheme(spec)

    # sets
    all_tags: set[str] = set()
    for op in spec_ops.values():
        all_tags.update(op.get("tags", []))

    return Fingerprint(
        endpoint_coverage=endpoint_coverage,
        assertion_density=assertion_density,
        schema_conformance=schema_conformance,
        spec_completeness=spec_completeness,
        flake_rate=flake_rate,
        spec_version=spec_version,
        auth_scheme=auth_scheme,
        generation_profile=suite.get("_generation_profile", "default"),
        operation_set=spec_op_ids,
        tag_set=frozenset(all_tags),
        required_param_set=_required_param_set(spec),
    )
