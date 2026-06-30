---
name: mcp-integration
description: "Expose CHERENKOV over MCP (JSON-RPC 2.0 stdio) for Claude Desktop, Cursor, and Open Interpreter."
scope: MCP Integration
invariants: [D7]
related_contracts: [Track B/C]
---

# MCP Integration Skill

## Purpose
Expose CHERENKOV over the Model Context Protocol (JSON-RPC 2.0 over stdio) so Claude Desktop, Cursor, Open Interpreter, and other MCP clients can query conformance results, trigger new runs, explain findings, and interact with the HITL queue — all without leaving the editor.

## When to Use
- You use Claude Desktop, Cursor, Open Interpreter, or another MCP-compatible agent
- You want to approve/reject HITL items from within your editor
- You want to run conformance checks, query drift findings, or get spec tightening suggestions from an MCP client

## Workflow

### Server (`cherenkov/mcp/server.py`)

```bash
./bin/cherenkov mcp serve
```

Blocks until stdin closes. Communicates via JSON-RPC 2.0 over stdio.

### Resources (read-only)
| URI | Description |
|-----|-------------|
| `cherenkov://hitl/pending` | Pending HITL items (`hitl/v1` envelope) |
| `cherenkov://hitl/item/{id}` | Single HITL item detail |
| `cherenkov://validate/latest` | Latest `validate/v1` ValidationReport |
| `cherenkov://validate/evidence` | Evidence directory listing |

### Tools
| Tool | Description |
|------|-------------|
| `hitl_list` | List HITL queue items by status |
| `hitl_approve` | Approve a pending item (atomic SQL gatekeeper) |
| `hitl_reject` | Reject a pending item (atomic SQL gatekeeper) |
| `validate_run_gate` | Run the Validation Gate in report-only mode (suggest-only, D7 honored) |
| `run_conformance_check` | Trigger `cherenkov validate` against a target URL; returns report summary (requires execute permission) |
| `get_last_report` | Return `.cherenkov/report.json` without triggering a new run |
| `list_drift_findings` | List spec-drift findings; filter by `severity` (high/medium/low) and `endpoint` |
| `get_tightening_suggestions` | Return OpenAPI spec tightening suggestions for a given endpoint + method |
| `explain_finding` | Natural-language LLM explanation of a specific finding by ID |
| `chat_query_verdicts` | Query recent test verdicts from the Reflector |
| `chat_query_idioms` | Query learned test idiom patterns |
| `chat_explain_divergence` | Explain a divergence via the Knowledge Mesh GraphRAG |
| `chat_run_test` | Plan test scenarios for an endpoint (suggest-only) |

### Security Model
- All tool arguments validated with Pydantic before reaching the HITL queue
- Writes go through the same atomic SQL gatekeeper as the `hitl approve` CLI command
- Server never reads secrets or env vars from client input
- MCP peers are treated as untrusted

### Client Configurations

#### Claude Desktop
Add to `claude_desktop_config.json → mcpServers`:
```json
{
  "cherenkov": {
    "command": "python3",
    "args": ["/path/to/cherenkov-qa/cherenkov.py", "mcp", "serve"],
    "cwd": "/path/to/cherenkov-qa"
  }
}
```

#### Open Interpreter
Add to `~/.openinterpreter/mcp.json`:
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
Restart Open Interpreter after adding the config. Cherenkov tools appear automatically in the tool list.

#### Cursor / VS Code
Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "python3",
      "args": ["cherenkov.py", "mcp", "serve"],
      "cwd": "/path/to/cherenkov-qa"
    }
  }
}
```

### Docker MCP Gateway Integration

The project supports the [Docker MCP Gateway](https://github.com/docker/mcp-gateway) (Docker Desktop 4.59+). It runs containerized MCP servers and provides a unified gateway endpoint for all AI clients.

#### Available Profiles

| Profile | Servers | Tools | Auth Required |
|---------|---------|-------|---------------|
| **full-dev** (recommended) | cherenkov, context7, sequentialthinking, github-official, atlassian-remote | ~48 (see below) | GitHub PAT + Atlassian OAuth |
| **ai_coding** | cherenkov, context7, sequentialthinking | 7 | None |
| **dev_workflow** | github-official, atlassian-remote | ~41 | GitHub PAT + Atlassian OAuth |

**Full-dev tool counts:**
| Server | Tools | Notes |
|--------|-------|-------|
| cherenkov | 13 tools + 5 resources | `hitl_list`, `hitl_approve`, `hitl_reject`, `validate_run_gate`, `run_conformance_check`, `get_last_report`, `list_drift_findings`, `get_tightening_suggestions`, `explain_finding`, `chat_*` (×4), `policy_*` (×2) |
| context7 | 2 | `resolve-library-id`, `get-library-docs` |
| sequentialthinking | 1 | Structured problem-solving |
| github-official | 41 + 2 prompts + 5 resource templates | Issue/PR/repo management (requires PAT) |
| atlassian-remote | remote SSE | Jira/Confluence (requires OAuth) |

#### Setup (already configured on this machine)

The gateway is configured system-wide. All listed clients connect automatically on next launch:

```bash
docker mcp client connect opencode --profile full-dev --global
```

This writes a config entry to `%USERPROFILE%\.config\opencode\opencode.json` that launches `docker mcp gateway run --profile full-dev` as an opencode MCP subprocess.

#### Authenticating GitHub and Atlassian

```bash
# Configure GitHub Personal Access Token
docker mcp secret set github.personal_access_token

# Authorize Atlassian (opens browser for OAuth)
docker mcp oauth authorize atlassian-remote
```

#### Adding CHERENKOV to Another Profile

```bash
docker mcp profile server add dev-workflow --server file:///home/moaid/cherenkov-qa/cherenkov-mcp.yaml
```

The YAML definition at `cherenkov-mcp.yaml` references the `cherenkov-mcp:latest` Docker image built from `Dockerfile.mcp`.

## References
- `cherenkov/mcp/server.py` — MCP server implementation
- `smoke_test_mcp.py` — MCP smoke tests
- `docs/GETTING_STARTED.md` — user-facing MCP docs
- `Dockerfile.mcp` — Slim MCP server Docker image
- `cherenkov-mcp.yaml` — MCP server entry spec for gateway profiles
- `docs/vision/12_DOCKER_AI_HORIZON.md` — Strategic Docker AI integration plan (sandboxes, governance, model runner, Compose agents)
