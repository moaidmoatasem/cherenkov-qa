"""cherenkov/synthetic/persona_generator.py — Per-persona test case generation.

Each TesterPersona produces tests from its own viewpoint, analogous to STORM's
WikiWriter × TopicExpert dialogue pairs running concurrently per persona.
No LLM calls — rule-based derivation from OperationContext + OpenAPI spec.
"""

from __future__ import annotations

from typing import Any

from cherenkov.synthetic.personas import TesterPersona, OperationContext


def generate_for_persona(
    persona: TesterPersona,
    contexts: dict[str, OperationContext],
    spec: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Generate tests for every operation under a single persona's lens."""
    suite: dict[str, list[dict[str, Any]]] = {}
    for op_id, ctx in contexts.items():
        tests = _generate_tests(persona, ctx, spec)
        if tests:
            suite[op_id] = tests
    return suite


def _generate_tests(
    persona: TesterPersona,
    ctx: OperationContext,
    spec: dict[str, Any],
) -> list[dict[str, Any]]:
    dispatch = {
        "HappyPath":      _happy_path_tests,
        "ErrorPath":      _error_path_tests,
        "SecurityProber": _security_prober_tests,
        "SchemaPedant":   _schema_pedant_tests,
        "BoundarySeeker": _boundary_seeker_tests,
    }
    fn = dispatch.get(persona.name)
    return fn(ctx, spec) if fn else []


# ── helpers ────────────────────────────────────────────────────────────────────

def _base_request(ctx: OperationContext) -> dict[str, Any]:
    req: dict[str, Any] = {"method": ctx.method, "path": ctx.path}
    if ctx.path_params:
        req["path_params"] = {p: "1" for p in ctx.path_params}
    return req


def _base_request_from_spec(
    ctx: OperationContext, spec: dict[str, Any]
) -> dict[str, Any]:
    """Build a minimal valid request using the drift maker's skeleton builder."""
    from cherenkov.drift.maker import build_test_skeleton, _find_operation
    found = _find_operation(ctx.operation_id, spec)
    if not found:
        return _base_request(ctx)
    path, method, operation = found
    skeleton = build_test_skeleton(ctx.operation_id, operation, spec, path, method)
    return dict(skeleton["request"])


# ── per-persona generators ─────────────────────────────────────────────────────

def _happy_path_tests(
    ctx: OperationContext, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    request = _base_request_from_spec(ctx, spec)
    assertions: list[dict[str, Any]] = [
        {"type": "status", "expected": ctx.success_codes},
        {"type": "header", "name": "Content-Type", "contains": "json"},
    ]
    for field in ctx.response_fields[:2]:
        assertions.append({"type": "json_key", "field": field, "exists": True})

    return [{
        "name": f"happy_path_{ctx.operation_id}",
        "description": f"[HappyPath] Validates 2xx response for {ctx.operation_id}",
        "request": request,
        "assertions": assertions,
    }]


def _error_path_tests(
    ctx: OperationContext, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    if ctx.has_request_body and ctx.required_body_fields:
        error_codes = [c for c in ctx.error_codes if 400 <= c < 500] or [400, 422]
        req: dict[str, Any] = {"method": ctx.method, "path": ctx.path, "body": {}}
        if ctx.path_params:
            req["path_params"] = {p: "1" for p in ctx.path_params}
        tests.append({
            "name": f"error_path_{ctx.operation_id}_missing_body",
            "description": (
                f"[ErrorPath] Empty body missing required fields "
                f"should yield {error_codes}"
            ),
            "request": req,
            "assertions": [{"type": "status", "expected": error_codes}],
        })

    if ctx.path_params and ctx.method.upper() in ("GET", "DELETE"):
        not_found = [c for c in ctx.error_codes if c == 404] or [404]
        tests.append({
            "name": f"error_path_{ctx.operation_id}_not_found",
            "description": f"[ErrorPath] Non-existent resource should yield 404",
            "request": {
                "method": ctx.method,
                "path": ctx.path,
                "path_params": {p: "nonexistent-99999" for p in ctx.path_params},
            },
            "assertions": [{"type": "status", "expected": not_found}],
        })

    return tests


def _security_prober_tests(
    ctx: OperationContext, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    error_codes = [c for c in ctx.error_codes if c in (401, 403)] or [401, 403]
    req: dict[str, Any] = {
        "method": ctx.method,
        "path": ctx.path,
        "headers": {"Authorization": "Bearer cherenkov-invalid-probe"},
    }
    if ctx.path_params:
        req["path_params"] = {p: "1" for p in ctx.path_params}
    return [{
        "name": f"security_probe_{ctx.operation_id}",
        "description": (
            f"[SecurityProber] Invalid credentials should yield "
            f"{error_codes} for {ctx.operation_id}"
        ),
        "request": req,
        "assertions": [{"type": "status", "expected": error_codes}],
    }]


def _schema_pedant_tests(
    ctx: OperationContext, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    request = _base_request_from_spec(ctx, spec)

    # Test 1: assert every declared response field exists
    assertions1: list[dict[str, Any]] = [
        {"type": "status", "expected": ctx.success_codes},
        {"type": "header", "name": "Content-Type", "contains": "json"},
    ]
    for field in ctx.response_fields:
        assertions1.append({"type": "json_key", "field": field, "exists": True})

    tests = [{
        "name": f"schema_pedant_{ctx.operation_id}_fields",
        "description": (
            f"[SchemaPedant] All declared response fields present for "
            f"{ctx.operation_id}"
        ),
        "request": request,
        "assertions": assertions1,
    }]

    # Test 2: minimal status+header check (schema conformance baseline)
    tests.append({
        "name": f"schema_pedant_{ctx.operation_id}_conformance",
        "description": (
            f"[SchemaPedant] Status and Content-Type conformance for "
            f"{ctx.operation_id}"
        ),
        "request": dict(request),
        "assertions": [
            {"type": "status", "expected": ctx.success_codes},
            {"type": "header", "name": "Content-Type", "contains": "json"},
        ],
    })

    return tests


def _boundary_seeker_tests(
    ctx: OperationContext, spec: dict[str, Any]
) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    if ctx.has_request_body and ctx.required_body_fields:
        error_codes = [c for c in ctx.error_codes if 400 <= c < 500] or [400, 422]
        boundary_body = {f: "" for f in ctx.required_body_fields}
        req: dict[str, Any] = {
            "method": ctx.method,
            "path": ctx.path,
            "body": boundary_body,
        }
        if ctx.path_params:
            req["path_params"] = {p: "1" for p in ctx.path_params}
        tests.append({
            "name": f"boundary_{ctx.operation_id}_empty_fields",
            "description": (
                f"[BoundarySeeker] Empty required fields should trigger "
                f"validation error for {ctx.operation_id}"
            ),
            "request": req,
            "assertions": [{"type": "status", "expected": error_codes}],
        })

    elif ctx.path_params:
        expected = list(set(ctx.success_codes + [404, 400]))
        tests.append({
            "name": f"boundary_{ctx.operation_id}_zero_id",
            "description": (
                f"[BoundarySeeker] Zero/invalid path param for "
                f"{ctx.operation_id}"
            ),
            "request": {
                "method": ctx.method,
                "path": ctx.path,
                "path_params": {p: "0" for p in ctx.path_params},
            },
            "assertions": [{"type": "status", "expected": expected}],
        })

    return tests
