---
name: governance-check
description: Run CHERENKOV's governance certification workflow via MCP tools. Checks spec compliance, HITL queue, drift findings, and validation gate status. Mirrors skills/governance-certification.md.
triggers:
  - "governance"
  - "compliance check"
  - "spec check"
  - "certification"
  - "governance-check"
---

# Skill: governance-check

## Purpose
Perform a full governance snapshot: validation gate, drift findings, HITL queue status, and spec tightening opportunities.
Output is a structured report — **suggest-only, no auto-fixes**.

## Workflow

### Step 1 — Validation Gate
```
[MCP] validate_run_gate → get gate status (PASS/FAIL/WARN)
```

### Step 2 — Drift Findings
```
[MCP] list_drift_findings severity=high → high-severity findings
[MCP] list_drift_findings severity=medium → medium findings
```

### Step 3 — HITL Queue
```
[MCP] hitl_list status=pending → pending human review items
```

### Step 4 — Last Report Summary
```
[MCP] get_last_report → full conformance report
```

### Step 5 — Produce Governance Report
Output a structured markdown report:

```markdown
# Governance Report — <date>

## Validation Gate: PASS / FAIL / WARN
<gate output>

## High-Severity Findings: N
| Finding ID | Endpoint | Method | Description |
|...|

## HITL Queue: N pending
| ID | Description | Created |
|...|

## Spec Tightening Opportunities
<list of suggestions for top 3 endpoints>

## Recommended Actions
1. <action> — <priority>
2. ...

## Status: COMPLIANT / NON-COMPLIANT
```

**This report is suggest-only. No auto-remediation.** (D7 invariant)

## References
- `skills/governance-certification.md` — source CHERENKOV skill
- MCP tools: `validate_run_gate`, `list_drift_findings`, `hitl_list`, `get_last_report`, `get_tightening_suggestions`
- `.qwen/memory/invariants.md` — D7 and spec-derived invariants
