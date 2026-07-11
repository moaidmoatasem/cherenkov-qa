"""
CHERENKOV divergence/probe_planner.py — spec-derived probe planning (R1).

Synthesizes endpoint probes and offline DivergenceHypothesis objects
mechanically from any loaded OpenAPI spec — no LLM required. This replaces
the hardcoded Petstore PROOF_RUN_PROBES whenever the user supplies a real
spec, making `cherenkov verify --spec <theirs>` probe *their* endpoints.

V1 emits status-code oracles only, because the Witness executes hypotheses
by parsing natural-language repro_steps ("Send GET /path", "Expect 400")
and extracts expected values as status codes. Response-schema and header
oracles need Witness extensions and are deliberately deferred.

Heuristics, priority-ordered per endpoint:
  1. required-field omission  (requestBody required props → expect 4xx)
  2. enum violation           (query param enum → invalid value → 4xx)
  3. documented error code    (integer path param + documented 400/404)
  4. happy path               (GET without required params → success code)
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from cherenkov.core.contracts import (
    DivergenceClass,
    DivergenceHypothesis,
    Severity,
)

_HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head"}

# Status codes the Witness's repro-step parser recognises.
_PARSEABLE_CODES = {200, 201, 204, 400, 401, 403, 404, 409, 422, 500}

_INVALID_ENUM_VALUE = "INVALID_VALUE_XYZ"


# ── spec helpers ─────────────────────────────────────────────────────────────


def _resolve_ref(node: Any, spec: dict[str, Any]) -> Any:
    """Depth-1 $ref resolution against #/components/... (house convention)."""
    if isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if isinstance(ref, str) and ref.startswith("#/"):
            target: Any = spec
            for part in ref[2:].split("/"):
                if not isinstance(target, dict) or part not in target:
                    return node
                target = target[part]
            return target
    return node


def _sample_value(prop_schema: dict[str, Any], name: str = "") -> Any:
    """Minimal plausible sample value for a property schema (emitter pattern)."""
    if "example" in prop_schema:
        return prop_schema["example"]
    if "default" in prop_schema:
        return prop_schema["default"]
    enum = prop_schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    t = prop_schema.get("type", "string")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "integer":
        return 1
    if t == "number":
        return 1.0
    if t == "boolean":
        return True
    if t == "array":
        items = prop_schema.get("items", {})
        return [_sample_value(items)] if items else []
    if t == "object":
        return {}
    if "email" in name:
        return "probe@cherenkov.invalid"
    return f"probe_{name or 'value'}"


