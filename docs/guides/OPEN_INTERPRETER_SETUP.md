# CHERENKOV × Open Interpreter — 5-Minute Setup

> **What you get:** A terminal AI agent that can run API conformance checks, query
> drift findings, explain violations, and approve HITL reviews — all from plain
> English in your terminal.

---

## Prerequisites

| Requirement | Check |
|-------------|-------|
| CHERENKOV installed | `./bin/cherenkov --version` |
| Python 3.10+ | `python3 --version` |
| Open Interpreter | `interpreter --version` (install: `pip install open-interpreter`) |

---

## Step 1 — Wire the MCP Server (one command)

```bash
bash scripts/setup_oi.sh
```

This writes `~/.openinterpreter/mcp.json` with the correct absolute paths for your
machine. If the file already exists, it merges the `cherenkov` entry without touching
your other servers.

**Manual alternative** — if you prefer to edit by hand, add to `~/.openinterpreter/mcp.json`:

```json
{
  "mcpServers": {
    "cherenkov": {
      "command": "python3",
      "args": ["/absolute/path/to/cherenkov-qa/cherenkov.py", "mcp", "serve"],
      "cwd": "/absolute/path/to/cherenkov-qa",
      "env": {
        "MCP_PROFILE": "full-dev"
      }
    }
  }
}
```

---

## Step 2 — Verify (optional but recommended)

```bash
# Start the MCP server manually to confirm it starts cleanly
PYTHONPATH=/path/to/cherenkov-qa python3 /path/to/cherenkov-qa/cherenkov.py mcp serve
# Should print: CHERENKOV MCP server ready (stdio)
# Ctrl-C to exit
```

---

## Step 3 — Launch Open Interpreter

```bash
interpreter
```

On startup, Open Interpreter auto-connects to the cherenkov MCP server. The tools
are immediately available — no further configuration needed.

---

## Example Prompts

### Run a conformance check
```
Run a cherenkov conformance check against http://localhost:8000
```

### Query findings
```
List all high-severity drift findings
Show drift findings for the /payments endpoint
```

### Get an explanation
```
Explain finding drift-abc123 in concise mode
```

### Spec tightening
```
What OpenAPI tightening suggestions does cherenkov have for POST /orders?
```

### HITL review
```
Show me pending HITL items
Approve HITL item hitl-xyz, actor is "alice"
```

### Read last report without a new run
```
Show me the last cherenkov conformance report
```

---

## How It Works

```
┌─────────────────────┐       JSON-RPC 2.0 over stdio
│   Open Interpreter  │ ────────────────────────────► cherenkov mcp serve
│  (your terminal AI) │                               │
└─────────────────────┘                               ▼
                                            ┌──────────────────────┐
                                            │  MCP Handler Layer   │
                                            │  (handlers.py)       │
                                            │  Policy engine       │
                                            │  Pydantic validation │
                                            └──────────┬───────────┘
                                                       │
                              ┌────────────────────────┴─────────────────────┐
                              │                                               │
                    ┌─────────▼──────────┐                     ┌─────────────▼──────┐
                    │  ValidationEngine  │                     │  HitlQueue         │
                    │  run_conformance   │                     │  approve/reject    │
                    │  get_last_report   │                     │  list items        │
                    └────────────────────┘                     └────────────────────┘
```

---

## Available MCP Tools

| Tool | Permission | Description |
|------|-----------|-------------|
| `run_conformance_check` | execute | Trigger `cherenkov validate`, get report summary |
| `get_last_report` | read | Read last `.cherenkov/report.json` |
| `list_drift_findings` | read | Filter findings by severity / endpoint |
| `get_tightening_suggestions` | read | OpenAPI tightening for a specific endpoint |
| `explain_finding` | read | LLM explanation of a finding (concise or detailed) |
| `hitl_list` | read | List HITL queue by status |
| `hitl_approve` | write | Approve a pending HITL item |
| `hitl_reject` | write | Reject a pending HITL item |
| `validate_run_gate` | read | Run Validation Gate (report-only, D7 safe) |
| `chat_explain_divergence` | read | GraphRAG explanation of an endpoint divergence |
| `chat_run_test` | read | Plan test scenarios for an endpoint (suggest-only) |
| `policy_list` / `policy_reload` | admin | View and hot-reload policy |

---

## MCP Profiles

The `MCP_PROFILE` env var controls which tools are available:

| Profile | Who | Tools |
|---------|-----|-------|
| `full-dev` (default) | developers | All 13+ tools |
| `ai_coding` | AI-only sessions | All cherenkov tools, no network egress |

Set in `~/.openinterpreter/mcp.json` → `env.MCP_PROFILE`, or:

```bash
export MCP_PROFILE=full-dev
interpreter
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tools not visible in Open Interpreter | Restart `interpreter` after editing `~/.openinterpreter/mcp.json` |
| `ModuleNotFoundError` on server start | Run `pip install -r requirements.txt` in the repo directory |
| `spec_path must be within working directory` | Ensure `cwd` in the MCP config points to the repo root |
| `Tool blocked by policy` | Check `MCP_PROFILE` — switch to `full-dev` |
| Server exits immediately | Run `python3 cherenkov.py mcp serve` manually to see the error |

For more help: [Troubleshooting](../wiki/Troubleshooting.md) · [GitHub Issues](https://github.com/moaidmoatasem/cherenkov-qa/issues)
