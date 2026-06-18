# Agent Orchestration — CHERENKOV ↔ Qwen Code

## Overview
CHERENKOV uses a multi-agent mesh architecture (ADR-008) for test creation, drift detection, and governance. With the integration of Qwen Code, we establish a strict separation of concerns to prevent agent conflicts and token bloat.

## Separation of Concerns

### CHERENKOV Owns:
- **Test execution & verification** (the Reflector loop)
- **Governance** (HITL, validation gates, D7 enforcement)
- **Knowledge indexing** (GraphRAG, second brain)
- **Event routing** (Event Bus)

### Qwen Code Owns:
- **Code generation & editing** (within D7 bounds)
- **Planning & task decomposition** (SubAgents)
- **Developer UX** (CLI chat, IDE plugins)
- **Tool discovery** (Auto-Skills)

## Handoff Protocol

### Scenario 1: Dev wants to write a new API test
1. Dev runs `qwen` in terminal
2. Dev says "Write a test for the POST /users endpoint"
3. Qwen Code (via MCP) calls `get_last_report` or `get_tightening_suggestions` to find spec expectations.
4. Qwen Code generates the test file as a suggestion.
5. Dev approves. Qwen Code saves file.
6. Dev asks "Verify this runs".
7. Qwen Code (via MCP) calls `run_conformance_check`. CHERENKOV takes over, runs the test, and returns the verdict to Qwen Code.

### Scenario 2: CHERENKOV detects a failure in CI
1. CHERENKOV runs nightly test. A test fails.
2. CHERENKOV's Copilot agent calls `run_qwen_code_agent` (via `tools/qwen_code_mcp.py`) with the prompt: "Analyze this failing test output and suggest a fix. Do not edit."
3. Qwen Code runs headlessly, reads the file, generates a diff, and returns it.
4. CHERENKOV queues the diff in the HITL (Human-in-the-Loop) queue.

## Shared State
- **Memory**: Both agents write to `agent_memory/sync/` (Sync Driven Development). SQLite is the ground truth.
- **Skills**: Kept in sync via `scripts/skill_sync.py`.
- **Token Budget**: Managed jointly via the `agent_sync.py` token tracker.
