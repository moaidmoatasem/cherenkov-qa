---
name: api-test-gen
description: Generate spec-derived API test skeletons for CHERENKOV conformance.
triggers:
  - "generate test"
  - "write test for"
  - "api test"
  - "test skeleton"
---

# Skill: api-test-gen

## Workflow

### Step 1 — Fetch spec-derived expected values
```
[MCP] get_last_report → extract endpoint + expected status codes
[MCP] get_tightening_suggestions endpoint=<endpoint> method=<method> → edge cases
```

**Never hardcode status codes.** Derive from the spec.

### Step 2 — Generate test skeleton
Follow the template in `.qwen/skills/references/api-test-template.md`.

### Step 3 — Output as suggestion
Diff block only. Do NOT auto-apply. (D7 invariant)

## References
- Template + eject check: `.qwen/skills/references/api-test-template.md`
- MCP tools: `get_last_report`, `get_tightening_suggestions`, `chat_run_test`
- Invariants: `.qwen/memory/invariants.md`
