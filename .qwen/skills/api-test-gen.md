---
name: api-test-gen
description: Generate API test skeletons from an OpenAPI spec fragment using CHERENKOV's conformance patterns. Mirrors the CHERENKOV skills/api-test-generation.md workflow but adapted for Qwen Code.
triggers:
  - "generate test"
  - "write test for"
  - "api test"
  - "test skeleton"
---

# Skill: api-test-gen

## Purpose
Generate spec-derived, portable API test skeletons for CHERENKOV conformance testing.

## Prerequisites
1. The CHERENKOV MCP server must be running (`cherenkov.py mcp serve`)
2. An OpenAPI spec must be loaded or accessible at `.cherenkov/spec.json`

## Workflow

### Step 1 — Fetch spec-derived expected values
```
[MCP] get_last_report → extract endpoint + expected status codes
[MCP] get_tightening_suggestions endpoint=<endpoint> method=<method> → get edge cases
```

**NEVER hardcode status codes.** Always derive from the spec.

### Step 2 — Generate the test skeleton
Generate a standalone Python test file following this template:

```python
"""
Test: <endpoint> <method>
Spec source: <spec_url or spec_file>
Generated: <date>
D7: suggest-only — review before applying
"""
import pytest
import httpx

BASE_URL = "<target_url>"  # Override via env var TARGET_URL

class Test<EndpointName>:
    def test_<scenario>(self, base_url=BASE_URL):
        """<description from spec>"""
        resp = httpx.get(f"{base_url}<path>")
        assert resp.status_code == <spec_derived_status>  # from OpenAPI spec
        # Additional assertions from spec schema
```

### Step 3 — Eject check
Verify the generated test has NO `from cherenkov import` statements.  
Run: `python3 -c "import ast; ast.parse(open('<test_file>').read()); print('OK')"`

### Step 4 — Output as suggestion
Output the generated file as a diff block. **Do NOT auto-apply.** (D7 invariant)

## Invariants
- No hardcoded status codes
- No CHERENKOV imports in generated tests
- Output as suggestion only — do not apply autonomously

## References
- `skills/api-test-generation.md` — source CHERENKOV skill
- MCP tools: `get_last_report`, `get_tightening_suggestions`, `chat_run_test`
- `.qwen/memory/invariants.md` — D7 details
