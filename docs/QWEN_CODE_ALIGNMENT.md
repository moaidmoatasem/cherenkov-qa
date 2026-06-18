# Qwen Code × CHERENKOV Alignment Guide

This document outlines the integration between Qwen Code (developer/coding agent) and CHERENKOV QA (test/governance agent).

## Division of Labor
- **Qwen Code**: Writes code, generates test skeletons, performs code reviews, automates CLI tasks.
- **CHERENKOV**: Runs tests against OpenAPI specs, enforces D7 (never auto-edit tests), manages HITL queue, and provides GraphRAG knowledge.

## Quick Start
1. Ensure Node.js 22+ and Ollama are installed.
2. Run `bash scripts/qwen-code-integration.sh`
   - This starts the CHERENKOV MCP server in the background.
   - Launches the interactive Qwen Code UI.

## Key Integration Points

### 1. MCP Bridge
Qwen Code communicates with CHERENKOV via the Model Context Protocol (MCP). The configuration is in `qwen.json`.
CHERENKOV tools available to Qwen Code:
- `validate_run_gate`
- `get_last_report`
- `get_tightening_suggestions`
- `hitl_list`
*(See `cherenkov-mcp.yaml` for the full list of 18+ tools).*

CHERENKOV can also call Qwen Code via the `run_qwen_code_agent` MCP tool.

### 2. Auto-Memory and Skills
- Qwen Code loads its memory from `.qwen/memory/` (architecture, invariants).
- Qwen Code loads CHERENKOV-tuned skills from `.qwen/skills/`.
- We use `scripts/memory_sync.py` and `scripts/skill_sync.py` to keep Qwen Code's state harmonized with CHERENKOV's internal SQLite/Redis knowledge base.

### 3. Sync Driven Development (SDD)
All Qwen Code sessions are logged to `agent_memory/sync/` just like CHERENKOV sessions.
Run `python3 scripts/agent_sync.py before --task code-review --source qwen-code` before starting a Qwen Code session to ensure correct tagging.
Use `agent_sync.py status` to view combined token usage and experience records.

## Design Invariants
When using Qwen Code, the D7 invariant still applies: **Never auto-edit test code.**
Always use `approvalMode: manual` in Qwen Code. Do not use `/edit` on test files.

## Further Reading
- `docs/agent-orchestration.md` — Detailed handoff protocol between the agents.
- `.qwen/subagent-per-spec.md` — Scaling test generation via SubAgents.
