"""
CHERENKOV Week 0 — Generate + Score
The "trigger." Slices a spec per endpoint, calls qwen2.5-coder:7b with the
Appendix A prompt, saves each test, and computes the MEANINGFUL ASSERTION RATE.

This is the heart of the validation gate. It is NOT pipeline infrastructure —
it's a measurement instrument. Building it does not violate Validate-First.

PREREQUISITES
  pip install requests
  Ollama running with:  ollama pull qwen2.5-coder:7b
  A spec to test (start with the Target API's spec):
    curl http://localhost:8000/openapi.json > target_spec.json

RUN
  python generate_and_score.py target_spec.json
  python generate_and_score.py target_spec.json --client-types ../stub/generated-types.ts

WHAT IT DOES NOT DO (on purpose)
  - No DB, no FastAPI, no Pydantic pipeline contracts. That's Week 2-3.
  - No real-server calls. Generation only. (Day 4 runs the tests separately.)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("GEN_MODEL", "qwen2.5-coder:7b")

# ── Appendix A: the STATIC system prompt (byte-identical every call = prefix cache) ──
SYSTEM_PROMPT = """You are an expert QA automation engineer writing Playwright API tests in TypeScript. You write ONE test per request.

STRICT RULES:
- Use ONLY the provided openapi-fetch client (client.GET/POST/PUT/DELETE). NEVER use fetch, axios, or Playwright's raw request context directly.
- Always import the client using: import { client } from '../client';
- Always import 'test' and 'expect' from '@playwright/test'.
- Every test MUST assert the SPECIFIC expected HTTP status code (e.g. expect(response.status).toBe(201)) — never a range like toBeLessThan(500).
- Every test MUST assert the response body SHAPE: the specific named properties that should exist and their types (e.g. expect(data).toHaveProperty('id')).
- Do NOT assert specific string values (the mock returns placeholder values).
- Use the test runner's assertion mechanisms (expect(...)). Do NOT throw custom errors (e.g. if (!res.ok) throw new Error()). The runner must see the assertion to report pass/fail correctly.
- Output ONLY the test code. No prose, no markdown fences, no explanation.

EXAMPLE OF CORRECT USAGE:
import { client } from '../client';
import { test, expect } from '@playwright/test';

test('create user happy path', async () => {
  const { data, response } = await client.POST('/users', {
    body: { email: 'test@example.com', password: 'password123' }
  });
  expect(response.status).toBe(201);
  expect(data).toHaveProperty('id');
});

