"""Emit a chained journey as a standalone Playwright test.

The eject invariant applies here exactly as it does to flat scenarios: the
output is ordinary Playwright that runs with no part of this project
installed. Nothing in the generated file may reference the tool that wrote it.

The generated test also cleans up after itself. An ejected suite runs on
somebody's CI against somebody's API, and a test that leaks a resource per run
is a bug we shipped into their environment.
"""
from __future__ import annotations

import json

from cherenkov.core.contracts import ChainStep, JourneyScenario


def _js_identifier(name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in name)
    return f"_{cleaned}" if cleaned[:1].isdigit() else cleaned


def _pointer_access(pointer: str) -> str:
    """JSON pointer to a JS accessor chain: "/data/0/id" -> ['data'][0]['id']."""
    parts = []
    for raw in pointer.lstrip("/").split("/"):
        if not raw:
            continue
        token = raw.replace("~1", "/").replace("~0", "~")
        parts.append(f"[{token}]" if token.isdigit() else f"[{json.dumps(token)}]")
    return "".join(parts)


def _template_path(step: ChainStep) -> str:
    """`/pet/{petId}` -> `` `/pet/${petId}` `` using captured variables."""
    path = step.endpoint
    for param in step.uses:
        path = path.replace(f"{{{param}}}", f"${{{_js_identifier(param)}}}")
    return f"`{path}`"


def _request_call(step: ChainStep, body: object | None, indent: str) -> str:
    method = step.method.lower()
    target = _template_path(step) if step.uses else json.dumps(step.endpoint)
    if body is not None and method in ("post", "put", "patch"):
        payload = json.dumps(body, indent=2).replace("\n", f"\n{indent}")
        return f"request.{method}({target}, {{ data: {payload} }})"
    return f"request.{method}({target})"


def generate_chain_test(
    chain: JourneyScenario,
    bodies: dict[str, object] | None = None,
) -> str:
    """Render one chain as a single Playwright test.

    ``bodies`` maps step id to a request payload taken from the spec.
    """
    bodies = bodies or {}
    has_delete = any(s.method.upper() == "DELETE" for s in chain.steps)

    captured = [
        _js_identifier(b.name) for s in chain.steps for b in s.captures
    ]
    cleanup_var = next(
        (_js_identifier(b.name)
         for s in chain.steps if s.creates_resource for b in s.captures),
        None,
    )
    cleanup_path = next((_template_path(s) for s in chain.steps if s.uses), None)
    # Only needed when the chain does not already delete what it made.
    needs_cleanup = bool(cleanup_var and cleanup_path and not has_delete)

    indent = "    " if needs_cleanup else "  "
    body: list[str] = []
    for step in chain.steps:
        response_var = _js_identifier(f"{step.id}Res")
        call = _request_call(step, bodies.get(step.id), indent)
        body.append(f"{indent}// {step.id}")
        body.append(f"{indent}const {response_var} = await {call};")
        body.append(f"{indent}expect({response_var}.status()).toBe({step.expected_status});")
        for binding in step.captures:
            var = _js_identifier(binding.name)
            body.append(
                f"{indent}{var} = (await {response_var}.json())"
                f"{_pointer_access(binding.pointer)};"
            )
            body.append(
                f"{indent}expect({var}, "
                f"'server must return {binding.name} to continue').toBeDefined();"
            )
        body.append("")

    lines = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"// {chain.label}: a stateful sequence. Each step uses values the",
        "// previous step's response actually returned, so no identifier here",
        "// is invented.",
        f"test({json.dumps(chain.label)}, async ({{ request }}) => {{",
    ]
    if captured:
        # Declared in the function scope, not inside try: a const declared in
        # the try block is not visible to finally, so the cleanup below would
        # silently never run.
        lines.append(f"  let {', '.join(dict.fromkeys(captured))};")
        lines.append("")

    if needs_cleanup:
        lines.append("  try {")
        lines.extend(body)
        lines.append("  } finally {")
        lines.append("    // Remove what this test created, pass or fail.")
        lines.append(f"    if ({cleanup_var} !== undefined) {{")
        lines.append(f"      await request.delete({cleanup_path});")
        lines.append("    }")
        lines.append("  }")
    else:
        lines.extend(body)

    lines.append("});")
    return "\n".join(lines).rstrip() + "\n"


def chain_filename(chain: JourneyScenario) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in chain.id)
    return f"journey_{safe}.spec.ts"
