---
title: MCP Ecosystem
---

# MCP Ecosystem

CHERENKOV ships a full **Model Context Protocol (MCP)** server with 14 tools and 3 resources.

## MCP Server

```bash
# Start the MCP server
cherenkov dashboard   # MCP server starts alongside dashboard
# MCP endpoint: http://localhost:8000/mcp
```

## Available Tools (14)

| Tool | Description |
|------|-------------|
| `generate_tests` | Generate Playwright tests from a spec |
| `validate_conformance` | Run conformance check |
| `query_knowledge` | Query the second brain |
| `list_divergences` | List recent divergences |
| `explain_divergence` | Explain a specific divergence |
| `approve_verdict` | Approve an HITL item |
| `reject_verdict` | Reject an HITL item |
| `eject_tests` | Eject tests to vanilla Playwright |
| `get_spec_coverage` | Get endpoint coverage stats |
| `list_idioms` | List learned idioms |
| `memory_search` | Search auto-memory |
| `run_healing` | Get healing suggestions |
| `get_health` | System health check |
| `get_certificate` | Get conformance certificate |

## MCP Resources (3)

| Resource | URI | Description |
|----------|-----|-------------|
| Spec | `cherenkov://spec` | Current loaded OpenAPI spec |
| Verdicts | `cherenkov://verdicts` | Recent verdict database |
| Coverage | `cherenkov://coverage` | Current endpoint coverage map |

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
