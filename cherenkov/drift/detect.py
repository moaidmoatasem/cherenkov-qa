"""cherenkov/drift/detect.py — Deterministic drift detection (no LLM).

detect_findings() is the only "smart" non-LLM logic in Phase 12.
It compares a baseline snapshot against current spec+suite and emits
DriftFindings for each detected deviation.

The design rule: this module NEVER calls the LLM. It is pure Python
comparisons against the fingerprint + spec + suite data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DriftKind(str, Enum):
    REMOVED_OP_STILL_TESTED = "removed_op_still_tested"
    NEW_OP_UNTESTED = "new_op_untested"
    BREAKING_SCHEMA_CHANGE = "breaking_schema_change"
    STATUS_CONTRACT_VIOLATION = "status_contract_violation"
    DEPRECATED_OP_TESTED = "deprecated_op_tested"
    ADDED_OPTIONAL_PARAM = "added_optional_param"


@dataclass
class DriftFinding:
    kind: DriftKind
    operation_id: str
    detail: str
    before: Any = None
    after: Any = None


def _extract_operations(spec: dict[str, Any]) -> dict[str, dict]:
    ops: dict[str, dict] = {}
    _http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    for path, path_item in spec.get("paths", {}).items():
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


def _required_fields(schema: dict[str, Any]) -> frozenset[str]:
    """Return frozenset of required field names from a JSON Schema object."""
    if not isinstance(schema, dict):
        return frozenset()
    return frozenset(schema.get("required", []))


def _resolve_schema(spec: dict[str, Any], ref: str) -> dict[str, Any]:
    """Very shallow $ref resolver for local #/components/schemas/Foo refs."""
    if not ref.startswith("#/"):
        return {}
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for part in parts:
        if not isinstance(node, dict):
            return {}
        node = node.get(part, {})
    return node if isinstance(node, dict) else {}


def _response_schemas(spec: dict[str, Any], operation: dict[str, Any]) -> dict[str, dict]:
    """Return {status_code: schema_dict} for a single operation."""
    result: dict[str, dict] = {}
    for status_code, response in operation.get("responses", {}).items():
        if not isinstance(response, dict):
            continue
        # OpenAPI 3.x content map
        for media_type, media_obj in response.get("content", {}).items():
            if not isinstance(media_obj, dict):
                continue
            schema = media_obj.get("schema", {})
            if "$ref" in schema:
                schema = _resolve_schema(spec, schema["$ref"])
            result[str(status_code)] = schema
        # OpenAPI 2.x direct schema
        if "schema" in response and str(status_code) not in result:
            schema = response["schema"]
            if "$ref" in schema:
                schema = _resolve_schema(spec, schema["$ref"])
            result[str(status_code)] = schema
    return result


def _check_breaking_schema(
    op_id: str,
    baseline_spec: dict[str, Any],
    current_spec: dict[str, Any],
    baseline_op: dict[str, Any],
    current_op: dict[str, Any],
) -> list[DriftFinding]:
    """Detect breaking schema changes for a single operation.

    Breaking = a required field was added to a response schema, or a field's
    type changed. Both would break existing assertions.
    """
    findings: list[DriftFinding] = []

    baseline_schemas = _response_schemas(baseline_spec, baseline_op)
    current_schemas = _response_schemas(current_spec, current_op)

    for status_code, current_schema in current_schemas.items():
        baseline_schema = baseline_schemas.get(status_code, {})

        # Required fields added to response body
        baseline_required = _required_fields(baseline_schema)
        current_required = _required_fields(current_schema)
        newly_required = current_required - baseline_required
        if newly_required:
            findings.append(
                DriftFinding(
                    kind=DriftKind.BREAKING_SCHEMA_CHANGE,
                    operation_id=op_id,
                    detail=(
                        f"Response {status_code}: newly required fields "
                        f"{sorted(newly_required)}"
                    ),
                    before=sorted(baseline_required),
                    after=sorted(current_required),
                )
            )

        # Type changes in existing properties
        baseline_props = baseline_schema.get("properties", {})
        current_props = current_schema.get("properties", {})
        for field_name, current_field_schema in current_props.items():
            if field_name not in baseline_props:
                continue
            baseline_type = baseline_props[field_name].get("type")
            current_type = current_field_schema.get("type")
            if baseline_type and current_type and baseline_type != current_type:
                findings.append(
                    DriftFinding(
                        kind=DriftKind.BREAKING_SCHEMA_CHANGE,
                        operation_id=op_id,
                        detail=(
                            f"Response {status_code}: field '{field_name}' type "
                            f"changed {baseline_type!r} → {current_type!r}"
                        ),
                        before=baseline_type,
                        after=current_type,
                    )
                )

    return findings


def _check_added_optional_params(
    op_id: str,
    baseline_op: dict[str, Any],
    current_op: dict[str, Any],
) -> list[DriftFinding]:
    baseline_params = {
        p["name"]: p
        for p in baseline_op.get("parameters", [])
        if isinstance(p, dict) and "name" in p
    }
    current_params = {
        p["name"]: p
        for p in current_op.get("parameters", [])
        if isinstance(p, dict) and "name" in p
    }
    findings: list[DriftFinding] = []
    for name, param in current_params.items():
        if name not in baseline_params and not param.get("required", False):
            findings.append(
                DriftFinding(
                    kind=DriftKind.ADDED_OPTIONAL_PARAM,
                    operation_id=op_id,
                    detail=f"New optional parameter '{name}' added",
                    after=name,
                )
            )
    return findings


