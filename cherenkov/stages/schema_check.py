"""
cherenkov/stages/schema_check.py — Standalone response schema validation.

Validates actual HTTP responses against the JSON Schema embedded in an
OpenAPI spec without requiring a running Prism server.

Core function:
    check_response(response_body, spec, endpoint, method, status_code)
        → SchemaCheckResult

Also provides a batch checker:
    SchemaCheckStage.run(reports, spec_path) → list[SchemaCheckResult]

SchemaCheckResult carries:
    ok          — True if body matches spec schema
    endpoint    — "GET /pets"
    status_code — actual HTTP status code
    issues      — list of SchemaViolation (path, message, schema_path)
    skipped     — True when spec has no schema for this response (not a failure)

Usage in tests/CI:
    from cherenkov.stages.schema_check import check_response
    import yaml, json

    spec = yaml.safe_load(open("openapi.yaml"))
    body = requests.get("http://api/pets").json()
    result = check_response(body, spec, "/pets", "GET", 200)
    assert result.ok, result.issues
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaViolation:
    path: str        # JSONPath-style e.g. "$.items[0].id"
    message: str
    schema_path: str = ""


@dataclass
class SchemaCheckResult:
    ok: bool
    endpoint: str
    method: str
    status_code: int
    issues: list[SchemaViolation] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def summary(self) -> str:
        if self.skipped:
            return f"SKIP  {self.method} {self.endpoint} → {self.skip_reason}"
        status = "PASS" if self.ok else "FAIL"
        detail = f" ({len(self.issues)} violation(s))" if not self.ok else ""
        return f"{status}  {self.method} {self.endpoint} [{self.status_code}]{detail}"


def _resolve_ref(ref: str, spec: dict) -> dict | None:
    """Resolve a local $ref (#/components/schemas/...) inside a spec dict."""
    if not ref.startswith("#/"):
        return None  # external refs unsupported
    parts = ref[2:].split("/")
    node: Any = spec
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) else None


def _deref(schema: dict, spec: dict, _depth: int = 0) -> dict:
    """Recursively inline all local $refs in *schema*. Depth-limited to avoid cycles."""
    if _depth > 20:
        return schema
    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], spec)
        if resolved:
            return _deref(resolved, spec, _depth + 1)
        return schema  # unresolvable — return as-is
    if isinstance(schema, dict):
        return {k: _deref(v, spec, _depth + 1) if isinstance(v, dict) else v
                for k, v in schema.items()}
    return schema


def _extract_response_schema(
    spec: dict, endpoint: str, method: str, status_code: int
) -> dict | None:
    """
    Pull the JSON schema for (endpoint, method, status_code) out of the spec.
    Returns None when the spec has no schema for this combination.
    """
    paths = spec.get("paths", {})
    path_item = paths.get(endpoint)
    if path_item is None:
        # Try matching with path template parameters e.g. /pets/{petId}
        for path_key, path_val in paths.items():
            # Replace {param} placeholders first, then escape the static parts
            parts = re.split(r"(\{[^}]+\})", path_key)
            escaped = "".join(
                "[^/]+" if p.startswith("{") else re.escape(p) for p in parts
            )
            pattern = escaped + "$"
            if re.match(pattern, endpoint):
                path_item = path_val
                break
        if path_item is None:
            return None

    op = path_item.get(method.lower())
    if not op or not isinstance(op, dict):
        return None

    responses = op.get("responses", {})

    # Try exact status first, then wildcard (e.g. "2XX")
    resp = responses.get(str(status_code))
    if resp is None:
        wildcard = f"{str(status_code)[0]}XX"
        resp = responses.get(wildcard)
    if resp is None:
        return None

    # Deref response object itself
    if "$ref" in resp:
        resp = _resolve_ref(resp["$ref"], spec) or resp

    content = resp.get("content", {})
    json_content = content.get("application/json") or content.get("application/json; charset=utf-8")
    if json_content is None:
        # Fall back to first content type
        for ct_val in content.values():
            json_content = ct_val
            break
    if json_content is None:
        return None

    schema = json_content.get("schema")
    if not schema:
        return None

    return _deref(schema, spec)


def check_response(
    response_body: Any,
    spec: dict,
    endpoint: str,
    method: str,
    status_code: int,
) -> SchemaCheckResult:
    """
    Validate *response_body* against the JSON Schema declared in *spec*
    for the given endpoint/method/status combination.

    Args:
        response_body: Parsed JSON response (dict, list, or scalar).
        spec: Parsed OpenAPI spec dict.
        endpoint: Path string e.g. "/pets" or "/pets/123".
        method: HTTP method string e.g. "GET".
        status_code: Actual HTTP status code returned by the server.

    Returns:
        SchemaCheckResult with ok=True on pass, ok=False on violation,
        skipped=True when the spec has no schema to check against.
    """
    schema = _extract_response_schema(spec, endpoint, method, status_code)

    if schema is None:
        return SchemaCheckResult(
            ok=True,
            endpoint=endpoint,
            method=method.upper(),
            status_code=status_code,
            skipped=True,
            skip_reason="no schema in spec for this response",
        )

    try:
        import jsonschema
        from jsonschema import Draft7Validator

        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(response_body), key=lambda e: e.path)

        issues = [
            SchemaViolation(
                path="$." + ".".join(str(p) for p in err.absolute_path) if err.absolute_path else "$",
                message=err.message,
                schema_path=".".join(str(p) for p in err.absolute_schema_path),
            )
            for err in errors
        ]

        return SchemaCheckResult(
            ok=not issues,
            endpoint=endpoint,
            method=method.upper(),
            status_code=status_code,
            issues=issues,
        )

    except ImportError:
        return SchemaCheckResult(
            ok=True,
            endpoint=endpoint,
            method=method.upper(),
            status_code=status_code,
            skipped=True,
            skip_reason="jsonschema not installed — pip install jsonschema",
        )


class SchemaCheckStage:
    """Batch schema checker: runs check_response for each report in a validate_suite result."""

    def __init__(self, spec: dict):
        self._spec = spec

    @classmethod
    def from_file(cls, spec_path: str) -> "SchemaCheckStage":
        from pathlib import Path

        text = Path(spec_path).read_text(encoding="utf-8")
        suffix = Path(spec_path).suffix.lower()
        if suffix == ".json":
            import json
            spec = json.loads(text)
        else:
            import yaml
            spec = yaml.safe_load(text)
        return cls(spec)

    def check(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_body: Any,
    ) -> SchemaCheckResult:
        return check_response(response_body, self._spec, endpoint, method, status_code)

    def check_many(
        self,
        entries: list[dict],
    ) -> list[SchemaCheckResult]:
        """
        Validate multiple responses at once.

        Each entry dict: {endpoint, method, status_code, response_body}
        """
        return [
            self.check(
                endpoint=e["endpoint"],
                method=e["method"],
                status_code=e["status_code"],
                response_body=e.get("response_body"),
            )
            for e in entries
        ]
