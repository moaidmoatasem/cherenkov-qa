# @cherenkov-qa/mcp-server

MCP server wrapper for [CHERENKOV QA](https://github.com/moaidmoatasem/cherenkov-qa).

Exposes CHERENKOV conformance, drift, HITL, performance, and compliance tools to any MCP-compatible client (Claude Desktop, Cursor, Windsurf, etc.).

## Install

```bash
npm install -g @cherenkov-qa/mcp-server
```

## Usage

```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "npx",
      "args": ["@cherenkov-qa/mcp-server"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

## Requirements

- Node.js 18+
- Python 3.10+
- CHERENKOV Python package installed (`pip install cherenkov-qa`) or run from a clone of the repo

## Tools

- `run_conformance_check` — validate a target API against its spec
- `run_k6_perf` — run K6 load tests
- `export_jira_ticket` — create a Jira ticket for a drift finding
- `scan_mena_compliance` — SAMA / FinCSF compliance checks
- `explain_finding` — natural-language explanation of a divergence
- ...and more from the full CHERENKOV MCP catalog.
