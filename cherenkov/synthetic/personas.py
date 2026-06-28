"""cherenkov/synthetic/personas.py — STORM-inspired tester personas + SpecContext.

Five built-in personas model different testing viewpoints, analogous to STORM's
perspective-guided questioning where each 'writer persona' pursues a different
angle of inquiry. Personas run in parallel inside SuiteEngine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Persona definition ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TesterPersona:
    name: str
    focus_area: str
    description: str
    target_success_codes: tuple[int, ...]
    target_error_codes: tuple[int, ...]
    assertion_types: tuple[str, ...]
    tests_per_op: int
    include_error_case: bool
    include_auth_probe: bool
    include_boundary: bool
    include_schema_fields: bool


HAPPY_PATH = TesterPersona(
    name="HappyPath",
    focus_area="2xx responses and basic response shape",
    description=(
        "Validates the successful request path: correct status, "
        "Content-Type header, and key response fields."
    ),
    target_success_codes=(200, 201, 204),
    target_error_codes=(),
    assertion_types=("status", "header", "json_key"),
    tests_per_op=1,
    include_error_case=False,
    include_auth_probe=False,
    include_boundary=False,
    include_schema_fields=True,
)

ERROR_PATH = TesterPersona(
    name="ErrorPath",
    focus_area="4xx error responses and validation",
    description=(
        "Probes error handling: omits required fields or sends malformed "
        "bodies to trigger 400/422/404."
    ),
    target_success_codes=(),
    target_error_codes=(400, 404, 422),
    assertion_types=("status",),
    tests_per_op=1,
    include_error_case=True,
    include_auth_probe=False,
    include_boundary=False,
    include_schema_fields=False,
)

SECURITY_PROBER = TesterPersona(
    name="SecurityProber",
    focus_area="authentication and authorization",
    description=(
        "Sends requests with invalid credentials to verify 401/403 are "
        "returned and secrets are not leaked."
    ),
    target_success_codes=(),
    target_error_codes=(401, 403),
    assertion_types=("status",),
    tests_per_op=1,
    include_error_case=True,
    include_auth_probe=True,
    include_boundary=False,
    include_schema_fields=False,
)

SCHEMA_PEDANT = TesterPersona(
    name="SchemaPedant",
    focus_area="response schema conformance",
    description=(
        "Asserts every declared response field is present in the body "
        "and Content-Type is correct."
    ),
    target_success_codes=(200, 201),
    target_error_codes=(),
    assertion_types=("status", "header", "json_key"),
    tests_per_op=2,
    include_error_case=False,
    include_auth_probe=False,
    include_boundary=False,
    include_schema_fields=True,
)

BOUNDARY_SEEKER = TesterPersona(
    name="BoundarySeeker",
    focus_area="edge cases and boundary values",
    description=(
        "Tests empty strings, zero/negative IDs, and missing optional fields "
        "to expose boundary-condition bugs."
    ),
    target_success_codes=(200,),
    target_error_codes=(400, 422),
    assertion_types=("status",),
    tests_per_op=1,
    include_error_case=True,
    include_auth_probe=False,
    include_boundary=True,
    include_schema_fields=False,
)

DEFAULT_PERSONAS: list[TesterPersona] = [
    HAPPY_PATH,
    ERROR_PATH,
    SECURITY_PROBER,
    SCHEMA_PEDANT,
    BOUNDARY_SEEKER,
]

PERSONA_BY_NAME: dict[str, TesterPersona] = {p.name: p for p in DEFAULT_PERSONAS}


# ── OperationContext — rich view of one spec operation ─────────────────────────

@dataclass
class OperationContext:
    """Extracted metadata for a single OpenAPI operation, consumed by all personas."""

    operation_id: str
    path: str
    method: str
    summary: str
    path_params: list[str]
    query_params: list[str]
    required_params: list[str]
    required_body_fields: list[str]
    has_request_body: bool
    success_codes: list[int]
    error_codes: list[int]
    response_fields: list[str]   # top-level keys in 200/201 JSON response schema
    auth_required: bool


# ── Spec context builder ───────────────────────────────────────────────────────

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete"})


def _resolve_ref(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/"):
            parts = ref.lstrip("#/").split("/")
            node: Any = spec
            for part in parts:
                node = node.get(part, {}) if isinstance(node, dict) else {}
            return node if isinstance(node, dict) else {}
    return schema


def _response_fields(responses: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    for code in ("200", "201"):
        resp = responses.get(code, {})
        content = resp.get("content", {})
        for media_type, media_obj in content.items():
            if "json" in media_type and isinstance(media_obj, dict):
                schema = _resolve_ref(media_obj.get("schema", {}), spec)
                keys = list(schema.get("properties", {}).keys())
                if keys:
                    return keys
    return []


def _required_body_fields(operation: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    req_body = operation.get("requestBody", {})
    if not req_body:
        return []
    for media_type, media_obj in req_body.get("content", {}).items():
        if "json" in media_type and isinstance(media_obj, dict):
            schema = _resolve_ref(media_obj.get("schema", {}), spec)
            return list(schema.get("required", []))
    return []


def build_spec_contexts(spec: dict[str, Any]) -> dict[str, OperationContext]:
    """Extract OperationContext for every operation in an OpenAPI spec."""
    contexts: dict[str, OperationContext] = {}
    global_security = bool(spec.get("security"))

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId", f"{method.upper()}:{path}")
            params = [p for p in operation.get("parameters", []) if isinstance(p, dict)]
            path_params  = [p["name"] for p in params if p.get("in") == "path"]
            query_params = [p["name"] for p in params if p.get("in") == "query"]
            required_params = [p["name"] for p in params if p.get("required", False)]

            responses = operation.get("responses", {})
            success_codes = sorted(
                int(c) for c in responses if str(c).startswith("2") and str(c).isdigit()
            )
            error_codes = sorted(
                int(c) for c in responses
                if str(c)[0] in ("4", "5") and str(c).isdigit()
            )

            op_security = operation.get("security")
            auth_required = global_security or (
                op_security is not None and op_security != []
            )

            contexts[op_id] = OperationContext(
                operation_id=op_id,
                path=path,
                method=method.upper(),
                summary=operation.get("summary", ""),
                path_params=path_params,
                query_params=query_params,
                required_params=required_params,
                required_body_fields=_required_body_fields(operation, spec),
                has_request_body=bool(operation.get("requestBody")),
                success_codes=success_codes or [200],
                error_codes=error_codes,
                response_fields=_response_fields(responses, spec),
                auth_required=auth_required,
            )

    return contexts