def detect_findings(
    baseline_snapshot: "SpecSuiteSnapshot",  # noqa: F821
    current_spec: dict[str, Any],
    current_suite: dict[str, Any],
    runner_violations: list[dict] | None = None,
) -> list[DriftFinding]:
    """Detect all drift findings deterministically — no LLM calls.

    Axis A + B: spec drift and suite staleness.
    Axis C: consumed from runner_violations (list of {operation_id, detail} dicts).

    Args:
        baseline_snapshot: The frozen SpecSuiteSnapshot to compare against.
        current_spec:      Parsed OpenAPI spec dict (current state).
        current_suite:     Suite manifest dict: {operationId: [test_dicts]}.
        runner_violations: Optional axis-C signals from benchmark_harness.

    Returns:
        List of DriftFinding, deterministically derived.
    """
    from cherenkov.drift.snapshot import SpecSuiteSnapshot

    findings: list[DriftFinding] = []

    # Reconstruct baseline spec operations from the baseline fingerprint's operation_set.
    # We only have hashes + fingerprint for the baseline spec itself, so we use
    # the operation_set from the fingerprint as the ground truth for "what existed."
    baseline_op_ids: frozenset[str] = baseline_snapshot.fingerprint.operation_set
    current_spec_ops = _extract_operations(current_spec)
    current_op_ids = frozenset(current_spec_ops.keys())
    suite_op_ids = frozenset(current_suite.keys()) - {"_generation_profile"}

    # A1: REMOVED_OP_STILL_TESTED — op was in baseline spec, gone from current, still in suite
    removed_ops = baseline_op_ids - current_op_ids
    for op_id in sorted(removed_ops):
        if op_id in suite_op_ids:
            findings.append(
                DriftFinding(
                    kind=DriftKind.REMOVED_OP_STILL_TESTED,
                    operation_id=op_id,
                    detail=f"Operation '{op_id}' removed from spec but suite still tests it",
                    before=op_id,
                    after=None,
                )
            )

    # A2: NEW_OP_UNTESTED — op appeared in current spec, not in suite
    new_ops = current_op_ids - baseline_op_ids
    for op_id in sorted(new_ops):
        if op_id not in suite_op_ids:
            findings.append(
                DriftFinding(
                    kind=DriftKind.NEW_OP_UNTESTED,
                    operation_id=op_id,
                    detail=f"New operation '{op_id}' in spec has no test",
                    after=op_id,
                )
            )

    # B1: DEPRECATED_OP_TESTED — op is marked deprecated in current spec but still tested
    for op_id, operation in current_spec_ops.items():
        if operation.get("deprecated", False) and op_id in suite_op_ids:
            findings.append(
                DriftFinding(
                    kind=DriftKind.DEPRECATED_OP_TESTED,
                    operation_id=op_id,
                    detail=f"Operation '{op_id}' is deprecated but suite still tests it",
                )
            )

    # For operations that exist in both baseline and current spec, we need the
    # baseline spec to detect schema changes. Since we only store the fingerprint
    # (not the full spec), we check schema changes by comparing what we *can*
    # derive: the required_param_set delta.
    baseline_required_params = baseline_snapshot.fingerprint.required_param_set
    current_required_params: set[str] = set()
    for op_id, op in current_spec_ops.items():
        for param in op.get("parameters", []):
            if isinstance(param, dict) and param.get("required", False):
                current_required_params.add(f"{op_id}:{param.get('name', '?')}")

    # B2: BREAKING_SCHEMA_CHANGE from required param set delta
    # New required params = breaking (existing tests won't supply them)
    newly_required_params = frozenset(current_required_params) - baseline_required_params
    for param_key in sorted(newly_required_params):
        op_id, param_name = param_key.split(":", 1)
        if op_id in current_op_ids:  # still exists (not a new op)
            findings.append(
                DriftFinding(
                    kind=DriftKind.BREAKING_SCHEMA_CHANGE,
                    operation_id=op_id,
                    detail=(
                        f"Parameter '{param_name}' became required — "
                        "existing tests may not supply it"
                    ),
                    before=False,
                    after=True,
                )
            )

    # B3: ADDED_OPTIONAL_PARAM — informational
    # New optional params in ops that existed in baseline
    baseline_optional_params = baseline_snapshot.fingerprint.optional_param_set
    for op_id, current_op in current_spec_ops.items():
        if op_id not in baseline_op_ids:
            continue  # new op, handled above
        for param in current_op.get("parameters", []):
            if not isinstance(param, dict):
                continue
            name = param.get("name", "")
            if not param.get("required", False):
                # Check that this param was actually absent from baseline
                param_key = f"{op_id}:{name}"
                if param_key not in baseline_optional_params and param_key not in baseline_required_params:
                    findings.append(
                        DriftFinding(
                            kind=DriftKind.ADDED_OPTIONAL_PARAM,
                            operation_id=op_id,
                            detail=f"New optional parameter '{name}' added to '{op_id}'",
                            after=name,
                        )
                    )

    # C: STATUS_CONTRACT_VIOLATION — wired in from runner
    for violation in runner_violations or []:
        findings.append(
            DriftFinding(
                kind=DriftKind.STATUS_CONTRACT_VIOLATION,
                operation_id=violation.get("operation_id", "unknown"),
                detail=violation.get("detail", "Status contract violated"),
                before=violation.get("expected_status"),
                after=violation.get("observed_status"),
            )
        )

    return findings
