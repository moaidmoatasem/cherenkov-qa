"""cherenkov/drift/maker.py — Phase 13 proposal maker.

Generates ReconciliationProposals from DriftFindings without calling the LLM.
Schema-driven: builds minimal but valid test skeletons from the OpenAPI spec.

LLM-enhanced generation is Phase 14+. This module stays deterministic so the
checker can be tested in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cherenkov.drift.detect import DriftFinding, DriftKind
from cherenkov.drift.loop import ReconciliationProposal


# ── schema → value helpers ─────────────────────────────────────────────────────

_TYPE_DEFAULTS: dict[str, Any] = {
    "string":  "example",
    "integer": 0,
    "number":  0.0,
    "boolean": False,
    "array":   [],
    "object":  {},
}


def _placeholder(schema: dict[str, Any], name: str = "") -> Any:
    """Return a minimal placeholder value for a JSON Schema property."""
    if not isinstance(schema, dict):
        return None
    fmt = schema.get("format", "")
    typ = schema.get("type", "string")
    if typ == "string":
        if fmt in ("uuid", "uuid4"):
            return "00000000-0000-0000-0000-000000000000"
        if fmt in ("date-time", "datetime"):
            return "2026-01-01T00:00:00Z"
        if fmt == "date":
            return "2026-01-01"
        if fmt == "email":
            return "test@example.com"
        if "id" in name.lower():
            return "1"
        return "example"
    return _TYPE_DEFAULTS.get(typ, None)


def _build_body(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Build a minimal request body dict from a JSON Schema object."""
    if not isinstance(schema, dict):
        return {}
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            parts = ref.lstrip("#/").split("/")
            node: Any = spec
            for part in parts:
                node = node.get(part, {}) if isinstance(node, dict) else {}
            return _build_body(node, spec)
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    return {
        name: _placeholder(prop_schema, name)
        for name, prop_schema in props.items()
        if name in required
    }


def build_test_skeleton(
    op_id: str,
    operation: dict[str, Any],
    spec: dict[str, Any],
    path: str = "",
    method: str = "GET",
) -> dict[str, Any]:
    """Build a minimal suite test dict for a single operation.

    The skeleton is immediately valid for the suite manifest format:
      { "name": ..., "request": {...}, "assertions": [...] }
    """
    # Parameters
    params: dict[str, Any] = {}
    path_params: dict[str, str] = {}
    for param in operation.get("parameters", []):
        if not isinstance(param, dict):
            continue
        name = param.get("name", "")
        location = param.get("in", "")
        schema = param.get("schema", {"type": "string"})
        value = _placeholder(schema, name)
        if location == "path":
            path_params[name] = str(value)
        elif location in ("query", "header") and param.get("required", False):
            params[name] = value

    # Request body (OpenAPI 3.x)
    body: dict[str, Any] | None = None
    req_body = operation.get("requestBody", {})
    if req_body:
        content = req_body.get("content", {})
        for media_type, media_obj in content.items():
            if isinstance(media_obj, dict):
                body = _build_body(media_obj.get("schema", {}), spec)
                break

    # Expected status codes — prefer 2xx
    responses = operation.get("responses", {})
    success_codes = sorted(
        int(c) for c in responses if str(c).startswith("2") and str(c).isdigit()
    )
    expected_statuses = success_codes or [200]

    request: dict[str, Any] = {
        "method": method.upper(),
        "path": path,
    }
    if path_params:
        request["path_params"] = path_params
    if params:
        request["params"] = params
    if body is not None:
        request["body"] = body

    assertions = [
        {
            "type": "status",
            "expected": expected_statuses,
        }
    ]

    return {
        "name": f"smoke_{op_id}",
        "description": f"Auto-generated skeleton for '{op_id}' (drift-reconcile)",
        "request": request,
        "assertions": assertions,
    }


# ── proposal factories ─────────────────────────────────────────────────────────

def _find_operation(
    op_id: str, spec: dict[str, Any]
) -> tuple[str, str, dict[str, Any]] | None:
    """Return (path, method, operation_dict) for an operationId, or None."""
    _http_methods = {"get", "post", "put", "patch", "delete", "options", "head"}
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _http_methods:
                continue
            if not isinstance(operation, dict):
                continue
            if operation.get("operationId", f"{method.upper()}:{path}") == op_id:
                return path, method, operation
    return None


def make_proposal(finding: DriftFinding, spec: dict[str, Any]) -> ReconciliationProposal:
    """Generate a ReconciliationProposal for a single DriftFinding.

    For NEW_OP_UNTESTED: builds a test skeleton from the spec.
    For ADDED_OPTIONAL_PARAM: returns a metadata-only proposal (no structural patch).
    """
    if finding.kind == DriftKind.NEW_OP_UNTESTED:
        found = _find_operation(finding.operation_id, spec)
        if found:
            path, method, operation = found
            skeleton = build_test_skeleton(
                finding.operation_id, operation, spec, path=path, method=method
            )
        else:
            skeleton = {
                "name": f"smoke_{finding.operation_id}",
                "description": f"Skeleton for '{finding.operation_id}' (operation not found in spec)",
                "request": {"method": "GET", "path": "/"},
                "assertions": [{"type": "status", "expected": [200]}],
            }
        return ReconciliationProposal(
            operation_id=finding.operation_id,
            drift_kind=finding.kind,
            action=(
                f"Add test skeleton for new operation '{finding.operation_id}' "
                f"to suite"
            ),
            patch={
                "op": "add_test",
                "suite_key": finding.operation_id,
                "test": skeleton,
            },
        )

    if finding.kind == DriftKind.ADDED_OPTIONAL_PARAM:
        param_name = finding.after or "(unknown)"
        return ReconciliationProposal(
            operation_id=finding.operation_id,
            drift_kind=finding.kind,
            action=(
                f"Annotate optional param '{param_name}' in existing tests "
                f"for '{finding.operation_id}'"
            ),
            patch={
                "op": "annotate_param",
                "suite_key": finding.operation_id,
                "param": param_name,
            },
        )

    # Fallback for any other non-FAIL kind
    return ReconciliationProposal(
        operation_id=finding.operation_id,
        drift_kind=finding.kind,
        action=f"Reconcile {finding.kind.value} for '{finding.operation_id}'",
        patch={},
    )


# ── suite commit ───────────────────────────────────────────────────────────────

def patch_suite(
    proposals: list[ReconciliationProposal],
    suite_path: Path,
) -> None:
    """Apply approved proposals to a suite JSON file (in-place).

    For "add_test" patches: appends the skeleton to the operation's test list.
    For "annotate_param" patches: no-op (metadata only, informational).
    """
    suite: dict[str, Any] = {}
    if suite_path.exists():
        suite = json.loads(suite_path.read_text())

    changed = False
    for proposal in proposals:
        patch = proposal.patch
        op = patch.get("op")
        key = patch.get("suite_key", proposal.operation_id)

        if op == "add_test":
            test = patch.get("test", {})
            if key not in suite:
                suite[key] = []
            existing_names = {t.get("name") for t in suite[key] if isinstance(t, dict)}
            if test.get("name") not in existing_names:
                suite[key].append(test)
                changed = True

        elif op == "annotate_param":
            # Informational — no structural mutation needed
            pass

    if changed:
        suite_path.write_text(json.dumps(suite, indent=2))
