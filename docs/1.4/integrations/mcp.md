---
title: MCP Ecosystem
description: CHERENKOV ships a Model Context Protocol server with 41 tools and 6 resources — drive conformance, generation, and certification from any MCP client.
---

# MCP Ecosystem

CHERENKOV ships a full **Model Context Protocol (MCP)** server with **41 tools** and **6 resources**.

## MCP Server

The MCP server speaks **JSON-RPC 2.0 over stdio** — MCP clients spawn the process directly. There is no HTTP port to configure.

```bash
# Start the MCP server (stdio transport)
cherenkov mcp serve
```

## Available Tools (41)

!!! note "Kept in sync with the code"
    This list is the exact tool set the server advertises via `tools/list`, mirrored 1:1 in the repository's [`manifest.json`](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/manifest.json). Both are generated from `cherenkov/mcp/handlers.py` `TOOLS`.

### Conformance & Verification

| Tool | Description |
|------|-------------|
| `run_conformance_check` | Run `cherenkov validate` against a target URL and return the report summary |
| `verify` | Probe a live server against its OpenAPI spec and return spec-drift divergences (`cherenkov verify`) |
| `verify_system` | Probe a live server against its OpenAPI spec; return spec-drift divergences as a VerificationReport |
| `verify_suite` | Run the 6-gate integrity check on an AI-generated test suite and return a VerificationReport |
| `validate_run_gate` | Run the Validation Gate and return a `validate/v1` ValidationReport |
| `check_suite` | Static integrity check of a candidate suite vs. a baseline: catches WEAKENED, DELETED, HALLUCINATED assertions |
| `get_last_report` | Return the most recent `.cherenkov/report.json` without triggering a new run |
| `list_drift_findings` | Return structured spec-drift findings from the last conformance run |
| `get_tightening_suggestions` | Return OpenAPI spec tightening suggestions for a specific endpoint |
| `explain_finding` | Natural-language explanation of a specific drift finding using the LLM |

### Generation & Healing

| Tool | Description |
|------|-------------|
| `generate` | Generate Playwright E2E tests from an OpenAPI spec (`cherenkov generate`) |
| `auto_heal_code` | Generate a suggested code patch for a failed validation item (suggest-only) |

### Test Integrity (IDE feedback)

| Tool | Description |
|------|-------------|
| `cherenkov/audit-test-file` | Audit a test file for integrity issues: weakened assertions, tautological checks, spec mismatches |
| `cherenkov/check-assertion` | Quickly check whether a single test assertion line is strong or weak |
| `cherenkov/suggest-spec-fix` | Given an integrity issue in a test file, suggest a spec-anchored fix |

### HITL Queue

| Tool | Description |
|------|-------------|
| `hitl_list` | List HITL queue items matching the given status |
| `hitl_approve` | Approve a pending HITL item |
| `hitl_reject` | Reject a pending HITL item with reason |

### Chat & Knowledge

| Tool | Description |
|------|-------------|
| `chat_query_verdicts` | Query recent test verdicts from the Reflector |
| `chat_query_idioms` | Query learned idiom patterns from the Reflector |
| `chat_explain_divergence` | Explain a divergence using the Knowledge Mesh GraphRAG |
| `chat_run_test` | Plan test scenarios for a specific endpoint (suggest-only, does not execute) |
| `query_rag_index` | Query the SQLite RAG index for test historical artifacts |

### Visual & Performance

| Tool | Description |
|------|-------------|
| `visual_diff_baseline` | Run visual snapshot regression and UI matching checks |
| `visual_diff_baseline_enhanced` | Comprehensive visual regression with baseline management and configurable thresholds |
| `run_k6_perf` | Run K6 performance load testing and latency analysis |

### Compliance & Governance

| Tool | Description |
|------|-------------|
| `scan_mena_compliance` | Run MENA compliance localization and data residency checks |
| `scan_mena_compliance_enhanced` | Targeted MENA compliance checks (SAMA CCSF / Egypt CBE FinCSF) against a live API |
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
| `policy_list` | List policy allow/block rules from `cherenkov-policy.json` |
| `policy_reload` | Reload `cherenkov-policy.json` from disk without restarting the server |
| `mcp_registry_list` | List all MCP servers registered in the mesh registry |
| `mcp_registry_publish` | Register an external MCP server with the mesh registry |

### Event Bus

| Tool | Description |
|------|-------------|
| `event_bus_list` | Fetch events from the UnifiedEventBus, optionally filtered by category |
| `event_bus_get` | Fetch a single event from the UnifiedEventBus by `event_id` |
| `event_bus_publish` | Publish a CHERENKOVEvent to the UnifiedEventBus for downstream consumers |
| `event_bus_stats` | Return UnifiedEventBus statistics (queue size, sink/source/handler counts, running state) |

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

Add to your MCP client config. The server is stdio, so the client launches it by command:

```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "cherenkov",
      "args": ["mcp", "serve"]
    }
  }
}
```

See [cherenkov-mcp.yaml](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/cherenkov-mcp.yaml) for the full MCP manifest.

---

## Next Steps

- [LangChain Integration](langchain.md) — wrap CHERENKOV as a LangChain tool for agent frameworks
- [CLI Reference](../cli/reference.md) — every command the MCP tools map onto
- [Check Suite (Integrity Audit)](../guides/check-suite.md) — the integrity checks agents call before reporting green
- [Certificates & Compliance](../guides/certificates.md) — issue an independent verdict from any MCP client
