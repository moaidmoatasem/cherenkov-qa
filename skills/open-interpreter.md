---
scope: Open Interpreter Integration
invariants: [D7]
related_contracts: [Track B/C, MCP]
---

# CHERENKOV × Open Interpreter

## Purpose
Use Open Interpreter as a terminal-native AI that drives CHERENKOV conformance checks,
queries drift findings, and explains API violations — all via the MCP tools exposed
by `cherenkov mcp serve`.

## When to Use
- You want to run conformance checks from a conversational terminal agent
- You want to ask in plain English: "what APIs are drifting?" or "explain finding X"
- You want to automate QA workflows with an AI that can write and run code locally

## First-Time Setup

```bash
# Wire CHERENKOV into Open Interpreter's global config
bash scripts/setup_oi.sh

# Restart Open Interpreter — cherenkov tools appear automatically
interpreter
```

Or manually add to `~/.openinterpreter/mcp.json`:
```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "python3",
      "args": ["/path/to/cherenkov-qa/cherenkov.py", "mcp", "serve"],
      "cwd": "/path/to/cherenkov-qa",
      "env": { "MCP_PROFILE": "full-dev" }
    }
  }
}
```

## Key Workflows

### 1. Run a conformance check
```
"Run a cherenkov conformance check against http://localhost:8000"
```
Uses: `run_conformance_check` → triggers `cherenkov validate`, returns passed/failed/drift_count.

### 2. Query drift findings
```
"Show me all high-severity drift findings"
"List drift findings for the /payments endpoint"
```
Uses: `list_drift_findings` with `severity` and `endpoint` filters.

### 3. Explain a finding
```
"Explain finding drift-abc123 in detail"
```
Uses: `explain_finding` → LLM produces what it means, why it matters, how to fix it.

### 4. Get spec-tightening suggestions
```
"What tightening suggestions does cherenkov have for POST /orders?"
```
Uses: `get_tightening_suggestions`

### 5. Approve a HITL item
```
"List pending HITL items, then approve item hitl-xyz"
```
Uses: `hitl_list` then `hitl_approve`

### 6. Check last report without a new run
```
"Show me the last cherenkov conformance report"
```
Uses: `get_last_report`

## Available Tools (via MCP)

| Tool | What to ask for |
|------|----------------|
| `run_conformance_check` | "Run a conformance check against \<url\>" |
| `get_last_report` | "Show last report" |
| `list_drift_findings` | "List drift findings" / "filter by severity: high" |
| `get_tightening_suggestions` | "Tightening suggestions for \<endpoint\>" |
| `explain_finding` | "Explain finding \<id\>" |
| `hitl_list` | "List pending HITL items" |
| `hitl_approve` | "Approve HITL item \<id\>" |
| `hitl_reject` | "Reject HITL item \<id\>" |
| `validate_run_gate` | "Run the validation gate" |
| `chat_explain_divergence` | "Why is \<endpoint\> diverging?" |
| `chat_run_test` | "Plan tests for \<endpoint\>" |

## D7 Invariant
All tools are suggest-only or read-only unless explicitly confirmed. `run_conformance_check`
writes a report to `.cherenkov/report.json` but never auto-edits test code.

## Troubleshooting
- Tools not visible? Restart Open Interpreter after editing `~/.openinterpreter/mcp.json`
- Server won't start? Run `PYTHONPATH=. python3 cherenkov.py mcp serve` in the terminal and check for import errors
- Wrong profile? Set `MCP_PROFILE=full-dev` in the `env` block or `export MCP_PROFILE=full-dev` before launching Open Interpreter
