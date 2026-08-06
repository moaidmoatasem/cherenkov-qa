---
title: MCP Ecosystem
---

# MCP Ecosystem

CHERENKOV ships a full **Model Context Protocol (MCP)** server with **37 tools** and **6 resources**.

## MCP Server

```bash
# Start the MCP server (runs alongside dashboard)
cherenkov dashboard
# MCP endpoint: http://localhost:8000/mcp
```

## Available Tools (37)

### HITL Queue

| Tool | Description |
|------|-------------|
| `hitl_list` | List HITL queue items matching the given status |
| `hitl_approve` | Approve a pending HITL item |
| `hitl_reject` | Reject a pending HITL item with reason |

### Verification

| Tool | Description |
|------|-------------|
| `verify_suite` | Run the 6-gate integrity check on an AI-generated test suite |
| `verify_system` | Probe a live server against its OpenAPI spec for spec-drift divergences |
| `validate_run_gate` | Run the Validation Gate and return a validation report |

### Chat & Knowledge

| Tool | Description |
|------|-------------|
| `chat_query_verdicts` | Query recent test verdicts from the Reflector |
| `chat_query_idioms` | Query learned idiom patterns from the Reflector |
| `chat_explain_divergence` | Explain a divergence using the Knowledge Mesh GraphRAG |
| `chat_run_test` | Plan test scenarios for a specific endpoint (suggest-only) |
| `query_rag_index` | Query the SQLite RAG index for test historical artifacts |

### Conformance

| Tool | Description |
|------|-------------|
| `run_conformance_check` | Run cherenkov validate against a target URL and return the report summary |
| `get_last_report` | Return the most recent report without triggering a new run |
| `list_drift_findings` | Return structured spec-drift findings from the last conformance run |
| `get_tightening_suggestions` | Return spec tightening suggestions for a specific endpoint |
| `explain_finding` | Natural-language explanation of a specific drift finding |

### Visual & Performance

| Tool | Description |
|------|-------------|
| `visual_diff_baseline` | Run visual snapshot regression and UI matching checks |
| `visual_diff_baseline_enhanced` | Enhanced visual diff with baseline management and configurable thresholds |
| `run_k6_perf` | Run K6 performance load testing and latency analysis |

### Compliance & Governance

| Tool | Description |
|------|-------------|
| `scan_mena_compliance` | Run MENA compliance localization and data residency checks |
| `scan_mena_compliance_enhanced` | Targeted MENA compliance checks (SAMA CCSF / Egypt CBE FinCSF) |
| `validate_governance_certification` | Validate a governance certification ID against quality standards |
| `report_compliance_findings` | Return structured compliance findings, filterable by severity/endpoint |

### Export & Issue Tracking

| Tool | Description |
|------|-------------|
| `export_jira_ticket` | Suggest-only Jira export for failed validation items |
| `export_linear_ticket` | Suggest-only Linear export for failed validation items |
| `export_github_ticket` | Suggest-only GitHub issue export for failed validation items |

### Policy & Registry

| Tool | Description |
|------|-------------|
| `policy_list` | List policy allow/block rules from cherenkov-policy.json |
| `policy_reload` | Reload cherenkov-policy.json without restarting |
| `mcp_registry_list` | List all MCP servers registered in the mesh registry |
| `mcp_registry_publish` | Register an external MCP server with the mesh registry |

### Pipeline (Agent-Invokable)

| Tool | Description |
|------|-------------|
| `run_check_suite` | Run a check-suite integrity check on a candidate test suite against its spec |
| `run_verify` | Run spec-derived probe planning and verification against a live server |
| `run_generate` | Generate Playwright tests from an OpenAPI spec via the local LLM |
| `get_health_score` | Return an A-F health grade for the API under test |
| `get_coverage_report` | Return endpoint-level coverage data from the last verification run |
| `run_guardian_scan` | Trigger a single Guardian scan against a live server |

### Healing

| Tool | Description |
|------|-------------|
| `auto_heal_code` | Generate a suggested code patch for a failed validation item (suggest-only) |

## MCP Resources (6)

| Resource | URI | Description |
|----------|-----|-------------|
| HITL Pending Queue | `cherenkov://hitl/pending` | List of HITL items awaiting human review |
| HITL Item Detail | `cherenkov://hitl/item/{id}` | Single HITL item by ID |
| Latest Validation Report | `cherenkov://validate/latest` | Most recent validation report from the Validation Gate |
| Validation Evidence | `cherenkov://validate/evidence` | Evidence files captured by the Validation Gate |
| Active Chat Sessions | `cherenkov://chat/sessions` | List of active chat sessions |
| Integrity Gates | `cherenkov://gates` | Machine-readable description of the 6 REVIEW gates |

## Use with Claude Desktop / Cursor

Add to your MCP client config:

```json
{
  "mcpServers": {
    "cherenkov": {
      "url": "http://localhost:8000/mcp",
      "transport": "http"
    }
  }
}
```

See [cherenkov-mcp.yaml](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/cherenkov-mcp.yaml) for the full MCP manifest.
