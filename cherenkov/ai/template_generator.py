"""
cherenkov/ai/template_generator.py — deterministic Playwright TypeScript test generator.

Produces real, runnable tests that pass all 6 ReviewStage gates without requiring an LLM.
Used as the fallback when Ollama is unavailable.
"""
from __future__ import annotations

import json
import re
from typing import Any


def _method_call(method: str, path: str) -> str:
    m = method.upper()
    if m in ("GET", "DELETE"):
        return f"client.{m}('{path}')"
    return f"client.{m}('{path}', {{ body: _body }})"


def _infer_body(operation: dict[str, Any], schemas: dict[str, Any], case_type: str, mutation_id: str | None) -> dict | None:
    """Build a minimal request body from the operation schema."""
    rb = operation.get("requestBody", {})
    content = rb.get("content", {})
    schema_ref = (
        content.get("application/json", {}).get("schema")
        or content.get("*/*", {}).get("schema")
    )
    if not schema_ref:
        return None

    # Resolve $ref
    ref = schema_ref.get("$ref", "")
    if ref:
        name = ref.split("/")[-1]
        schema_ref = schemas.get(name, schema_ref)

    props = schema_ref.get("properties", {})
    required = schema_ref.get("required", [])
    body: dict = {}

    # For validation mutations, deliberately omit a required field or send bad values
    omit_field = None
    if case_type == "validation" and mutation_id:
        for fld in required:
            if fld in (mutation_id or ""):
                omit_field = fld
                break
        if not omit_field and required:
            omit_field = required[0]

    for key, info in props.items():
        if key == omit_field:
            continue
        t = info.get("type", "string")
        if isinstance(t, list):
            t = next((x for x in t if x != "null"), "string")
        if t == "integer":
            val = 999 if (case_type == "security" and mutation_id and "boundary" in mutation_id) else 1
        elif t == "boolean":
            val = True
        elif t == "array":
            val = []
        elif t == "object":
            val = {}
        else:
            if "email" in key:
                val = "test@cherenkov.dev"
            elif "password" in key or "secret" in key:
                val = "Password123!"
            elif "url" in key:
                val = "https://example.com"
            elif "name" in key:
                val = "Cherenkov Test"
            elif key in ("status",):
                val = "available"
            else:
                val = f"test_{key}"
        body[key] = val

    return body or None


def _infer_response_property(operation: dict[str, Any], schemas: dict[str, Any], expected_status: int) -> str | None:
    """Return a top-level property name we can assert on from the response body."""
    responses = operation.get("responses", {})
    resp = responses.get(str(expected_status)) or responses.get("200") or responses.get("201")
    if not resp:
        return None
    content = resp.get("content", {})
    schema = (
        content.get("application/json", {}).get("schema")
        or content.get("*/*", {}).get("schema")
    )
    if not schema:
        return None
    ref = schema.get("$ref", "")
    if ref:
        name = ref.split("/")[-1]
        schema = schemas.get(name, schema)
    props = schema.get("properties", {})
    for candidate in ("id", "status", "name", "email", "message", "result", "data"):
        if candidate in props:
            return candidate
    if props:
        return next(iter(props))
    return None


def _path_with_example_param(path: str, operation: dict[str, Any], mutation_id: str | None) -> str:
    """Replace {param} placeholders with realistic test values."""
    params = operation.get("parameters", [])
    result = path
    for param in params:
        if param.get("in") != "path":
            continue
        name = param.get("name", "")
        schema = param.get("schema", {})
        t = schema.get("type", "string")
        if t == "integer":
            val = "0" if (mutation_id and "invalid" in mutation_id) else "1"
        else:
            val = "invalid-id" if (mutation_id and "invalid" in mutation_id) else "test-id"
        result = result.replace("{" + name + "}", val)
    return result


def generate_test(
    path: str,
    method: str,
    operation: dict[str, Any],
    schemas: dict[str, Any],
    scenario: Any,
    instruction: str = "",
) -> str:
    """
    Build a Playwright TypeScript test that passes all 6 ReviewStage gates:
      1. syntax    — no markdown fences, non-empty
      2. structure — imports from '../client' and '@playwright/test'
      3. ast       — uses client.METHOD(), no raw fetch/axios
      4. assertions— toBe(status) + toHaveProperty(field)
      5. tsc       — valid TypeScript
      6. prism     — best-effort (gate skipped when Prism unavailable)
    """
    mutation_id = getattr(scenario, "mutation_id", None) or ""
    case_type = getattr(scenario, "case_type", "happy_path")
    expected_status = getattr(scenario, "expected_status", 200)

    resolved_path = _path_with_example_param(path, operation, mutation_id)
    body = _infer_body(operation, schemas, case_type, mutation_id)
    resp_prop = _infer_response_property(operation, schemas, expected_status)

    test_name = f"{method.lower()} {path} {case_type} {mutation_id or ''}".strip().replace("  ", " ")

    lines: list[str] = [
        "import { client } from '../client';",
        "import { test, expect } from '@playwright/test';",
        "",
    ]

    # Build body variable if needed
    needs_body = method.upper() not in ("GET", "DELETE", "HEAD") and body is not None
    if needs_body:
        lines.append(f"const _body = {json.dumps(body, indent=2)};")
        lines.append("")

    lines.append(f"test('{test_name}', async () => {{")

    call = _method_call(method, resolved_path)
    lines.append(f"  const {{ data, response }} = await {call};")
    lines.append(f"  expect(response.status).toBe({expected_status});")

    # Body assertion — only for success responses that return data
    if resp_prop and expected_status in (200, 201, 202):
        lines.append(f"  expect(data).toHaveProperty('{resp_prop}');")
    elif expected_status >= 400:
        # Error responses: check that data exists (may be null on 4xx)
        lines.append("  expect(response.status).toBeGreaterThanOrEqual(400);")
    else:
        lines.append("  expect(data).toBeDefined();")

    lines.append("});")
    lines.append("")

    return "\n".join(lines)
