---
scope: MCP Integration
invariants: [D7]
related_contracts: [Track B/C]
---

# MCP Integration Skill

## Purpose
Expose CHERENKOV over the Model Context Protocol (JSON-RPC 2.0 over stdio) so Claude Desktop, Cursor, and other MCP clients can interact with the HITL queue and run the Validation Gate without leaving the IDE.

## When to Use
- You use Claude Desktop, Cursor, or another MCP-compatible IDE
- You want to approve/reject HITL items from within your editor
- You want to run the Validation Gate from an MCP client

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

### Security Model
- All tool arguments validated with Pydantic before reaching the HITL queue
- Writes go through the same atomic SQL gatekeeper as the `hitl approve` CLI command
- Server never reads secrets or env vars from client input
- MCP peers are treated as untrusted

### Claude Desktop Configuration
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

## References
- `cherenkov/mcp/server.py` — MCP server implementation
- `smoke_test_mcp.py` — MCP smoke tests
- `docs/GETTING_STARTED.md` — user-facing MCP docs