test('get health happy path', async () => {
  const { data, response } = await client.GET('/health');
  expect(response.status).toBe(200);
  expect(data).toHaveProperty('status');
});
"""


def resolve_refs_depth(
    node, schemas: dict, resolved: dict, depth: int, max_depth: int
) -> None:
    if depth > max_depth:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if (
                k == "$ref"
                and isinstance(v, str)
                and v.startswith("#/components/schemas/")
            ):
                ref_name = v.split("/")[-1]
                if ref_name not in resolved and ref_name in schemas:
                    resolved[ref_name] = schemas[ref_name]
                    resolve_refs_depth(
                        schemas[ref_name], schemas, resolved, depth + 1, max_depth
                    )
            else:
                resolve_refs_depth(v, schemas, resolved, depth, max_depth)
    elif isinstance(node, list):
        for item in node:
            resolve_refs_depth(item, schemas, resolved, depth, max_depth)


def slice_spec(spec: dict) -> list[dict]:
    """Parse + slice per endpoint. A 7B model must NEVER see a whole spec.
    Each slice is self-contained: one path+method plus ONLY the schemas it references (depth 1)."""
    slices = []
    components = spec.get("components", {}).get("schemas", {})
    for path, methods in spec.get("paths", {}).items():
        for method, op in methods.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch"):
                continue

            # Resolve ONLY referenced schemas at depth 1 (immediate parents/body schemas)
            resolved_schemas = {}
            resolve_refs_depth(op, components, resolved_schemas, 1, 1)

            slices.append(
                {
                    "path": path,
                    "method": method.upper(),
                    "operation": op,
                    "schemas": resolved_schemas,
                }
            )
    return slices


def build_user_prompt(slice_: dict, client_types: str | None) -> str:
    return (
        "ENDPOINT SLICE (the only schema you need):\n"
        + json.dumps(
            {
                "path": slice_["path"],
                "method": slice_["method"],
                "operation": slice_["operation"],
                "schemas": slice_["schemas"],
            },
            indent=2,
        )
        + "\n\nSCENARIO:\n"
        + f"  endpoint: {slice_['method']} {slice_['path']}\n"
        + "  case_type: happy_path\n"
        + "\n=== CRITICAL INSTRUCTIONS AND EXAMPLE ===\n"
        + "You are writing a Playwright API test in TypeScript using openapi-fetch client.\n"
        + "STRICT RULES:\n"
        + "- Import the client exactly as: import { client } from '../client';\n"
        + "- Import 'test' and 'expect' from '@playwright/test'.\n"
        + "- Use ONLY the provided openapi-fetch client (e.g. const { data, response } = await client.POST('/path', { body: {...} })).\n"
        + "- Do NOT use standard Playwright 'request' directly. Do NOT use default imports for 'client'.\n"
        + "- Every test MUST assert the specific HTTP status code: expect(response.status).toBe(200) (status is a PROPERTY, not a function!).\n"
        + "- Every test MUST assert the response body shape: expect(data).toHaveProperty('id') (body shape is in the destructured 'data' object!).\n"
        + "- Output ONLY the TypeScript code block starting with the imports. No prose, no explanations, no markdown fences.\n"
        + "\nEXAMPLE OF CORRECT USAGE:\n"
        + "import { client } from '../client';\n"
        + "import { test, expect } from '@playwright/test';\n\n"
        + "test('get health happy path', async () => {\n"
        + "  const { data, response } = await client.GET('/health');\n"
        + "  expect(response.status).toBe(200);\n"
        + "  expect(data).toHaveProperty('status');\n"
        + "});\n\n"
        + "test('create user happy path', async () => {\n"
        + "  const { data, response } = await client.POST('/users', {\n"
        + "    body: { email: 'test@example.com', password: 'password123' }\n"
        + "  });\n"
        + "  expect(response.status).toBe(201);\n"
        + "  expect(data).toHaveProperty('id');\n"
        + "});\n\n"
        + "Write the Playwright API test adhering to these critical rules now."
    )


def call_ollama(user_prompt: str) -> str:
    """Single generate call. We put the system prompt directly inside the user prompt for 100% reliability."""
    combined_prompt = f"{SYSTEM_PROMPT}\n\n=== TASK ===\n{user_prompt}"
    resp = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": combined_prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        },
        timeout=300,
    )
    resp.raise_for_status()
    text = resp.json().get("response", "")
    # strip any stray markdown fences the model adds despite instructions
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


# ── Day 2 scoring: the four booleans that define a MEANINGFUL test ──
def score_test(code: str) -> dict:
    uses_client = bool(re.search(r"\bclient\.(GET|POST|PUT|DELETE|PATCH)\b", code))
    forbidden = bool(re.search(r"\b(fetch|axios)\b|\.request\b|throw new Error", code))
    specific_status = bool(
        re.search(r"\.status\)?\s*\)?\s*\.toBe\(\s*\d{3}\s*\)", code)
    ) or bool(re.search(r"toBe\(\s*(200|201|204|400|401|404|422|500)\s*\)", code))
    body_shape = bool(re.search(r"toHaveProperty\(|typeof\s", code))
    # "would fail on wrong output" ≈ asserts a specific status AND a body shape
    would_fail_on_wrong = specific_status and body_shape
    compiles_likely = "import" in code and "test(" in code and not forbidden

    return {
        "uses_openapi_fetch_client": uses_client,
        "no_forbidden_http": not forbidden,
        "asserts_specific_status": specific_status,
        "asserts_body_shape": body_shape,
        "would_fail_on_wrong_output": would_fail_on_wrong,
        "compiles_likely": compiles_likely,
        # MEANINGFUL = the three that matter (D1/D8 compliant + real assertions)
        "meaningful": uses_client and would_fail_on_wrong and not forbidden,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="path to OpenAPI json (e.g. target_spec.json)")
    ap.add_argument(
        "--client-types", help="path to generated-types.ts to embed in prompt"
    )
    ap.add_argument(
        "--out", default="generated_tests", help="output dir for .spec.ts files"
    )
    ap.add_argument(
        "--limit", type=int, help="limit the number of endpoints to generate tests for"
    )
    ap.add_argument(
        "--filter", help="filter endpoints by path keyword (e.g., v1_customers)"
    )
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).read_text())
    client_types = Path(args.client_types).read_text() if args.client_types else None
    out = Path(args.out)
    out.mkdir(exist_ok=True)

    slices = slice_spec(spec)
    total_raw = len(slices)

    if args.filter:
        slices = [
            s
            for s in slices
            if args.filter in s["path"] or args.filter in s["method"].lower()
        ]
        print(
            f"Filtered to {len(slices)} endpoint(s) out of {total_raw} using filter '{args.filter}'"
        )
    else:
        print(f"Sliced {len(slices)} endpoint(s) from {args.spec}")

    if args.limit and args.limit < len(slices):
        slices = slices[: args.limit]
        print(f"Limited to first {args.limit} endpoint(s)")

    print("")

    results = []
    for i, sl in enumerate(slices, 1):
        name = f"{sl['method']}_{sl['path'].strip('/').replace('/', '_').replace('{','').replace('}','') or 'root'}"
        print(
            f"[{i}/{len(slices)}] generating {sl['method']} {sl['path']} ...",
            flush=True,
        )
        t0 = time.time()
        try:
            code = call_ollama(build_user_prompt(sl, client_types))
        except Exception as e:
            print(f"    ERROR: {e}")
            continue
        dt = time.time() - t0
        (out / f"{name}.spec.ts").write_text(code)
        sc = score_test(code)
        sc["_name"] = name
        sc["_seconds"] = round(dt, 1)
        results.append(sc)
        flag = "OK " if sc["meaningful"] else "weak"
        print(
            f"    {flag} ({dt:.1f}s)  status={sc['asserts_specific_status']} "
            f"shape={sc['asserts_body_shape']} client={sc['uses_openapi_fetch_client']}"
        )

    if not results:
        print("\nNo tests generated. Check your filters or limits.")
        sys.exit(1)

    meaningful = sum(1 for r in results if r["meaningful"])
    rate = round(100 * meaningful / len(results))
    print("\n" + "=" * 52)
    print(f"  MEANINGFUL ASSERTION RATE: {rate}%  ({meaningful}/{len(results)})")
    print("=" * 52)
    print("  GATE: proceed if > 60% AND Day-4 bug is caught AND a QA lead approves.")
    print("        pivot if shallow; stop if < 30%.")
    (out / "_scores.json").write_text(json.dumps(results, indent=2))
    print(f"\n  Per-test scores written to {out / '_scores.json'}")


if __name__ == "__main__":
    main()
