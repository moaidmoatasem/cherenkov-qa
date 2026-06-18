# SDD Protocol — Sync Driven Development (Qwen Code Reference)

## What is SDD?
Token-efficient agent protocol that prevents AI amnesia by compounding experience across sessions.  
Runtime: `agent_memory/sync/` (JSON state files + findings log)  
Script: `scripts/agent_sync.py`

## Before Any Work
```bash
python3 scripts/agent_sync.py before --task <task_type>
```
- Loads pre-computed context snippets (saves ~5–10k tokens)
- Sets up session tracking and token budget (default: 50k)

## During Work — Log Decisions & Findings
```bash
python3 scripts/agent_sync.py log --type decision "chose adapter pattern for qwen_code_mcp.py"
python3 scripts/agent_sync.py log --type finding "MCP server requires stdio, not TCP"
python3 scripts/agent_sync.py log --type pitfall "qwen.json model name must match ollama model ID exactly"
python3 scripts/agent_sync.py token --action generate --count 500 --item qwen_code_mcp
```

## After Work
```bash
python3 scripts/agent_sync.py after --summary "built qwen_code_mcp.py adapter, tested MCP round-trip"
```
- Closes session, extracts experience records, updates token history

## Check Status
```bash
python3 scripts/agent_sync.py status
python3 scripts/agent_sync.py experience query "qwen"
```

## Token Budget Rules
- Default: 50k tokens per session
- When >80% used: call `compact` command and continue in a new session
- `qwen.json` has `compact: true` — Qwen Code auto-compacts when context is large

## State Files
| File | Purpose |
|------|---------|
| `agent_memory/sync/session.json` | Active session state |
| `agent_memory/sync/context.json` | Pre-computed context snippets |
| `agent_memory/sync/experience.json` | Past session experience records |
| `agent_memory/sync/tokens.json` | Token usage history |
| `agent_memory/sync/findings/` | Individual finding files |

## Qwen Code ↔ SDD Integration (Phase 2)
Qwen Code sessions are also logged here via:
```bash
python3 scripts/agent_sync.py before --task code-generation --source qwen-code
```
Both CHERENKOV and Qwen Code sessions write to the same `agent_memory/sync/` store.
