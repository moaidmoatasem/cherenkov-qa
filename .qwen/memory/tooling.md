# CHERENKOV MCP Tools — Qwen Code Reference

## MCP Server Start
```bash
python3 cherenkov.py mcp serve   # stdio transport (blocks until stdin closed)
```

## Available MCP Tools (from cherenkov-mcp.yaml)

### HITL Queue
| Tool | Args | Side Effects | Notes |
|------|------|-------------|-------|
| `hitl_list` | `status?: "pending"\|"approved"\|"rejected"` | None | Read-only |
| `hitl_approve` | `id: str, reason?: str` | Writes SQLite | Atomic gatekeeper |
| `hitl_reject` | `id: str, reason: str` | Writes SQLite | Atomic gatekeeper |

### Validation & Conformance
| Tool | Args | Side Effects | Notes |
|------|------|-------------|-------|
| `validate_run_gate` | none | None | Report-only (D7 safe) |
| `run_conformance_check` | `url: str, spec?: str` | Triggers test run | Requires execute permission |
| `get_last_report` | none | None | Returns `.cherenkov/report.json` |

### Spec Drift
| Tool | Args | Side Effects | Notes |
|------|------|-------------|-------|
| `list_drift_findings` | `severity?: "high"\|"medium"\|"low"`, `endpoint?: str` | None | Read-only |
| `get_tightening_suggestions` | `endpoint: str, method: str` | None | Returns suggestions only |
| `explain_finding` | `finding_id: str` | None | LLM explanation |

### Chat / Knowledge
| Tool | Args | Side Effects | Notes |
|------|------|-------------|-------|
| `chat_query_verdicts` | `query: str` | None | Reflector query |
| `chat_query_idioms` | `query: str` | None | Pattern query |
| `chat_explain_divergence` | `divergence_id: str` | None | GraphRAG explanation |
| `chat_run_test` | `endpoint: str, method: str` | None | Suggest-only (D7 safe) |

### Governance (planned via qwen_code_mcp.py — Phase 3)
| Tool | Args | Notes |
|------|------|-------|
| `run_qwen_code_agent` | `prompt: str, context?: str` | Delegates to Qwen Code headless |

## MCP Resources (read-only URIs)
- `cherenkov://hitl/pending` — pending HITL queue
- `cherenkov://hitl/item/{id}` — single item detail
- `cherenkov://validate/latest` — latest validation report
- `cherenkov://validate/evidence` — evidence directory listing

## Docker MCP Gateway (alternative to direct stdio)
```bash
docker mcp gateway run --profile full-dev
```
Profiles: `full-dev` (all tools), `ai_coding` (cherenkov + context7), `dev_workflow` (github + atlassian)