def _sample_body(schema: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Build a full sample request body containing every required property."""
    schema = _resolve_ref(schema, spec)
    body: dict[str, Any] = {}
    props = schema.get("properties", {})
    for prop_name, prop_schema in props.items():
        body[prop_name] = _sample_value(_resolve_ref(prop_schema, spec), prop_name)
    return body


def _request_schema(operation: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any] | None:
    content = operation.get("requestBody", {})
    content = _resolve_ref(content, spec).get("content", {})
    media = content.get("application/json")
    if not isinstance(media, dict):
        return None
    schema = _resolve_ref(media.get("schema", {}), spec)
    return schema if isinstance(schema, dict) else None


def _documented_codes(operation: dict[str, Any]) -> set[int]:
    codes: set[int] = set()
    for code_str in operation.get("responses", {}):
        try:
            codes.add(int(code_str))
        except (TypeError, ValueError):
            continue
    return codes


def _expected_4xx(operation: dict[str, Any], default: int = 422) -> int:
    """Pick the documented client-error code the Witness can parse, else default."""
    for candidate in (422, 400, 409, 404, 401, 403):
        if candidate in _documented_codes(operation):
            return candidate
    return default


def _success_code(operation: dict[str, Any]) -> int | None:
    for candidate in (200, 201, 204):
        if candidate in _documented_codes(operation):
            return candidate
    return None


def _path_with_samples(path: str, operation: dict[str, Any], spec: dict[str, Any]) -> str | None:
    """Substitute sample values for path params; None if any param is unfillable."""
    if "{" not in path:
        return path
    filled = path
    for param in operation.get("parameters", []):
        param = _resolve_ref(param, spec)
        if param.get("in") != "path":
            continue
        schema = _resolve_ref(param.get("schema", {}), spec)
        value = _sample_value(schema, param.get("name", ""))
        filled = filled.replace(f'{{{param.get("name", "")!s}}}', str(value))
    return None if "{" in filled else filled


def _required_query_params(operation: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for param in operation.get("parameters", []):
        param = _resolve_ref(param, spec)
        if param.get("in") == "query" and param.get("required"):
            out.append(param)
    return out


# ── hypothesis synthesis ─────────────────────────────────────────────────────


def spec_hypotheses(
    endpoint: str,
    method: str,
    operation: dict[str, Any],
    spec: dict[str, Any],
) -> list[DivergenceHypothesis]:
    """Mechanically derive offline hypotheses for one operation from the spec."""
    hypotheses: list[DivergenceHypothesis] = []
    method = method.upper()

    # 1. required-field omission (bodies)
    if method in ("POST", "PUT", "PATCH"):
        schema = _request_schema(operation, spec)
        required = (schema or {}).get("required") or []
        if schema and required:
            omitted = required[0]
            body = _sample_body(schema, spec)
            body.pop(omitted, None)
            expect = _expected_4xx(operation)
            hypotheses.append(
                DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D1_SPEC_CODE,
                    claim_a=f"spec: '{omitted}' is a required field for {method} {endpoint}; omitting it → {expect}",
                    claim_b="implementation accepts the request without the required field",
                    predicted_evidence=f"{method} {endpoint} without '{omitted}' returns 2xx",
                    severity=Severity.HIGH,
                    endpoint=f"{method} {endpoint}",
                    repro_steps=[
                        f"Send {method} {endpoint} with body {json.dumps(body)}",
                        f"Expect {expect} because '{omitted}' is required per schema",
                    ],
                )
            )

    # 2. enum violation (query params)
    for param in operation.get("parameters", []) or []:
        param = _resolve_ref(param, spec)
        if param.get("in") != "query":
            continue
        schema = _resolve_ref(param.get("schema", {}), spec)
        if not schema.get("enum"):
            continue
        name = param.get("name", "")
        probe_path = _path_with_samples(endpoint, operation, spec)
        if probe_path is None:
            continue
        expect = _expected_4xx(operation, default=400)
        hypotheses.append(
            DivergenceHypothesis(
                id=str(uuid.uuid4()),
                divergence_class=DivergenceClass.D1_SPEC_CODE,
                claim_a=f"spec: '{name}' query param is enum({'|'.join(map(str, schema['enum']))}); invalid value → {expect}",
                claim_b="implementation accepts arbitrary values for the enum param",
                predicted_evidence=f"{method} {probe_path}?{name}={_INVALID_ENUM_VALUE} returns 2xx",
                severity=Severity.MEDIUM,
                endpoint=f"{method} {endpoint}",
                repro_steps=[
                    f"Send {method} {probe_path}?{name}={_INVALID_ENUM_VALUE}",
                    f"Expect {expect} response per spec enum constraint",
                ],
            )
        )
        break  # one enum probe per operation is enough

    # 3. documented error code for invalid integer path param
    if "{" in endpoint:
        for param in operation.get("parameters", []) or []:
            param = _resolve_ref(param, spec)
            if param.get("in") != "path":
                continue
            schema = _resolve_ref(param.get("schema", {}), spec)
            if schema.get("type") != "integer":
                continue
            documented = _documented_codes(operation) & {400, 404}
            if not documented:
                continue
            expect = min(documented)
            name = param.get("name", "")
            probe_path = endpoint.replace(f"{{{name}}}", "0")
            if "{" in probe_path:
                continue
            hypotheses.append(
                DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D5_SPEC_PROD,
                    claim_a=f"spec: {method} {endpoint} documents {expect} for an invalid '{name}'",
                    claim_b=f"implementation returns a different status for {name}=0",
                    predicted_evidence=f"{method} {probe_path} does not return {expect}",
                    severity=Severity.LOW,
                    endpoint=f"{method} {endpoint}",
                    repro_steps=[
                        f"Send {method} {probe_path}",
                        f"Expect {expect} per spec for invalid {name}",
                    ],
                )
            )
            break

    # 4. happy path (GET without required query params)
    if method == "GET" and not _required_query_params(operation, spec):
        success = _success_code(operation)
        probe_path = _path_with_samples(endpoint, operation, spec)
        if success is not None and probe_path is not None and "{" not in endpoint:
            hypotheses.append(
                DivergenceHypothesis(
                    id=str(uuid.uuid4()),
                    divergence_class=DivergenceClass.D5_SPEC_PROD,
                    claim_a=f"spec: {method} {endpoint} responds {success}",
                    claim_b="implementation returns a non-documented status (5xx/404 drift)",
                    predicted_evidence=f"{method} {probe_path} returns a status other than {success}",
                    severity=Severity.MEDIUM,
                    endpoint=f"{method} {endpoint}",
                    repro_steps=[
                        f"Send {method} {probe_path}",
                        f"Expect {success} response per spec",
                    ],
                )
            )

    # Keep only hypotheses whose expected code the Witness can parse.
    return [
        h
        for h in hypotheses
        if any(str(c) in h.repro_steps[-1] for c in _PARSEABLE_CODES)
    ]


# ── probe planning ───────────────────────────────────────────────────────────


def plan_probes(
    spec: dict[str, Any], max_probes: int = 40, include_bare: bool = False
) -> list[tuple[str, str, dict[str, Any], str]]:
    """Enumerate (endpoint, method, spec_fragment, context) probes from *spec*.

    Same tuple shape as proof_run.PROOF_RUN_PROBES. By default only
    operations that yield at least one offline hypothesis are included, so
    every probe is actionable in offline mode. With include_bare=True (LLM
    mode) every operation is probed — the Skeptic can hypothesise beyond
    the mechanical heuristics.
    """
    probes: list[tuple[str, str, dict[str, Any], str]] = []
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in _HTTP_METHODS or not isinstance(operation, dict):
                continue
            if not include_bare and not spec_hypotheses(path, method, operation, spec):
                continue
            summary = operation.get("summary") or operation.get("operationId") or ""
            context = (
                f"{method.upper()} {path}: {summary}. "
                f"Documented responses: {', '.join(sorted(operation.get('responses', {})))}."
            )
            probes.append((path, method.upper(), operation, context))
            if len(probes) >= max_probes:
                return probes
    return probes
