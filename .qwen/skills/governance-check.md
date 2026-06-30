---
name: governance-check
description: Snapshot governance status — validation gate, drift findings, HITL queue, spec tightening.
triggers:
  - "governance"
  - "compliance check"
  - "spec check"
  - "certification"
  - "governance-check"
---

# Skill: governance-check

## Workflow

```
[MCP] validate_run_gate               → gate status (PASS/FAIL/WARN)
[MCP] list_drift_findings severity=high
[MCP] list_drift_findings severity=medium
[MCP] hitl_list status=pending        → pending review items
[MCP] get_last_report                 → full conformance report
```

Produce a structured governance report. Use the report template in
`.qwen/skills/references/governance-report-template.md`.

**Suggest-only — no auto-remediation (D7 invariant).**

## References
- Report template: `.qwen/skills/references/governance-report-template.md`
- MCP tools: `validate_run_gate`, `list_drift_findings`, `hitl_list`, `get_last_report`, `get_tightening_suggestions`
- Invariants: `.qwen/memory/invariants.md`
